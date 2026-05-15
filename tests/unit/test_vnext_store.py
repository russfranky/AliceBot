from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from alicebot_api.vnext_event_log import build_event_log_record
from alicebot_api.vnext_store import PostgresVNextStore, _search_patterns


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        if params is not None:
            assert query.count("%s") == len(params)
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def _event_row(target_id: object | None = None) -> dict[str, object]:
    return {
        "id": uuid4(),
        "event_type": "audit",
        "target_id": str(target_id) if target_id is not None else None,
    }


def _event_log_insert_count(cursor: RecordingCursor) -> int:
    return sum(1 for query, _params in cursor.executed if "INSERT INTO event_log" in query)


def test_source_crud_and_chunks_write_audit_events() -> None:
    source_id = str(uuid4())
    chunk_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": source_id},
            _event_row(source_id),
            {"id": source_id},
            {"id": source_id},
            _event_row(source_id),
            {"id": source_id},
            _event_row(source_id),
            {"id": chunk_id, "source_id": source_id},
            _event_row(chunk_id),
        ],
        fetchall_result=[{"id": chunk_id, "source_id": source_id}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    created = store.create_source(
        {
            "id": source_id,
            "source_type": "document",
            "title": "Spec",
            "content_hash": "sha256:abc",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"path": "docs/spec.md"},
        }
    )
    fetched = store.get_source(source_id)
    updated = store.update_source(source_id=source_id, patch={"title": "Spec v2", "metadata_json": {"rev": 2}})
    deleted = store.delete_source(source_id=source_id)
    chunk = store.create_source_chunk(
        {
            "id": chunk_id,
            "source_id": source_id,
            "chunk_index": 0,
            "text": "Alice vNext",
            "token_count": 3,
            "metadata_json": {"section": "intro"},
        }
    )
    chunks = store.list_source_chunks(source_id)

    assert created["id"] == source_id
    assert fetched is not None
    assert updated["id"] == source_id
    assert deleted["id"] == source_id
    assert chunk["source_id"] == source_id
    assert chunks == [{"id": chunk_id, "source_id": source_id}]
    assert _event_log_insert_count(cursor) == 4

    source_insert_query, source_insert_params = cursor.executed[0]
    assert "INSERT INTO sources" in source_insert_query
    assert source_insert_params is not None
    assert isinstance(source_insert_params[-1], Jsonb)
    assert source_insert_params[-1].obj == {"path": "docs/spec.md"}

    source_update_query, source_update_params = cursor.executed[3]
    assert "UPDATE sources" in source_update_query
    assert source_update_params is not None
    assert isinstance(source_update_params[6], Jsonb)
    assert source_update_params[6].obj == {"rev": 2}


def test_get_source_by_content_hash_uses_dedupe_lookup() -> None:
    source_id = str(uuid4())
    cursor = RecordingCursor(fetchone_results=[{"id": source_id, "content_hash": "sha256:abc"}])
    store = PostgresVNextStore(RecordingConnection(cursor))

    source = store.get_source_by_content_hash("sha256:abc")

    assert source is not None
    assert source["id"] == source_id
    query, params = cursor.executed[0]
    assert "FROM sources" in query
    assert "content_hash = %s" in query
    assert "deleted_at IS NULL" in query
    assert params == ("sha256:abc",)


def test_search_patterns_strip_quotes_and_add_keyword_fallbacks() -> None:
    patterns = _search_patterns('"agent-first /vnext audit correction cockpit"')

    assert patterns[0] == "%agent-first /vnext audit correction cockpit%"
    assert "%agent-first%" in patterns
    assert "%vnext%" in patterns
    assert "%audit%" in patterns
    assert "%correction%" in patterns
    assert "%cockpit%" in patterns


