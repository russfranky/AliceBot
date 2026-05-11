from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import UUID, uuid4

import alicebot_api.cli as cli_module
from alicebot_api.config import Settings
from alicebot_api.contracts import ContinuityRecallResponse


def test_parser_routes_required_commands() -> None:
    parser = cli_module.build_parser()
    continuity_object_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    cases = [
        (["capture", "Decision: Keep rollout phased"], "_run_capture"),
        (["context-pack", "What should Alice remember?"], "_run_context_pack"),
        (["daily-brief", "--generate"], "_run_daily_brief"),
        (["weekly-synthesis", "--generate"], "_run_weekly_synthesis"),
        (["connections", "generate"], "_run_connections_generate"),
        (["vnext", "connectors", "list"], "_run_vnext_connectors_list"),
        (
            ["vnext", "connectors", "ingest", "browser_clipper", "clips.json"],
            "_run_vnext_connectors_ingest",
        ),
        (["vnext", "sources", "capture-text", "Fact: Keep vNext provenance-first"], "_run_vnext_sources_capture_text"),
        (["vnext", "sources", "capture-file", "notes.md"], "_run_vnext_sources_capture_file"),
        (["vnext", "sources", "import-markdown", "notes"], "_run_vnext_sources_import_markdown"),
        (["vnext", "sources", "import-chatgpt", "conversations.json"], "_run_vnext_sources_import_chatgpt"),
        (
            ["vnext", "queue", "add", "--type", "synthesize", "--title", "T", "--instructions", "Do it"],
            "_run_vnext_queue_add",
        ),
        (["vnext", "queue", "process-next"], "_run_vnext_queue_process_next"),
        (["vnext", "artifacts", "review", "artifact-1", "--action", "accept"], "_run_vnext_artifact_review"),
        (["vnext", "artifacts", "export", "artifact-1", "--output-dir", "."], "_run_vnext_artifact_export"),
        (["vnext", "graph", "review", "edge-1", "--action", "accept"], "_run_vnext_graph_review"),
        (["vnext", "graph", "neighborhood", "source-1"], "_run_vnext_graph_neighborhood"),
        (["vnext", "contradictions", "generate"], "_run_vnext_contradictions_generate"),
        (["vnext", "beliefs", "review", "belief-1", "--action", "challenge"], "_run_vnext_belief_review"),
        (["vnext", "beliefs", "state", "belief-1"], "_run_vnext_belief_state"),
        (["vnext", "projects", "update-candidate"], "_run_vnext_project_update_candidate"),
        (["vnext", "projects", "review-update", "artifact-1", "--action", "accept"], "_run_vnext_project_update_review"),
        (["vnext", "projects", "dashboard", "project-1"], "_run_vnext_project_dashboard"),
        (["vnext", "open-loops", "extract"], "_run_vnext_open_loops_extract"),
        (["vnext", "open-loops", "review", "loop-1", "--action", "close"], "_run_vnext_open_loop_review"),
        (
            ["vnext", "agents", "propose-memory", "--agent-id", "hermes", "--title", "T", "--canonical-text", "Fact"],
            "_run_vnext_agent_propose_memory",
        ),
        (["vnext", "scheduler", "status"], "_run_vnext_scheduler_status"),
        (["vnext", "scheduler", "run-now", "daily_brief"], "_run_vnext_scheduler_run_now"),
        (["vnext", "scheduler", "run-due"], "_run_vnext_scheduler_run_due"),
        (["vnext", "scheduler", "pause"], "_run_vnext_scheduler_pause"),
        (["vnext", "scheduler", "resume"], "_run_vnext_scheduler_resume"),
        (["vnext", "smoke", "agentic-scheduler"], "_run_vnext_smoke_agentic_scheduler"),
        (["mutations", "generate"], "_run_mutation_generate"),
        (["mutations", "candidates"], "_run_mutation_candidates"),
        (["mutations", "commit"], "_run_mutation_commit"),
        (["mutations", "operations"], "_run_mutation_operations"),
        (["brief"], "_run_brief"),
        (["recall"], "_run_recall"),
        (["state-at", continuity_object_id], "_run_state_at"),
        (["timeline", continuity_object_id], "_run_timeline"),
        (["lifecycle", "list"], "_run_lifecycle_list"),
        (["lifecycle", "show", continuity_object_id], "_run_lifecycle_show"),
        (["resume"], "_run_resume"),
        (["task-briefs", "compile", "--mode", "resume"], "_run_task_brief_compile"),
        (["task-briefs", "show", continuity_object_id], "_run_task_brief_show"),
        (
            ["task-briefs", "compare", "--mode", "worker_subtask", "--compare-to-mode", "user_recall"],
            "_run_task_brief_compare",
        ),
        (["open-loops"], "_run_open_loops"),
        (["review", "queue"], "_run_review_queue"),
        (["review", "show", continuity_object_id], "_run_review_show"),
        (["review", "apply", continuity_object_id, "--action", "confirm"], "_run_review_apply"),
        (["contradictions", "detect"], "_run_contradictions_detect"),
        (["contradictions", "list"], "_run_contradictions_list"),
        (["contradictions", "show", continuity_object_id], "_run_contradictions_show"),
        (
            ["contradictions", "resolve", continuity_object_id, "--action", "confirm_primary"],
            "_run_contradictions_resolve",
        ),
        (["trust", "signals"], "_run_trust_signals"),
        (["explain", continuity_object_id], "_run_explain"),
        (["explain", "--entity-id", continuity_object_id], "_run_explain"),
        (["evidence", "artifact", continuity_object_id], "_run_evidence_artifact"),
        (["patterns", "list"], "_run_pattern_list"),
        (["patterns", "explain", continuity_object_id], "_run_pattern_explain"),
        (["playbooks", "list"], "_run_playbook_list"),
        (["playbooks", "explain", continuity_object_id], "_run_playbook_explain"),
        (["status"], "_run_status"),
        (["eval", "seed"], "_run_vnext_eval_seed"),
        (["eval", "run", "--suite", "all"], "_run_vnext_eval_run"),
        (["eval", "report"], "_run_vnext_eval_report"),
        (["evals", "suites"], "_run_eval_suites"),
        (["evals", "run"], "_run_eval_run"),
        (["evals", "runs"], "_run_eval_runs"),
        (["evals", "show", continuity_object_id], "_run_eval_show"),
    ]

    for argv, expected_handler_name in cases:
        parsed = parser.parse_args(argv)
        assert parsed.handler.__name__ == expected_handler_name


