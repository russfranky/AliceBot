from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass, field
from datetime import datetime
import io
import json
from pathlib import Path
from typing import Any, Protocol, cast

from alicebot_api.telegram_channels import normalize_telegram_update
from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService, VNextCaptureStore
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


class VNextConnectorValidationError(ValueError):
    """Raised when a connector payload cannot be normalized safely."""


class VNextConnectorStore(VNextCaptureStore, Protocol):
    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class ConnectorDefinition:
    name: str
    display_name: str
    phase: str
    source_type: str
    default_domain: str
    default_sensitivity: str
    raw_evidence_kind: str
    cursor_field: str
    description: str

    def to_record(self) -> JsonObject:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "phase": self.phase,
            "source_type": self.source_type,
            "default_domain": self.default_domain,
            "default_sensitivity": self.default_sensitivity,
            "raw_evidence_kind": self.raw_evidence_kind,
            "cursor_field": self.cursor_field,
            "description": self.description,
            "supports_default_domain": True,
            "supports_default_sensitivity": True,
            "supports_sync_cursor": True,
            "preserves_raw_evidence": True,
        }


@dataclass(frozen=True, slots=True)
class NormalizedConnectorItem:
    connector_name: str
    source_type: str
    external_id: str
    cursor: str
    raw_text: str
    title: str
    author: str | None = None
    uri: str | None = None
    raw_path: str | None = None
    source_created_at: str | None = None
    source_modified_at: str | None = None
    metadata_json: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectorSyncResult:
    status: str
    connector_name: str
    item_count: int
    imported_count: int
    duplicate_count: int
    skipped_count: int
    failed_count: int
    previous_cursor: str | None
    sync_cursor: str | None
    source_ids: tuple[str, ...] = ()
    failed_external_ids: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_record(self) -> JsonObject:
        return {
            "status": self.status,
            "connector_name": self.connector_name,
            "item_count": self.item_count,
            "imported_count": self.imported_count,
            "duplicate_count": self.duplicate_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "previous_cursor": self.previous_cursor,
            "sync_cursor": self.sync_cursor,
            "source_ids": list(self.source_ids),
            "failed_external_ids": list(self.failed_external_ids),
            "errors": list(self.errors),
        }


SUPPORTED_CONNECTORS: tuple[ConnectorDefinition, ...] = (
    ConnectorDefinition(
        name="telegram",
        display_name="Telegram capture",
        phase="phase_2",
        source_type="telegram_message",
        default_domain="personal",
        default_sensitivity="private",
        raw_evidence_kind="telegram_webhook_json",
        cursor_field="provider_update_id",
        description="Captures already-received Telegram webhook payloads into raw source evidence.",
    ),
    ConnectorDefinition(
        name="browser_clipper",
        display_name="Browser clipper",
        phase="phase_2",
        source_type="browser_clip",
        default_domain="learning",
        default_sensitivity="private",
        raw_evidence_kind="browser_clip_json",
        cursor_field="captured_at_or_external_id",
        description="Captures clipped page text, URL, selection, and optional HTML snapshots.",
    ),
    ConnectorDefinition(
        name="pdf_document",
        display_name="PDF processing",
        phase="phase_2",
        source_type="pdf_document",
        default_domain="unknown",
        default_sensitivity="private",
        raw_evidence_kind="extracted_pdf_text",
        cursor_field="source_modified_at_or_external_id",
        description="Archives extracted PDF text and file metadata as reviewable source evidence.",
    ),
    ConnectorDefinition(
        name="docx_document",
        display_name="DOCX processing",
        phase="phase_2",
        source_type="docx_document",
        default_domain="unknown",
        default_sensitivity="private",
        raw_evidence_kind="extracted_docx_text",
        cursor_field="source_modified_at_or_external_id",
        description="Archives extracted DOCX text and file metadata as reviewable source evidence.",
    ),
    ConnectorDefinition(
        name="csv_table",
        display_name="CSV processing",
        phase="phase_2",
        source_type="csv_table",
        default_domain="professional",
        default_sensitivity="private",
        raw_evidence_kind="csv_rows_or_text",
        cursor_field="source_modified_at_or_external_id",
        description="Normalizes CSV text or rows into deterministic source text with raw row evidence.",
    ),
    ConnectorDefinition(
        name="screenshot_ocr",
        display_name="Screenshot processing",
        phase="phase_2",
        source_type="screenshot_ocr",
        default_domain="unknown",
        default_sensitivity="private",
        raw_evidence_kind="ocr_text",
        cursor_field="captured_at_or_external_id",
        description="Archives OCR output from screenshots with conservative privacy defaults.",
    ),
    ConnectorDefinition(
        name="voice_transcription",
        display_name="Voice transcription",
        phase="phase_2",
        source_type="voice_transcript",
        default_domain="personal",
        default_sensitivity="private",
        raw_evidence_kind="transcript_segments",
        cursor_field="recorded_at_or_external_id",
        description="Captures transcript text and segment metadata from a configured transcription pipeline.",
    ),
)

