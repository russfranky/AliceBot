from __future__ import annotations

import pytest

from alicebot_api.vnext_connections import (
    ConnectionFinderRequest,
    VNextConnectionService,
    VNextConnectionValidationError,
)


class InMemoryVNextConnectionStore:
    def __init__(self) -> None:
        self.sources: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.edges: dict[str, dict[str, object]] = {}
        self.artifacts: dict[str, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def create_artifact(self, artifact: dict[str, object]) -> dict[str, object]:
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
        self.artifacts[str(row["id"])] = row
        return row

    def create_edge(self, edge: dict[str, object]) -> dict[str, object]:
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
        return _filter_rows(self.memories, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]


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


def _seed_store() -> InMemoryVNextConnectionStore:
    store = InMemoryVNextConnectionStore()
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Queue retrieval pattern note",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "raw_text": "The queue and retrieval pattern both need provenance trace review.",
                "source_chunk_ids": ["chunk-1"],
            },
        }
    )
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "semantic",
            "canonical_text": "Retrieval provenance trace review improves queue artifacts.",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    store.memories.append(
        {
            "id": "belief-1",
            "memory_type": "belief",
            "canonical_text": "Provenance trace review should guide retrieval quality.",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    return store


def test_connection_report_creates_candidate_edges_artifact_and_logs_each_edge() -> None:
    store = _seed_store()

    artifact = VNextConnectionService(store).generate_connection_report(
        ConnectionFinderRequest(domains=("project",), max_connections=2)
    )

    assert artifact["artifact_type"] == "connection_report"
    assert artifact["status"] == "needs_review"
    assert artifact["sensitivity"] == "private"
    assert len(artifact["metadata_json"]["candidate_edge_ids"]) == 2
    assert "## Candidate Connections" in artifact["content_markdown"]
    assert "[edge for edge" not in artifact["content_markdown"]
    first_edge = store.edges["edge-1"]
    assert first_edge["from_type"] == "source"
    assert first_edge["to_type"] == "memory"
    assert first_edge["metadata_json"]["status"] == "candidate"
    assert first_edge["metadata_json"]["connection"]["confidence"] >= 0.6
    assert "chunk-1" in first_edge["metadata_json"]["connection"]["provenance"]
    assert [event["event_type"] for event in store.events].count("connection.candidate_edge_logged") == 2
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_connection_report_filters_sensitivity_and_can_auto_accept_high_confidence_edges() -> None:
    store = _seed_store()
    store.memories.append(
        {
            "id": "secret-memory",
            "memory_type": "semantic",
            "canonical_text": "Retrieval provenance trace secret review.",
            "domain": "project",
            "sensitivity": "highly_sensitive",
        }
    )

    artifact = VNextConnectionService(store).generate_connection_report(
        ConnectionFinderRequest(
            domains=("project",),
            sensitivity_allowed=("public", "private"),
            max_connections=3,
            auto_accept_threshold=0.6,
        )
    )

    assert "secret-memory" not in artifact["content_markdown"]
    assert store.edges["edge-1"]["metadata_json"]["status"] == "accepted"
    assert store.edges["edge-1"]["metadata_json"]["candidate"] is False


def test_connection_edge_review_and_graph_neighborhood() -> None:
    store = _seed_store()
    service = VNextConnectionService(store)
    service.generate_connection_report(ConnectionFinderRequest(domains=("project",), max_connections=1))

    accepted = service.review_edge(edge_id="edge-1", action="accept")
    neighborhood = service.graph_neighborhood(target_id="source-1")

    assert accepted["metadata_json"]["status"] == "accepted"
    assert accepted["metadata_json"]["candidate"] is False
    assert store.events[-1]["event_type"] == "graph_edge.reviewed"
    assert neighborhood["edge_count"] == 1
    assert neighborhood["from_edges"][0]["id"] == "edge-1"

    rejected = service.review_edge(edge_id="edge-1", action="reject")
    assert rejected["metadata_json"]["status"] == "rejected"
    assert service.graph_neighborhood(target_id="source-1")["edge_count"] == 0


def test_connection_request_validation() -> None:
    service = VNextConnectionService(InMemoryVNextConnectionStore())

    with pytest.raises(VNextConnectionValidationError, match="max_connections"):
        service.generate_connection_report(ConnectionFinderRequest(max_connections=0))

    with pytest.raises(VNextConnectionValidationError, match="edge review action"):
        service.review_edge(edge_id="edge-1", action="ship")
