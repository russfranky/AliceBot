from __future__ import annotations

import pytest

from alicebot_api.vnext_projects import ProjectAutomationRequest, VNextProjectService, VNextProjectValidationError


class InMemoryVNextProjectStore:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, object]] = {}
        self.sources: list[dict[str, object]] = []
        self.memories: dict[str, dict[str, object]] = {}
        self.open_loops: dict[str, dict[str, object]] = {}
        self.artifacts: dict[str, dict[str, object]] = {}
        self.revisions: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []

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
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories[str(row["id"])] = row
        return row

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        memory = self.memories[memory_id]
        memory.update(patch)
        return memory

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

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
        rows = [row for row in self.projects.values() if status is None or row.get("status") == status]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops[str(row["id"])] = row
        return row

    def get_open_loop(self, loop_id: str) -> dict[str, object] | None:
        return self.open_loops.get(loop_id)

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
        rows = [
            row
            for row in self.open_loops.values()
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
            and (person_id is None or row.get("person_id") == person_id)
        ]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def update_open_loop(self, *, loop_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        loop = self.open_loops[loop_id]
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
        loop = self.open_loops[loop_id]
        loop["status"] = status
        if resolution_note is not None:
            loop["resolution_note"] = resolution_note
        return loop

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query
        return _filter_rows(self.sources, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query
        return _filter_rows(list(self.memories.values()), domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.artifacts.values()
            if artifact_type is None or row.get("artifact_type") == artifact_type
        ]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]


def _filter_rows(
    rows: list[dict[str, object]],
    *,
    domains: list[str] | None,
    sensitivity_allowed: list[str] | None,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        domain = row.get("domain")
        sensitivity = row.get("sensitivity")
        if domains is not None and isinstance(domain, str) and domain not in domains and domain != "unknown":
            continue
        if sensitivity_allowed is not None and isinstance(sensitivity, str) and sensitivity not in sensitivity_allowed:
            continue
        output.append(row)
    return output


def _seed_store() -> InMemoryVNextProjectStore:
    store = InMemoryVNextProjectStore()
    store.projects["project-1"] = {
        "id": "project-1",
        "name": "Alice vNext",
        "slug": "alice-vnext",
        "status": "active",
        "current_state": "Sprint 7 seed complete.",
        "domain": "project",
        "sensitivity": "private",
    }
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Alice project note",
            "content_hash": "sha256:abc",
            "captured_at": "2026-05-10T09:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "raw_text": (
                    "Project: Alice vNext now needs project auto-update review.\n"
                    "TODO: validate project dashboard Owner: Samir\n"
                    "Waiting on: UI decision Owner: Designer"
                )
            },
        }
    )
    store.memories["memory-existing"] = {
        "id": "memory-existing",
        "memory_type": "project_state",
        "canonical_text": "Alice vNext has project automation scope.",
        "status": "active",
        "domain": "project",
        "sensitivity": "private",
    }
    return store


def test_project_update_candidate_creates_reviewable_artifact_and_candidate_memory() -> None:
    store = _seed_store()

    artifact = VNextProjectService(store).generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    assert artifact["artifact_type"] == "project_update"
    assert artifact["status"] == "needs_review"
    assert artifact["metadata_json"]["project_id"] == "project-1"
    assert artifact["metadata_json"]["candidate_memory_id"] == "memory-2"
    assert "Project Update Candidate - Alice vNext" in artifact["content_markdown"]
    assert store.memories["memory-2"]["status"] == "candidate"
    assert store.events[-1]["event_type"] == "project.update_candidate_created"


def test_project_update_candidate_model_backed_mode_is_review_only_and_source_grounded() -> None:
    store = _seed_store()

    artifact = VNextProjectService(store).generate_project_update_candidate(
        ProjectAutomationRequest(
            project_id="project-1",
            domains=("project",),
            generation_mode="model_backed",
            model_route_mode="local_only",
        )
    )

    assert artifact["status"] == "needs_review"
    assert store.memories["memory-2"]["status"] == "candidate"
    assert artifact["metadata_json"]["workflow_type"] == "project_update_scan"
    assert artifact["metadata_json"]["generation_mode"] == "model_backed"
    assert artifact["model_info_json"]["provider"] == "deterministic_local"
    assert artifact["prompt_hash"].startswith("sha256:")
    assert "## Facts" in artifact["content_markdown"]
    assert "## Open Questions" in artifact["content_markdown"]
    assert "source:source-1" in artifact["content_markdown"]


def test_accepting_project_update_updates_project_promotes_memory_and_appends_revision() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(ProjectAutomationRequest(project_id="project-1", domains=("project",)))

    reviewed = service.review_project_update(
        artifact_id=str(artifact["id"]),
        action="edit",
        edited_current_state="Alice vNext project automation is under review.",
    )

    assert reviewed["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Alice vNext project automation is under review."
    assert store.memories["memory-2"]["status"] == "active"
    assert store.revisions[0]["memory_id"] == "memory-2"
    assert store.revisions[0]["memory_key"] == store.memories["memory-2"]["memory_key"]
    assert store.revisions[0]["revision_type"] == "edited"
    assert store.events[-1]["event_type"] == "project.update_candidate_accepted"


def test_rejecting_project_update_logs_rejection_without_updating_project() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(ProjectAutomationRequest(project_id="project-1", domains=("project",)))

    reviewed = service.review_project_update(artifact_id=str(artifact["id"]), action="reject")

    assert reviewed["status"] == "rejected"
    assert store.projects["project-1"]["current_state"] == "Sprint 7 seed complete."
    assert store.events[-1]["event_type"] == "project.update_candidate_rejected"


def test_open_loop_extraction_and_review_support_source_owner_and_filters() -> None:
    store = _seed_store()
    service = VNextProjectService(store)

    loops = service.extract_open_loops(ProjectAutomationRequest(project_id="project-1", domains=("project",)))
    snoozed = service.review_open_loop(loop_id="loop-1", action="snooze", due_at="2026-05-12T09:00:00Z")
    closed = service.review_open_loop(loop_id="loop-2", action="close", resolution_note="Decision captured.")
    dashboard = service.project_dashboard(project_id="project-1")

    assert [loop["metadata_json"]["loop_type"] for loop in loops] == ["task", "waiting_on_person"]
    assert loops[0]["source_id"] == "source-1"
    assert loops[0]["metadata_json"]["source_captured_at"] == "2026-05-10T09:00:00Z"
    assert loops[0]["metadata_json"]["owner"] == "Samir"
    assert snoozed["due_at"] == "2026-05-12T09:00:00Z"
    assert closed["status"] == "resolved"
    assert dashboard["project"]["id"] == "project-1"
    assert dashboard["counts"]["open_loops"] == 1


def test_project_service_validation_errors() -> None:
    service = VNextProjectService(InMemoryVNextProjectStore())

    with pytest.raises(VNextProjectValidationError, match="max_items"):
        service.extract_open_loops(ProjectAutomationRequest(max_items=0))

    with pytest.raises(VNextProjectValidationError, match="no active project"):
        service.generate_project_update_candidate(ProjectAutomationRequest())

    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(ProjectAutomationRequest(project_id="project-1"))
    with pytest.raises(VNextProjectValidationError, match="edited_current_state"):
        service.review_project_update(artifact_id=str(artifact["id"]), action="edit")