_CONNECTOR_BY_NAME = {definition.name: definition for definition in SUPPORTED_CONNECTORS}
_VALID_DOMAINS = frozenset(
    {
        "professional",
        "personal",
        "family",
        "health",
        "spiritual",
        "financial",
        "legal",
        "learning",
        "relationship",
        "project",
        "agent_run",
        "system",
        "unknown",
    }
)
_VALID_SENSITIVITIES = frozenset(
    {
        "public",
        "internal",
        "private",
        "confidential",
        "highly_sensitive",
        "sacred",
        "regulated",
        "unknown",
    }
)


def list_connector_definitions() -> tuple[ConnectorDefinition, ...]:
    return SUPPORTED_CONNECTORS


def get_connector_definition(connector_name: str) -> ConnectorDefinition:
    normalized = connector_name.strip().casefold()
    definition = _CONNECTOR_BY_NAME.get(normalized)
    if definition is None:
        raise VNextConnectorValidationError(f"unknown vNext connector: {connector_name}")
    return definition


def _as_json_object(value: object, *, label: str) -> JsonObject:
    if not isinstance(value, dict):
        raise VNextConnectorValidationError(f"{label} must be a JSON object")
    return cast(JsonObject, value)


def _as_optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _required_text(payload: Mapping[str, object], keys: Sequence[str], *, connector_name: str) -> str:
    for key in keys:
        value = _as_optional_text(payload.get(key))
        if value is not None:
            return value
    joined = ", ".join(keys)
    raise VNextConnectorValidationError(f"{connector_name} item requires one of: {joined}")


def _first_text(payload: Mapping[str, object], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = _as_optional_text(payload.get(key))
        if value is not None:
            return value
    return None


def _optional_iso(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _external_id(payload: Mapping[str, object], *, fallback: str) -> str:
    value = _first_text(payload, ("external_id", "id", "message_id", "filename", "path", "url"))
    return value or fallback


def _cursor_value(payload: Mapping[str, object], *, external_id: str, keys: Sequence[str]) -> str:
    value = _first_text(payload, keys)
    return value or external_id


def _cursor_lte(left: str, right: str | None) -> bool:
    if right is None:
        return False
    if left.isdecimal() and right.isdecimal():
        return int(left) <= int(right)
    return left <= right


def _cursor_sort_key(cursor: str) -> tuple[int, int | str]:
    if cursor.isdecimal():
        return (0, int(cursor))
    return (1, cursor)


def _csv_rows_to_text(rows: object) -> str | None:
    if not isinstance(rows, list) or len(rows) == 0:
        return None

    output = io.StringIO()
    first_row = rows[0]
    if isinstance(first_row, dict):
        fieldnames: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                raise VNextConnectorValidationError("csv_table rows must all be objects or all be arrays")
            for key in row:
                if isinstance(key, str) and key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cast(Mapping[str, object], row).get(key, "") for key in fieldnames})
        return output.getvalue().strip()

    writer = csv.writer(output)
    for row in rows:
        if not isinstance(row, list):
            raise VNextConnectorValidationError("csv_table rows must all be objects or all be arrays")
        writer.writerow(row)
    return output.getvalue().strip()


