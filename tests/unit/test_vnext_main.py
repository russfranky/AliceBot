from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from alicebot_api.config import Settings


class FakeVNextStore:
    def __init__(self, _conn) -> None:
        self.sources: dict[str, dict[str, object]] = {}
        self.source_by_hash: dict[str, dict[str, object]] = {}
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.open_loops: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.provenance_links: list[dict[str, object]] = []
        self.tasks: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.quality_ratings: list[dict[str, object]] = []
        self.edges: dict[str, dict[str, object]] = {}
        self.beliefs: dict[str, dict[str, object]] = {}
        self.projects: dict[str, dict[str, object]] = {}
        self.agent_identities: dict[str, dict[str, object]] = {}
        self.revisions: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        return self.source_by_hash.get(content_hash)

    def create_source(self, source: dict[str, object], **_kwargs) -> dict[str, object]:
        source_id = str(uuid4())
        row = {**source, "id": source_id}
        self.sources[source_id] = row
        self.source_by_hash[str(source["content_hash"])] = row
        return row

    def get_source(self, source_id: str) -> dict[str, object] | None:
        source = self.sources.get(source_id)
        if source is not None and source.get("deleted_at") is None:
            return source
        return None

    def list_sources(self, **kwargs) -> list[dict[str, object]]:
        return list(self.sources.values())[: kwargs.get("limit", 20)]

    def delete_source(self, *, source_id: str, **_kwargs) -> dict[str, object]:
        source = self.sources[source_id]
        source["deleted_at"] = "now"
        return source

    def create_source_chunk(self, chunk: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**chunk, "id": f"chunk-{len(self.chunks) + 1}"}
        self.chunks.append(row)
        return row

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories.append(row)
        return row

    def list_memories(self, *, status: str | None = None) -> list[dict[str, object]]:
        return [memory for memory in self.memories if status is None or memory.get("status") == status]

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

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**link, "id": f"provenance-{len(self.provenance_links) + 1}"}
        self.provenance_links.append(row)
        return row

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops.append(row)
        return row

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query, domains, sensitivity_allowed
        return self.memories[:limit]

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query, domains, sensitivity_allowed
        return list(self.sources.values())[:limit]

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [
            row
            for row in self.open_loops
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
            and (person_id is None or row.get("person_id") == person_id)
        ]
        return rows[:limit]

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

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[dict[str, object]]:
        return [
            link
            for link in self.provenance_links
            if link.get("target_type") == target_type and link.get("target_id") == target_id
        ]

    def create_task(self, task: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**task, "id": str(uuid4()), "status": task.get("status", "pending")}
        self.tasks.append(row)
        return row

    def claim_next_task(self) -> dict[str, object] | None:
        for task in self.tasks:
            if task.get("status") == "pending":
                task["status"] = "running"
                return task
        return None

    def update_task_status(
        self,
        *,
        task_id: str,
        status: str,
        details: dict[str, object] | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = status
                if details is not None:
                    task.update(details)
                return task
        raise AssertionError(task_id)

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": str(uuid4())}
        self.artifacts[str(row["id"])] = row
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 4,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [
            row
            for row in self.artifacts.values()
            if artifact_type is None or row.get("artifact_type") == artifact_type
        ]
        return rows[:limit]

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact

    def create_artifact_quality_rating(self, rating: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**rating, "id": f"quality-{len(self.quality_ratings) + 1}"}
        self.quality_ratings.append(row)
        return row

    def list_artifact_quality_ratings(
        self,
        *,
        artifact_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.quality_ratings
            if artifact_id is None or row.get("artifact_id") == artifact_id
        ]
        return rows[:limit]

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [row for row in self.projects.values() if status is None or row.get("status") == status]
        return rows[:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def create_edge(self, edge: dict[str, object], *, actor_type: str = "system") -> dict[str, object]:
        del actor_type
        row = {**edge, "id": f"edge-{len(self.edges) + 1}"}
        self.edges[str(row["id"])] = row
        return row

    def update_edge_status(self, *, edge_id: str, status: str) -> dict[str, object]:
        edge = self.edges[edge_id]
        metadata = edge.get("metadata_json")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update({"status": status, "candidate": status != "accepted"})
        edge["metadata_json"] = metadata
        if status == "rejected":
            edge["valid_to"] = "now"
        return edge

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[dict[str, object]]:
        return [
            edge
            for edge in self.edges.values()
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def create_belief(self, belief: dict[str, object]) -> dict[str, object]:
        row = {**belief, "id": f"belief-{len(self.beliefs) + 1}"}
        self.beliefs[str(row["id"])] = row
        return row

    def get_belief(self, belief_id: str) -> dict[str, object] | None:
        return self.beliefs.get(belief_id)

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [row for row in self.beliefs.values() if status is None or row.get("status") == status]
        return rows[:limit]

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
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

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        rows = [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]
        return rows[:limit] if limit is not None else rows

    def upsert_agent_identity(self, identity: dict[str, object], **_kwargs) -> dict[str, object]:
        self.agent_identities[str(identity["agent_id"])] = identity
        return identity

    def list_scheduler_runs(self, **_kwargs) -> list[dict[str, object]]:
        return []


def _install_fake_vnext_store(monkeypatch, store: FakeVNextStore) -> None:
    @contextmanager
    def fake_user_connection(database_url, current_user_id):
        assert database_url == "postgresql://db"
        assert current_user_id is not None
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://db"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "PostgresVNextStore", lambda _conn: store)


def test_create_vnext_source_endpoint_captures_text(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: vNext source API preserves provenance.",
            title="API capture",
            domain="project",
            sensitivity="private",
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "imported"
    assert payload["candidate_memory_count"] == 1
    assert list(store.sources.values())[0]["domain"] == "project"
    assert store.memories[0]["canonical_text"] == "vNext source API preserves provenance."


def test_vnext_connector_endpoints_list_and_sync_payloads(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    list_response = main_module.list_vnext_connectors(user_id=user_id)
    sync_response = main_module.sync_vnext_connector(
        "browser_clipper",
        main_module.VNextConnectorSyncRequest(
            user_id=user_id,
            items=[
                {
                    "external_id": "clip-1",
                    "cursor": "1",
                    "title": "API connector clip",
                    "url": "https://example.test/api-clip",
                    "text": "Fact: API connector sync preserves raw evidence.",
                }
            ],
            default_domain="learning",
            default_sensitivity="private",
        ),
    )

    list_payload = json.loads(list_response.body)
    sync_payload = json.loads(sync_response.body)
    assert list_response.status_code == 200
    assert "browser_clipper" in list_payload["order"]
    assert sync_response.status_code == 201
    assert sync_payload["status"] == "ok"
    assert sync_payload["sync_cursor"] == "1"
    source = next(iter(store.sources.values()))
    assert source["connector_name"] == "browser_clipper"
    assert source["metadata_json"]["raw_payload"]["external_id"] == "clip-1"
    assert store.events[-1]["event_type"] == "connector.sync_completed"


def test_get_vnext_source_endpoint_returns_404_for_missing_source(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    missing_source_id = uuid4()

    response = main_module.get_vnext_source(missing_source_id, user_id=uuid4())

    assert response.status_code == 404
    assert f"vNext source {missing_source_id} was not found" in json.loads(response.body)["detail"]


def test_delete_vnext_source_endpoint_soft_deletes_source(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {"id": source_id, "deleted_at": None}
    _install_fake_vnext_store(monkeypatch, store)

    response = main_module.delete_vnext_source(source_id=uuid4(), user_id=uuid4())
    assert response.status_code == 404

    response = main_module.delete_vnext_source(source_id=main_module.UUID(source_id), user_id=uuid4())

    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["id"] == source_id
    assert payload["deleted_at"] == "now"


def test_create_vnext_context_pack_endpoint_returns_structured_pack(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Alice context source",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "semantic",
            "canonical_text": "Alice context packs include sources.",
            "status": "active",
            "confidence": 0.9,
            "domain": "project",
            "sensitivity": "private",
            "first_seen_at": "2026-05-10T00:00:00Z",
            "last_seen_at": "2026-05-10T00:00:00Z",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)

    response = main_module.create_vnext_context_pack(
        main_module.VNextContextPackRequest(
            user_id=uuid4(),
            query="Alice context sources",
            scope={"domains": ["project"]},
            options={"sensitivity_allowed": ["public", "private"], "max_items": 4},
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["relevant_memories"][0]["id"] == "memory-1"
    assert payload["sources"][0]["id"] == source_id
    assert payload["trace_id"] == payload["trace"]["trace_id"]
    assert store.events[-1]["event_type"] == "retrieval.context_pack_compiled"


def test_vnext_brain_artifact_generation_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Alice daily API note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "TODO: validate daily API endpoint"},
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "project_state",
            "canonical_text": "Alice vNext API generates brain artifacts.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    request = main_module.VNextBrainArtifactGenerateRequest(
        user_id=user_id,
        scope={"domains": ["project"]},
        options={"generated_for": "2026-05-10", "sensitivity_allowed": ["public", "private"]},
    )

    daily_response = main_module.generate_vnext_daily_brief(request)
    weekly_response = main_module.generate_vnext_weekly_synthesis(request)

    daily_payload = json.loads(daily_response.body)
    weekly_payload = json.loads(weekly_response.body)
    assert daily_response.status_code == 201
    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["metadata_json"]["candidate_open_loop_ids"] == ["loop-1"]
    assert weekly_response.status_code == 201
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"] == ["memory-2"]
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_vnext_connection_and_graph_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Queue retrieval pattern note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "Queue retrieval provenance trace review."},
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "semantic",
            "canonical_text": "Retrieval provenance trace review improves queue artifacts.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    generate_response = main_module.generate_vnext_connection_report(
        main_module.VNextConnectionReportGenerateRequest(
            user_id=user_id,
            scope={"domains": ["project"]},
            options={"max_connections": 1},
        )
    )
    review_response = main_module.review_vnext_graph_edge(
        "edge-1",
        main_module.VNextGraphEdgeReviewRequest(user_id=user_id, action="accept"),
    )
    neighborhood_response = main_module.get_vnext_graph_neighborhood(source_id, user_id=user_id)

    generate_payload = json.loads(generate_response.body)
    review_payload = json.loads(review_response.body)
    neighborhood_payload = json.loads(neighborhood_response.body)
    assert generate_response.status_code == 201
    assert generate_payload["artifact_type"] == "connection_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_response.status_code == 200
    assert review_payload["metadata_json"]["status"] == "accepted"
    assert neighborhood_response.status_code == 200
    assert neighborhood_payload["edge_count"] == 1
    assert neighborhood_payload["from_edges"][0]["id"] == "edge-1"


def test_vnext_contradiction_and_belief_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Artifact policy note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "Alice should not auto-promote generated artifacts into memory."},
    }
    store.beliefs["belief-1"] = {
        "id": "belief-1",
        "memory_id": "memory-belief-1",
        "claim": "Alice should auto-promote generated artifacts into memory.",
        "status": "active",
        "confidence": 0.8,
        "domain": "project",
        "sensitivity": "private",
        "memory_type": "belief",
    }
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    generate_response = main_module.generate_vnext_contradiction_report(
        main_module.VNextContradictionReportGenerateRequest(
            user_id=user_id,
            scope={"domains": ["project"]},
            options={"max_contradictions": 1},
        )
    )
    review_response = main_module.review_vnext_belief(
        "belief-1",
        main_module.VNextBeliefReviewRequest(user_id=user_id, action="challenge", confidence=0.25),
    )
    state_response = main_module.get_vnext_belief_state("belief-1", user_id=user_id)

    generate_payload = json.loads(generate_response.body)
    review_payload = json.loads(review_response.body)
    state_payload = json.loads(state_response.body)
    assert generate_response.status_code == 201
    assert generate_payload["artifact_type"] == "contradiction_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_response.status_code == 200
    assert review_payload["status"] == "challenged"
    assert review_payload["confidence"] == 0.25
    assert state_response.status_code == 200
    assert state_payload["current"]["status"] == "challenged"
    assert "challenged" in state_payload["previous_statuses"]


def test_vnext_project_and_open_loop_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    store.projects["project-1"] = {
        "id": "project-1",
        "name": "Alice vNext",
        "slug": "alice-vnext",
        "status": "active",
        "current_state": "Sprint 7 complete.",
        "domain": "project",
        "sensitivity": "private",
    }
    store.sources[str(uuid4())] = {
        "id": "source-1",
        "source_type": "manual_text",
        "title": "Alice project note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "raw_text": "Project: Alice vNext needs project automation.\nTODO: validate dashboard Owner: Samir"
        },
    }
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    request = main_module.VNextProjectAutomationRequest(
        user_id=user_id,
        scope={"domains": ["project"], "project_id": "project-1"},
        options={"sensitivity_allowed": ["public", "private"]},
    )

    update_response = main_module.generate_vnext_project_update_candidate(request)
    update_payload = json.loads(update_response.body)
    extract_response = main_module.extract_vnext_open_loops(request)
    review_update_response = main_module.review_vnext_project_update_candidate(
        update_payload["id"],
        main_module.VNextProjectUpdateReviewRequest(
            user_id=user_id,
            action="edit",
            edited_current_state="Project automation reviewed.",
        ),
    )
    review_loop_response = main_module.review_vnext_open_loop(
        "loop-1",
        main_module.VNextOpenLoopReviewRequest(
            user_id=user_id,
            action="snooze",
            due_at="2026-05-12T09:00:00Z",
        ),
    )
    dashboard_response = main_module.get_vnext_project_dashboard("project-1", user_id=user_id)

    extract_payload = json.loads(extract_response.body)
    review_update_payload = json.loads(review_update_response.body)
    review_loop_payload = json.loads(review_loop_response.body)
    dashboard_payload = json.loads(dashboard_response.body)
    assert update_response.status_code == 201
    assert update_payload["artifact_type"] == "project_update"
    assert update_payload["metadata_json"]["candidate_memory_id"] == "memory-1"
    assert extract_response.status_code == 201
    assert extract_payload["created_count"] == 1
    assert extract_payload["open_loops"][0]["metadata_json"]["owner"] == "Samir"
    assert review_update_response.status_code == 200
    assert review_update_payload["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Project automation reviewed."
    assert review_loop_response.status_code == 200
    assert review_loop_payload["due_at"] == "2026-05-12T09:00:00Z"
    assert dashboard_response.status_code == 200
    assert dashboard_payload["counts"]["open_loops"] == 1


def test_vnext_queue_and_artifact_endpoints(monkeypatch, tmp_path) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    create_response = main_module.create_vnext_queue_task(
        main_module.VNextQueueTaskCreateRequest(
            user_id=user_id,
            title="Draft launch note",
            task_type="draft",
            instructions="Write from approved sources.",
            domain="project",
            sensitivity="private",
            scope_json={"project": "alice"},
            allowed_sources_json=["source-1"],
        )
    )

    create_payload = json.loads(create_response.body)
    assert create_response.status_code == 201
    assert create_payload["status"] == "pending"
    assert create_payload["requested_by"] == "api"
    assert store.events[-1]["event_type"] == "queue.task_enqueued"

    process_response = main_module.process_next_vnext_queue_task(
        main_module.VNextQueueProcessNextRequest(user_id=user_id)
    )

    process_payload = json.loads(process_response.body)
    artifact_id = process_payload["artifact_id"]
    assert process_response.status_code == 200
    assert process_payload["status"] == "completed"
    assert store.tasks[0]["status"] == "completed"
    assert store.tasks[0]["output_artifact_id"] == artifact_id
    assert store.artifacts[artifact_id]["content_markdown"].startswith("# Draft launch note")

    get_response = main_module.get_vnext_artifact(main_module.UUID(artifact_id), user_id=user_id)
    assert get_response.status_code == 200
    assert json.loads(get_response.body)["id"] == artifact_id

    review_response = main_module.review_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="accept"),
    )
    assert review_response.status_code == 200
    assert json.loads(review_response.body)["status"] == "accepted"

    quality_response = main_module.rate_vnext_artifact_quality(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactQualityRatingRequest(
            user_id=user_id,
            reviewer_id="reviewer-1",
            usefulness=4,
            accuracy=5,
            source_grounding=5,
            novel_connections=3,
            actionability=4,
            hallucination_risk=1,
            verbosity="right_sized",
            comments="Useful and grounded.",
        ),
    )
    quality_payload = json.loads(quality_response.body)
    export_quality_response = main_module.list_vnext_quality_evals(
        user_id=user_id,
        artifact_id=main_module.UUID(artifact_id),
        limit=10,
    )
    export_quality_payload = json.loads(export_quality_response.body)

    assert quality_response.status_code == 201
    assert quality_payload["artifact_id"] == artifact_id
    assert quality_payload["usefulness"] == 4
    assert export_quality_response.status_code == 200
    assert export_quality_payload["count"] == 1
    assert export_quality_payload["items"][0]["artifact_id"] == artifact_id

    export_response = main_module.export_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactExportRequest(user_id=user_id, output_dir=str(tmp_path)),
    )
    export_payload = json.loads(export_response.body)
    output_path = Path(export_payload["output_path"])
    assert export_response.status_code == 200
    assert output_path.name.startswith("artifact-")
    assert output_path.suffix == ".md"
    assert output_path.read_text(encoding="utf-8").startswith("# Draft launch note")