def test_parser_preserves_explicit_vnext_sensitivity_filter() -> None:
    parser = cli_module.build_parser()
    explicit = parser.parse_args(["context-pack", "coffee", "--sensitivity-allowed", "public"])
    omitted = parser.parse_args(["context-pack", "coffee"])

    assert explicit.sensitivity_allowed == ["public"]
    assert cli_module._vnext_sensitivity_allowed(explicit) == ("public",)
    assert omitted.sensitivity_allowed is None
    assert cli_module._vnext_sensitivity_allowed(omitted) == ("public", "internal", "private", "unknown")


class FakeVNextCliStore:
    def __init__(self) -> None:
        self.sources: list[dict[str, object]] = []
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.open_loops: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.source_by_hash: dict[str, dict[str, object]] = {}
        self.tasks: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.edges: dict[str, dict[str, object]] = {}
        self.beliefs: dict[str, dict[str, object]] = {}
        self.projects: dict[str, dict[str, object]] = {}
        self.revisions: list[dict[str, object]] = []
        self.agent_identities: dict[str, dict[str, object]] = {}
        self.scheduler_workflows: dict[str, dict[str, object]] = {}
        self.scheduler_runs: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def upsert_agent_identity(self, identity: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            **identity,
            "id": self.agent_identities.get(str(identity["agent_id"]), {}).get("id")
            or f"agent-{len(self.agent_identities) + 1}",
        }
        self.agent_identities[str(identity["agent_id"])] = row
        return row

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        return self.source_by_hash.get(content_hash)

    def create_source(self, source: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**source, "id": f"source-{len(self.sources) + 1}"}
        self.sources.append(row)
        self.source_by_hash[str(source["content_hash"])] = row
        return row

    def create_source_chunk(self, chunk: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**chunk, "id": f"chunk-{len(self.chunks) + 1}"}
        self.chunks.append(row)
        return row

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
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

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        return {**link, "id": "provenance-1"}

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
        return self.sources[:limit]

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
        del target_type, target_id
        return []

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

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[dict[str, object]]:
        return [
            edge
            for edge in self.edges.values()
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def create_belief(self, belief: dict[str, object], **_kwargs) -> dict[str, object]:
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

    def create_task(self, task: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**task, "id": f"task-{len(self.tasks) + 1}", "status": "pending"}
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
            if task["id"] == task_id:
                task["status"] = status
                if details:
                    task.update(details)
                return task
        raise AssertionError(task_id)

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
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

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact

    def upsert_scheduler_workflow(self, workflow: dict[str, object], **_kwargs) -> dict[str, object]:
        workflow_type = str(workflow["workflow_type"])
        existing = self.scheduler_workflows.get(workflow_type, {})
        row = {
            **existing,
            **workflow,
            "id": existing.get("id") or f"workflow-{len(self.scheduler_workflows) + 1}",
        }
        self.scheduler_workflows[workflow_type] = row
        return row

    def update_scheduler_workflow(
        self,
        *,
        workflow_type: str,
        patch: dict[str, object],
        **_kwargs,
    ) -> dict[str, object]:
        workflow = self.get_scheduler_workflow(workflow_type)
        if workflow is None:
            workflow = self.upsert_scheduler_workflow(
                {
                    "workflow_type": workflow_type,
                    "enabled": False,
                    "paused": False,
                    "schedule_json": {"kind": "manual"},
                    "timezone": "UTC",
                    "next_run_at": None,
                    "metadata_json": {},
                }
            )
        workflow.update(patch)
        return workflow

    def get_scheduler_workflow(self, workflow_type: str) -> dict[str, object] | None:
        return self.scheduler_workflows.get(workflow_type)

    def list_scheduler_workflows(self) -> list[dict[str, object]]:
        return list(self.scheduler_workflows.values())

    def create_scheduler_run(self, run: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            **run,
            "id": f"scheduler-run-{len(self.scheduler_runs) + 1}",
            "started_at": datetime.now(UTC).isoformat(),
        }
        self.scheduler_runs.append(row)
        self.append_event(
            {
                "event_type": "scheduler.run_started",
                "target_type": "scheduler_run",
                "target_id": row["id"],
                "payload_json": {"workflow_type": row["workflow_type"]},
            }
        )
        return row

    def update_scheduler_run(
        self,
        *,
        run_id: str,
        patch: dict[str, object],
        **_kwargs,
    ) -> dict[str, object]:
        for run in self.scheduler_runs:
            if run["id"] == run_id:
                run.update(patch)
                run["finished_at"] = datetime.now(UTC).isoformat()
                self.append_event(
                    {
                        "event_type": "scheduler.run_succeeded" if run.get("status") == "succeeded" else "scheduler.run_failed",
                        "target_type": "scheduler_run",
                        "target_id": run_id,
                        "payload_json": {"workflow_type": run["workflow_type"]},
                    }
                )
                return run
        raise AssertionError(run_id)

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[dict[str, object]]:
        rows = [
            run
            for run in reversed(self.scheduler_runs)
            if workflow_type is None or run.get("workflow_type") == workflow_type
        ]
        return rows[:limit]


def test_vnext_capture_text_cli_uses_vnext_capture_service(monkeypatch) -> None:
    store = FakeVNextCliStore()

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    args = cli_module.build_parser().parse_args(
        [
            "vnext",
            "sources",
            "capture-text",
            "Fact: Alice vNext captures sources with provenance.",
            "--domain",
            "project",
            "--sensitivity",
            "private",
        ]
    )

    output = args.handler(ctx, args)

    payload = json.loads(output)
    assert payload["status"] == "imported"
    assert payload["chunk_count"] == 1
    assert payload["candidate_memory_count"] == 1
    assert store.sources[0]["domain"] == "project"
    assert store.sources[0]["metadata_json"]["raw_text"] == "Fact: Alice vNext captures sources with provenance."
    assert store.memories[0]["memory_type"] == "semantic"


def test_vnext_connector_cli_lists_and_ingests_payload_file(monkeypatch, tmp_path: Path) -> None:
    store = FakeVNextCliStore()
    payload_path = tmp_path / "clips.json"
    payload_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "external_id": "clip-1",
                        "cursor": "1",
                        "title": "Connector clip",
                        "url": "https://example.test/clip",
                        "text": "Fact: Connector CLI preserves raw evidence.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    list_args = parser.parse_args(["vnext", "connectors", "list"])
    ingest_args = parser.parse_args(
        [
            "vnext",
            "connectors",
            "ingest",
            "browser_clipper",
            str(payload_path),
            "--domain",
            "learning",
            "--sensitivity",
            "private",
        ]
    )

    list_payload = json.loads(list_args.handler(ctx, list_args))
    ingest_payload = json.loads(ingest_args.handler(ctx, ingest_args))

    assert "browser_clipper" in list_payload["order"]
    assert ingest_payload["status"] == "ok"
    assert ingest_payload["imported_count"] == 1
    assert store.sources[0]["connector_name"] == "browser_clipper"
    assert store.sources[0]["metadata_json"]["raw_payload"]["external_id"] == "clip-1"
    assert store.sources[0]["domain"] == "learning"


def test_context_pack_cli_returns_structured_vnext_pack(monkeypatch) -> None:
    store = FakeVNextCliStore()
    memory_id = uuid4()
    source_id = uuid4()
    captured_at = datetime(2026, 5, 10, 0, 0, tzinfo=UTC)
    store.memories.append(
        {
            "id": memory_id,
            "memory_type": "semantic",
            "canonical_text": "Alice context packs need provenance.",
            "status": "active",
            "confidence": 0.8,
            "domain": "project",
            "sensitivity": "private",
            "first_seen_at": captured_at,
            "last_seen_at": captured_at,
        }
    )
    store.sources.append(
        {
            "id": source_id,
            "source_type": "manual_text",
            "title": "Alice context source",
            "content_hash": "sha256:abc",
            "captured_at": captured_at,
            "domain": "project",
            "sensitivity": "private",
        }
    )

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    args = cli_module.build_parser().parse_args(
        ["context-pack", "Alice context provenance", "--domain", "project", "--max-items", "4"]
    )

    output = args.handler(ctx, args)

    payload = json.loads(output)
    assert payload["query_interpretation"]["query_type"] == "strategic_synthesis"
    assert payload["relevant_memories"][0]["id"] == str(memory_id)
    assert payload["relevant_memories"][0]["first_seen_at"] == "2026-05-10T00:00:00+00:00"
    assert payload["sources"][0]["id"] == str(source_id)
    assert payload["sources"][0]["captured_at"] == "2026-05-10T00:00:00+00:00"
    assert payload["trace"]["selected_count"] == 2


def test_vnext_brain_cli_generates_daily_and_weekly_artifacts(monkeypatch) -> None:
    store = FakeVNextCliStore()
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Alice daily note",
            "content_hash": "sha256:abc",
            "captured_at": "2026-05-10T00:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"raw_text": "TODO: validate daily brief CLI"},
        }
    )
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "project_state",
            "canonical_text": "Alice vNext CLI generates brain artifacts.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    daily_args = parser.parse_args(
        ["daily-brief", "--generate", "--generated-for", "2026-05-10", "--domain", "project"]
    )
    weekly_args = parser.parse_args(
        ["weekly-synthesis", "--generate", "--generated-for", "2026-05-10", "--domain", "project"]
    )

    daily_payload = json.loads(daily_args.handler(ctx, daily_args))
    weekly_payload = json.loads(weekly_args.handler(ctx, weekly_args))

    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["metadata_json"]["candidate_open_loop_ids"] == ["loop-1"]
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"] == ["memory-2"]
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_vnext_agentic_scheduler_smoke_cli_runs_required_gates(monkeypatch) -> None:
    store = FakeVNextCliStore()

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    args = cli_module.build_parser().parse_args(["vnext", "smoke", "agentic-scheduler"])

    output = args.handler(ctx, args)

    payload = json.loads(output)
    assert payload["status"] == "passed"
    assert all(payload["gates"].values())
    assert payload["policy_decisions"]["blocked"]["decision"] == "blocked"
    assert store.memories[-1]["status"] == "candidate"
    assert len(store.scheduler_runs) == 3
    assert {run["status"] for run in store.scheduler_runs} == {"succeeded"}
    assert any(event["event_type"] == "agent.policy_blocked" for event in store.events)


