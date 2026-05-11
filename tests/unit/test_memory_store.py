from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.store import ContinuityStore, ContinuityStoreInvariantError


class RecordingCursor:
    def __init__(
        self,
        fetchone_results: list[dict[str, Any]],
        fetchall_results: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_results = list(fetchall_results or [])

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        if not self.fetchall_results:
            return []
        return self.fetchall_results.pop(0)


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_memory_methods_use_expected_queries_and_payload_serialization() -> None:
    memory_id = uuid4()
    event_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": memory_id,
                "user_id": uuid4(),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "black"},
                "status": "active",
                "source_event_ids": [str(event_id)],
            },
            {
                "id": memory_id,
                "user_id": uuid4(),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": [str(event_id)],
            },
            {
                "id": uuid4(),
                "memory_id": memory_id,
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "black"},
                "source_event_ids": [str(event_id)],
                "candidate": {"memory_key": "user.preference.coffee"},
            },
        ],
        fetchall_results=[
            [{"id": event_id, "sequence_no": 1}],
            [{"sequence_no": 1, "action": "ADD"}],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_memory(
        memory_key="user.preference.coffee",
        value={"likes": "black"},
        status="active",
        source_event_ids=[str(event_id)],
    )
    updated = store.update_memory(
        memory_id=memory_id,
        value={"likes": "oat milk"},
        status="active",
        source_event_ids=[str(event_id)],
    )
    revision = store.append_memory_revision(
        memory_id=memory_id,
        action="ADD",
        memory_key="user.preference.coffee",
        previous_value=None,
        new_value={"likes": "black"},
        source_event_ids=[str(event_id)],
        candidate={"memory_key": "user.preference.coffee"},
    )
    listed_events = store.list_events_by_ids([event_id])
    listed_revisions = store.list_memory_revisions(memory_id)
    listed_context_memories = store.list_context_memories()

    assert created["id"] == memory_id
    assert updated["value"] == {"likes": "oat milk"}
    assert revision["sequence_no"] == 1
    assert listed_events == [{"id": event_id, "sequence_no": 1}]
    assert listed_revisions == [{"sequence_no": 1, "action": "ADD"}]
    assert listed_context_memories == []

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO memories" in create_query
    assert "clock_timestamp()" in create_query
    assert create_params is not None
    assert create_params[0] == "user.preference.coffee"
    assert isinstance(create_params[1], Jsonb)
    assert create_params[1].obj == {"likes": "black"}
    assert create_params[2] == "active"
    assert isinstance(create_params[3], Jsonb)
    assert create_params[3].obj == [str(event_id)]
    assert create_params[4] == "preference"
    assert create_params[5] is None
    assert create_params[6] is None
    assert create_params[7] == "unconfirmed"
    assert create_params[8] == "deterministic"
    assert create_params[9] == "promotable"
    assert create_params[10] is None
    assert create_params[11] is None
    assert create_params[12] is None
    assert create_params[13] is None
    assert create_params[14] is None
    assert create_params[15] is None
    assert create_params[16] is None
    assert create_params[17] == "assistant_default"

    update_query, update_params = cursor.executed[1]
    assert "UPDATE memories" in update_query
    assert "updated_at = clock_timestamp()" in update_query
    assert "THEN clock_timestamp()" in update_query
    assert update_params is not None
    assert isinstance(update_params[0], Jsonb)
    assert update_params[0].obj == {"likes": "oat milk"}
    assert update_params[1] == "active"
    assert isinstance(update_params[2], Jsonb)
    assert update_params[2].obj == [str(event_id)]
    assert update_params[3] == "preference"
    assert update_params[4] is None
    assert update_params[5] is None
    assert update_params[6] == "unconfirmed"
    assert update_params[7] == "deterministic"
    assert update_params[8] == "promotable"
    assert update_params[9] is None
    assert update_params[10] is None
    assert update_params[11] is None
    assert update_params[12] is None
    assert update_params[13] is None
    assert update_params[14] is None
    assert update_params[15] is None
    assert update_params[16] == "active"
    assert update_params[17] == memory_id

    assert cursor.executed[2] == (
        "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 1))",
        (str(memory_id),),
    )
    append_revision_query, append_revision_params = cursor.executed[3]
    assert "INSERT INTO memory_revisions" in append_revision_query
    assert append_revision_params is not None
    assert append_revision_params[:5] == (
        memory_id,
        memory_id,
        "ADD",
        "ADD",
        "user.preference.coffee",
    )
    assert isinstance(append_revision_params[5], Jsonb)
    assert append_revision_params[5].obj is None
    assert isinstance(append_revision_params[6], Jsonb)
    assert append_revision_params[6].obj == {"likes": "black"}
    assert isinstance(append_revision_params[7], Jsonb)
    assert append_revision_params[7].obj == [str(event_id)]
    assert isinstance(append_revision_params[8], Jsonb)
    assert append_revision_params[8].obj == {"memory_key": "user.preference.coffee"}
    assert append_revision_params[9] is None
    assert append_revision_params[10] == '{"likes": "black"}'
    assert cursor.executed[6] == (
        """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """,
        None,
    )


def test_get_memory_by_key_returns_none_when_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    assert store.get_memory_by_key("user.preference.coffee") is None


def test_append_memory_revision_raises_clear_error_when_returning_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="append_memory_revision did not return a row",
    ):
        store.append_memory_revision(
            memory_id=uuid4(),
            action="ADD",
            memory_key="user.preference.coffee",
            previous_value=None,
            new_value={"likes": "black"},
            source_event_ids=["event-1"],
            candidate={"memory_key": "user.preference.coffee"},
        )


