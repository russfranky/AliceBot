from __future__ import annotations

import pytest

from alicebot_api.vnext_contradictions import (
    ContradictionFinderRequest,
    VNextContradictionService,
    VNextContradictionValidationError,
)


class InMemoryVNextContradictionStore:
    def __init__(self) -> None:
        self.sources: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.beliefs: dict[str, dict[str, object]] = {}
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

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        rows = [row for row in self.beliefs.values() if status is None or row.get("status") == status]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def get_belief(self, belief_id: str) -> dict[str, object] | None:
        return self.beliefs.get(belief_id)

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

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[dict[str, object]]:
        return [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]


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


def _seed_store() -> InMemoryVNextContradictionStore:
    store = InMemoryVNextContradictionStore()
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
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "decision",
            "canonical_text": "Alice should not auto-promote generated artifacts into memory.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    store.beliefs["belief-1"] = {
        "id": "belief-1",
        "memory_id": "belief-memory-1",
        "claim": "Alice should auto-promote generated artifacts into memory.",
        "status": "active",
        "confidence": 0.8,
        "domain": "project",
        "sensitivity": "private",
        "memory_type": "belief",
    }
    return store


def test_contradiction_report_creates_candidate_edges_and_preserves_beliefs() -> None:
    store = _seed_store()

    artifact = VNextContradictionService(store).generate_contradiction_report(
        ContradictionFinderRequest(domains=("project",), max_contradictions=2)
    )

    assert artifact["artifact_type"] == "contradiction_report"
    assert artifact["status"] == "needs_review"
    assert artifact["sensitivity"] == "private"
    assert len(artifact["metadata_json"]["candidate_edge_ids"]) == 2
    assert "New claim:" in artifact["content_markdown"]
    assert "Active belief:" in artifact["content_markdown"]
    assert store.beliefs["belief-1"]["status"] == "active"
    first_edge = store.edges["edge-1"]
    assert first_edge["edge_type"] == "contradicts"
    assert first_edge["metadata_json"]["status"] == "candidate"
    contradiction = first_edge["metadata_json"]["contradiction"]
    assert contradiction["recommended_action"] == "review"
    assert "belief:belief-1" in contradiction["provenance"]
    assert [event["event_type"] for event in store.events].count("contradiction.candidate_edge_logged") == 2
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_contradiction_report_filters_sensitivity_and_distinguishes_nuance() -> None:
    store = _seed_store()
    store.sources.append(
        {
            "id": "source-secret",
            "source_type": "manual_text",
            "title": "Secret policy note",
            "content_hash": "sha256:secret",
            "domain": "project",
            "sensitivity": "highly_sensitive",
            "metadata_json": {"raw_text": "Alice should not auto-promote generated artifacts into memory."},
        }
    )
    store.sources[0]["metadata_json"] = {
        "raw_text": "Alice might not auto-promote generated artifacts into memory when context depends."
    }

    artifact = VNextContradictionService(store).generate_contradiction_report(
        ContradictionFinderRequest(
            domains=("project",),
            sensitivity_allowed=("public", "private"),
            max_contradictions=2,
        )
    )

    assert "source-secret" not in artifact["content_markdown"]
    nuanced = [
        contradiction
        for contradiction in artifact["metadata_json"]["contradictions"]
        if contradiction["nuance"] == "possible nuance"
    ]
    assert nuanced[0]["recommended_action"] == "request more info"


def test_belief_review_and_state_history() -> None:
    store = _seed_store()
    service = VNextContradictionService(store)

    challenged = service.review_belief(belief_id="belief-1", action="challenge", confidence=0.35)
    state = service.belief_state(belief_id="belief-1")

    assert challenged["status"] == "challenged"
    assert challenged["confidence"] == 0.35
    assert state["current"]["status"] == "challenged"
    assert "challenged" in state["previous_statuses"]
    assert store.events[-1]["event_type"] == "belief.challenged"

    superseded = service.review_belief(belief_id="belief-1", action="supersede", superseded_by="belief-2")
    assert superseded["status"] == "superseded"
    assert superseded["superseded_by"] == "belief-2"


def test_contradiction_validation_errors() -> None:
    service = VNextContradictionService(InMemoryVNextContradictionStore())

    with pytest.raises(VNextContradictionValidationError, match="max_contradictions"):
        service.generate_contradiction_report(ContradictionFinderRequest(max_contradictions=0))

    with pytest.raises(VNextContradictionValidationError, match="belief review action"):
        service.review_belief(belief_id="belief-1", action="delete")

    with pytest.raises(VNextContradictionValidationError, match="was not found"):
        service.belief_state(belief_id="missing")