def test_vnext_artifact_review_endpoint_maps_validation_errors(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    artifact_id = str(uuid4())
    store.artifacts[artifact_id] = {"id": artifact_id, "title": "Draft", "content_markdown": "# Draft"}

    invalid_response = main_module.review_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="ship"),
    )
    missing_response = main_module.review_vnext_artifact(
        uuid4(),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="accept"),
    )

    assert invalid_response.status_code == 400
    assert missing_response.status_code == 404


def test_live_capture_connector_api_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    config_response = main_module.update_vnext_connector_config(
        "telegram",
        main_module.VNextConnectorConfigRequest(
            user_id=user_id,
            enabled=True,
            secret_ref="env:TELEGRAM_BOT_TOKEN",
            config_json={"allowed_chat_ids": ["999001"]},
        ),
    )
    telegram_response = main_module.sync_vnext_telegram_connector(
        main_module.VNextTelegramSyncRequest(
            user_id=user_id,
            updates=[
                {
                    "update_id": 1,
                    "message": {
                        "message_id": 10,
                        "date": 1_778_400_000,
                        "chat": {"id": 999001},
                        "from": {"id": 1001, "username": "samir"},
                        "text": "Fact: API Telegram capture works.",
                    },
                }
            ],
        )
    )
    browser_response = main_module.capture_vnext_browser_clip(
        main_module.VNextBrowserClipperCaptureRequest(
            user_id=user_id,
            url="https://example.test/clip",
            title="Clip",
            selected_text="Fact: Browser API clip works.",
            user_note="Remember: keep this reviewable.",
        )
    )
    health_response = main_module.get_vnext_connectors_health(user_id=user_id)

    assert config_response.status_code == 200
    assert telegram_response.status_code == 201
    assert browser_response.status_code == 201
    assert json.loads(telegram_response.body)["imported_count"] == 1
    assert json.loads(browser_response.body)["imported_count"] == 1
    health_payload = json.loads(health_response.body)
    assert health_payload["count"] >= 4
    assert any(item["connector_name"] == "telegram" for item in health_payload["items"])