def test_vnext_connection_cli_generates_reviews_and_lists_neighborhood(monkeypatch) -> None:
    store = FakeVNextCliStore()
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Queue retrieval pattern note",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"raw_text": "Queue retrieval provenance trace review."},
        }
    )
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

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    generate_args = parser.parse_args(
        ["connections", "generate", "--domain", "project", "--max-connections", "1"]
    )
    review_args = parser.parse_args(["vnext", "graph", "review", "edge-1", "--action", "accept"])
    neighborhood_args = parser.parse_args(["vnext", "graph", "neighborhood", "source-1"])

    generate_payload = json.loads(generate_args.handler(ctx, generate_args))
    review_payload = json.loads(review_args.handler(ctx, review_args))
    neighborhood_payload = json.loads(neighborhood_args.handler(ctx, neighborhood_args))

    assert generate_payload["artifact_type"] == "connection_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["metadata_json"]["status"] == "accepted"
    assert neighborhood_payload["edge_count"] == 1
    assert neighborhood_payload["from_edges"][0]["id"] == "edge-1"


def test_vnext_contradiction_and_belief_cli(monkeypatch) -> None:
    store = FakeVNextCliStore()
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Artifact policy note",
            "content_hash": "sha256:abc",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"raw_text": "Alice should not auto-promote generated artifacts into memory."},
        }
    )
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

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    generate_args = parser.parse_args(
        ["vnext", "contradictions", "generate", "--domain", "project", "--max-contradictions", "1"]
    )
    review_args = parser.parse_args(
        ["vnext", "beliefs", "review", "belief-1", "--action", "challenge", "--confidence", "0.3"]
    )
    state_args = parser.parse_args(["vnext", "beliefs", "state", "belief-1"])

    generate_payload = json.loads(generate_args.handler(ctx, generate_args))
    review_payload = json.loads(review_args.handler(ctx, review_args))
    state_payload = json.loads(state_args.handler(ctx, state_args))

    assert generate_payload["artifact_type"] == "contradiction_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["status"] == "challenged"
    assert review_payload["confidence"] == 0.3
    assert state_payload["current"]["status"] == "challenged"
    assert "challenged" in state_payload["previous_statuses"]


