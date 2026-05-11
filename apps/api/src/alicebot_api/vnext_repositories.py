from __future__ import annotations

from typing import Protocol


JsonObject = dict[str, object]


class EventStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[JsonObject]: ...


class SourceStore(Protocol):
    def create_source(self, source: JsonObject) -> JsonObject: ...

    def get_source(self, source_id: str) -> JsonObject | None: ...

    def get_source_by_content_hash(self, content_hash: str) -> JsonObject | None: ...

    def update_source(self, *, source_id: str, patch: JsonObject) -> JsonObject: ...

    def delete_source(self, *, source_id: str) -> JsonObject: ...

    def create_source_chunk(self, chunk: JsonObject) -> JsonObject: ...

    def list_source_chunks(self, source_id: str) -> list[JsonObject]: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...


class MemoryStore(Protocol):
    def create_memory(self, memory: JsonObject) -> JsonObject: ...

    def get_memory(self, memory_id: str) -> JsonObject | None: ...

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def update_memory(self, *, memory_id: str, patch: JsonObject) -> JsonObject: ...


class RevisionStore(Protocol):
    def append_revision(self, revision: JsonObject) -> JsonObject: ...

    def list_revisions(self, memory_id: str) -> list[JsonObject]: ...


class ProvenanceStore(Protocol):
    def create_provenance_link(self, link: JsonObject) -> JsonObject: ...

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[JsonObject]: ...


class EmbeddingStore(Protocol):
    def upsert_embedding(self, embedding: JsonObject) -> JsonObject: ...

    def list_embeddings(self, *, target_type: str, target_id: str) -> list[JsonObject]: ...


class GraphStore(Protocol):
    def create_edge(self, edge: JsonObject) -> JsonObject: ...

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[JsonObject]: ...

    def update_edge_status(self, *, edge_id: str, status: str) -> JsonObject: ...

    def expire_edge(self, *, edge_id: str) -> JsonObject: ...


class ProjectStore(Protocol):
    def create_project(self, project: JsonObject) -> JsonObject: ...

    def get_project(self, project_id: str) -> JsonObject | None: ...

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def update_project(self, *, project_id: str, patch: JsonObject) -> JsonObject: ...


class PeopleStore(Protocol):
    def create_person(self, person: JsonObject) -> JsonObject: ...

    def get_person(self, person_id: str) -> JsonObject | None: ...

    def update_person(self, *, person_id: str, patch: JsonObject) -> JsonObject: ...


class BeliefStore(Protocol):
    def create_belief(self, belief: JsonObject) -> JsonObject: ...

    def get_belief(self, belief_id: str) -> JsonObject | None: ...

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
    ) -> JsonObject: ...


class OpenLoopStore(Protocol):
    def create_open_loop(self, loop: JsonObject) -> JsonObject: ...

    def get_open_loop(self, loop_id: str) -> JsonObject | None: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def update_open_loop(self, *, loop_id: str, patch: JsonObject) -> JsonObject: ...

    def update_open_loop_status(self, *, loop_id: str, status: str, resolution_note: str | None = None) -> JsonObject: ...


class ArtifactStore(Protocol):
    def create_artifact(self, artifact: JsonObject) -> JsonObject: ...

    def get_artifact(self, artifact_id: str) -> JsonObject | None: ...

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def update_artifact_status(self, *, artifact_id: str, status: str) -> JsonObject: ...


class TaskQueueStore(Protocol):
    def create_task(self, task: JsonObject) -> JsonObject: ...

    def claim_next_task(self) -> JsonObject | None: ...

    def update_task_status(self, *, task_id: str, status: str, details: JsonObject | None = None) -> JsonObject: ...


class BrainCharterStore(Protocol):
    def upsert_brain_charter(self, charter: JsonObject) -> JsonObject: ...

    def get_brain_charter(self) -> JsonObject | None: ...


class PolicyStore(Protocol):
    def get_connector_policy(self, connector_name: str) -> JsonObject | None: ...

    def evaluate_retrieval_policy(self, request: JsonObject) -> JsonObject: ...

    def evaluate_write_policy(self, request: JsonObject) -> JsonObject: ...


class EvalStore(Protocol):
    def create_eval_run(self, run: JsonObject) -> JsonObject: ...

    def append_eval_result(self, result: JsonObject) -> JsonObject: ...

    def list_eval_runs(self, *, suite: str | None = None) -> list[JsonObject]: ...


__all__ = [
    "ArtifactStore",
    "EmbeddingStore",
    "EvalStore",
    "EventStore",
    "GraphStore",
    "JsonObject",
    "BeliefStore",
    "BrainCharterStore",
    "MemoryStore",
    "OpenLoopStore",
    "PeopleStore",
    "PolicyStore",
    "ProjectStore",
    "ProvenanceStore",
    "RevisionStore",
    "SourceStore",
    "TaskQueueStore",
]
