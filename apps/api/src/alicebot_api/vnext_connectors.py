from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
import fnmatch
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Protocol, cast
from urllib import parse, request
from uuid import uuid4

from alicebot_api.telegram_channels import normalize_telegram_update
from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService, VNextCaptureStore
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


class VNextConnectorValidationError(ValueError):
    """Raised when a connector payload cannot be normalized safely."""


class VNextConnectorStore(VNextCaptureStore, Protocol):
    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[JsonObject]: ...

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject: ...


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
    captured_at: str | None = None
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


@dataclass(frozen=True, slots=True)
class AgentOutputIngestResult:
    status: str
    source_id: str | None
    artifact_id: str | None
    memory_id: str | None
    policy_decision: JsonObject | None

    def to_record(self) -> JsonObject:
        return {
            "status": self.status,
            "source_id": self.source_id,
            "artifact_id": self.artifact_id,
            "memory_id": self.memory_id,
            "policy_decision": self.policy_decision,
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
        phase="live_capture",
        source_type="browser_clip",
        default_domain="professional",
        default_sensitivity="private",
        raw_evidence_kind="browser_clip_json",
        cursor_field="captured_at_or_external_id",
        description="Captures clipped page text, URL, selection, and optional HTML snapshots.",
    ),
    ConnectorDefinition(
        name="local_folder",
        display_name="Local folder watcher",
        phase="live_capture",
        source_type="local_file",
        default_domain="project",
        default_sensitivity="private",
        raw_evidence_kind="local_text_file",
        cursor_field="mtime_ns_path",
        description="Backfills and incrementally scans configured Markdown/text folders such as Obsidian vaults.",
    ),
    ConnectorDefinition(
        name="agent_output",
        display_name="Agent output ingestion",
        phase="live_capture",
        source_type="agent_output",
        default_domain="project",
        default_sensitivity="private",
        raw_evidence_kind="agent_output_json",
        cursor_field="agent_run_id_or_external_id",
        description="Captures Hermes/OpenClaw outputs as reviewable source evidence and optional proposals.",
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

DEFAULT_LOCAL_FOLDER_IGNORES = (
    ".alice",
    "generated",
    "alice export",
    "07 generated",
    "08 queue",
)
DEFAULT_LOCAL_FOLDER_EXTENSIONS = (".md", ".txt")
LOCAL_FOLDER_ROOTS_ENV = "ALICE_VNEXT_LOCAL_FOLDER_ROOTS"

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


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _redacted_error(error: Exception) -> str:
    message = str(error)
    for marker in ("bot", "token", "secret"):
        if marker in message.casefold():
            return type(error).__name__
    return message


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


def _stable_external_id(*parts: str) -> str:
    joined = "|".join(parts)
    return "sha256:" + sha256(joined.encode("utf-8")).hexdigest()


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


def _telegram_attachment_metadata(payload: Mapping[str, object]) -> list[JsonObject]:
    message = payload.get("message")
    if not isinstance(message, Mapping):
        return []
    attachments: list[JsonObject] = []
    for key in ("photo", "document", "voice", "audio", "video"):
        value = message.get(key)
        if value is None:
            continue
        if key == "photo" and isinstance(value, list):
            attachments.append({"type": key, "count": len(value)})
        elif isinstance(value, Mapping):
            metadata: JsonObject = {"type": key}
            for field_name in ("file_id", "file_unique_id", "file_name", "mime_type", "duration", "file_size"):
                field_value = value.get(field_name)
                if isinstance(field_value, (str, int, float, bool)) or field_value is None:
                    metadata[field_name] = field_value
            attachments.append(metadata)
    return attachments


def _telegram_chat_id(payload: Mapping[str, object]) -> str | None:
    for key in ("message", "edited_message", "channel_post"):
        message = payload.get(key)
        if not isinstance(message, Mapping):
            continue
        chat = message.get("chat")
        if isinstance(chat, Mapping):
            chat_id = chat.get("id")
            if isinstance(chat_id, (str, int)):
                return str(chat_id)
    return None


def _is_ignored_local_file(relative_path: Path, *, ignore_patterns: Sequence[str]) -> bool:
    normalized_parts = tuple(part.casefold() for part in relative_path.parts)
    if any(part in DEFAULT_LOCAL_FOLDER_IGNORES for part in normalized_parts):
        return True
    normalized_path = str(relative_path).replace("\\", "/")
    for pattern in ignore_patterns:
        cleaned = pattern.strip()
        if cleaned and fnmatch.fnmatch(normalized_path, cleaned):
            return True
    return False


def _path_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False


def _allowed_local_folder_roots() -> tuple[Path, ...]:
    configured = os.environ.get(LOCAL_FOLDER_ROOTS_ENV)
    if configured:
        candidates = [Path(value).expanduser() for value in configured.split(os.pathsep) if value.strip()]
    else:
        candidates = [Path.home(), Path.cwd(), Path(tempfile.gettempdir())]

    roots: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            continue
        if resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def _relative_parts_under_allowed_root(raw_root: str | Path, allowed_root: Path) -> tuple[str, ...] | None:
    raw_text = os.fspath(raw_root).strip()
    if not raw_text or "\x00" in raw_text:
        return None
    expanded = os.path.realpath(os.path.abspath(os.path.expanduser(raw_text)))
    allowed_text = str(allowed_root)
    if expanded == allowed_text:
        return ()
    prefix = allowed_text + os.sep
    if not expanded.startswith(prefix):
        return None

    parts: list[str] = []
    for raw_part in expanded[len(prefix) :].split(os.sep):
        if raw_part in {"", ".", ".."}:
            return None
        safe_part = os.path.basename(raw_part)
        if safe_part != raw_part:
            return None
        parts.append(safe_part)
    return tuple(parts)


def _resolve_local_folder_root(raw_root: str | Path) -> Path:
    allowed_roots = _allowed_local_folder_roots()
    for allowed_root in allowed_roots:
        relative_parts = _relative_parts_under_allowed_root(raw_root, allowed_root)
        if relative_parts is None:
            continue
        root = allowed_root.joinpath(*relative_parts).resolve(strict=True)
        if not _path_within(root, allowed_root) or not root.is_dir():
            break
        return root

    allowed = ", ".join(str(allowed_root) for allowed_root in allowed_roots)
    raise VNextConnectorValidationError(
        f"local_folder watched path must be an existing directory under an allowed root; set {LOCAL_FOLDER_ROOTS_ENV} "
        f"to override. Allowed roots: {allowed}"
    )


def _agent_artifact_type(output_type: str | None) -> str:
    if output_type == "research_summary":
        return "research_brief"
    if output_type == "project_update":
        return "project_update"
    if output_type in {"sprint_summary", "code_review", "decision", "generated_plan", "meeting_summary"}:
        return "system_report"
    return "system_report"


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
        title=f"Telegram capture - {str(normalized['sent_at']).replace('T', ' ')[:16]}",
        author=author,
        source_created_at=_optional_iso(normalized["sent_at"]),
        metadata_json={
            "raw_payload": payload,
            "normalized_payload": cast(JsonObject, normalized["normalized_payload"]),
            "provider_update_id": normalized["provider_update_id"],
            "provider_message_id": normalized["provider_message_id"],
            "external_chat_id": normalized["external_chat_id"],
            "idempotency_key": normalized["idempotency_key"],
            "chat_id": normalized["external_chat_id"],
            "message_id": normalized["provider_message_id"],
            "sender_id": normalized["external_user_id"],
            "sender_username": username,
            "message_date": _optional_iso(normalized["sent_at"]),
            "contains_links": "http://" in text.casefold() or "https://" in text.casefold(),
            "attachment_metadata": _telegram_attachment_metadata(payload),
            "untrusted_source_material": True,
            "raw_evidence_preserved": True,
        },
    )


