from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Protocol

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONTRADICTION_LIMIT = 8
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
BELIEF_REVIEW_ACTIONS = {
    "reinforce": "active",
    "challenge": "challenged",
    "supersede": "superseded",
    "retire": "retired",
}
NEGATION_PATTERNS = (
    r"\bnot\b",
    r"\bnever\b",
    r"\bno longer\b",
    r"\bshould not\b",
    r"\bmust not\b",
    r"\bdo not\b",
    r"\bdoes not\b",
    r"\bcannot\b",
)
NUANCE_TERMS = {"sometimes", "maybe", "might", "could", "depends", "partially"}
STOPWORDS = {
    "about",
    "after",
    "again",
    "alice",
    "because",
    "before",
    "being",
    "belief",
    "claim",
    "could",
    "from",
    "have",
    "into",
    "memory",
    "note",
    "project",
    "should",
    "that",
    "this",
    "with",
}


class VNextContradictionValidationError(ValueError):
    """Raised when a vNext contradiction or belief operation is invalid."""


class VNextContradictionStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_artifact(self, artifact: JsonObject) -> JsonObject: ...

    def create_edge(self, edge: JsonObject) -> JsonObject: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTRADICTION_LIMIT,
    ) -> list[JsonObject]: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTRADICTION_LIMIT,
    ) -> list[JsonObject]: ...

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTRADICTION_LIMIT,
    ) -> list[JsonObject]: ...

    def get_belief(self, belief_id: str) -> JsonObject | None: ...

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
    ) -> JsonObject: ...

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class ContradictionFinderRequest:
    query: str = ""
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    max_contradictions: int = DEFAULT_CONTRADICTION_LIMIT
    generated_by: str = "system"
    actor_id: str | None = None
    trace_id: str | None = None
    run_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    metadata_json: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContradictionCandidate:
    new_item: JsonObject
    belief: JsonObject
    contradiction_type: str
    explanation: str
    nuance: str
    recommended_action: str
    confidence: float
    shared_terms: tuple[str, ...]

    def to_record(self) -> JsonObject:
        return {
            "source_item": f"{self._item_type()}:{self.new_item.get('id')}",
            "belief_id": str(self.belief.get("id")),
            "belief_memory_id": str(self.belief.get("memory_id")),
            "contradiction_type": self.contradiction_type,
            "quote_new": _text(self.new_item),
            "quote_belief": str(self.belief.get("claim", "")),
            "explanation": self.explanation,
            "nuance": self.nuance,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "provenance": [f"{self._item_type()}:{self.new_item.get('id')}", f"belief:{self.belief.get('id')}"],
            "shared_terms": list(self.shared_terms),
        }

    def _item_type(self) -> str:
        return "source" if "content_hash" in self.new_item or "source_type" in self.new_item else "memory"


def _validate_request(request: ContradictionFinderRequest) -> None:
    if request.max_contradictions < 1 or request.max_contradictions > 50:
        raise VNextContradictionValidationError("max_contradictions must be between 1 and 50")
    if not request.sensitivity_allowed:
        raise VNextContradictionValidationError("sensitivity_allowed must not be empty")


