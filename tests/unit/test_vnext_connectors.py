from __future__ import annotations

from pathlib import Path

import pytest

from alicebot_api.vnext_connectors import (
    VNextConnectorService,
    VNextConnectorValidationError,
    list_connector_definitions,
    load_connector_items_from_file,
    normalize_connector_item,
)


class InMemoryVNextConnectorStore:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.sources: list[dict[str, object]] = []
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.provenance_links: list[dict[str, object]] = []
        self._source_by_hash: dict[str, dict[str, object]] = {}

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[dict[str, object]]:
        return [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        return self._source_by_hash.get(content_hash)

    def create_source(self, source: dict[str, object]) -> dict[str, object]:
        row = {**source, "id": f"source-{len(self.sources) + 1}"}
        self.sources.append(row)
        self._source_by_hash[str(source["content_hash"])] = row
        return row

    def create_source_chunk(self, chunk: dict[str, object]) -> dict[str, object]:
        row = {**chunk, "id": f"chunk-{len(self.chunks) + 1}"}
        self.chunks.append(row)
        return row

    def create_memory(self, memory: dict[str, object]) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories.append(row)
        return row

    def create_provenance_link(self, link: dict[str, object]) -> dict[str, object]:
        row = {**link, "id": f"provenance-{len(self.provenance_links) + 1}"}
        self.provenance_links.append(row)
        return row


def _telegram_payload(update_id: int, text: str = "Fact: Telegram capture preserves raw evidence.") -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id + 100,
            "date": 1_778_400_000,
            "chat": {"id": 999001, "type": "private"},
            "from": {"id": 1001, "username": "samir"},
            "text": text,
        },
    }


def test_connector_definitions_cover_sprint_11_sources_with_conservative_defaults() -> None:
    definitions = {definition.name: definition for definition in list_connector_definitions()}

    assert set(definitions) == {
        "telegram",
        "browser_clipper",
        "pdf_document",
        "docx_document",
        "csv_table",
        "screenshot_ocr",
        "voice_transcription",
    }
    assert definitions["telegram"].default_domain == "personal"
    assert definitions["telegram"].default_sensitivity == "private"
    assert all(definition.to_record()["preserves_raw_evidence"] is True for definition in definitions.values())
    assert all(definition.to_record()["supports_sync_cursor"] is True for definition in definitions.values())


def test_telegram_sync_preserves_raw_evidence_defaults_and_uses_cursor_for_duplicates() -> None:
    store = InMemoryVNextConnectorStore()
    service = VNextConnectorService(store)

    first = service.sync_items("telegram", [_telegram_payload(42)])
    second = service.sync_items("telegram", [_telegram_payload(42)])

    assert first.status == "ok"
    assert first.imported_count == 1
    assert first.sync_cursor == "42"
    assert second.status == "skipped"
    assert second.skipped_count == 1
    assert len(store.sources) == 1
    source = store.sources[0]
    assert source["connector_name"] == "telegram"
    assert source["external_id"] == "999001:142"
    assert source["domain"] == "personal"
    assert source["sensitivity"] == "private"
    metadata = source["metadata_json"]
    assert metadata["raw_payload"]["update_id"] == 42
    assert metadata["raw_evidence_preserved"] is True
    assert metadata["sync_cursor"] == "42"
    assert [event["event_type"] for event in store.events].count("connector.sync_completed") == 2