def test_keyword_search_methods_apply_domain_sensitivity_and_limit_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "matched-1", "domain": "project", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    memories = store.search_memories(
        query="Alice provenance",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=4,
    )
    sources = store.search_sources(
        query="Alice provenance",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=3,
    )
    open_loops = store.list_open_loops(
        status="open",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=2,
    )

    assert memories[0]["id"] == "matched-1"
    assert sources[0]["id"] == "matched-1"
    assert open_loops[0]["id"] == "matched-1"
    memory_query, memory_params = cursor.executed[0]
    source_query, source_params = cursor.executed[1]
    open_loop_query, open_loop_params = cursor.executed[2]
    assert "FROM memories" in memory_query
    assert "status IN ('active', 'accepted')" in memory_query
    assert "domain = ANY" in memory_query
    assert "sensitivity = ANY" in memory_query
    assert "ILIKE ANY" in memory_query
    assert memory_params is not None
    assert memory_params[4] == ["%Alice provenance%", "%alice%", "%provenance%"]
    assert memory_params[-1] == 4
    assert "FROM sources" in source_query
    assert "ILIKE ANY" in source_query
    assert source_params is not None
    assert source_params[4] == ["%Alice provenance%", "%alice%", "%provenance%"]
    assert source_params[-1] == 3
    assert "FROM open_loops" in open_loop_query
    assert "%s::text IS NULL OR status = %s" in open_loop_query
    assert "%s::uuid IS NULL OR project_id = %s::uuid" in open_loop_query
    assert "%s::uuid IS NULL OR person_id = %s::uuid" in open_loop_query
    assert open_loop_params == (
        "open",
        "open",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        None,
        None,
        None,
        None,
        2,
    )


def test_list_artifacts_applies_type_domain_sensitivity_and_limit_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "artifact-1", "artifact_type": "daily_brief", "domain": "project", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    artifacts = store.list_artifacts(
        artifact_type="daily_brief",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=5,
    )

    assert artifacts[0]["id"] == "artifact-1"
    query, params = cursor.executed[0]
    assert "FROM generated_artifacts" in query
    assert "%s::text IS NULL OR artifact_type = %s" in query
    assert "domain = ANY" in query
    assert "sensitivity = ANY" in query
    assert params == (
        "daily_brief",
        "daily_brief",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        5,
    )


