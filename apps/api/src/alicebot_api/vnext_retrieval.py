from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Protocol
from uuid import uuid4

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONTEXT_PACK_LIMIT = 8
DEFAULT_SOURCE_LIMIT = 8
DEFAULT_OPEN_LOOP_LIMIT = 8
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
STRATEGIC_QUERY_TYPES = {"strategic_synthesis", "contradiction_check", "project_status", "agent_context"}


class VNextRetrievalValidationError(ValueError):
    """Raised when a vNext retrieval request is invalid."""


class VNextRetrievalStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTEXT_PACK_LIMIT,
    ) -> list[JsonObject]: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_SOURCE_LIMIT,
    ) -> list[JsonObject]: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_OPEN_LOOP_LIMIT,
    ) -> list[JsonObject]: ...

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[JsonObject]: ...

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class VNextRetrievalRequest:
    query: str
    domains: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    people: tuple[str, ...] = ()
    time_window: str = "all"
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    include_sources: bool = True
    include_contradictions: bool = True
    max_items: int = DEFAULT_CONTEXT_PACK_LIMIT
    max_tokens: int = 8_000
    actor_type: str = "system"
    actor_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    trace_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    item: JsonObject
    target_type: str
    rank: int
    lexical_score: int
    selected: bool
    exclusion_reason: str | None = None

    def to_trace_record(self) -> JsonObject:
        return {
            "target_type": self.target_type,
            "target_id": str(self.item.get("id")),
            "rank": self.rank,
            "selected": self.selected,
            "exclusion_reason": self.exclusion_reason,
            "stage_scores": {
                "keyword": {
                    "raw": self.lexical_score,
                    "reason": "case-insensitive token overlap against title/body/source text",
                },
                "vector": {
                    "raw": 0,
                    "reason": "vector search scaffold not enabled in this local vNext slice",
                },
                "graph": {
                    "raw": 0,
                    "reason": "graph traversal scaffold records linked edges when available",
                },
                "temporal": {
                    "raw": 0,
                    "reason": "temporal filter scaffold records requested time_window",
                },
            },
        }


def normalize_query(query: str) -> str:
    normalized = " ".join(query.split()).strip()
    if normalized == "":
        raise VNextRetrievalValidationError("query must not be empty")
    return normalized


def query_terms(query: str) -> list[str]:
    terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalize_query(query))]
    stopwords = {"about", "what", "when", "where", "which", "with", "from", "this", "that", "should", "could"}
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in stopwords or term in seen:
            continue
        deduped.append(term)
        seen.add(term)
    return deduped


def _contains_any(query: str, words: tuple[str, ...]) -> bool:
    lowered = query.casefold()
    return any(word in lowered for word in words)


def classify_query(request: VNextRetrievalRequest) -> JsonObject:
    query = normalize_query(request.query)
    lowered = query.casefold()

    if _contains_any(lowered, ("contradict", "conflict", "inconsistent", "disagree")):
        query_type = "contradiction_check"
    elif _contains_any(lowered, ("open loop", "todo", "waiting", "blocked", "unresolved")):
        query_type = "open_loop_review"
    elif _contains_any(lowered, ("project", "status", "roadmap", "milestone", "next step")):
        query_type = "project_status"
    elif _contains_any(lowered, ("who is", "person", "people", "relationship")):
        query_type = "people_context"
    elif _contains_any(lowered, ("when", "timeline", "history", "changed", "since")):
        query_type = "temporal_recall"
    elif _contains_any(lowered, ("draft", "write", "compose")):
        query_type = "draft_generation"
    elif _contains_any(lowered, ("agent", "context pack", "handoff", "resume")):
        query_type = "agent_context"
    elif query.startswith('"') and query.endswith('"'):
        query_type = "exact_recall"
    else:
        query_type = "strategic_synthesis"

    domains = list(request.domains) or _infer_domains(lowered)
    sensitivity_allowed = list(request.sensitivity_allowed) or list(DEFAULT_SENSITIVITY_ALLOWED)
    return {
        "query": query,
        "query_type": query_type,
        "terms": query_terms(query),
        "domains": domains,
        "projects": list(request.projects),
        "people": list(request.people),
        "time_window": request.time_window,
        "sensitivity_allowed": sensitivity_allowed,
        "requires_sources": request.include_sources or query_type in STRATEGIC_QUERY_TYPES,
        "requires_contradictions": request.include_contradictions and query_type in STRATEGIC_QUERY_TYPES,
        "requires_raw_evidence": _contains_any(lowered, ("quote", "source", "evidence", "prove", "where did")),
    }