def test_browser_and_document_connectors_apply_explicit_defaults_and_source_types() -> None:
    store = InMemoryVNextConnectorStore()
    service = VNextConnectorService(store)

    browser = service.sync_items(
        "browser_clipper",
        [
            {
                "external_id": "clip-1",
                "title": "Provenance article",
                "url": "https://example.test/provenance",
                "captured_at": "2026-05-11T08:30:00Z",
                "selection": "Fact: Browser clips should keep source URLs.",
                "html": "<main>Fact: Browser clips should keep source URLs.</main>",
            }
        ],
        default_domain="learning",
        default_sensitivity="internal",
    )
    pdf = service.sync_items(
        "pdf_document",
        [
            {
                "external_id": "pdf-1",
                "filename": "brief.pdf",
                "source_modified_at": "2026-05-11T09:00:00Z",
                "extracted_text": "Fact: PDF processing keeps raw extracted text.",
            }
        ],
        default_domain="professional",
        default_sensitivity="confidential",
    )
    csv_result = service.sync_items(
        "csv_table",
        [{"external_id": "csv-1", "rows": [{"name": "Alice", "state": "vNext"}]}],
    )

    assert browser.imported_count == 1
    assert pdf.imported_count == 1
    assert csv_result.imported_count == 1
    assert [source["source_type"] for source in store.sources] == ["browser_clip", "pdf_document", "csv_table"]
    assert store.sources[0]["uri"] == "https://example.test/provenance"
    assert store.sources[0]["sensitivity"] == "internal"
    assert store.sources[1]["sensitivity"] == "confidential"
    assert "Alice" in store.sources[2]["metadata_json"]["raw_text"]


def test_screenshot_and_voice_normalizers_capture_processed_text_and_raw_payload() -> None:
    screenshot = normalize_connector_item(
        "screenshot_ocr",
        {
            "external_id": "shot-1",
            "filename": "screen.png",
            "captured_at": "2026-05-11T10:00:00Z",
            "ocr_text": "Fact: Screenshot OCR is reviewable source evidence.",
            "image_hash": "sha256:image",
        },
    )
    voice = normalize_connector_item(
        "voice_transcription",
        {
            "external_id": "voice-1",
            "title": "Morning note",
            "recorded_at": "2026-05-11T10:30:00Z",
            "segments": [
                {"speaker": "Samir", "text": "Decision: Keep connector sync deterministic."},
                {"speaker": "Alice", "text": "Noted."},
            ],
            "transcription_provider": "local-whisper",
        },
    )

    assert screenshot.source_type == "screenshot_ocr"
    assert screenshot.metadata_json["raw_payload"]["image_hash"] == "sha256:image"
    assert voice.source_type == "voice_transcript"
    assert "Samir: Decision: Keep connector sync deterministic." in voice.raw_text
    assert voice.metadata_json["transcription_provider"] == "local-whisper"


def test_connector_failure_does_not_advance_cursor_past_failed_item_or_corrupt_memory() -> None:
    store = InMemoryVNextConnectorStore()
    service = VNextConnectorService(store)

    result = service.sync_items(
        "browser_clipper",
        [
            {
                "external_id": "clip-1",
                "cursor": "1",
                "title": "Good clip",
                "text": "Fact: First clip imports.",
            },
            {"external_id": "clip-2", "cursor": "2", "title": "Broken clip"},
            {
                "external_id": "clip-3",
                "cursor": "3",
                "title": "Later clip",
                "text": "Fact: Later clip imports but cursor does not skip the failed item.",
            },
        ],
    )

    assert result.status == "partial"
    assert result.imported_count == 2
    assert result.failed_count == 1
    assert result.sync_cursor is None
    assert result.failed_external_ids == ("clip-2",)
    assert len(store.sources) == 2
    assert all(source["external_id"] != "clip-2" for source in store.sources)
    assert store.events[-1]["event_type"] == "connector.sync_completed"
    assert store.events[-1]["payload_json"]["sync_cursor"] is None


def test_connector_payload_loader_accepts_json_items_and_csv_file(tmp_path: Path) -> None:
    json_path = tmp_path / "clips.json"
    json_path.write_text('{"items": [{"external_id": "clip-1", "text": "Fact: Loaded."}]}', encoding="utf-8")
    csv_path = tmp_path / "table.csv"
    csv_path.write_text("name,state\nAlice,vNext\n", encoding="utf-8")

    assert load_connector_items_from_file(json_path) == [{"external_id": "clip-1", "text": "Fact: Loaded."}]
    csv_items = load_connector_items_from_file(csv_path)
    assert csv_items[0]["filename"] == "table.csv"
    assert "Alice" in str(csv_items[0]["csv_text"])


def test_unknown_connector_rejected() -> None:
    with pytest.raises(VNextConnectorValidationError, match="unknown vNext connector"):
        normalize_connector_item("not-real", {"text": "Fact: no."})