def _normalize_browser_clip_item(payload: JsonObject) -> NormalizedConnectorItem:
    selected_text = _first_text(payload, ("selected_text", "selection", "excerpt"))
    user_note = _first_text(payload, ("user_note", "note"))
    page_text = _first_text(payload, ("page_text", "text", "markdown"))
    parts = [
        f"Selected text:\n{selected_text}" if selected_text else "",
        f"User note:\n{user_note}" if user_note else "",
        f"Page text:\n{page_text}" if page_text else "",
    ]
    text = "\n\n".join(part for part in parts if part)
    if text.strip() == "":
        raise VNextConnectorValidationError("browser_clipper item requires selected_text, user_note, page_text, or text")
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
        captured_at=captured_at,
        source_created_at=captured_at,
        metadata_json={
            "raw_payload": payload,
            "url": url,
            "title": title,
            "selected_text_present": selected_text is not None,
            "user_note_present": user_note is not None,
            "captured_from_browser": True,
            "selection": selected_text,
            "html": _as_optional_text(payload.get("html")),
            "untrusted_source_material": True,
            "raw_evidence_preserved": True,
        },
    )


def _normalize_local_folder_item(payload: JsonObject) -> NormalizedConnectorItem:
    text = _required_text(payload, ("text", "content"), connector_name="local_folder")
    path = _required_text(payload, ("path",), connector_name="local_folder")
    title = _first_text(payload, ("title", "filename")) or Path(path).name
    external_id = _external_id(payload, fallback=path)
    mtime_ns = payload.get("mtime_ns")
    cursor = _cursor_value(
        payload,
        external_id=external_id,
        keys=("cursor", "mtime_ns", "source_modified_at", "mtime"),
    )
    if isinstance(mtime_ns, int):
        cursor = f"{mtime_ns}:{external_id}"
    return NormalizedConnectorItem(
        connector_name="local_folder",
        source_type="local_file",
        external_id=external_id,
        cursor=cursor,
        raw_text=text,
        title=title,
        raw_path=path,
        source_modified_at=_optional_iso(payload.get("source_modified_at") or payload.get("mtime")),
        metadata_json={
            "raw_payload": payload,
            "path": path,
            "relative_path": _as_optional_text(payload.get("relative_path")),
            "file_size": payload.get("file_size") if isinstance(payload.get("file_size"), int) else None,
            "mtime": payload.get("mtime"),
            "extension": _as_optional_text(payload.get("extension")),
            "watched_root": _as_optional_text(payload.get("watched_root")),
            "untrusted_source_material": True,
            "raw_evidence_preserved": True,
        },
    )


