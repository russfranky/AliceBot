from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    encoded_body = b"" if payload is None else json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start_message["status"]), json.loads(body)


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_vnext_live_workspace_happy_path_writes_reviewable_postgres_state(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="vnext-live-workspace@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )
    user_id_text = str(user_id)

    workspace_status, workspace_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert workspace_status == 200
    assert workspace_payload["mode"] == "live"
    assert workspace_payload["summary"]["source_count"] == 0

    project_status, project_payload = invoke_request(
        "POST",
        "/v0/vnext/projects",
        payload={
            "user_id": user_id_text,
            "name": "Alice Live UI",
            "description": "Live-backed vNext workspace sprint.",
            "current_state": "Preparing live workspace smoke coverage.",
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert project_status == 201
    project_id = project_payload["project"]["id"]

    source_status, source_payload = invoke_request(
        "POST",
        "/v0/vnext/sources",
        payload={
            "user_id": user_id_text,
            "raw_text": "\n".join(
                [
                    "Decision: Alice Live UI uses Postgres workspace data.",
                    "Todo: Confirm project dashboard updates before release.",
                    "Question: Did the live workspace preserve provenance?",
                ]
            ),
            "title": "Live workspace launch note",
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert source_status == 201
    assert source_payload["candidate_memory_count"] >= 3
    source_id = source_payload["source_id"]

    refreshed_status, refreshed_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert refreshed_status == 200
    assert refreshed_payload["summary"]["source_count"] == 1
    assert refreshed_payload["summary"]["candidate_memory_count"] >= 3
    review_memories = refreshed_payload["review_memories"]
    decision_memory = next(memory for memory in review_memories if "Alice Live UI" in memory["canonical_text"])
    rejected_memory = next(memory for memory in review_memories if memory["id"] != decision_memory["id"])

    edit_status, edit_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "edit",
            "canonical_text": "Alice Live UI uses Postgres workspace data with provenance intact.",
            "summary": "Alice Live UI is backed by Postgres workspace state.",
            "domain": "project",
            "sensitivity": "private",
            "reason": "Smoke-test edit before accepting the candidate.",
        },
    )
    assert edit_status == 200
    assert edit_payload["memory"]["canonical_text"].startswith("Alice Live UI uses Postgres")

    assign_status, assign_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "assign_project",
            "project_id": project_id,
            "reason": "Attach the accepted memory to the live UI project.",
        },
    )
    assert assign_status == 200
    assert assign_payload["memory"]["metadata_json"]["project_id"] == project_id

    accept_status, accept_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={"user_id": user_id_text, "action": "accept"},
    )
    assert accept_status == 200
    assert accept_payload["memory"]["status"] == "active"

    reject_status, reject_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{rejected_memory['id']}/review",
        payload={"user_id": user_id_text, "action": "reject", "reason": "Smoke-test rejection path."},
    )
    assert reject_status == 200
    assert reject_payload["memory"]["status"] == "rejected"

    pack_status, pack_payload = invoke_request(
        "POST",
        "/v0/vnext/context-packs",
        payload={
            "user_id": user_id_text,
            "query": "Alice Live UI uses Postgres",
            "scope": {"domains": ["project"]},
            "options": {"sensitivity_allowed": ["public", "internal", "private", "unknown"], "max_items": 6},
        },
    )
    assert pack_status == 201
    assert pack_payload["relevant_memories"]
    assert pack_payload["sources"]
    assert pack_payload["trace"]["selected_count"] >= 2
    assert "supporting_evidence" in pack_payload
    assert "contradicting_evidence" in pack_payload

    open_loop_status, open_loop_payload = invoke_request(
        "POST",
        "/v0/vnext/open-loops",
        payload={
            "user_id": user_id_text,
            "title": "Confirm project dashboard updates before release",
            "description": "Created from the live /vnext workspace smoke.",
            "priority": "high",
            "memory_id": decision_memory["id"],
            "project_id": project_id,
            "source_id": source_id,
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert open_loop_status == 201
    loop_id = open_loop_payload["open_loop"]["id"]

    edit_loop_status, edit_loop_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={
            "user_id": user_id_text,
            "action": "edit",
            "title": "Confirm dashboard counts before release",
            "priority": "urgent",
        },
    )
    assert edit_loop_status == 200
    assert edit_loop_payload["priority"] == "urgent"

    snooze_status, snooze_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "snooze", "due_at": "2026-05-12T09:00:00Z"},
    )
    assert snooze_status == 200
    assert snooze_payload["due_at"].startswith("2026-05-12T09:00:00")

    close_status, close_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "close", "resolution_note": "Closed in smoke."},
    )
    assert close_status == 200
    assert close_payload["status"] == "resolved"

    reopen_status, reopen_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "reopen"},
    )
    assert reopen_status == 200
    assert reopen_payload["status"] == "open"

    daily_status, daily_payload = invoke_request(
        "POST",
        "/v0/vnext/artifacts/generate/daily-brief",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"generated_for": "2026-05-11"},
        },
    )
    assert daily_status == 201
    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["status"] == "needs_review"

    daily_review_status, daily_review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{daily_payload['id']}/review",
        payload={"user_id": user_id_text, "action": "archive"},
    )
    assert daily_review_status == 200
    assert daily_review_payload["status"] == "archived"

    weekly_status, weekly_payload = invoke_request(
        "POST",
        "/v0/vnext/artifacts/generate/weekly-synthesis",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"generated_for": "2026-05-11"},
        },
    )
    assert weekly_status == 201
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"]

    weekly_review_status, weekly_review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{weekly_payload['id']}/review",
        payload={"user_id": user_id_text, "action": "accept"},
    )
    assert weekly_review_status == 200
    assert weekly_review_payload["status"] == "accepted"

    project_update_status, project_update_payload = invoke_request(
        "POST",
        "/v0/vnext/projects/update-candidates",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"project_id": project_id, "max_items": 6},
        },
    )
    assert project_update_status == 201
    assert project_update_payload["artifact_type"] == "project_update"
    assert project_update_payload["status"] == "needs_review"

    dashboard_status, dashboard_payload = invoke_request(
        "GET",
        f"/v0/vnext/projects/{project_id}/dashboard",
        query_params={"user_id": user_id_text},
    )
    assert dashboard_status == 200
    assert dashboard_payload["counts"]["memories"] >= 1
    assert dashboard_payload["counts"]["open_loops"] >= 1
    assert dashboard_payload["counts"]["artifacts"] >= 1

    charter_status, charter_payload = invoke_request(
        "PUT",
        "/v0/vnext/settings/brain-charter",
        payload={
            "user_id": user_id_text,
            "content_markdown": "# ALICE.md\n\nPrefer provenance-first review.",
            "owner_json": {"name": "Alice Live UI"},
            "memory_philosophy_json": {"promotion": "review_required"},
            "life_domains_json": {"project": {"default_sensitivity": "private"}},
            "active_projects_json": [{"id": project_id, "name": "Alice Live UI"}],
            "communication_style_json": {"tone": "direct"},
            "priorities_json": {"current": ["live workspace"]},
            "autonomous_rules_json": [{"rule": "no_auto_promotion"}],
            "quality_standard_json": [{"rule": "source-backed"}],
            "sensitivity": "private",
        },
    )
    assert charter_status == 200
    assert charter_payload["brain_charter"]["content_markdown"].startswith("# ALICE.md")

    charter_get_status, charter_get_payload = invoke_request(
        "GET",
        "/v0/vnext/settings/brain-charter",
        query_params={"user_id": user_id_text},
    )
    assert charter_get_status == 200
    assert charter_get_payload["brain_charter"]["owner_json"]["name"] == "Alice Live UI"

    final_workspace_status, final_workspace_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert final_workspace_status == 200
    assert final_workspace_payload["summary"]["artifact_count"] >= 3
    assert final_workspace_payload["project_dashboards"][0]["counts"]["open_loops"] >= 1
    assert final_workspace_payload["brain_charter"]["id"] == charter_payload["brain_charter"]["id"]
    assert final_workspace_payload["recent_events"]

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event_type FROM event_log ORDER BY occurred_at ASC, id ASC")
            event_types = {row["event_type"] for row in cur.fetchall()}
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = 'active'
                  AND memory_type = 'artifact_summary'
                  AND metadata_json ->> 'discovered_by' = 'vnext_weekly_synthesis'
                """
            )
            active_artifact_summary_count = cur.fetchone()["count"]

    assert {
        "project.created",
        "source.created",
        "source.captured",
        "memory.updated",
        "memory_revision.created",
        "graph_edge.created",
        "retrieval.context_pack_compiled",
        "open_loop.created",
        "open_loop.updated",
        "artifact.generated",
        "artifact.reviewed",
        "project.update_candidate_created",
        "brain_charter.upserted",
    }.issubset(event_types)
    assert active_artifact_summary_count == 0