def test_vnext_project_and_open_loop_cli(monkeypatch) -> None:
    store = FakeVNextCliStore()
    store.projects["project-1"] = {
        "id": "project-1",
        "name": "Alice vNext",
        "slug": "alice-vnext",
        "status": "active",
        "current_state": "Sprint 7 complete.",
        "domain": "project",
        "sensitivity": "private",
    }
    store.sources.append(
        {
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
    )

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    update_args = parser.parse_args(
        ["vnext", "projects", "update-candidate", "--project-id", "project-1", "--domain", "project"]
    )
    extract_args = parser.parse_args(
        ["vnext", "open-loops", "extract", "--project-id", "project-1", "--domain", "project"]
    )
    review_update_args = parser.parse_args(
        [
            "vnext",
            "projects",
            "review-update",
            "artifact-1",
            "--action",
            "edit",
            "--edited-current-state",
            "Project automation reviewed.",
        ]
    )
    review_loop_args = parser.parse_args(
        ["vnext", "open-loops", "review", "loop-1", "--action", "snooze", "--due-at", "2026-05-12T09:00:00Z"]
    )
    dashboard_args = parser.parse_args(["vnext", "projects", "dashboard", "project-1"])

    update_payload = json.loads(update_args.handler(ctx, update_args))
    extract_payload = json.loads(extract_args.handler(ctx, extract_args))
    review_update_payload = json.loads(review_update_args.handler(ctx, review_update_args))
    review_loop_payload = json.loads(review_loop_args.handler(ctx, review_loop_args))
    dashboard_payload = json.loads(dashboard_args.handler(ctx, dashboard_args))

    assert update_payload["artifact_type"] == "project_update"
    assert update_payload["metadata_json"]["candidate_memory_id"] == "memory-1"
    assert extract_payload["created_count"] == 1
    assert extract_payload["open_loops"][0]["metadata_json"]["owner"] == "Samir"
    assert review_update_payload["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Project automation reviewed."
    assert review_loop_payload["due_at"] == "2026-05-12T09:00:00Z"
    assert dashboard_payload["counts"]["open_loops"] == 1


def test_vnext_queue_cli_add_process_review_and_export(monkeypatch, tmp_path: Path) -> None:
    store = FakeVNextCliStore()

    @contextmanager
    def fake_vnext_store_context(_ctx):
        yield store

    monkeypatch.setattr(cli_module, "_vnext_store_context", fake_vnext_store_context)
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()

    add_args = parser.parse_args(
        [
            "vnext",
            "queue",
            "add",
            "--type",
            "draft",
            "--title",
            "Draft launch note",
            "--instructions",
            "Draft it.",
        ]
    )
    added = json.loads(add_args.handler(ctx, add_args))
    process_args = parser.parse_args(["vnext", "queue", "process-next"])
    processed = json.loads(process_args.handler(ctx, process_args))
    review_args = parser.parse_args(["vnext", "artifacts", "review", "artifact-1", "--action", "accept"])
    reviewed = json.loads(review_args.handler(ctx, review_args))
    export_args = parser.parse_args(["vnext", "artifacts", "export", "artifact-1", "--output-dir", str(tmp_path)])
    exported = json.loads(export_args.handler(ctx, export_args))

    assert added["id"] == "task-1"
    assert processed["status"] == "completed"
    assert processed["artifact_id"] == "artifact-1"
    assert reviewed["status"] == "accepted"
    assert Path(exported["output_path"]).exists()


def test_vnext_eval_cli_seed_run_and_report(tmp_path: Path) -> None:
    ctx = cli_module.CLIContext(
        settings=Settings(database_url="postgresql://db"),
        database_url="postgresql://db",
        user_id=uuid4(),
    )
    parser = cli_module.build_parser()
    corpus_path = tmp_path / "vnext_corpus.json"
    report_path = tmp_path / "vnext_report.json"

    seed_args = parser.parse_args(["eval", "seed", "--output-path", str(corpus_path)])
    seed_payload = json.loads(seed_args.handler(ctx, seed_args))
    run_args = parser.parse_args(["eval", "run", "--suite", "all", "--corpus-path", str(corpus_path)])
    run_payload = json.loads(run_args.handler(ctx, run_args))
    report_args = parser.parse_args(
        [
            "eval",
            "report",
            "--suite",
            "privacy",
            "--corpus-path",
            str(corpus_path),
            "--report-path",
            str(report_path),
        ]
    )
    report_payload = json.loads(report_args.handler(ctx, report_args))

    assert Path(seed_payload["written_corpus_path"]) == corpus_path.resolve()
    assert run_payload["report"]["status"] == "pass"
    assert run_payload["report"]["baseline_metrics"]["critical_privacy_leak_count"] == 0
    assert Path(report_payload["written_report_path"]) == report_path.resolve()
    assert report_payload["report"]["suite"] == "privacy"
    assert json.loads(report_path.read_text(encoding="utf-8")) == report_payload["report"]


def test_resolve_user_id_prefers_flag_then_settings_then_env_then_default(monkeypatch) -> None:
    flag_user_id = UUID("11111111-1111-4111-8111-111111111111")
    configured_user_id = UUID("22222222-2222-4222-8222-222222222222")
    env_user_id = UUID("33333333-3333-4333-8333-333333333333")

    settings_without_auth = Settings(auth_user_id="")
    settings_with_auth = Settings(auth_user_id=str(configured_user_id))

    monkeypatch.setenv("ALICEBOT_AUTH_USER_ID", str(env_user_id))
    assert cli_module._resolve_user_id(settings_without_auth, str(flag_user_id)) == flag_user_id
    assert cli_module._resolve_user_id(settings_with_auth, None) == configured_user_id
    assert cli_module._resolve_user_id(settings_without_auth, None) == env_user_id

    monkeypatch.delenv("ALICEBOT_AUTH_USER_ID")
    assert cli_module._resolve_user_id(settings_without_auth, None) == UUID(cli_module.DEFAULT_CLI_USER_ID)


def test_main_returns_error_for_non_object_json_on_review_apply(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(database_url="postgresql://db", auth_user_id=str(uuid4())),
    )

    exit_code = cli_module.main(
        [
            "review",
            "apply",
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "--action",
            "edit",
            "--body-json",
            "[]",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "error: --body-json must be a JSON object" in captured.err


def test_recall_formatting_is_deterministic() -> None:
    payload: ContinuityRecallResponse = {
        "items": [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "capture_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "object_type": "Decision",
                "status": "active",
                "lifecycle": {
                    "is_preserved": True,
                    "preservation_status": "preserved",
                    "is_searchable": True,
                    "searchability_status": "searchable",
                    "is_promotable": True,
                    "promotion_status": "promotable",
                },
                "title": "Decision: Keep rollout phased",
                "body": {"decision_text": "Keep rollout phased"},
                "provenance": {"thread_id": "thread-1"},
                "confirmation_status": "confirmed",
                "admission_posture": "DERIVED",
                "confidence": 0.95,
                "relevance": 1.0,
                "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                "supersedes_object_id": None,
                "superseded_by_object_id": None,
                "scope_matches": [{"kind": "thread", "value": "thread-1"}],
                "provenance_references": [
                    {"source_kind": "continuity_capture_event", "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
                    {"source_kind": "thread", "source_id": "thread-1"},
                ],
                "ordering": {
                    "scope_match_count": 1,
                    "query_term_match_count": 2,
                    "confirmation_rank": 3,
                    "freshness_posture": "fresh",
                    "freshness_rank": 4,
                    "provenance_posture": "strong",
                    "provenance_rank": 3,
                    "supersession_posture": "current",
                    "supersession_rank": 3,
                    "posture_rank": 2,
                    "lifecycle_rank": 4,
                    "open_contradiction_count": 0,
                    "contradiction_penalty_score": 0.0,
                    "confidence": 0.95,
                },
                "explanation": {
                    "source_facts": [
                        {"kind": "capture_event", "label": "raw_content", "value": "Decision: Keep rollout phased"},
                        {"kind": "body", "label": "decision_text", "value": "Keep rollout phased"},
                    ],
                    "trust": {
                        "trust_class": "human_curated",
                        "trust_reason": "Inferred from confirmation or correction history.",
                        "confirmation_status": "confirmed",
                        "confidence": 0.95,
                        "provenance_posture": "strong",
                        "evidence_segment_count": 1,
                        "correction_count": 0,
                        "active_signal_count": 0,
                    },
                    "contradictions": {
                        "open_case_count": 0,
                        "resolved_case_count": 0,
                        "open_case_ids": [],
                        "kinds": [],
                        "counterpart_object_ids": [],
                        "penalty_score": 0.0,
                    },
                    "evidence_segments": [
                        {
                            "relationship": "captured_from",
                            "source_kind": "continuity_capture_event",
                            "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                            "display_name": "capture event",
                            "relative_path": None,
                            "segment_kind": "capture_event",
                            "locator": None,
                            "snippet": "Decision: Keep rollout phased",
                            "created_at": "2026-03-30T09:58:00+00:00",
                        }
                    ],
                    "supersession_notes": [],
                    "timestamps": {
                        "capture_created_at": "2026-03-30T09:58:00+00:00",
                        "created_at": "2026-03-30T09:59:00+00:00",
                        "updated_at": "2026-03-30T10:00:00+00:00",
                        "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                    },
                },
                "created_at": "2026-03-30T09:59:00+00:00",
                "updated_at": "2026-03-30T10:00:00+00:00",
            }
        ],
        "summary": {
            "query": "rollout",
            "filters": {"thread_id": "thread-1", "since": None, "until": None},
            "limit": 20,
            "returned_count": 1,
            "total_count": 1,
            "order": ["relevance_desc", "created_at_desc", "id_desc"],
        },
    }

    rendered = cli_module.format_recall_output(payload)

    assert rendered == (
        "recall summary\n"
        "query: rollout\n"
        "filters: thread_id=thread-1\n"
        "returned: 1/1 (limit=20)\n"
        "order: relevance_desc, created_at_desc, id_desc\n"
        "items:\n"
        "  1. [Decision|active] Decision: Keep rollout phased\n"
        "    id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa capture_event_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb\n"
        "    lifecycle=preserved:True searchable:True promotable:True\n"
        "    confidence=0.950 relevance=1.000 confirmation=confirmed\n"
        "    freshness=fresh provenance=strong supersession=current\n"
        "    contradictions=0 penalty=0.000\n"
        "    source=(unknown)\n"
        "    provenance_refs=continuity_capture_event:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb; thread:thread-1\n"
        "    trust=human_curated reason=Inferred from confirmation or correction history. evidence_segments=1 corrections=0 active_signals=0\n"
        "    contradiction_summary=open=0 resolved=0 kinds= penalty=0.000\n"
        "    timestamps=capture_created_at=2026-03-30T09:58:00+00:00 created_at=2026-03-30T09:59:00+00:00 updated_at=2026-03-30T10:00:00+00:00 last_confirmed_at=2026-03-30T10:00:00+00:00\n"
        "    source_facts=raw_content=Decision: Keep rollout phased | decision_text=Keep rollout phased\n"
        "    evidence_segments=continuity_capture_event:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb \"Decision: Keep rollout phased\"\n"
        "    supersession_notes=(none)"
    )


def test_status_command_returns_unreachable_without_db_connection(monkeypatch, capsys) -> None:
    user_id = UUID("44444444-4444-4444-8444-444444444444")
    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(
            database_url="postgresql://db",
            healthcheck_timeout_seconds=2,
            auth_user_id=str(user_id),
        ),
    )
    monkeypatch.setattr(cli_module, "ping_database", lambda *_args, **_kwargs: False)

    exit_code = cli_module.main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "database: unreachable" in captured.out
    assert f"user_id: {user_id}" in captured.out


def test_status_command_surfaces_latest_maintenance_snapshot(monkeypatch, capsys, tmp_path: Path) -> None:
    user_id = UUID("44444444-4444-4444-8444-444444444444")
    maintenance_report_path = tmp_path / "maintenance_status_latest.json"
    maintenance_report_path.write_text(
        json.dumps(
            {
                "summary": {
                    "status": "warn",
                    "schedule": "nightly",
                    "run_completed_at": "2026-04-11T01:00:00Z",
                    "failure_count": 0,
                    "warning_count": 2,
                },
                "jobs": [
                    {
                        "job_key": "stale_fact_marking",
                        "details": {"stale_fact_count": 3},
                    },
                    {
                        "job_key": "reembed_missing_segments",
                        "details": {"reembedded_segment_count": 5},
                    },
                    {
                        "job_key": "pattern_candidate_recompute",
                        "details": {"pattern_candidate_count": 8},
                    },
                    {
                        "job_key": "benchmark_regeneration",
                        "details": {"benchmark_status": "pass"},
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(cli_module.MAINTENANCE_REPORT_PATH_ENV, str(maintenance_report_path))
    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(
            database_url="postgresql://db",
            healthcheck_timeout_seconds=2,
            auth_user_id=str(user_id),
        ),
    )
    monkeypatch.setattr(cli_module, "ping_database", lambda *_args, **_kwargs: False)

    exit_code = cli_module.main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "maintenance: status=warn schedule=nightly" in captured.out
    assert "last_run=2026-04-11T01:00:00Z" in captured.out
    assert "failures=0 warnings=2 stale_facts=3 reembedded_segments=5 pattern_candidates=8 benchmark=pass" in captured.out


def test_status_command_reports_memory_hygiene_and_thread_health_when_database_is_reachable(
    monkeypatch,
    capsys,
) -> None:
    user_id = UUID("44444444-4444-4444-8444-444444444444")

    class FakeStatusStore:
        def count_continuity_review_queue(self, *, statuses: list[str]) -> int:
            return {
                ("active",): 2,
                ("stale",): 1,
                ("superseded",): 0,
                ("deleted",): 0,
            }[tuple(statuses)]

        def list_continuity_recall_candidates(self) -> list[dict[str, object]]:
            return [
                {
                    "id": uuid4(),
                    "status": "active",
                    "object_type": "Decision",
                    "is_searchable": True,
                    "is_promotable": True,
                },
                {
                    "id": uuid4(),
                    "status": "stale",
                    "object_type": "WaitingFor",
                    "is_searchable": True,
                    "is_promotable": False,
                },
            ]

        def count_continuity_capture_events(self) -> int:
            return 7

    @contextmanager
    def fake_store_context(_ctx):
        yield FakeStatusStore()

    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(
            database_url="postgresql://db",
            healthcheck_timeout_seconds=2,
            auth_user_id=str(user_id),
        ),
    )
    monkeypatch.setattr(cli_module, "ping_database", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_module, "_store_context", fake_store_context)
    monkeypatch.setattr(
        cli_module,
        "compile_continuity_open_loop_dashboard",
        lambda *_args, **_kwargs: {
            "dashboard": {
                "summary": {"total_count": 3},
                "waiting_for": {"summary": {"total_count": 1}},
                "blocker": {"summary": {"total_count": 1}},
                "stale": {"summary": {"total_count": 1}},
                "next_action": {"summary": {"total_count": 0}},
            }
        },
    )
    monkeypatch.setattr(
        cli_module,
        "get_retrieval_evaluation_summary",
        lambda *_args, **_kwargs: {
            "summary": {
                "status": "healthy",
                "precision_at_k_mean": 0.875,
                "precision_at_1_mean": 1.0,
            }
        },
    )
    monkeypatch.setattr(
        cli_module,
        "get_memory_hygiene_dashboard_summary",
        lambda *_args, **_kwargs: {
            "dashboard": {
                "posture": "watch",
                "duplicate_group_count": 2,
                "stale_fact_count": 1,
                "unresolved_contradiction_count": 1,
                "weak_trust_count": 3,
                "review_queue_pressure": {"posture": "critical"},
            }
        },
    )
    monkeypatch.setattr(
        cli_module,
        "get_thread_health_dashboard",
        lambda *_args, **_kwargs: {
            "dashboard": {
                "posture": "critical",
                "recent_thread_count": 4,
                "stale_thread_count": 2,
                "risky_thread_count": 1,
                "watch_thread_count": 3,
            }
        },
    )

    exit_code = cli_module.main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "database: reachable" in captured.out
    assert (
        "memory_hygiene: posture=watch duplicate_groups=2 stale_facts=1 "
        "open_contradictions=1 weak_trust=3 queue_pressure=critical"
    ) in captured.out
    assert "thread_health: posture=critical recent=4 stale=2 risky=1 watch=3" in captured.out


def test_recall_formatting_renders_provenance_source_label_when_present() -> None:
    payload: ContinuityRecallResponse = {
        "items": [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "capture_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "object_type": "Decision",
                "status": "active",
                "lifecycle": {
                    "is_preserved": True,
                    "preservation_status": "preserved",
                    "is_searchable": True,
                    "searchability_status": "searchable",
                    "is_promotable": True,
                    "promotion_status": "promotable",
                },
                "title": "Decision: Keep rollout phased",
                "body": {"decision_text": "Keep rollout phased"},
                "provenance": {"source_kind": "openclaw_import", "source_label": "OpenClaw"},
                "confirmation_status": "confirmed",
                "admission_posture": "DERIVED",
                "confidence": 0.95,
                "relevance": 1.0,
                "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                "supersedes_object_id": None,
                "superseded_by_object_id": None,
                "scope_matches": [],
                "provenance_references": [
                    {"source_kind": "continuity_capture_event", "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}
                ],
                "ordering": {
                    "scope_match_count": 0,
                    "query_term_match_count": 0,
                    "confirmation_rank": 3,
                    "freshness_posture": "fresh",
                    "freshness_rank": 4,
                    "provenance_posture": "strong",
                    "provenance_rank": 3,
                    "supersession_posture": "current",
                    "supersession_rank": 3,
                    "posture_rank": 2,
                    "lifecycle_rank": 4,
                    "confidence": 0.95,
                },
                "explanation": {
                    "source_facts": [],
                    "trust": {
                        "trust_class": "llm_single_source",
                        "trust_reason": "Inferred from a single capture or provenance chain.",
                        "confirmation_status": "confirmed",
                        "confidence": 0.95,
                        "provenance_posture": "strong",
                        "evidence_segment_count": 1,
                        "correction_count": 0,
                    },
                    "evidence_segments": [
                        {
                            "relationship": "captured_from",
                            "source_kind": "continuity_capture_event",
                            "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                            "display_name": "capture event",
                            "relative_path": None,
                            "segment_kind": "capture_event",
                            "locator": None,
                            "snippet": "Decision: Keep rollout phased",
                            "created_at": "2026-03-30T09:58:00+00:00",
                        }
                    ],
                    "supersession_notes": [],
                    "timestamps": {
                        "capture_created_at": "2026-03-30T09:58:00+00:00",
                        "created_at": "2026-03-30T09:59:00+00:00",
                        "updated_at": "2026-03-30T10:00:00+00:00",
                        "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                    },
                },
                "created_at": "2026-03-30T09:59:00+00:00",
                "updated_at": "2026-03-30T10:00:00+00:00",
            }
        ],
        "summary": {
            "query": None,
            "filters": {"since": None, "until": None},
            "limit": 20,
            "returned_count": 1,
            "total_count": 1,
            "order": ["relevance_desc", "created_at_desc", "id_desc"],
        },
    }

    rendered = cli_module.format_recall_output(payload)
    assert "source=OpenClaw (openclaw_import)" in rendered
