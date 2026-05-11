from __future__ import annotations

import json
from pathlib import Path

from alicebot_api.brain_charter import BRAIN_CHARTER_TEMPLATE, BrainCharter, default_brain_charter
from alicebot_api import vnext_repositories
from alicebot_api.vnext_event_log import build_event_log_record, integrity_hash_for_event


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_schema(name: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_vnext_json_schemas_exist_for_required_shared_contracts() -> None:
    expected = {
        "source.schema.json",
        "memory.schema.json",
        "artifact.schema.json",
        "graph-edge.schema.json",
        "context-pack.schema.json",
        "event.schema.json",
    }

    for schema_name in expected:
        payload = _load_schema(schema_name)
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["type"] == "object"


def test_vnext_schemas_preserve_domain_sensitivity_and_provenance_requirements() -> None:
    source_schema = _load_schema("source.schema.json")
    memory_schema = _load_schema("memory.schema.json")
    artifact_schema = _load_schema("artifact.schema.json")
    context_pack_schema = _load_schema("context-pack.schema.json")

    assert "domain" in source_schema["required"]
    assert "sensitivity" in source_schema["required"]
    assert "domain" in memory_schema["required"]
    assert "sensitivity" in artifact_schema["required"]
    assert "sources" in context_pack_schema["required"]
    assert "trace_id" in context_pack_schema["required"]


def test_vnext_repository_protocols_cover_specified_store_interfaces() -> None:
    for protocol_name in (
        "EventStore",
        "SourceStore",
        "MemoryStore",
        "RevisionStore",
        "ProvenanceStore",
        "EmbeddingStore",
        "GraphStore",
        "ProjectStore",
        "PeopleStore",
        "BeliefStore",
        "OpenLoopStore",
        "ArtifactStore",
        "TaskQueueStore",
        "BrainCharterStore",
        "PolicyStore",
        "EvalStore",
    ):
        assert hasattr(vnext_repositories, protocol_name)


def test_event_log_records_are_hashable_and_deterministic_for_payload() -> None:
    first = build_event_log_record(
        event_type="source.captured",
        actor_type="system",
        target_type="source",
        target_id="source-1",
        payload={"b": 2, "a": 1},
        occurred_at="2026-05-10T12:00:00Z",
    )
    second = {
        **first,
        "integrity_hash": None,
        "payload_json": {"a": 1, "b": 2},
    }

    assert first["integrity_hash"] == integrity_hash_for_event(first)
    second["integrity_hash"] = integrity_hash_for_event(second)
    assert second["integrity_hash"] == first["integrity_hash"]


def test_brain_charter_default_exports_spec_sections() -> None:
    charter = default_brain_charter()
    record = charter.to_record()

    assert isinstance(charter, BrainCharter)
    assert "# ALICE.md - Brain Charter" in BRAIN_CHARTER_TEMPLATE
    assert "Autonomous Operation Rules" in record["content_markdown"]
    assert "Always preserve provenance." in record["autonomous_rules_json"]
    assert record["sensitivity"] == "private"