def test_artifact_quality_ratings_insert_and_export_json_safe_payloads() -> None:
    artifact_id = str(uuid4())
    rating_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": rating_id, "artifact_id": artifact_id, "reviewer_id": "samir"},
            _event_row(artifact_id),
        ],
        fetchall_result=[{"id": rating_id, "artifact_id": artifact_id, "usefulness": 5}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    created = store.create_artifact_quality_rating(
        {
            "id": rating_id,
            "artifact_id": artifact_id,
            "reviewer_id": "samir",
            "usefulness": 5,
            "accuracy": 4,
            "source_grounding": 5,
            "novel_connections": 3,
            "actionability": 4,
            "hallucination_risk": 1,
            "verbosity": "right_sized",
            "missed_context": "Needs one more source.",
            "comments": "Useful artifact.",
            "metadata_json": {"prompt_hash": "sha256:test"},
        }
    )
    rows = store.list_artifact_quality_ratings(artifact_id=artifact_id, limit=10)

    assert created["id"] == rating_id
    assert rows == [{"id": rating_id, "artifact_id": artifact_id, "usefulness": 5}]
    assert _event_log_insert_count(cursor) == 1
    insert_query, insert_params = cursor.executed[0]
    assert "INSERT INTO artifact_quality_ratings" in insert_query
    assert insert_params is not None
    assert isinstance(insert_params[-1], Jsonb)
    assert insert_params[-1].obj == {"prompt_hash": "sha256:test"}
    list_query, list_params = cursor.executed[2]
    assert "FROM artifact_quality_ratings" in list_query
    assert list_params == (artifact_id, artifact_id, 10)


def test_list_beliefs_joins_memory_domain_sensitivity_filters() -> None:
    belief_id = str(uuid4())
    memory_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {
                "id": belief_id,
                "memory_id": memory_id,
                "claim": "Alice should preserve provenance.",
                "domain": "project",
                "sensitivity": "private",
            },
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    beliefs = store.list_beliefs(
        status="active",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=6,
    )

    assert beliefs[0]["id"] == belief_id
    query, params = cursor.executed[0]
    assert "FROM beliefs b" in query
    assert "JOIN memories m" in query
    assert "%s::text IS NULL OR b.status = %s" in query
    assert "m.domain = ANY" in query
    assert "m.sensitivity = ANY" in query
    assert params == (
        "active",
        "active",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        6,
    )


def test_memory_revision_provenance_and_graph_methods_write_audit_events() -> None:
    memory_id = str(uuid4())
    revision_id = str(uuid4())
    provenance_id = str(uuid4())
    edge_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": memory_id},
            _event_row(memory_id),
            {"id": memory_id},
            {"id": memory_id},
            _event_row(memory_id),
            {"id": revision_id, "memory_id": memory_id},
            _event_row(memory_id),
            {"id": provenance_id, "target_type": "memory", "target_id": memory_id},
            _event_row(memory_id),
            {"id": edge_id, "edge_type": "supports"},
            _event_row(edge_id),
            {"id": edge_id, "edge_type": "supports"},
            _event_row(edge_id),
            {"id": edge_id, "edge_type": "supports", "metadata_json": {"status": "accepted"}},
            _event_row(edge_id),
        ],
        fetchall_result=[{"id": memory_id}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_memory(
        {
            "id": memory_id,
            "memory_key": "project.alice.status",
            "value": {"status": "building"},
            "canonical_text": "Alice vNext is being built.",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"source": "spec"},
        }
    )
    store.get_memory(memory_id)
    store.update_memory(memory_id=memory_id, patch={"status": "active", "metadata_json": {"reviewed": True}})
    store.list_memories(status="active")
    store.append_revision(
        {
            "id": revision_id,
            "memory_id": memory_id,
            "memory_key": "project.alice.status",
            "previous_value": {"status": "candidate"},
            "new_value": {"status": "active"},
            "text_after": "Alice vNext is active.",
            "revision_type": "promoted",
        }
    )
    store.list_revisions(memory_id)
    store.create_provenance_link(
        {
            "id": provenance_id,
            "target_type": "memory",
            "target_id": memory_id,
            "evidence_role": "supports",
            "confidence": 0.9,
        }
    )
    store.list_provenance_links(target_type="memory", target_id=memory_id)
    store.create_edge(
        {
            "id": edge_id,
            "from_type": "memory",
            "from_id": memory_id,
            "to_type": "project",
            "to_id": "alice-vnext",
            "edge_type": "supports",
            "created_by": "system",
        }
    )
    store.list_edges(from_id=memory_id)
    store.update_edge_status(edge_id=edge_id, status="accepted")
    store.expire_edge(edge_id=edge_id)

    assert _event_log_insert_count(cursor) == 7
    memory_insert_query = cursor.executed[0][0]
    assert "INSERT INTO memories" in memory_insert_query
    assert "canonical_text" in memory_insert_query
    assert "domain" in memory_insert_query
    assert "sensitivity" in memory_insert_query
    assert "metadata_json" in memory_insert_query
    assert any("WITH next_revision" in query for query, _params in cursor.executed)
    assert any("INSERT INTO provenance_links" in query for query, _params in cursor.executed)
    assert any("INSERT INTO graph_edges" in query for query, _params in cursor.executed)
    assert any("UPDATE graph_edges" in query for query, _params in cursor.executed)
    assert any("%s::text IS NULL OR from_id = %s" in query for query, _params in cursor.executed)
    update_edge_query, update_edge_params = cursor.executed[-4]
    assert "metadata_json = metadata_json || %s" in update_edge_query
    assert update_edge_params is not None
    assert update_edge_params[1] == "accepted"