def test_memory_review_read_methods_use_explicit_order_filter_and_limit() -> None:
    memory_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": memory_id,
                "user_id": uuid4(),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "black"},
                "status": "active",
                "source_event_ids": ["event-1"],
            },
            {"count": 2},
            {"count": 3},
        ],
        fetchall_results=[
            [{"id": memory_id, "memory_key": "user.preference.coffee"}],
            [{"sequence_no": 1, "action": "ADD"}],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    memory = store.get_memory_optional(memory_id)
    memory_count = store.count_memories(status="active")
    listed_memories = store.list_review_memories(status="active", limit=5)
    revision_count = store.count_memory_revisions(memory_id)
    listed_revisions = store.list_memory_revisions(memory_id, limit=2)

    assert memory is not None
    assert memory["id"] == memory_id
    assert memory_count == 2
    assert listed_memories == [{"id": memory_id, "memory_key": "user.preference.coffee"}]
    assert revision_count == 3
    assert listed_revisions == [{"sequence_no": 1, "action": "ADD"}]
    assert cursor.executed == [
        (
            """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = %s
                """,
            (memory_id,),
        ),
        (
            """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = %s
                """,
            ("active",),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = %s
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            ("active", 5),
        ),
        (
            """
                SELECT COUNT(*) AS count
                FROM memory_revisions
                WHERE memory_id = %s
                """,
            (memory_id,),
        ),
        (
            """
                SELECT id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                FROM memory_revisions
                WHERE memory_id = %s
                ORDER BY sequence_no ASC
                LIMIT %s
                """,
            (memory_id, 2),
        ),
    ]


def test_memory_review_label_methods_use_append_only_queries_and_deterministic_order() -> None:
    memory_id = uuid4()
    reviewer_user_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": uuid4(),
                "user_id": reviewer_user_id,
                "memory_id": memory_id,
                "label": "correct",
                "note": "Supported by the latest event.",
                "created_at": "2026-03-12T09:00:00+00:00",
            }
        ],
        fetchall_results=[
            [
                {
                    "id": uuid4(),
                    "user_id": reviewer_user_id,
                    "memory_id": memory_id,
                    "label": "correct",
                    "note": "Supported by the latest event.",
                    "created_at": "2026-03-12T09:00:00+00:00",
                }
            ],
            [
                {"label": "correct", "count": 1},
                {"label": "outdated", "count": 2},
            ],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_memory_review_label(
        memory_id=memory_id,
        label="correct",
        note="Supported by the latest event.",
    )
    listed = store.list_memory_review_labels(memory_id)
    counts = store.list_memory_review_label_counts(memory_id)

    assert created["memory_id"] == memory_id
    assert listed[0]["label"] == "correct"
    assert counts == [{"label": "correct", "count": 1}, {"label": "outdated", "count": 2}]
    assert cursor.executed == [
        (
            """
                INSERT INTO memory_review_labels (user_id, memory_id, label, note)
                VALUES (app.current_user_id(), %s, %s, %s)
                RETURNING id, user_id, memory_id, label, note, created_at
                """,
            (memory_id, "correct", "Supported by the latest event."),
        ),
        (
            """
                SELECT id, user_id, memory_id, label, note, created_at
                FROM memory_review_labels
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """,
            (memory_id,),
        ),
        (
            """
                SELECT label, COUNT(*) AS count
                FROM memory_review_labels
                WHERE memory_id = %s
                GROUP BY label
                ORDER BY label ASC
                """,
            (memory_id,),
        ),
    ]


def test_open_loop_methods_use_expected_queries_and_lifecycle_serialization() -> None:
    memory_id = uuid4()
    open_loop_id = uuid4()
    opened_at = datetime(2026, 3, 23, 11, 0, tzinfo=UTC)
    due_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
    resolved_at = datetime(2026, 3, 24, 9, 0, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": open_loop_id,
                "user_id": uuid4(),
                "memory_id": memory_id,
                "title": "Confirm magnesium reorder",
                "status": "open",
                "opened_at": opened_at,
                "due_at": due_at,
                "resolved_at": None,
                "resolution_note": None,
                "created_at": opened_at,
                "updated_at": opened_at,
            },
            {
                "id": open_loop_id,
                "user_id": uuid4(),
                "memory_id": memory_id,
                "title": "Confirm magnesium reorder",
                "status": "open",
                "opened_at": opened_at,
                "due_at": due_at,
                "resolved_at": None,
                "resolution_note": None,
                "created_at": opened_at,
                "updated_at": opened_at,
            },
            {"count": 1},
            {"count": 1},
            {
                "id": open_loop_id,
                "user_id": uuid4(),
                "memory_id": memory_id,
                "title": "Confirm magnesium reorder",
                "status": "resolved",
                "opened_at": opened_at,
                "due_at": due_at,
                "resolved_at": resolved_at,
                "resolution_note": "Resolved after order confirmation.",
                "created_at": opened_at,
                "updated_at": resolved_at,
            },
        ],
        fetchall_results=[
            [
                {
                    "id": open_loop_id,
                    "memory_id": memory_id,
                    "status": "open",
                    "opened_at": opened_at,
                }
            ],
            [
                {
                    "id": open_loop_id,
                    "memory_id": memory_id,
                    "status": "open",
                    "opened_at": opened_at,
                }
            ],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_open_loop(
        memory_id=memory_id,
        title="Confirm magnesium reorder",
        status="open",
        opened_at=None,
        due_at=due_at,
        resolved_at=None,
        resolution_note=None,
    )
    detail = store.get_open_loop_optional(open_loop_id)
    listed_all = store.list_open_loops(limit=5)
    listed_open = store.list_open_loops(status="open", limit=3)
    count_all = store.count_open_loops()
    count_open = store.count_open_loops(status="open")
    updated = store.update_open_loop_status_optional(
        open_loop_id=open_loop_id,
        status="resolved",
        resolved_at=None,
        resolution_note="Resolved after order confirmation.",
    )

    assert created["id"] == open_loop_id
    assert detail is not None
    assert detail["status"] == "open"
    assert listed_all[0]["id"] == open_loop_id
    assert listed_open[0]["status"] == "open"
    assert count_all == 1
    assert count_open == 1
    assert updated is not None
    assert updated["status"] == "resolved"
    assert updated["resolved_at"] == resolved_at

    assert cursor.executed[0] == (
        """
                INSERT INTO open_loops (
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                """,
        (memory_id, "Confirm magnesium reorder", "open", None, due_at, None, None),
    )
    assert cursor.executed[1] == (
        """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                WHERE id = %s
                """,
        (open_loop_id,),
    )
    assert cursor.executed[2] == (
        """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
        (5,),
    )
    assert cursor.executed[3] == (
        """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                WHERE status = %s
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
        ("open", 3),
    )
    assert cursor.executed[4] == (
        """
                SELECT COUNT(*) AS count
                FROM open_loops
                """,
        None,
    )
    assert cursor.executed[5] == (
        """
                SELECT COUNT(*) AS count
                FROM open_loops
                WHERE status = %s
                """,
        ("open",),
    )
    assert cursor.executed[6] == (
        """
                UPDATE open_loops
                SET status = %s,
                    resolved_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE COALESCE(%s, clock_timestamp())
                    END,
                    resolution_note = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE %s
                    END,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                """,
        (
            "resolved",
            "resolved",
            None,
            "resolved",
            "Resolved after order confirmation.",
            open_loop_id,
        ),
    )
