from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from io import BytesIO
import json
from uuid import UUID, uuid4

import pytest

import alicebot_api.mcp_server as mcp_server
import alicebot_api.mcp_tools as mcp_tools_module
from alicebot_api.mcp_tools import MCPRuntimeContext, MCPToolError, MCPToolNotFoundError, call_mcp_tool, list_mcp_tools


def test_mcp_tool_surface_is_adr_aligned_and_deterministic() -> None:
    tools = list_mcp_tools()
    names = [tool["name"] for tool in tools]
    assert names == [
        "alice_capture",
        "alice_capture_candidates",
        "alice_commit_captures",
        "alice_memory_mutations_generate",
        "alice_memory_mutations_list_candidates",
        "alice_memory_mutations_commit",
        "alice_memory_mutations_list_operations",
        "alice_recall",
        "alice_recall_debug",
        "alice_state_at",
        "alice_resume",
        "alice_resume_debug",
        "alice_brief",
        "alice_task_brief",
        "alice_task_brief_show",
        "alice_task_brief_compare",
        "alice_retrieval_trace",
        "alice_prefetch_context",
        "alice_open_loops",
        "alice_recent_decisions",
        "alice_recent_changes",
        "alice_timeline",
        "alice_review_queue",
        "alice_review_apply",
        "alice_contradictions_detect",
        "alice_contradictions_list",
        "alice_contradictions_resolve",
        "alice_trust_signals",
        "alice_memory_review",
        "alice_memory_correct",
        "alice_explain",
        "alice_artifact_inspect",
        "alice_context_pack",
        "alice_vnext_context_pack",
        "alice_generate_daily_brief",
        "alice_generate_weekly_synthesis",
        "alice_generate_connections",
        "alice_graph_edge_review",
        "alice_graph_neighborhood",
        "alice_generate_contradictions",
        "alice_belief_review",
        "alice_belief_state",
        "alice_project_update_candidate",
        "alice_project_update_review",
        "alice_project_dashboard",
        "alice_open_loop_extract",
        "alice_open_loop_review",
        "alice_vnext_capture",
        "alice_vnext_queue_task",
        "alice_vnext_generate_artifact",
        "alice_vnext_project_dashboard",
        "alice_vnext_open_loops",
        "alice_vnext_recent_decisions",
        "alice_vnext_recent_changes",
        "alice_vnext_find_connections",
        "alice_vnext_find_contradictions",
        "alice_vnext_propose_memory",
        "alice_vnext_review_items",
        "alice_vnext_artifact_get",
        "alice_vnext_artifact_review",
        "alice_vnext_scheduler_status",
        "alice_vnext_scheduler_run_now",
        "alice_vnext_scheduler_run_due",
        "alice_vnext_scheduler_pause",
        "alice_vnext_scheduler_resume",
    ]

    for tool in tools:
        assert isinstance(tool["inputSchema"], dict)
        assert tool["inputSchema"].get("type") == "object"
        assert tool["inputSchema"].get("additionalProperties") is False


def test_call_mcp_tool_rejects_unknown_tool() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolNotFoundError, match="unknown tool"):
        call_mcp_tool(context, name="alice_nonexistent", arguments={})


def test_call_mcp_tool_requires_object_arguments() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolError, match="tool arguments must be a JSON object"):
        call_mcp_tool(context, name="alice_recall", arguments=["not-a-json-object"])