def _text(row: JsonObject) -> str:
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        raw_text = metadata.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            return " ".join(raw_text.split())
    for key in ("claim", "canonical_text", "summary", "title", "memory_key"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    value = row.get("value")
    if isinstance(value, dict):
        text = " ".join(str(child) for child in value.values() if isinstance(child, (str, int, float, bool)))
        if text.strip():
            return " ".join(text.split())
    return str(row.get("id", "item"))


def _terms(text: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        if token.casefold() not in STOPWORDS
    }


def _is_negated(text: str) -> bool:
    lowered = text.casefold()
    return any(re.search(pattern, lowered) for pattern in NEGATION_PATTERNS)


def _has_nuance(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in NUANCE_TERMS)


def _contradiction_type(new_text: str, belief: JsonObject) -> str:
    belief_text = str(belief.get("claim", ""))
    memory_type = belief.get("memory_type")
    if memory_type in {"belief", "thesis"}:
        return "belief_conflict"
    if "priority" in (new_text + " " + belief_text).casefold():
        return "priority_conflict"
    if "before" in (new_text + " " + belief_text).casefold() or "after" in (new_text + " " + belief_text).casefold():
        return "timeline_conflict"
    return "factual_conflict"


def _candidate_for(new_item: JsonObject, belief: JsonObject) -> ContradictionCandidate | None:
    new_text = _text(new_item)
    belief_text = str(belief.get("claim", ""))
    shared_terms = _terms(new_text) & _terms(belief_text)
    if len(shared_terms) < 2:
        return None
    new_negated = _is_negated(new_text)
    belief_negated = _is_negated(belief_text)
    if new_negated == belief_negated:
        return None
    nuanced = _has_nuance(new_text) or _has_nuance(belief_text)
    confidence = round(min(0.58 + min(len(shared_terms), 5) * 0.06, 0.9), 2)
    return ContradictionCandidate(
        new_item=new_item,
        belief=belief,
        contradiction_type=_contradiction_type(new_text, belief),
        explanation=(
            f"New claim and active belief disagree on {', '.join(sorted(shared_terms)[:4])}."
        ),
        nuance="possible nuance" if nuanced else "direct conflict",
        recommended_action="request more info" if nuanced else "review",
        confidence=confidence,
        shared_terms=tuple(sorted(shared_terms)),
    )


def _find_candidates(
    *,
    new_items: list[JsonObject],
    beliefs: list[JsonObject],
    limit: int,
) -> list[ContradictionCandidate]:
    candidates: list[ContradictionCandidate] = []
    seen: set[tuple[str, str]] = set()
    for item in new_items:
        for belief in beliefs:
            pair = (str(item.get("id")), str(belief.get("id")))
            if pair in seen:
                continue
            seen.add(pair)
            candidate = _candidate_for(item, belief)
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda candidate: (-candidate.confidence, candidate.to_record()["source_item"]))
    return candidates[:limit]


def _report_markdown(records: list[JsonObject], edge_ids: list[str]) -> str:
    lines = ["# Contradiction Report", "", "## Candidate Contradictions"]
    if not records:
        lines.append("- No contradiction candidates were detected from the selected inputs.")
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"### {index}. {record['contradiction_type']}",
                f"- New claim: {record['quote_new']} ({record['source_item']})",
                f"- Active belief: {record['quote_belief']} (belief:{record['belief_id']})",
                f"- Confidence: {record['confidence']}",
                f"- Nuance: {record['nuance']}",
                f"- Recommended action: {record['recommended_action']}",
                f"- Provenance: {', '.join(str(item) for item in record['provenance'])}",
                "",
            ]
        )
    lines.extend(["## Candidate Contradiction Edges", *(f"- graph_edge:{edge_id}" for edge_id in edge_ids)])
    return "\n".join(lines).rstrip() + "\n"