def test_agent_output_ingest_api_creates_review_only_records(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    response = main_module.ingest_vnext_agent_output(
        main_module.VNextAgentOutputIngestRequest(
            user_id=user_id,
            agent_id="openclaw",
            agent_type="coding_agent",
            permission_profile="project_scoped_agent",
            agent_run_id="run-1",
            project_scope=["Alice"],
            title="Sprint summary",
            content="Decision: API agent output ingestion is review-only.",
            output_type="sprint_summary",
            propose_memory=True,
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "imported"
    assert payload["artifact_id"] in store.artifacts
    assert store.artifacts[payload["artifact_id"]]["status"] == "needs_review"
    assert payload["memory_id"] is not None
    assert any(memory["status"] == "candidate" for memory in store.memories)


def test_dogfooding_dashboard_and_insight_feedback_api(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    artifact = store.create_artifact(
        {
            "artifact_type": "daily_brief",
            "title": "Daily",
            "content_markdown": "# Daily",
            "status": "needs_review",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    store.create_artifact_quality_rating(
        {
            "artifact_id": artifact["id"],
            "usefulness": 5,
            "verbosity": "right_sized",
            "metadata_json": {},
        }
    )

    feedback_response = main_module.record_vnext_artifact_insight_feedback(
        main_module.UUID(str(artifact["id"])),
        main_module.VNextArtifactInsightFeedbackRequest(user_id=user_id, useful_insight="yes", surfaced_missed="yes"),
    )
    dashboard_response = main_module.get_vnext_dogfooding_dashboard(user_id=user_id)
    dashboard = json.loads(dashboard_response.body)

    assert feedback_response.status_code == 201
    assert dashboard_response.status_code == 200
    assert dashboard["artifact_quality_rating_count"] == 1
    assert dashboard["insight_feedback"]["useful_yes"] == 1