def _normalize_agent_output_item(payload: JsonObject) -> NormalizedConnectorItem:
    content = _required_text(payload, ("content", "text", "summary"), connector_name="agent_output")
    title = _first_text(payload, ("title",)) or "Agent output"
    agent_id = _required_text(payload, ("agent_id",), connector_name="agent_output")
    external_id = _external_id(
        payload,
        fallback=_stable_external_id(agent_id, _first_text(payload, ("agent_run_id", "task_id")) or title, content),
    )
    captured_at = _optional_iso(payload.get("captured_at")) or _utc_now_iso()
    cursor = _cursor_value(payload, external_id=external_id, keys=("cursor", "agent_run_id", "captured_at"))
    return NormalizedConnectorItem(
        connector_name="agent_output",
        source_type="agent_output",
        external_id=external_id,
        cursor=cursor,
        raw_text=content,
        title=title,
        author=agent_id,
        captured_at=captured_at,
        source_created_at=captured_at,
        metadata_json={
            "raw_payload": payload,
            "agent_id": agent_id,
            "agent_type": _as_optional_text(payload.get("agent_type")),
            "agent_run_id": _as_optional_text(payload.get("agent_run_id")),
            "task_id": _as_optional_text(payload.get("task_id")),
            "project_scope": payload.get("project_scope") if isinstance(payload.get("project_scope"), list) else [],
            "output_type": _as_optional_text(payload.get("output_type")) or "general",
            "rationale": _as_optional_text(payload.get("rationale")),
            "source_refs": payload.get("source_refs") if isinstance(payload.get("source_refs"), list) else [],
            "untrusted_source_material": True,
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
            "untrusted_source_material": True,
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
            "untrusted_source_material": True,
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
            "untrusted_source_material": True,
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
            "untrusted_source_material": True,
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
    if definition.name == "local_folder":
        return _normalize_local_folder_item(item)
    if definition.name == "agent_output":
        return _normalize_agent_output_item(item)
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

    def update_config(
        self,
        connector_name: str,
        *,
        enabled: bool | None = None,
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
        secret_ref: str | None = None,
        config_json: JsonObject | None = None,
    ) -> JsonObject:
        definition = get_connector_definition(connector_name)
        domain = default_domain or definition.default_domain
        sensitivity = default_sensitivity or definition.default_sensitivity
        if domain not in _VALID_DOMAINS:
            raise VNextConnectorValidationError(f"invalid connector default domain: {domain}")
        if sensitivity not in _VALID_SENSITIVITIES:
            raise VNextConnectorValidationError(f"invalid connector default sensitivity: {sensitivity}")
        config = {
            "connector_name": definition.name,
            "enabled": bool(enabled) if enabled is not None else False,
            "configured": True,
            "secret_ref": secret_ref,
            "default_domain": domain,
            "default_sensitivity": sensitivity,
            "config_json": config_json or {},
            "updated_at": _utc_now_iso(),
        }
        self._log_event(
            event_type="connector.config_updated",
            connector_name=definition.name,
            payload=config,
        )
        return config

    def get_config(self, connector_name: str) -> JsonObject:
        definition = get_connector_definition(connector_name)
        events = [
            event
            for event in self.store.list_events(target_type="connector", target_id=definition.name)
            if event.get("event_type") == "connector.config_updated"
        ]
        events.sort(key=lambda event: str(event.get("occurred_at") or ""), reverse=True)
        if events:
            payload = events[0].get("payload_json")
            if isinstance(payload, dict):
                return cast(JsonObject, payload)
        return {
            "connector_name": definition.name,
            "enabled": False,
            "configured": False,
            "secret_ref": None,
            "default_domain": definition.default_domain,
            "default_sensitivity": definition.default_sensitivity,
            "config_json": {},
            "updated_at": None,
        }

    def connector_health(self, connector_name: str) -> JsonObject:
        definition = get_connector_definition(connector_name)
        config = self.get_config(definition.name)
        events = self.store.list_events(target_type="connector", target_id=definition.name)
        events.sort(key=lambda event: str(event.get("occurred_at") or ""), reverse=True)
        sync_events = [
            event
            for event in events
            if event.get("event_type") in {"connector.sync_completed", "connector.sync_failed"}
            and isinstance(event.get("payload_json"), dict)
        ]
        latest_success = next((event for event in sync_events if event.get("event_type") == "connector.sync_completed"), None)
        latest_failure = next((event for event in sync_events if event.get("event_type") == "connector.sync_failed"), None)
        latest_item_failure = next((event for event in events if event.get("event_type") == "connector.item_failed"), None)
        latest_import = next((event for event in events if event.get("event_type") == "connector.item_imported"), None)

        items_seen = 0
        items_captured = 0
        items_deduped = 0
        items_failed = 0
        processing_times: list[float] = []
        cursor_state: str | None = None
        for event in sync_events:
            payload = cast(JsonObject, event["payload_json"])
            items_seen += int(payload.get("item_count", 0) or 0)
            items_captured += int(payload.get("imported_count", 0) or 0)
            items_deduped += int(payload.get("duplicate_count", 0) or 0)
            items_failed += int(payload.get("failed_count", 0) or 0)
            cursor = _as_optional_text(payload.get("sync_cursor"))
            if cursor_state is None and cursor is not None:
                cursor_state = cursor
            processing_time = payload.get("processing_time_ms")
            if isinstance(processing_time, (int, float)) and not isinstance(processing_time, bool):
                processing_times.append(float(processing_time))
        last_error = None
        if latest_failure is not None and isinstance(latest_failure.get("payload_json"), dict):
            errors = latest_failure["payload_json"].get("errors")  # type: ignore[index]
            last_error = str(errors[0]) if isinstance(errors, list) and errors else None
        if last_error is None and latest_item_failure is not None and isinstance(latest_item_failure.get("payload_json"), dict):
            last_error = _as_optional_text(latest_item_failure["payload_json"].get("error_message"))  # type: ignore[index]

        latest_import_payload = latest_import.get("payload_json") if latest_import is not None else None
        return {
            "connector_name": definition.name,
            "display_name": definition.display_name,
            "enabled": bool(config.get("enabled")),
            "configured": bool(config.get("configured")),
            "default_domain": config.get("default_domain") or definition.default_domain,
            "default_sensitivity": config.get("default_sensitivity") or definition.default_sensitivity,
            "last_sync_at": sync_events[0].get("occurred_at") if sync_events else None,
            "last_success_at": latest_success.get("occurred_at") if latest_success is not None else None,
            "last_failure_at": latest_failure.get("occurred_at") if latest_failure is not None else None,
            "last_error": last_error,
            "last_captured_item": latest_import_payload if isinstance(latest_import_payload, dict) else None,
            "items_seen": items_seen,
            "items_captured": items_captured,
            "items_deduped": items_deduped,
            "items_failed": items_failed,
            "cursor_state": cursor_state or self.get_cursor(definition.name),
            "average_processing_time": round(sum(processing_times) / len(processing_times), 3)
            if processing_times
            else None,
        }

    def connector_health_all(self) -> JsonObject:
        items = [self.connector_health(definition.name) for definition in list_connector_definitions()]
        return {"items": items, "count": len(items), "order": [str(item["connector_name"]) for item in items]}

    def sync_telegram_updates(
        self,
        updates: Sequence[Mapping[str, object]],
        *,
        allowed_chat_ids: Sequence[str],
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
    ) -> ConnectorSyncResult:
        allowed = {str(chat_id) for chat_id in allowed_chat_ids if str(chat_id).strip()}
        if not allowed:
            raise VNextConnectorValidationError("telegram connector requires at least one allowed chat id")
        accepted: list[Mapping[str, object]] = []
        rejected_count = 0
        for update in updates:
            chat_id = _telegram_chat_id(update)
            if chat_id is None or chat_id not in allowed:
                rejected_count += 1
                self._log_event(
                    event_type="connector.item_rejected",
                    connector_name="telegram",
                    payload={
                        "connector_name": "telegram",
                        "external_id": _first_text(update, ("update_id", "id")) or "unknown",
                        "reason": "chat_not_allowlisted",
                        "chat_id": chat_id,
                    },
                )
                continue
            accepted.append(update)
        result = self.sync_items(
            "telegram",
            accepted,
            default_domain=default_domain,
            default_sensitivity=default_sensitivity,
        )
        if rejected_count == 0:
            return result
        return ConnectorSyncResult(
            status="partial" if result.status == "ok" else result.status,
            connector_name=result.connector_name,
            item_count=len(updates),
            imported_count=result.imported_count,
            duplicate_count=result.duplicate_count,
            skipped_count=result.skipped_count + rejected_count,
            failed_count=result.failed_count,
            previous_cursor=result.previous_cursor,
            sync_cursor=result.sync_cursor,
            source_ids=result.source_ids,
            failed_external_ids=result.failed_external_ids,
            errors=result.errors,
        )

    def fetch_telegram_updates(
        self,
        *,
        bot_token: str | None = None,
        bot_token_env: str = "TELEGRAM_BOT_TOKEN",
        timeout: int = 10,
        limit: int = 100,
    ) -> list[JsonObject]:
        token = bot_token or os.environ.get(bot_token_env)
        if not token:
            raise VNextConnectorValidationError(f"telegram bot token is not configured in {bot_token_env}")
        cursor = self.get_cursor("telegram")
        query: dict[str, str] = {"timeout": str(timeout), "limit": str(limit)}
        if cursor is not None and cursor.isdecimal():
            query["offset"] = str(int(cursor) + 1)
        url = f"https://api.telegram.org/bot{parse.quote(token)}/getUpdates?{parse.urlencode(query)}"
        try:
            with request.urlopen(url, timeout=timeout + 5) as response:  # noqa: S310 - local operator supplied bot API URL.
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self._log_event(
                event_type="connector.sync_failed",
                connector_name="telegram",
                payload={
                    "connector_name": "telegram",
                    "error_type": type(exc).__name__,
                    "error_message": _redacted_error(exc),
                    "sync_cursor": cursor,
                },
            )
            raise VNextConnectorValidationError("telegram polling failed") from exc
        if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("result"), list):
            raise VNextConnectorValidationError("telegram polling returned an invalid response")
        return [cast(JsonObject, item) for item in payload["result"] if isinstance(item, dict)]

    def sync_local_folder(
        self,
        paths: Sequence[str | Path],
        *,
        recursive: bool = True,
        extensions: Sequence[str] = DEFAULT_LOCAL_FOLDER_EXTENSIONS,
        ignore_patterns: Sequence[str] = (),
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
    ) -> ConnectorSyncResult:
        normalized_extensions = tuple(extension.casefold() for extension in extensions)
        if not normalized_extensions:
            raise VNextConnectorValidationError("local_folder requires at least one file extension")
        items: list[JsonObject] = []
        ignored_count = 0
        for raw_root in paths:
            root = _resolve_local_folder_root(raw_root)
            iterator = root.rglob("*") if recursive else root.glob("*")
            for file_path in sorted(iterator):
                try:
                    resolved_file = file_path.resolve(strict=True)
                except OSError:
                    continue
                if not resolved_file.is_file() or not _path_within(resolved_file, root):
                    continue
                if resolved_file.suffix.casefold() not in normalized_extensions:
                    continue
                relative_path = resolved_file.relative_to(root)
                if _is_ignored_local_file(relative_path, ignore_patterns=ignore_patterns):
                    ignored_count += 1
                    continue
                stat = resolved_file.stat()
                items.append(
                    {
                        "path": str(resolved_file),
                        "relative_path": str(relative_path),
                        "filename": resolved_file.name,
                        "text": resolved_file.read_text(encoding="utf-8"),
                        "file_size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat().replace("+00:00", "Z"),
                        "mtime_ns": stat.st_mtime_ns,
                        "extension": resolved_file.suffix.casefold(),
                        "watched_root": str(root),
                        "external_id": str(resolved_file),
                    }
                )
        self._log_event(
            event_type="connector.local_folder_scan",
            connector_name="local_folder",
            payload={
                "connector_name": "local_folder",
                "path_count": len(paths),
                "file_count": len(items),
                "ignored_count": ignored_count,
                "recursive": recursive,
                "extensions": list(normalized_extensions),
            },
        )
        return self.sync_items(
            "local_folder",
            items,
            default_domain=default_domain,
            default_sensitivity=default_sensitivity,
            use_cursor=False,
        )

    def capture_browser_clip(
        self,
        payload: Mapping[str, object],
        *,
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
    ) -> ConnectorSyncResult:
        return self.sync_items(
            "browser_clipper",
            [payload],
            default_domain=default_domain,
            default_sensitivity=default_sensitivity,
            use_cursor=False,
        )

    def ingest_agent_output(
        self,
        payload: Mapping[str, object],
        *,
        policy_decision: JsonObject | None = None,
    ) -> AgentOutputIngestResult:
        item = normalize_connector_item("agent_output", payload)
        agent_id = str(item.metadata_json.get("agent_id") or item.author or "unknown")
        agent_identity = {
            "agent_id": agent_id,
            "agent_type": item.metadata_json.get("agent_type") or "unknown",
            "agent_run_id": item.metadata_json.get("agent_run_id"),
            "task_id": item.metadata_json.get("task_id"),
            "project_scope": item.metadata_json.get("project_scope") or [],
        }
        capture = VNextCaptureService(
            self.store,
            actor_type="agent",
            actor_id=agent_id,
            run_id=_as_optional_text(payload.get("agent_run_id")),
            agent_identity=agent_identity,
            policy_decision=policy_decision,
        ).capture_source(
            SourceCaptureInput(
                source_type=item.source_type,
                title=item.title,
                raw_text=item.raw_text,
                author=item.author,
                connector_name=item.connector_name,
                external_id=item.external_id,
                domain=_as_optional_text(payload.get("domain")) or "project",
                sensitivity=_as_optional_text(payload.get("sensitivity")) or "private",
                captured_at=item.captured_at,
                source_created_at=item.source_created_at,
                metadata_json={
                    **item.metadata_json,
                    "connector_name": "agent_output",
                    "external_id": item.external_id,
                    "policy_decision": policy_decision,
                },
            )
        )
        source_id = capture.source_id
        artifact_id: str | None = None
        memory_id: str | None = None
        artifact = self.store.create_artifact(
            {
                "artifact_type": _agent_artifact_type(_as_optional_text(payload.get("output_type"))),
                "title": item.title,
                "content_markdown": item.raw_text,
                "status": "needs_review",
                "domain": _as_optional_text(payload.get("domain")) or "project",
                "sensitivity": _as_optional_text(payload.get("sensitivity")) or "private",
                "generated_by": agent_id,
                "metadata_json": {
                    "connector_name": "agent_output",
                    "agent_identity": agent_identity,
                    "source_id": source_id,
                    "source_refs": [f"source:{source_id}"] if source_id else [],
                    "output_type": _as_optional_text(payload.get("output_type")) or "general",
                    "review_status": "needs_review",
                },
            },
            actor_type="agent",
        )
        artifact_id = str(artifact["id"])
        if source_id is not None:
            self.store.create_provenance_link(
                {
                    "target_type": "artifact",
                    "target_id": artifact_id,
                    "source_id": source_id,
                    "source_chunk_id": None,
                    "quote": item.title,
                    "evidence_role": "summarizes",
                    "confidence": 0.72,
                },
                actor_type="agent",
            )

        if bool(payload.get("propose_memory")):
            memory = self.store.create_memory(
                {
                    "memory_key": f"vnext.agent_output.{sha256((item.external_id + item.raw_text).encode('utf-8')).hexdigest()[:16]}",
                    "value": {
                        "text": item.title,
                        "source_id": source_id,
                        "artifact_id": artifact_id,
                        "rationale": item.metadata_json.get("rationale"),
                    },
                    "status": "candidate",
                    "source_event_ids": [value for value in (source_id, artifact_id) if value],
                    "memory_type": "agent_run",
                    "confidence": 0.62,
                    "title": item.title,
                    "canonical_text": item.title,
                    "summary": _as_optional_text(payload.get("rationale")) or item.raw_text[:280],
                    "domain": _as_optional_text(payload.get("domain")) or "project",
                    "sensitivity": _as_optional_text(payload.get("sensitivity")) or "private",
                    "metadata_json": {
                        "connector_name": "agent_output",
                        "agent_identity": agent_identity,
                        "source_id": source_id,
                        "artifact_id": artifact_id,
                        "review_required": True,
                        "policy_decision": policy_decision,
                    },
                },
                actor_type="agent",
            )
            memory_id = str(memory["id"])
            if source_id is not None:
                self.store.create_provenance_link(
                    {
                        "target_type": "memory",
                        "target_id": memory_id,
                        "source_id": source_id,
                        "source_chunk_id": None,
                        "quote": item.title,
                        "evidence_role": "inferred_from",
                        "confidence": 0.62,
                    },
                    actor_type="agent",
                )
            self._log_event(
                event_type="memory.candidate_created",
                connector_name="agent_output",
                payload={"memory_id": memory_id, "source_id": source_id, "artifact_id": artifact_id, "review_required": True},
            )

        append_event(
            self.store,
            event_type="agent.output_ingested",
            actor_type="agent",
            actor_id=agent_id,
            target_type="connector",
            target_id="agent_output",
            payload={
                "connector_name": "agent_output",
                "agent_identity": agent_identity,
                "source_id": source_id,
                "artifact_id": artifact_id,
                "memory_id": memory_id,
                "propose_memory": bool(payload.get("propose_memory")),
                "policy_decision": policy_decision,
            },
        )
        return AgentOutputIngestResult(
            status="imported",
            source_id=source_id,
            artifact_id=artifact_id,
            memory_id=memory_id,
            policy_decision=policy_decision,
        )

    def sync_items(
        self,
        connector_name: str,
        items: Sequence[Mapping[str, object]],
        *,
        default_domain: str | None = None,
        default_sensitivity: str | None = None,
        use_cursor: bool = True,
    ) -> ConnectorSyncResult:
        started_at = time.perf_counter()
        definition = get_connector_definition(connector_name)
        domain = default_domain or definition.default_domain
        sensitivity = default_sensitivity or definition.default_sensitivity
        if domain not in _VALID_DOMAINS:
            raise VNextConnectorValidationError(f"invalid connector default domain: {domain}")
        if sensitivity not in _VALID_SENSITIVITIES:
            raise VNextConnectorValidationError(f"invalid connector default sensitivity: {sensitivity}")

        previous_cursor = self.get_cursor(definition.name) if use_cursor else None
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
                        captured_at=item.captured_at,
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
            payload={**result.to_record(), "processing_time_ms": round((time.perf_counter() - started_at) * 1000, 3)},
        )
        return result


__all__ = [
    "AgentOutputIngestResult",
    "ConnectorDefinition",
    "ConnectorSyncResult",
    "DEFAULT_LOCAL_FOLDER_EXTENSIONS",
    "DEFAULT_LOCAL_FOLDER_IGNORES",
    "LOCAL_FOLDER_ROOTS_ENV",
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
