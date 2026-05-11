from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alicebot_api.vnext_scheduler import (
    SchedulerRunRequest,
    VNextSchedulerService,
    VNextSchedulerValidationError,
    compute_next_run_at,
    validate_schedule,
)


class InMemorySchedulerStore:
    def __init__(self, *, fail_artifact_create: bool = False) -> None:
        self.fail_artifact_create = fail_artifact_create
        self.events: list[dict[str, object]] = []
        self.workflows: dict[str, dict[str, object]] = {}
        self.runs: dict[str, dict[str, object]] = {}
        self.artifacts: dict[str, dict[str, object]] = {}
        self.sources: list[dict[str, object]] = [
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Daily scheduler note",
                "domain": "project",
                "sensitivity": "private",
                "captured_at": "2026-05-10T08:00:00Z",
                "metadata_json": {"raw_text": "TODO: review scheduled daily brief"},
            }
        ]
        self.memories: list[dict[str, object]] = [
            {
                "id": "memory-1",
                "memory_type": "project_state",
                "canonical_text": "Scheduler generated artifacts stay reviewable.",
                "status": "active",
                "domain": "project",
                "sensitivity": "private",
            }
        ]
        self.open_loops: list[dict[str, object]] = []
        self.projects: list[dict[str, object]] = []
        self.locked_workflows: set[str] = set()

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def upsert_scheduler_workflow(self, workflow: dict[str, object], *, actor_type: str = "system") -> dict[str, object]:
        workflow_type = str(workflow["workflow_type"])
        row = {
            "id": f"workflow-{workflow_type}",
            "workflow_type": workflow_type,
            "enabled": bool(workflow.get("enabled", False)),
            "paused": bool(workflow.get("paused", False)),
            "schedule_json": workflow.get("schedule_json", {"kind": "manual"}),
            "timezone": workflow.get("timezone", "UTC"),
            "next_run_at": workflow.get("next_run_at"),
            "metadata_json": workflow.get("metadata_json", {}),
            "last_run_id": None,
            "last_run_at": None,
            "last_result": None,
            "last_error": None,
        }
        self.workflows[workflow_type] = row
        self.append_event({"event_type": "scheduler.workflow_upserted", "actor_type": actor_type})
        return row

    def update_scheduler_workflow(
        self,
        *,
        workflow_type: str,
        patch: dict[str, object],
        actor_type: str = "system",
    ) -> dict[str, object]:
        row = self.workflows[workflow_type]
        row.update(
            {
                key: value
                for key, value in patch.items()
                if value is not None or key in {"last_error", "next_run_at"}
            }
        )
        self.append_event({"event_type": "scheduler.workflow_updated", "actor_type": actor_type})
        return row

    def get_scheduler_workflow(self, workflow_type: str) -> dict[str, object] | None:
        return self.workflows.get(workflow_type)

    def list_scheduler_workflows(self) -> list[dict[str, object]]:
        return list(self.workflows.values())

    def create_scheduler_run(self, run: dict[str, object], *, actor_type: str = "scheduler") -> dict[str, object]:
        row = {
            **run,
            "id": f"run-{len(self.runs) + 1}",
            "started_at": "2026-05-10T08:00:00Z",
            "finished_at": None,
            "artifact_id": None,
            "error_message": None,
        }
        self.runs[str(row["id"])] = row
        self.append_event(
            {
                "event_type": "scheduler.run_started",
                "actor_type": actor_type,
                "run_id": row["id"],
                "trace_id": row["trace_id"],
            }
        )
        return row

    def update_scheduler_run(
        self,
        *,
        run_id: str,
        patch: dict[str, object],
        actor_type: str = "scheduler",
    ) -> dict[str, object]:
        row = self.runs[run_id]
        row.update(patch)
        if row["status"] in {"succeeded", "failed"}:
            row["finished_at"] = "2026-05-10T08:01:00Z"
        event_type = "scheduler.run_succeeded" if row["status"] == "succeeded" else "scheduler.run_failed"
        self.append_event(
            {
                "event_type": event_type,
                "actor_type": actor_type,
                "run_id": row["id"],
                "trace_id": row["trace_id"],
            }
        )
        return row

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.runs.values()
            if workflow_type is None or row["workflow_type"] == workflow_type
        ]
        return rows[:limit]

    def try_scheduler_workflow_lock(self, workflow_type: str) -> bool:
        return workflow_type not in self.locked_workflows

    def create_artifact(self, artifact: dict[str, object], *, actor_type: str = "system") -> dict[str, object]:
        if self.fail_artifact_create:
            raise RuntimeError("artifact store unavailable")
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
        self.artifacts[str(row["id"])] = row
        self.append_event({"event_type": "artifact.created", "actor_type": actor_type, "target_id": row["id"]})
        return row

    def search_sources(self, **kwargs) -> list[dict[str, object]]:
        return self.sources[: kwargs.get("limit", 8)]

    def search_memories(self, **kwargs) -> list[dict[str, object]]:
        return self.memories[: kwargs.get("limit", 8)]

    def list_open_loops(self, **_kwargs) -> list[dict[str, object]]:
        return list(self.open_loops)

    def list_artifacts(self, **kwargs) -> list[dict[str, object]]:
        return list(self.artifacts.values())[: kwargs.get("limit", 8)]

    def list_projects(self, **kwargs) -> list[dict[str, object]]:
        return self.projects[: kwargs.get("limit", 8)]

    def list_beliefs(self, **kwargs) -> list[dict[str, object]]:
        return [] if kwargs else []

    def list_events(self, **kwargs) -> list[dict[str, object]]:
        limit = kwargs.get("limit")
        rows = list(reversed(self.events))
        return rows[:limit] if isinstance(limit, int) else rows