def _normalize_telegram_item(payload: JsonObject) -> NormalizedConnectorItem:
    normalized = normalize_telegram_update(cast(dict[str, Any], payload), bot_username=None)
    text = normalized["message_text"].strip()
    if text == "":
        raise VNextConnectorValidationError("telegram item requires non-empty message text")
    external_id = f"{normalized['external_chat_id']}:{normalized['provider_message_id']}"
    cursor = normalized["provider_update_id"]
    username = normalized.get("external_username")
    author = f"@{username}" if username else normalized["external_user_id"]
    return NormalizedConnectorItem(
        connector_name="telegram",
        source_type="telegram_message",
        external_id=external_id,
        cursor=cursor,
        raw_text=text,
        title=f"Telegram message {normalized['provider_message_id']}",
        author=author,
        source_created_at=_optional_iso(normalized["sent_at"]),
        metadata_json={
            "raw_payload": payload,
            "normalized_payload": cast(JsonObject, normalized["normalized_payload"]),
            "provider_update_id": normalized["provider_update_id"],
            "provider_message_id": normalized["provider_message_id"],
            "external_chat_id": normalized["external_chat_id"],
            "idempotency_key": normalized["idempotency_key"],
            "raw_evidence_preserved": True,
        },
    )


def _normalize_browser_clip_item(payload: JsonObject) -> NormalizedConnectorItem:
    text = _required_text(payload, ("text", "selection", "markdown", "excerpt"), connector_name="browser_clipper")
    url = _as_optional_text(payload.get("url"))
    title = _first_text(payload, ("title", "page_title")) or "Browser clip"
    external_id = _external_id(payload, fallback=url or title)
    captured_at = _optional_iso(payload.get("captured_at"))
    cursor = _cursor_value(payload, external_id=external_id, keys=("cursor", "captured_at", "source_modified_at"))
    return NormalizedConnectorItem(
        connector_name="browser_clipper",
        source_type="browser_clip",
        external_id=external_id,
        cursor=cursor,
        raw_text=text,
        title=title,
        uri=url,
        source_created_at=captured_at,
        metadata_json={
            "raw_payload": payload,
            "selection": _as_optional_text(payload.get("selection")),
            "html": _as_optional_text(payload.get("html")),
            "raw_evidence_preserved": True,
        },
    )


def _normalize_document_item(connector_name: str, source_type: str, payload: JsonObject) -> NormalizedConnectorItem:
    text = _required_text(payload, ("text", "extracted_text", "content"), connector_name=connector_name)
    filename = _first_text(payload, ("filename", "name", "path")) or f"{connector_name} item"
    external_id = _external_id(payload, fallback=filename)
    cursor = _cursor_value(
        payload,
        external_id=external_id,
        keys=("cursor", "source_modified_at", "modified_at", "source_created_at", "created_at"),
    )
    return NormalizedConnectorItem(
        connector_name=connector_name,
        source_type=source_type,
        external_id=external_id,
        cursor=cursor,
        raw_text=text,
        title=filename,
        raw_path=_as_optional_text(payload.get("path")),
        source_created_at=_optional_iso(payload.get("source_created_at") or payload.get("created_at")),
        source_modified_at=_optional_iso(payload.get("source_modified_at") or payload.get("modified_at")),
        metadata_json={
            "raw_payload": payload,
            "filename": filename,
            "raw_evidence_preserved": True,
        },
    )