def _infer_domains(lowered_query: str) -> list[str]:
    domains: list[str] = []
    if _contains_any(lowered_query, ("alice", "project", "roadmap", "sprint", "build")):
        domains.extend(["project", "professional"])
    if _contains_any(lowered_query, ("family", "health", "spiritual", "money", "legal")):
        domains.append("personal")
    return domains


def _record_text(item: JsonObject) -> str:
    parts: list[str] = []
    for key in ("title", "canonical_text", "summary", "text", "source_type", "content_hash"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
    metadata = item.get("metadata_json")
    if isinstance(metadata, dict):
        for key in ("raw_text", "relative_path", "filename"):
            value = metadata.get(key)
            if isinstance(value, str):
                parts.append(value)
    value_payload = item.get("value")
    if isinstance(value_payload, dict):
        for value in value_payload.values():
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts).casefold()


def _lexical_score(item: JsonObject, terms: list[str]) -> int:
    text = _record_text(item)
    return sum(1 for term in terms if term in text)


def _allowed(item: JsonObject, *, domains: list[str], sensitivity_allowed: list[str]) -> str | None:
    item_domain = item.get("domain")
    item_sensitivity = item.get("sensitivity")
    if domains and isinstance(item_domain, str) and item_domain not in domains and item_domain != "unknown":
        return "domain_filtered"
    if isinstance(item_sensitivity, str) and item_sensitivity not in sensitivity_allowed:
        return "sensitivity_filtered"
    return None


def _rank_candidates(
    items: list[JsonObject],
    *,
    target_type: str,
    terms: list[str],
    domains: list[str],
    sensitivity_allowed: list[str],
    limit: int,
) -> list[RetrievalCandidate]:
    candidates: list[RetrievalCandidate] = []
    for item in items:
        lexical_score = _lexical_score(item, terms)
        exclusion_reason = _allowed(item, domains=domains, sensitivity_allowed=sensitivity_allowed)
        if lexical_score == 0 and terms:
            exclusion_reason = exclusion_reason or "keyword_miss"
        candidates.append(
            RetrievalCandidate(
                item=item,
                target_type=target_type,
                rank=0,
                lexical_score=lexical_score,
                selected=False,
                exclusion_reason=exclusion_reason,
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.lexical_score, str(candidate.item.get("id"))))
    ranked: list[RetrievalCandidate] = []
    selected_count = 0
    for index, candidate in enumerate(candidates, start=1):
        selected = candidate.exclusion_reason is None and selected_count < limit
        if selected:
            selected_count += 1
        ranked.append(
            RetrievalCandidate(
                item=candidate.item,
                target_type=candidate.target_type,
                rank=index,
                lexical_score=candidate.lexical_score,
                selected=selected,
                exclusion_reason=candidate.exclusion_reason if not selected else None,
            )
        )
    return ranked


def _compact_item(item: JsonObject) -> JsonObject:
    return {key: value for key, value in item.items() if key != "deleted_at"}