def test_schedule_validation_and_next_run_are_deterministic() -> None:
    schedule = validate_schedule(
        "daily_brief",
        {"kind": "daily", "time_of_day": "08:30", "days_of_week": ["monday", "wednesday"]},
    )
    next_run = compute_next_run_at(
        workflow_type="daily_brief",
        enabled=True,
        paused=False,
        schedule_json=schedule,
        timezone="UTC",
        now=datetime(2026, 5, 11, 8, 0, tzinfo=UTC),
    )

    assert schedule == {"kind": "daily", "time_of_day": "08:30", "days_of_week": ["monday", "wednesday"]}
    assert next_run == "2026-05-11T08:30:00+00:00"
    with pytest.raises(VNextSchedulerValidationError, match="time_of_day"):
        validate_schedule("daily_brief", {"kind": "daily", "time_of_day": "bad"})


def test_scheduler_defaults_are_disabled_and_run_now_creates_reviewable_artifact_only() -> None:
    store = InMemorySchedulerStore()
    service = VNextSchedulerService(store)

    status = service.status()
    configured = service.configure_workflow(
        workflow_type="daily_brief",
        enabled=True,
        schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
        timezone="UTC",
    )
    result = service.run_now(
        SchedulerRunRequest(
            workflow_type="daily_brief",
            domains=("project",),
            sensitivity_allowed=("public", "private"),
            generated_for="2026-05-11",
        )
    )

    assert status["disabled_by_default"] is True
    assert status["enabled_count"] == 0
    assert configured["enabled"] is True
    assert result["run"]["status"] == "succeeded"
    assert result["artifact"]["status"] == "needs_review"
    assert result["artifact"]["generated_by"] == "scheduler"
    assert result["artifact"]["metadata_json"]["scheduler_run_id"] == result["run"]["id"]
    assert [memory["status"] for memory in store.memories] == ["active"]
    assert "scheduler.run_started" in [event["event_type"] for event in store.events]
    assert "scheduler.run_succeeded" in [event["event_type"] for event in store.events]
    assert "scheduler.artifact_created" in [event["event_type"] for event in store.events]


def test_scheduler_run_due_executes_due_enabled_workflows_and_advances_next_run() -> None:
    store = InMemorySchedulerStore()
    service = VNextSchedulerService(store)
    service.configure_workflow(
        workflow_type="daily_brief",
        enabled=True,
        schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
        timezone="UTC",
    )
    store.workflows["daily_brief"]["next_run_at"] = "2026-05-11T08:00:00+00:00"

    result = service.run_due_workflows(now=datetime(2026, 5, 11, 8, 5, tzinfo=UTC))

    assert result["due_count"] == 1
    assert result["runs"][0]["workflow_type"] == "daily_brief"
    assert result["runs"][0]["run"]["status"] == "succeeded"
    assert result["runs"][0]["artifact"]["status"] == "needs_review"
    assert store.workflows["daily_brief"]["next_run_at"] != "2026-05-11T08:00:00+00:00"
    assert "scheduler.due_scan" in [event["event_type"] for event in store.events]


def test_scheduler_due_scan_can_run_model_backed_workflow_from_metadata_options() -> None:
    store = InMemorySchedulerStore()
    service = VNextSchedulerService(store)
    service.configure_workflow(
        workflow_type="daily_brief",
        enabled=True,
        schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
        timezone="UTC",
        metadata_json={
            "model_options": {
                "generation_mode": "model_backed",
                "model_route_mode": "local_only",
                "model_provider": "deterministic_local",
            }
        },
    )
    store.workflows["daily_brief"]["next_run_at"] = "2026-05-11T08:00:00+00:00"

    result = service.run_due_workflows(now=datetime(2026, 5, 11, 8, 5, tzinfo=UTC))

    artifact = result["runs"][0]["artifact"]
    assert result["due_count"] == 1
    assert artifact["status"] == "needs_review"
    assert artifact["metadata_json"]["generation_mode"] == "model_backed"
    assert artifact["metadata_json"]["model_routing"]["route_mode"] == "local_only"
    assert artifact["model_info_json"]["provider"] == "deterministic_local"
    assert "## Source References" in artifact["content_markdown"]