def _normalize_csv_item(payload: JsonObject) -> NormalizedConnectorItem:
    csv_text = _first_text(payload, ("csv_text", "text", "content"))
    if csv_text is None:
        csv_text = _csv_rows_to_text(payload.get("rows"))
    if csv_text is None or csv_text.strip() == "":
        raise VNextConnectorValidationError("csv_table item requires csv_text or non-empty rows")

    filename = _first_text(payload, ("filename", "name", "path")) or "CSV table"
    external_id = _external_id(payload, fallback=filename)
    cursor = _cursor_value(
        payload,
        external_id=external_id,
        keys=("cursor", "source_modified_at", "modified_at", "source_created_at", "created_at"),
    )
    return NormalizedConnectorItem(
        connector_name="csv_table",
        source_type="csv_table",
        external_id=external_id,
        cursor=cursor,
        raw_text=csv_text,
        title=filename,
        raw_path=_as_optional_text(payload.get("path")),
        source_created_at=_optional_iso(payload.get("source_created_at") or payload.get("created_at")),
        source_modified_at=_optional_iso(payload.get("source_modified_at") or payload.get("modified_at")),
        metadata_json={
            "raw_payload": payload,
            "row_count": len(cast(list[object], payload.get("rows"))) if isinstance(payload.get("rows"), list) else None,
            "raw_evidence_preserved": True,
        },
    )


def _normalize_screenshot_item(payload: JsonObject) -> NormalizedConnectorItem:
    text = _required_text(payload, ("ocr_text", "text", "extracted_text"), connector_name="screenshot_ocr")
    filename = _first_text(payload, ("filename", "name", "path")) or "Screenshot OCR"
    external_id = _external_id(payload, fallback=filename)
    captured_at = _optional_iso(payload.get("captured_at") or payload.get("source_created_at"))
    cursor = _cursor_value(payload, external_id=external_id, keys=("cursor", "captured_at", "source_created_at"))
    return NormalizedConnectorItem(
        connector_name="screenshot_ocr",
        source_type="screenshot_ocr",
        external_id=external_id,
        cursor=cursor,
        raw_text=text,
        title=filename,
        raw_path=_as_optional_text(payload.get("path")),
        source_created_at=captured_at,
        metadata_json={
            "raw_payload": payload,
            "image_hash": _as_optional_text(payload.get("image_hash")),
            "raw_evidence_preserved": True,
        },
    )


def _transcript_segments_to_text(segments: object) -> str | None:
    if not isinstance(segments, list):
        return None
    lines: list[str] = []
    for segment in segments:
        if isinstance(segment, str):
            stripped = segment.strip()
            if stripped:
                lines.append(stripped)
            continue
        if isinstance(segment, dict):
            text = _as_optional_text(segment.get("text"))
            if text is None:
                continue
            speaker = _as_optional_text(segment.get("speaker"))
            prefix = f"{speaker}: " if speaker else ""
            lines.append(f"{prefix}{text}")
    return "\n".join(lines) if lines else None


def _normalize_voice_item(payload: JsonObject) -> NormalizedConnectorItem:
    transcript = _first_text(payload, ("transcript", "text", "content"))
    if transcript is None:
        transcript = _transcript_segments_to_text(payload.get("segments"))
    if transcript is None or transcript.strip() == "":
        raise VNextConnectorValidationError("voice_transcription item requires transcript text or segments")

    title = _first_text(payload, ("title", "filename", "name", "path")) or "Voice transcript"
    external_id = _external_id(payload, fallback=title)
    recorded_at = _optional_iso(payload.get("recorded_at") or payload.get("source_created_at"))
    cursor = _cursor_value(payload, external_id=external_id, keys=("cursor", "recorded_at", "source_created_at"))
    return NormalizedConnectorItem(
        connector_name="voice_transcription",
        source_type="voice_transcript",
        external_id=external_id,
        cursor=cursor,
        raw_text=transcript,
        title=title,
        raw_path=_as_optional_text(payload.get("path")),
        source_created_at=recorded_at,
        metadata_json={
            "raw_payload": payload,
            "segments": payload.get("segments") if isinstance(payload.get("segments"), list) else None,
            "transcription_provider": _as_optional_text(payload.get("transcription_provider")),
            "raw_evidence_preserved": True,
        },
    )


