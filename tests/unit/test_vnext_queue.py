from __future__ import annotations

from pathlib import Path

import pytest

from alicebot_api.vnext_queue import QueueTaskRequest, VNextQueueService, VNextQueueValidationError


class InMemoryVNextQueueStore:
    def __init__(self, *, fail_artifact_create: bool = False) -> None:
        self.tasks: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []
        self.fail_artifact_create = fail_artifact_create

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def create_task(self, task: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            **task,
            "id": f"task-{len(self.tasks) + 1}",
            "status": task.get("status", "pending"),
        }
        self.tasks.append(row)
        return row

    def claim_next_task(self) -> dict[str, object] | None:
        for task in self.tasks:
            if task["status"] == "pending":
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
            if task["id"] != task_id:
                continue
            task["status"] = status
            if details:
                task.update(details)
            return task
        raise AssertionError(f"missing task {task_id}")

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        if self.fail_artifact_create:
            raise RuntimeError("artifact renderer failed")
        row = {
            **artifact,
            "id": f"artifact-{len(self.artifacts) + 1}",
        }
        self.artifacts[str(row["id"])] = row
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact


def test_enqueue_task_creates_pending_task_and_logs_event() -> None:
    store = InMemoryVNextQueueStore()
    service = VNextQueueService(store)

    task = service.enqueue_task(
        QueueTaskRequest(
            title="Synthesize Alice retrieval",
            task_type="synthesize",
            instructions="Summarize the retrieval state.",
            domain="project",
            sensitivity="private",
        )
    )

    assert task["id"] == "task-1"
    assert task["status"] == "pending"
    assert task["domain"] == "project"
    assert store.events[-1]["event_type"] == "queue.task_enqueued"
    assert store.events[-1]["target_id"] == "task-1"


def test_worker_processes_next_task_and_creates_artifact() -> None:
    store = InMemoryVNextQueueStore()
    service = VNextQueueService(store)
    service.enqueue_task(
        QueueTaskRequest(
            title="Draft launch note",
            task_type="draft",
            instructions="Draft a launch note.",
            write_policy="auto_generate_artifact",
        )
    )

    result = service.process_next_task()

    assert result.status == "completed"
    assert result.task_id == "task-1"
    assert result.artifact_id == "artifact-1"
    assert store.tasks[0]["status"] == "completed"
    assert store.tasks[0]["output_artifact_id"] == "artifact-1"
    artifact = store.artifacts["artifact-1"]
    assert artifact["artifact_type"] == "draft"
    assert artifact["status"] == "reviewed"
    assert "# Draft launch note" in artifact["content_markdown"]
    assert store.events[-1]["event_type"] == "queue.task_completed"


def test_worker_records_failed_task_with_useful_error() -> None:
    store = InMemoryVNextQueueStore(fail_artifact_create=True)
    service = VNextQueueService(store)
    service.enqueue_task(
        QueueTaskRequest(
            title="Research failure mode",
            task_type="research",
            instructions="This should fail.",
        )
    )

    result = service.process_next_task()

    assert result.status == "failed"
    assert result.task_id == "task-1"
    assert result.error_message == "artifact renderer failed"
    assert store.tasks[0]["status"] == "failed"
    assert store.tasks[0]["error_message"] == "artifact renderer failed"
    assert store.events[-1]["event_type"] == "queue.task_failed"
    assert store.events[-1]["payload_json"]["error_type"] == "RuntimeError"


def test_artifact_review_actions_map_to_expected_statuses() -> None:
    store = InMemoryVNextQueueStore()
    service = VNextQueueService(store)
    store.artifacts["artifact-1"] = {"id": "artifact-1", "title": "Artifact", "content_markdown": "# Artifact"}

    reviewed = service.review_artifact(artifact_id="artifact-1", action="accept")

    assert reviewed["status"] == "accepted"
    assert store.events[-1]["event_type"] == "artifact.reviewed"
    assert store.events[-1]["payload_json"]["action"] == "accept"

    with pytest.raises(VNextQueueValidationError, match="artifact review action"):
        service.review_artifact(artifact_id="artifact-1", action="invalid")


def test_export_artifact_markdown_writes_file_and_logs_event(tmp_path: Path) -> None:
    store = InMemoryVNextQueueStore()
    service = VNextQueueService(store)
    store.artifacts["artifact-1"] = {
        "id": "artifact-1",
        "title": "Alice Queue Result",
        "content_markdown": "# Alice Queue Result\n\nDone.",
    }

    output_path = service.export_artifact_markdown(artifact_id="artifact-1", output_dir=tmp_path)

    assert output_path.name.startswith("artifact-")
    assert output_path.suffix == ".md"
    assert output_path.read_text(encoding="utf-8") == "# Alice Queue Result\n\nDone."
    assert store.events[-1]["event_type"] == "artifact.exported"
    assert store.events[-1]["payload_json"]["output_path"] == str(output_path)


def test_enqueue_task_rejects_empty_required_fields() -> None:
    service = VNextQueueService(InMemoryVNextQueueStore())

    with pytest.raises(VNextQueueValidationError, match="instructions must not be empty"):
        service.enqueue_task(QueueTaskRequest(title="Task", task_type="draft", instructions=" "))