class VNextRetrievalService:
    def __init__(self, store: VNextRetrievalStore) -> None:
        self.store = store

    def compile_context_pack(self, request: VNextRetrievalRequest) -> JsonObject:
        interpretation = classify_query(request)
        terms = list(interpretation["terms"])  # type: ignore[arg-type]
        domains = list(interpretation["domains"])  # type: ignore[arg-type]
        sensitivity_allowed = list(interpretation["sensitivity_allowed"])  # type: ignore[arg-type]
        trace_id = request.trace_id or str(uuid4())
        context_pack_id = str(uuid4())

        memory_rows = self.store.search_memories(
            query=request.query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(request.max_items * 2, request.max_items),
        )
        source_rows = self.store.search_sources(
            query=request.query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(DEFAULT_SOURCE_LIMIT, request.max_items),
        )
        open_loop_rows = self.store.list_open_loops(
            status="open",
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        memory_candidates = _rank_candidates(
            memory_rows,
            target_type="memory",
            terms=terms,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=request.max_items,
        )
        source_candidates = _rank_candidates(
            source_rows,
            target_type="source",
            terms=terms,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_SOURCE_LIMIT,
        )
        open_loop_candidates = _rank_candidates(
            open_loop_rows,
            target_type="open_loop",
            terms=terms,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        selected_memories = [_compact_item(candidate.item) for candidate in memory_candidates if candidate.selected]
        selected_sources = [_compact_item(candidate.item) for candidate in source_candidates if candidate.selected]
        selected_open_loops = [_compact_item(candidate.item) for candidate in open_loop_candidates if candidate.selected]
        supporting_evidence = self._supporting_evidence(selected_memories)
        warnings = self._warnings(
            memory_candidates=memory_candidates,
            source_candidates=source_candidates,
            open_loop_candidates=open_loop_candidates,
        )
        trace_candidates = [
            *(candidate.to_trace_record() for candidate in memory_candidates),
            *(candidate.to_trace_record() for candidate in source_candidates),
            *(candidate.to_trace_record() for candidate in open_loop_candidates),
        ]
        trace = {
            "trace_id": trace_id,
            "candidate_count": len(trace_candidates),
            "selected_count": sum(1 for candidate in trace_candidates if candidate["selected"]),
            "query_terms": terms,
            "filters": {
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "time_window": request.time_window,
            },
            "candidates": trace_candidates,
        }
        pack: JsonObject = {
            "context_pack_id": context_pack_id,
            "query_interpretation": interpretation,
            "current_known_state": selected_memories[:3],
            "relevant_memories": selected_memories,
            "relevant_beliefs": [item for item in selected_memories if item.get("memory_type") in {"belief", "thesis"}],
            "decisions": [item for item in selected_memories if item.get("memory_type") == "decision"],
            "open_loops": selected_open_loops,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": [],
            "recent_changes": [],
            "historical_timeline": [],
            "missing_information": self._missing_information(selected_memories, selected_sources),
            "sources": selected_sources,
            "warnings": warnings,
            "trace_id": trace_id,
            "trace": trace,
            "agent_identity": request.agent_identity,
            "policy_decision": request.policy_decision,
        }
        append_event(
            self.store,
            event_type="retrieval.context_pack_compiled",
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            target_type="context_pack",
            target_id=context_pack_id,
            trace_id=trace_id,
            run_id=request.run_id,
            payload={
                "query": request.query,
                "query_type": interpretation["query_type"],
                "candidate_count": trace["candidate_count"],
                "selected_count": trace["selected_count"],
                "warnings": warnings,
                "agent_identity": request.agent_identity,
                "policy_decision": request.policy_decision,
            },
        )
        if request.actor_type == "agent" and request.actor_id is not None:
            append_event(
                self.store,
                event_type="agent.context_pack_requested",
                actor_type="agent",
                actor_id=request.actor_id,
                target_type="context_pack",
                target_id=context_pack_id,
                trace_id=trace_id,
                run_id=request.run_id,
                payload={
                    "query": request.query,
                    "query_type": interpretation["query_type"],
                    "selected_count": trace["selected_count"],
                    "agent_identity": request.agent_identity,
                    "policy_decision": request.policy_decision,
                },
            )
        return pack

    def _supporting_evidence(self, memories: list[JsonObject]) -> list[JsonObject]:
        evidence: list[JsonObject] = []
        for memory in memories:
            memory_id = str(memory.get("id"))
            for link in self.store.list_provenance_links(target_type="memory", target_id=memory_id):
                evidence.append(
                    {
                        "target_type": "memory",
                        "target_id": memory_id,
                        "source_id": link.get("source_id"),
                        "source_chunk_id": link.get("source_chunk_id"),
                        "quote": link.get("quote"),
                        "evidence_role": link.get("evidence_role"),
                        "confidence": link.get("confidence"),
                    }
                )
        return evidence

    @staticmethod
    def _warnings(
        *,
        memory_candidates: list[RetrievalCandidate],
        source_candidates: list[RetrievalCandidate],
        open_loop_candidates: list[RetrievalCandidate],
    ) -> list[str]:
        candidates = [*memory_candidates, *source_candidates, *open_loop_candidates]
        warnings: list[str] = []
        if not any(candidate.selected for candidate in memory_candidates):
            warnings.append("no_relevant_memories_selected")
        if any(candidate.exclusion_reason == "sensitivity_filtered" for candidate in candidates):
            warnings.append("sensitive_items_filtered")
        if any(candidate.exclusion_reason == "domain_filtered" for candidate in candidates):
            warnings.append("domain_items_filtered")
        return warnings

    @staticmethod
    def _missing_information(memories: list[JsonObject], sources: list[JsonObject]) -> list[JsonObject]:
        missing: list[JsonObject] = []
        if not memories:
            missing.append({"kind": "memory", "reason": "No matching memory was selected."})
        if not sources:
            missing.append({"kind": "source", "reason": "No matching source was selected."})
        return missing


__all__ = [
    "DEFAULT_CONTEXT_PACK_LIMIT",
    "DEFAULT_SENSITIVITY_ALLOWED",
    "VNextRetrievalRequest",
    "VNextRetrievalService",
    "VNextRetrievalStore",
    "VNextRetrievalValidationError",
    "classify_query",
    "normalize_query",
    "query_terms",
]