def normalize_connector_item(connector_name: str, payload: Mapping[str, object]) -> NormalizedConnectorItem:
    definition = get_connector_definition(connector_name)
    item = _as_json_object(dict(payload), label=f"{definition.name} item")
    if definition.name == "telegram":
        return _normalize_telegram_item(item)
    if definition.name == "browser_clipper":
        return _normalize_browser_clip_item(item)
    if definition.name == "pdf_document":
        return _normalize_document_item("pdf_document", "pdf_document", item)
    if definition.name == "docx_document":
        return _normalize_document_item("docx_document", "docx_document", item)
    if definition.name == "csv_table":
        return _normalize_csv_item(item)
    if definition.name == "screenshot_ocr":
        return _normalize_screenshot_item(item)
    if definition.name == "voice_transcription":
        return _normalize_voice_item(item)
    raise VNextConnectorValidationError(f"unknown vNext connector: {connector_name}")


def load_connector_items_from_file(path: str | Path) -> list[JsonObject]:
    payload_path = Path(path).expanduser().resolve()
    if payload_path.suffix.casefold() == ".csv":
        return [
            {
                "filename": payload_path.name,
                "path": str(payload_path),
                "external_id": str(payload_path),
                "source_modified_at": datetime.fromtimestamp(payload_path.stat().st_mtime).isoformat(),
                "csv_text": payload_path.read_text(encoding="utf-8"),
            }
        ]

    loaded = json.loads(payload_path.read_text(encoding="utf-8"))
    if isinstance(loaded, list):
        values = loaded
    elif isinstance(loaded, dict) and isinstance(loaded.get("items"), list):
        values = cast(list[object], loaded["items"])
    elif isinstance(loaded, dict):
        values = [loaded]
    else:
        raise VNextConnectorValidationError("connector payload file must contain an object, item array, or items array")

    items: list[JsonObject] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise VNextConnectorValidationError(f"connector payload item {index} must be an object")
        items.append(cast(JsonObject, value))
    return items