def test_project_people_belief_and_open_loop_methods_write_audit_events() -> None:
    project_id = str(uuid4())
    person_id = str(uuid4())
    memory_id = str(uuid4())
    belief_id = str(uuid4())
    loop_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": project_id},
            _event_row(project_id),
            {"id": project_id},
            {"id": project_id},
            _event_row(project_id),
            {"id": person_id},
            _event_row(person_id),
            {"id": person_id},
            {"id": person_id},
            _event_row(person_id),
            {"id": belief_id, "memory_id": memory_id},
            _event_row(belief_id),
            {"id": belief_id, "memory_id": memory_id},
            {"id": belief_id, "memory_id": memory_id},
            _event_row(belief_id),
            {"id": loop_id},
            _event_row(loop_id),
            {"id": loop_id},
            {"id": loop_id},
            _event_row(loop_id),
            {"id": loop_id},
            _event_row(loop_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_project({"id": project_id, "name": "Alice vNext", "slug": "alice-vnext"})
    store.get_project(project_id)
    store.list_projects(status="active", domains=["project"], sensitivity_allowed=["private"], limit=3)
    store.update_project(project_id=project_id, patch={"current_state": "Sprint 1"})
    store.create_person({"id": person_id, "name": "Samir", "aliases_json": ["owner"]})
    store.get_person(person_id)
    store.update_person(person_id=person_id, patch={"notes": "Project owner"})
    store.create_belief({"id": belief_id, "memory_id": memory_id, "claim": "Provenance is mandatory."})
    store.get_belief(belief_id)
    store.update_belief_status(belief_id=belief_id, status="challenged", confidence=0.4)
    store.create_open_loop({"id": loop_id, "title": "Validate migration on Postgres", "priority": "high"})
    store.get_open_loop(loop_id)
    store.update_open_loop_status(loop_id=loop_id, status="resolved", resolution_note="Covered by CI")
    store.update_open_loop(loop_id=loop_id, patch={"title": "Validate migration", "priority": "normal"})

    assert _event_log_insert_count(cursor) == 9
    assert "INSERT INTO projects" in cursor.executed[0][0]
    assert "FROM projects" in cursor.executed[3][0]
    assert "%s::text IS NULL OR status = %s" in cursor.executed[3][0]
    assert cursor.executed[3][1] == ("active", "active", ["project"], ["project"], ["private"], ["private"], 3)
    assert "UPDATE projects" in cursor.executed[4][0]
    assert "INSERT INTO people" in cursor.executed[6][0]
    assert "UPDATE people" in cursor.executed[9][0]
    assert "INSERT INTO beliefs" in cursor.executed[11][0]
    assert "UPDATE beliefs" in cursor.executed[14][0]
    assert "INSERT INTO open_loops" in cursor.executed[16][0]
    assert "UPDATE open_loops" in cursor.executed[19][0]
    assert "UPDATE open_loops" in cursor.executed[21][0]


def test_artifact_task_and_brain_charter_methods_write_audit_events() -> None:
    artifact_id = str(uuid4())
    task_id = str(uuid4())
    charter_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": artifact_id, "artifact_type": "context_pack"},
            _event_row(artifact_id),
            {"id": artifact_id, "artifact_type": "context_pack"},
            {"id": artifact_id, "artifact_type": "context_pack"},
            _event_row(artifact_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": charter_id},
            _event_row(charter_id),
            {"id": charter_id},
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_artifact(
        {
            "id": artifact_id,
            "artifact_type": "context_pack",
            "title": "Sprint 1 Context",
            "content_markdown": "# Context",
            "generated_by": "system",
        }
    )
    store.get_artifact(artifact_id)
    store.update_artifact_status(artifact_id=artifact_id, status="reviewed")
    store.create_task(
        {
            "id": task_id,
            "title": "Synthesize evidence",
            "task_type": "synthesize",
            "instructions": "Create a context pack.",
            "scope_json": {"project": "alice-vnext"},
        }
    )
    claimed = store.claim_next_task()
    store.update_task_status(task_id=task_id, status="completed", details={"metadata_json": {"ok": True}})
    store.upsert_brain_charter(
        {
            "id": charter_id,
            "content_markdown": "# ALICE.md - Brain Charter",
            "owner_json": {"name": "Owner"},
            "autonomous_rules_json": ["Always preserve provenance."],
            "quality_standard_json": ["Do not fabricate."],
        }
    )
    store.get_brain_charter()

    assert claimed is not None
    assert _event_log_insert_count(cursor) == 6
    assert "INSERT INTO generated_artifacts" in cursor.executed[0][0]
    assert "UPDATE generated_artifacts" in cursor.executed[3][0]
    assert "INSERT INTO task_queue" in cursor.executed[5][0]
    assert "FOR UPDATE SKIP LOCKED" in cursor.executed[7][0]
    assert "UPDATE task_queue" in cursor.executed[9][0]
    assert "ON CONFLICT (user_id)" in cursor.executed[11][0]


def test_append_and_list_event_log_records_use_integrity_payload() -> None:
    event = build_event_log_record(
        event_type="memory.created",
        actor_type="system",
        target_type="memory",
        target_id="memory-1",
        payload={"b": 2, "a": 1},
        occurred_at="2026-05-10T12:00:00Z",
    )
    cursor = RecordingCursor(fetchone_results=[_event_row("memory-1")], fetchall_result=[_event_row("memory-1")])
    store = PostgresVNextStore(RecordingConnection(cursor))

    appended = store.append_event(event)
    events = store.list_events(target_type="memory", target_id="memory-1")
    all_events = store.list_events()

    assert appended["target_id"] == "memory-1"
    assert events[0]["target_id"] == "memory-1"
    assert all_events[0]["target_id"] == "memory-1"
    event_insert_query, event_insert_params = cursor.executed[0]
    assert "INSERT INTO event_log" in event_insert_query
    assert event_insert_params is not None
    assert event_insert_params[1:6] == (
        "memory.created",
        "system",
        None,
        "memory",
        "memory-1",
    )
    assert isinstance(event_insert_params[7], Jsonb)
    assert event_insert_params[7].obj == {"b": 2, "a": 1}
    assert event_insert_params[10] == event["integrity_hash"]
    event_list_query = cursor.executed[1][0]
    assert "%s::text IS NULL OR target_type = %s" in event_list_query
    assert "%s::text IS NULL OR target_id = %s" in event_list_query


def test_connector_settings_and_state_methods_use_dedicated_tables_and_audit_events() -> None:
    setting_id = str(uuid4())
    state_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": setting_id,
                "connector_name": "telegram",
                "enabled": True,
                "configured": True,
                "default_domain": "personal",
                "default_sensitivity": "private",
                "sync_mode": "polling",
                "poll_interval_seconds": 60,
                "secret_ref": "telegram.bot_token.default",
                "validation_errors_json": [],
            },
            _event_row("telegram"),
            {"id": setting_id, "connector_name": "telegram"},
                {
                    "id": state_id,
                    "connector_id": setting_id,
                    "connector_name": "telegram",
                    "cursor_type": "sync_cursor",
                    "cursor_value": "42",
                    "last_sync_at": "2026-05-11T12:00:00Z",
                    "last_success_at": "2026-05-11T12:00:00Z",
                    "last_failure_at": None,
                    "items_seen": 3,
                    "items_captured": 1,
                    "items_deduped": 1,
                "items_failed": 1,
            },
            _event_row("telegram"),
            {"id": state_id, "connector_name": "telegram", "cursor_value": "42"},
            {"connector_settings_exists": True, "connector_state_exists": True, "migration_revision": "20260511_0070"},
        ],
        fetchall_result=[{"id": setting_id, "connector_name": "telegram"}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    setting = store.upsert_connector_setting(
        {
            "connector_name": "telegram",
            "enabled": True,
            "configured": True,
            "default_domain": "personal",
            "default_sensitivity": "private",
            "sync_mode": "polling",
            "poll_interval_seconds": 60,
            "secret_ref": "telegram.bot_token.default",
            "validation_errors_json": [],
            "metadata_json": {"config_json": {"allowed_chat_ids": ["999001"]}},
        }
    )
    settings = store.list_connector_settings()
    fetched_setting = store.get_connector_setting("telegram")
    state = store.upsert_connector_state(
        {
            "connector_name": "telegram",
            "cursor_value": "42",
            "last_sync_at": "2026-05-11T12:00:00Z",
            "last_success_at": "2026-05-11T12:00:00Z",
            "items_seen_delta": 3,
            "items_captured_delta": 1,
            "items_deduped_delta": 1,
            "items_failed_delta": 1,
            "average_processing_time_ms": 12.5,
            "state_json": {"last_status": "partial"},
        }
    )
    fetched_state = store.get_connector_state("telegram")
    storage_status = store.connector_storage_status()

    assert setting["id"] == setting_id
    assert settings == [{"id": setting_id, "connector_name": "telegram"}]
    assert fetched_setting is not None
    assert state["cursor_value"] == "42"
    assert fetched_state is not None
    assert storage_status["connector_settings_exists"] is True
    assert _event_log_insert_count(cursor) == 2
    setting_query, setting_params = cursor.executed[0]
    assert "INSERT INTO connector_settings" in setting_query
    assert "ON CONFLICT (user_id, connector_name)" in setting_query
    assert setting_params is not None
    assert isinstance(setting_params[8], Jsonb)
    assert setting_params[8].obj == []
    assert isinstance(setting_params[9], Jsonb)
    assert setting_params[9].obj == {"config_json": {"allowed_chat_ids": ["999001"]}}
    state_query, state_params = cursor.executed[4]
    assert "INSERT INTO connector_state" in state_query
    assert "items_seen = connector_state.items_seen + EXCLUDED.items_seen" in state_query
    assert state_params is not None
    assert isinstance(state_params[-1], Jsonb)
    assert state_params[-1].obj == {"last_status": "partial"}


def test_workspace_list_methods_apply_bounded_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "workspace-row-1", "status": "active", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    sources = store.list_sources(domains=["project"], sensitivity_allowed=["private"], limit=7)
    people = store.list_people(sensitivity_allowed=["private"], limit=5)
    tasks = store.list_tasks(status=None, limit=4)
    events = store.list_events(limit=3)

    assert sources[0]["id"] == "workspace-row-1"
    assert people[0]["id"] == "workspace-row-1"
    assert tasks[0]["id"] == "workspace-row-1"
    assert events[0]["id"] == "workspace-row-1"

    source_query, source_params = cursor.executed[0]
    people_query, people_params = cursor.executed[1]
    task_query, task_params = cursor.executed[2]
    event_query, event_params = cursor.executed[3]
    assert "FROM sources" in source_query
    assert "deleted_at IS NULL" in source_query
    assert source_params == (["project"], ["project"], ["private"], ["private"], 7)
    assert "FROM people" in people_query
    assert people_params == (["private"], ["private"], 5)
    assert "FROM task_queue" in task_query
    assert task_params == (None, None, 4)
    assert "FROM event_log" in event_query
    assert "LIMIT %s" in event_query
    assert event_params == (3,)


def test_jsonb_and_event_hash_normalize_postgres_scalar_values() -> None:
    project_id = uuid4()
    captured_at = datetime(2026, 5, 10, 12, 30, tzinfo=UTC)
    event = build_event_log_record(
        event_type="project.update_candidate_created",
        actor_type="system",
        target_type="project",
        target_id=str(project_id),
        payload={
            "project_id": project_id,
            "source": {
                "captured_at": captured_at,
            },
        },
    )
    cursor = RecordingCursor(fetchone_results=[{"id": str(project_id)}, _event_row(project_id)])
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_project(
        {
            "id": str(project_id),
            "name": "Alice vNext",
            "slug": "alice-vnext",
            "metadata_json": {
                "candidate_memory_id": project_id,
                "source_captured_at": captured_at,
            },
        }
    )

    assert event["payload_json"] == {
        "project_id": str(project_id),
        "source": {
            "captured_at": "2026-05-10T12:30:00+00:00",
        },
    }
    project_insert_params = cursor.executed[0][1]
    assert project_insert_params is not None
    assert isinstance(project_insert_params[-1], Jsonb)
    assert project_insert_params[-1].obj == {
        "candidate_memory_id": str(project_id),
        "source_captured_at": "2026-05-10T12:30:00+00:00",
    }