class FakeVNextMCPStore:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.open_loops: list[dict[str, object]] = []
        self.edges: dict[str, dict[str, object]] = {}
        self.projects: dict[str, dict[str, object]] = {
            "project-1": {
                "id": "project-1",
                "name": "Alice vNext",
                "slug": "alice-vnext",
                "status": "active",
                "current_state": "Sprint 7 complete.",
                "domain": "project",
                "sensitivity": "private",
            }
        }
        self.revisions: list[dict[str, object]] = []
        self.beliefs: dict[str, dict[str, object]] = {
            "belief-1": {
                "id": "belief-1",
                "memory_id": "memory-belief-1",
                "claim": "Alice should auto-promote generated artifacts into memory.",
                "status": "active",
                "confidence": 0.8,
                "domain": "project",
                "sensitivity": "private",
                "memory_type": "belief",
            }
        }

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
        self.artifacts[str(row["id"])] = row
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 2}"}
        self.memories.append(row)
        return row

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        for memory in self.memories:
            if memory["id"] == memory_id:
                memory.update(patch)
                return memory
        raise AssertionError(memory_id)

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops.append(row)
        return row

    def create_edge(self, edge: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**edge, "id": f"edge-{len(self.edges) + 1}"}
        self.edges[str(row["id"])] = row
        return row

    def update_edge_status(self, *, edge_id: str, status: str, **_kwargs) -> dict[str, object]:
        edge = self.edges[edge_id]
        metadata = edge.get("metadata_json")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update({"status": status, "candidate": status != "accepted"})
        edge["metadata_json"] = metadata
        if status == "rejected":
            edge["valid_to"] = "now"
        return edge

    def search_memories(self, **_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": "memory-1",
                "memory_type": "semantic",
                "canonical_text": "Alice vNext MCP context packs preserve provenance.",
                "status": "active",
                "confidence": 0.9,
                "domain": "project",
                "sensitivity": "private",
                "first_seen_at": "2026-05-10T00:00:00Z",
                "last_seen_at": "2026-05-10T00:00:00Z",
            }
        ][: _kwargs.get("limit", 8)]

    def search_sources(self, **_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Alice vNext MCP source",
                "content_hash": "sha256:abc",
                "captured_at": "2026-05-10T00:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "raw_text": (
                        "TODO: validate MCP brief generation Owner: Samir\n"
                        "Alice should not auto-promote generated artifacts into memory."
                    )
                },
            }
        ][: _kwargs.get("limit", 8)]

    def list_open_loops(self, **_kwargs) -> list[dict[str, object]]:
        status = _kwargs.get("status", "open")
        project_id = _kwargs.get("project_id")
        return [
            row
            for row in self.open_loops
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
        ]

    def get_open_loop(self, loop_id: str) -> dict[str, object] | None:
        for loop in self.open_loops:
            if loop["id"] == loop_id:
                return loop
        return None

    def update_open_loop(self, *, loop_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        loop = self.get_open_loop(loop_id)
        if loop is None:
            raise AssertionError(loop_id)
        loop.update(patch)
        return loop

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        loop = self.update_open_loop(loop_id=loop_id, patch={"status": status})
        if resolution_note is not None:
            loop["resolution_note"] = resolution_note
        return loop

    def list_artifacts(self, **_kwargs) -> list[dict[str, object]]:
        return list(self.artifacts.values())[: _kwargs.get("limit", 4)]

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def list_projects(self, **kwargs) -> list[dict[str, object]]:
        status = kwargs.get("status", "active")
        limit = kwargs.get("limit", 8)
        return [row for row in self.projects.values() if status is None or row.get("status") == status][:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def list_edges(self, **kwargs) -> list[dict[str, object]]:
        from_id = kwargs.get("from_id")
        to_id = kwargs.get("to_id")
        return [
            edge
            for edge in self.edges.values()
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def list_beliefs(self, **kwargs) -> list[dict[str, object]]:
        status = kwargs.get("status", "active")
        return [row for row in self.beliefs.values() if status is None or row.get("status") == status]

    def get_belief(self, belief_id: str) -> dict[str, object] | None:
        return self.beliefs.get(belief_id)

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        belief = self.beliefs[belief_id]
        belief["status"] = status
        if confidence is not None:
            belief["confidence"] = confidence
        if superseded_by is not None:
            belief["superseded_by"] = superseded_by
        self.append_event(
            {
                "event_type": "belief.updated",
                "target_type": "belief",
                "target_id": belief_id,
                "payload_json": {"status": status},
            }
        )
        return belief

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[dict[str, object]]:
        return [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]

    def list_provenance_links(self, **_kwargs) -> list[dict[str, object]]:
        return []


def test_alice_vnext_context_pack_mcp_tool(monkeypatch) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_context_pack",
        arguments={"query": "Alice vNext MCP provenance", "domains": ["project"]},
    )

    assert payload["relevant_memories"][0]["id"] == "memory-1"
    assert payload["sources"][0]["id"] == "source-1"
    assert payload["trace_id"] == payload["trace"]["trace_id"]
    assert store.events[-1]["event_type"] == "retrieval.context_pack_compiled"


def test_alice_vnext_context_pack_mcp_tool_normalizes_row_scalars(monkeypatch) -> None:
    store = FakeVNextMCPStore()
    memory_id = uuid4()
    source_id = uuid4()
    captured_at = datetime(2026, 5, 10, 9, 0, tzinfo=UTC)

    def search_memories(**_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": memory_id,
                "memory_type": "semantic",
                "canonical_text": "Coffee preference is pour over.",
                "status": "active",
                "confidence": 0.9,
                "domain": "personal",
                "sensitivity": "private",
                "first_seen_at": captured_at,
                "last_seen_at": captured_at,
            }
        ]

    def search_sources(**_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": source_id,
                "source_type": "manual_text",
                "title": "Coffee note",
                "content_hash": "sha256:coffee",
                "captured_at": captured_at,
                "domain": "personal",
                "sensitivity": "private",
            }
        ]

    store.search_memories = search_memories  # type: ignore[method-assign]
    store.search_sources = search_sources  # type: ignore[method-assign]

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_context_pack",
        arguments={"query": "coffee preference"},
    )

    json.dumps(payload)
    assert payload["relevant_memories"][0]["id"] == str(memory_id)
    assert payload["relevant_memories"][0]["first_seen_at"] == "2026-05-10T09:00:00+00:00"
    assert payload["sources"][0]["id"] == str(source_id)