def test_scheduler_run_due_skips_workflow_when_lock_is_not_acquired() -> None:
    store = InMemorySchedulerStore()
    store.locked_workflows.add("daily_brief")
    service = VNextSchedulerService(store)
    service.configure_workflow(
        workflow_type="daily_brief",
        enabled=True,
        schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
        timezone="UTC",
    )
    store.workflows["daily_brief"]["next_run_at"] = "2026-05-11T08:00:00+00:00"

    result = service.run_due_workflows(now=datetime(2026, 5, 11, 8, 5, tzinfo=UTC))

    assert result["due_count"] == 0
    assert not store.runs
    assert "scheduler.workflow_lock_skipped" in [event["event_type"] for event in store.events]


@pytest.mark.parametrize(
    ("workflow_type", "artifact_type"),
    [
        ("connection_report", "connection_report"),
        ("contradiction_report", "contradiction_report"),
        ("open_loop_review", "open_loop_report"),
        ("project_update_scan", "project_update"),
    ],
)
def test_remaining_scheduler_workflows_create_reviewable_artifacts(workflow_type: str, artifact_type: str) -> None:
    store = InMemorySchedulerStore()
    store.open_loops.append(
        {
            "id": "loop-1",
            "title": "Review scheduler output",
            "status": "open",
            "description": "Confirm non-primary workflows produce reviewable artifacts.",
            "source_id": "source-1",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    service = VNextSchedulerService(store)

    result = service.run_now(
        SchedulerRunRequest(
            workflow_type=workflow_type,
            domains=("project",),
            sensitivity_allowed=("public", "private"),
            generated_for="2026-05-11",
        )
    )

    artifact = result["artifact"]
    metadata = artifact["metadata_json"]
    assert result["run"]["status"] == "succeeded"
    assert artifact["artifact_type"] == artifact_type
    assert artifact["status"] == "needs_review"
    assert artifact["generated_by"] == "scheduler"
    assert metadata["workflow_type"] == workflow_type
    assert metadata["scheduler_run_id"] == result["run"]["id"]
    assert metadata["trace_id"] == result["run"]["trace_id"]
    assert "source_refs" in metadata
    assert metadata["review_status"] == "needs_review"


@pytest.mark.parametrize("workflow_type", ["connection_report", "contradiction_report", "open_loop_review", "project_update_scan"])
def test_remaining_scheduler_workflows_support_model_backed_mode(workflow_type: str) -> None:
    store = InMemorySchedulerStore()
    store.open_loops.append(
        {
            "id": "loop-1",
            "title": "Review scheduler output",
            "status": "open",
            "description": "Confirm model-backed scheduled workflows are review-only.",
            "source_id": "source-1",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    service = VNextSchedulerService(store)

    result = service.run_now(
        SchedulerRunRequest(
            workflow_type=workflow_type,
            domains=("project",),
            sensitivity_allowed=("public", "private"),
            generated_for="2026-05-11",
            options={
                "generation_mode": "model_backed",
                "model_route_mode": "local_only",
                "model_provider": "deterministic_local",
            },
        )
    )

    artifact = result["artifact"]
    assert result["run"]["status"] == "succeeded"
    assert artifact["status"] == "needs_review"
    assert artifact["metadata_json"]["generation_mode"] == "model_backed"
    assert artifact["model_info_json"]["provider"] == "deterministic_local"
    assert "## Facts" in artifact["content_markdown"]


def test_scheduler_pause_clears_stale_next_run() -> None:
    store = InMemorySchedulerStore()
    service = VNextSchedulerService(store)
    service.configure_workflow(
        workflow_type="daily_brief",
        enabled=True,
        schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
        timezone="UTC",
    )

    paused = service.configure_workflow(workflow_type="daily_brief", paused=True)

    assert paused["paused"] is True
    assert paused["next_run_at"] is None


def test_scheduler_failure_marks_run_failed_without_raising() -> None:
    store = InMemorySchedulerStore(fail_artifact_create=True)
    service = VNextSchedulerService(store)

    result = service.run_now(SchedulerRunRequest(workflow_type="project_update_scan", domains=("project",)))

    assert result["artifact"] is None
    assert result["run"]["status"] == "failed"
    assert result["run"]["error_message"] == "artifact store unavailable"
    assert store.workflows["project_update_scan"]["last_result"] == "failed"
    assert store.workflows["project_update_scan"]["last_error"] == "artifact store unavailable"