class VNextConnectorService:
    def __init__(self, store: VNextConnectorStore) -> None:
        self.store = store
        self.capture_service = VNextCaptureService(store)

    def list_settings(self) -> JsonObject:
        return {
            "items": [definition.to_record() for definition in list_connector_definitions()],
            "count": len(SUPPORTED_CONNECTORS),
            "order": [definition.name for definition in SUPPORTED_CONNECTORS],
        }

    def get_cursor(self, connector_name: str) -> str | None:
        definition = get_connector_definition(connector_name)
        events = [
            event
            for event in self.store.list_events(target_type="connector", target_id=definition.name)
            if event.get("event_type") == "connector.sync_completed"
        ]
        events.sort(key=lambda event: str(event.get("occurred_at") or ""), reverse=True)
        for event in events:
            payload = event.get("payload_json")
            if not isinstance(payload, dict):
                continue
            cursor = _as_optional_text(payload.get("sync_cursor"))
            if cursor is not None:
                return cursor
        return None

    def _log_event(
        self,
        *,
        event_type: str,
        connector_name: str,
        payload: JsonObject,
    ) -> JsonObject:
        return append_event(
            self.store,
            event_type=event_type,
            actor_type="system",
            target_type="connector",
            target_id=connector_name,
            payload=payload,
        )

    def sync_items(
        self,
        connector_name: str,
        items: Sequence[Mapping[str, object]],
        *,
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
    ) -> ConnectorSyncResult:
        definition = get_connector_definition(connector_name)
        domain = default_domain or definition.default_domain
        sensitivity = default_sensitivity or definition.default_sensitivity
        if domain not in _VALID_DOMAINS:
            raise VNextConnectorValidationError(f"invalid connector default domain: {domain}")
        if sensitivity not in _VALID_SENSITIVITIES:
            raise VNextConnectorValidationError(f"invalid connector default sensitivity: {sensitivity}")

        previous_cursor = self.get_cursor(definition.name)
        self._log_event(
            event_type="connector.sync_started",
            connector_name=definition.name,
            payload={
                "connector_name": definition.name,
                "item_count": len(items),
                "previous_cursor": previous_cursor,
                "default_domain": domain,
                "default_sensitivity": sensitivity,
            },
        )

        normalized_items: list[NormalizedConnectorItem] = []
        source_ids: list[str] = []
        errors: list[str] = []
        failed_external_ids: list[str] = []
        imported_count = 0
        duplicate_count = 0
        skipped_count = 0
        failed_count = 0
        sync_cursor = previous_cursor
        failure_blocked_cursor_advance = False

        for index, item in enumerate(items):
            try:
                normalized_items.append(normalize_connector_item(definition.name, item))
            except Exception as exc:
                failed_count += 1
                external_id = _first_text(item, ("external_id", "id", "filename", "path", "url")) or f"item-{index}"
                failed_external_ids.append(external_id)
                errors.append(f"{external_id}: {exc}")
                failure_blocked_cursor_advance = True
                self._log_event(
                    event_type="connector.item_failed",
                    connector_name=definition.name,
                    payload={
                        "connector_name": definition.name,
                        "external_id": external_id,
                        "sync_cursor": None,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )

        normalized_items.sort(key=lambda item: _cursor_sort_key(item.cursor))

        for item in normalized_items:
            if _cursor_lte(item.cursor, previous_cursor):
                skipped_count += 1
                continue

            try:
                result = self.capture_service.capture_source(
                    SourceCaptureInput(
                        source_type=item.source_type,
                        title=item.title,
                        author=item.author,
                        uri=item.uri,
                        raw_path=item.raw_path,
                        raw_text=item.raw_text,
                        connector_name=item.connector_name,
                        external_id=item.external_id,
                        domain=domain,
                        sensitivity=sensitivity,
                        source_created_at=item.source_created_at,
                        source_modified_at=item.source_modified_at,
                        metadata_json={
                            **item.metadata_json,
                            "connector_name": item.connector_name,
                            "external_id": item.external_id,
                            "sync_cursor": item.cursor,
                            "default_domain": domain,
                            "default_sensitivity": sensitivity,
                        },
                    )
                )
            except Exception as exc:
                failed_count += 1
                failed_external_ids.append(item.external_id)
                errors.append(f"{item.external_id}: {exc}")
                failure_blocked_cursor_advance = True
                self._log_event(
                    event_type="connector.item_failed",
                    connector_name=definition.name,
                    payload={
                        "connector_name": definition.name,
                        "external_id": item.external_id,
                        "sync_cursor": item.cursor,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )
                continue

            if result.duplicate:
                duplicate_count += 1
            else:
                imported_count += 1
                if result.source_id is not None:
                    source_ids.append(result.source_id)

            self._log_event(
                event_type="connector.item_imported",
                connector_name=definition.name,
                payload={
                    "connector_name": definition.name,
                    "external_id": item.external_id,
                    "sync_cursor": item.cursor,
                    "source_id": result.source_id,
                    "duplicate": result.duplicate,
                    "raw_evidence_preserved": True,
                },
            )
            if not failure_blocked_cursor_advance:
                sync_cursor = item.cursor

        status = "ok"
        if failed_count > 0 and (imported_count > 0 or duplicate_count > 0):
            status = "partial"
        elif failed_count > 0:
            status = "failed"
        elif imported_count == 0 and duplicate_count == 0 and skipped_count > 0:
            status = "skipped"

        result = ConnectorSyncResult(
            status=status,
            connector_name=definition.name,
            item_count=len(items),
            imported_count=imported_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            previous_cursor=previous_cursor,
            sync_cursor=sync_cursor,
            source_ids=tuple(source_ids),
            failed_external_ids=tuple(failed_external_ids),
            errors=tuple(errors),
        )
        final_event_type = "connector.sync_failed" if status == "failed" else "connector.sync_completed"
        self._log_event(
            event_type=final_event_type,
            connector_name=definition.name,
            payload=result.to_record(),
        )
        return result


__all__ = [
    "ConnectorDefinition",
    "ConnectorSyncResult",
    "NormalizedConnectorItem",
    "SUPPORTED_CONNECTORS",
    "VNextConnectorService",
    "VNextConnectorStore",
    "VNextConnectorValidationError",
    "get_connector_definition",
    "list_connector_definitions",
    "load_connector_items_from_file",
    "normalize_connector_item",
]