class VNextContradictionService:
    def __init__(self, store: VNextContradictionStore) -> None:
        self.store = store

    def generate_contradiction_report(self, request: ContradictionFinderRequest | None = None) -> JsonObject:
        request = request or ContradictionFinderRequest()
        _validate_request(request)
        domains = list(request.domains) if request.domains else None
        sensitivity_allowed = list(request.sensitivity_allowed)
        sources = self.store.search_sources(
            query=request.query,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(request.max_contradictions * 2, request.max_contradictions),
        )
        memories = [
            memory
            for memory in self.store.search_memories(
                query=request.query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=max(request.max_contradictions * 2, request.max_contradictions),
            )
            if memory.get("memory_type") not in {"belief", "thesis"}
        ]
        beliefs = self.store.list_beliefs(
            status="active",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(request.max_contradictions * 2, request.max_contradictions),
        )
        candidates = _find_candidates(
            new_items=[*sources, *memories],
            beliefs=beliefs,
            limit=request.max_contradictions,
        )
        edge_ids: list[str] = []
        records: list[JsonObject] = []
        for candidate in candidates:
            record = candidate.to_record()
            edge = self.store.create_edge(
                {
                    "from_type": "source" if record["source_item"].startswith("source:") else "memory",
                    "from_id": str(candidate.new_item.get("id")),
                    "to_type": "belief",
                    "to_id": str(candidate.belief.get("id")),
                    "edge_type": "contradicts",
                    "confidence": candidate.confidence,
                    "explanation": candidate.explanation,
                    "created_by": "vnext_contradiction_finder",
                    "metadata_json": {
                        "status": "candidate",
                        "candidate": True,
                        "contradiction": record,
                        "generated_by": request.generated_by,
                        "scheduler_run_id": request.run_id if request.generated_by == "scheduler" else None,
                        "trace_id": request.trace_id,
                        "policy_decision": request.policy_decision,
                    },
                }
            )
            edge_id = str(edge["id"])
            edge_ids.append(edge_id)
            records.append(record)
            append_event(
                self.store,
                event_type="contradiction.candidate_edge_logged",
                actor_type=request.generated_by,
                actor_id=request.actor_id,
                target_type="graph_edge",
                target_id=edge_id,
                trace_id=request.trace_id,
                run_id=request.run_id,
                payload={
                    "contradiction_type": candidate.contradiction_type,
                    "belief_id": str(candidate.belief.get("id")),
                    "confidence": candidate.confidence,
                    "recommended_action": candidate.recommended_action,
                    "policy_decision": request.policy_decision,
                },
            )

        source_ids = [str(source.get("id")) for source in sources if source.get("id") is not None]
        memory_ids = [str(memory.get("id")) for memory in memories if memory.get("id") is not None]
        belief_ids = [str(belief.get("id")) for belief in beliefs if belief.get("id") is not None]
        artifact = self.store.create_artifact(
            {
                "artifact_type": "contradiction_report",
                "title": "Contradiction Report",
                "content_markdown": _report_markdown(records, edge_ids),
                "status": "needs_review",
                "domain": request.domains[0] if len(request.domains) == 1 else "unknown",
                "sensitivity": self._highest_sensitivity([*sources, *memories, *beliefs]),
                "generated_by": request.generated_by if request.generated_by != "system" else "vnext_contradiction_finder",
                "metadata_json": {
                    "workflow": "contradiction_finder",
                    "workflow_type": "contradiction_report",
                    "candidate_edge_ids": edge_ids,
                    "contradictions": records,
                    "source_ids": source_ids,
                    "memory_ids": memory_ids,
                    "belief_ids": belief_ids,
                    "source_refs": [f"source:{source_id}" for source_id in source_ids],
                    "input_counts": {
                        "sources": len(sources),
                        "memories": len(memories),
                        "beliefs": len(beliefs),
                    },
                    "generated_by": request.generated_by,
                    "agent_identity": request.agent_identity,
                    "agent_id": request.actor_id if request.generated_by == "agent" else None,
                    "agent_run_id": request.run_id if request.generated_by == "agent" else None,
                    "scheduler_run_id": request.run_id if request.generated_by == "scheduler" else None,
                    "trace_id": request.trace_id,
                    "policy_decision": request.policy_decision,
                    "review_status": "needs_review",
                    **request.metadata_json,
                },
            }
        )
        append_event(
            self.store,
            event_type="artifact.generated",
            actor_type=request.generated_by,
            actor_id=request.actor_id,
            target_type="artifact",
            target_id=str(artifact["id"]),
            trace_id=request.trace_id,
            run_id=request.run_id,
            payload={
                "workflow": "contradiction_finder",
                "workflow_type": "contradiction_report",
                "artifact_type": "contradiction_report",
                "candidate_edge_count": len(edge_ids),
                "policy_decision": request.policy_decision,
            },
        )
        return artifact

    def review_belief(
        self,
        *,
        belief_id: str,
        action: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
    ) -> JsonObject:
        status = BELIEF_REVIEW_ACTIONS.get(action)
        if status is None:
            raise VNextContradictionValidationError("belief review action must be reinforce, challenge, supersede, or retire")
        belief = self.store.update_belief_status(
            belief_id=belief_id,
            status=status,
            confidence=confidence,
            superseded_by=superseded_by,
        )
        append_event(
            self.store,
            event_type=f"belief.{status}",
            actor_type="system",
            target_type="belief",
            target_id=belief_id,
            payload={"action": action, "status": status, "confidence": confidence, "superseded_by": superseded_by},
        )
        return belief

    def belief_state(self, *, belief_id: str) -> JsonObject:
        belief = self.store.get_belief(belief_id)
        if belief is None:
            raise VNextContradictionValidationError(f"belief {belief_id} was not found")
        events = self.store.list_events(target_type="belief", target_id=belief_id)
        return {
            "belief_id": belief_id,
            "current": belief,
            "history": events,
            "previous_statuses": [
                event.get("payload_json", {}).get("status")
                for event in events
                if isinstance(event.get("payload_json"), dict) and event.get("payload_json", {}).get("status") is not None
            ],
        }

    @staticmethod
    def _highest_sensitivity(rows: list[JsonObject]) -> str:
        rank = {
            "public": 1,
            "internal": 2,
            "unknown": 2,
            "private": 3,
            "confidential": 4,
            "highly_sensitive": 5,
            "sacred": 6,
            "regulated": 6,
        }
        sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
        if not sensitivities:
            return "unknown"
        return max(sensitivities, key=lambda value: rank.get(value, rank["unknown"]))


__all__ = [
    "ContradictionFinderRequest",
    "VNextContradictionService",
    "VNextContradictionStore",
    "VNextContradictionValidationError",
]