def test_alice_generate_daily_and_weekly_brief_mcp_tools(monkeypatch) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    daily_payload = call_mcp_tool(
        context,
        name="alice_generate_daily_brief",
        arguments={"generated_for": "2026-05-10", "domains": ["project"]},
    )
    weekly_payload = call_mcp_tool(
        context,
        name="alice_generate_weekly_synthesis",
        arguments={"generated_for": "2026-05-10", "domains": ["project"]},
    )

    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["metadata_json"]["candidate_open_loop_ids"] == ["loop-1"]
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"] == ["memory-2"]
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_alice_generate_connections_and_graph_mcp_tools(monkeypatch) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    connection_payload = call_mcp_tool(
        context,
        name="alice_generate_connections",
        arguments={"domains": ["project"], "max_connections": 1},
    )
    review_payload = call_mcp_tool(
        context,
        name="alice_graph_edge_review",
        arguments={"edge_id": "edge-1", "action": "accept"},
    )
    neighborhood_payload = call_mcp_tool(
        context,
        name="alice_graph_neighborhood",
        arguments={"target_id": "source-1"},
    )

    assert connection_payload["artifact_type"] == "connection_report"
    assert connection_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["metadata_json"]["status"] == "accepted"
    assert neighborhood_payload["edge_count"] == 1
    assert neighborhood_payload["from_edges"][0]["id"] == "edge-1"


def test_alice_generate_contradictions_and_belief_mcp_tools(monkeypatch) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    contradiction_payload = call_mcp_tool(
        context,
        name="alice_generate_contradictions",
        arguments={"domains": ["project"], "max_contradictions": 1},
    )
    review_payload = call_mcp_tool(
        context,
        name="alice_belief_review",
        arguments={"belief_id": "belief-1", "action": "challenge", "confidence": 0.2},
    )
    state_payload = call_mcp_tool(
        context,
        name="alice_belief_state",
        arguments={"belief_id": "belief-1"},
    )

    assert contradiction_payload["artifact_type"] == "contradiction_report"
    assert contradiction_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["status"] == "challenged"
    assert review_payload["confidence"] == 0.2
    assert state_payload["current"]["status"] == "challenged"
    assert "challenged" in state_payload["previous_statuses"]


def test_alice_project_and_open_loop_mcp_tools(monkeypatch) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    update_payload = call_mcp_tool(
        context,
        name="alice_project_update_candidate",
        arguments={"project_id": "project-1", "domains": ["project"]},
    )
    extract_payload = call_mcp_tool(
        context,
        name="alice_open_loop_extract",
        arguments={"project_id": "project-1", "domains": ["project"]},
    )
    review_update_payload = call_mcp_tool(
        context,
        name="alice_project_update_review",
        arguments={
            "artifact_id": "artifact-1",
            "action": "edit",
            "edited_current_state": "Project automation reviewed.",
        },
    )
    review_loop_payload = call_mcp_tool(
        context,
        name="alice_open_loop_review",
        arguments={"loop_id": "loop-1", "action": "snooze", "due_at": "2026-05-12T09:00:00Z"},
    )
    dashboard_payload = call_mcp_tool(
        context,
        name="alice_project_dashboard",
        arguments={"project_id": "project-1"},
    )

    assert update_payload["artifact_type"] == "project_update"
    assert update_payload["metadata_json"]["candidate_memory_id"] == "memory-2"
    assert extract_payload["created_count"] == 1
    assert extract_payload["open_loops"][0]["metadata_json"]["owner"] == "Samir"
    assert review_update_payload["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Project automation reviewed."
    assert review_loop_payload["due_at"] == "2026-05-12T09:00:00Z"
    assert dashboard_payload["counts"]["open_loops"] == 1


def test_mcp_server_initialize_and_tools_list(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    initialize_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
    )
    assert initialize_response is not None
    assert initialize_response["result"]["protocolVersion"] == "2024-11-05"
    assert initialize_response["result"]["serverInfo"]["name"] == "alice-core-mcp"

    monkeypatch.setattr(
        mcp_server,
        "list_mcp_tools",
        lambda: [{"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}],
    )
    list_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )
    assert list_response is not None
    assert list_response["result"]["tools"] == [
        {"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}
    ]


def test_mcp_server_tools_call_success_and_error_paths(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    monkeypatch.setattr(mcp_server, "call_mcp_tool", lambda *_args, **_kwargs: {"ok": True})
    success_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert success_response is not None
    assert success_response["result"]["isError"] is False
    assert success_response["result"]["structuredContent"] == {"ok": True}

    def raise_tool_error(*_args, **_kwargs):
        raise MCPToolError("invalid input")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", raise_tool_error)
    error_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert error_response is not None
    assert error_response["result"]["isError"] is True
    assert error_response["result"]["content"][0]["text"] == "invalid input"
