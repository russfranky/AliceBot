from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import re
from typing import Protocol
from uuid import uuid4

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_BRAIN_LIMIT = 8
DEFAULT_ARTIFACT_LIMIT = 4
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
SENSITIVITY_RANK = {
    "public": 1,
    "internal": 2,
    "unknown": 2,
    "private": 3,
    "confidential": 4,
    "highly_sensitive": 5,
    "sacred": 6,
    "regulated": 6,
}


class VNextBrainValidationError(ValueError):
    """Raised when a vNext brain workflow request is invalid."""


class VNextBrainStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_open_loop(self, loop: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_BRAIN_LIMIT,
    ) -> list[JsonObject]: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_BRAIN_LIMIT,
    ) -> list[JsonObject]: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_BRAIN_LIMIT,
    ) -> list[JsonObject]: ...

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_ARTIFACT_LIMIT,
    ) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class BrainArtifactRequest:
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    generated_for: str | None = None
    source_limit: int = DEFAULT_BRAIN_LIMIT
    memory_limit: int = DEFAULT_BRAIN_LIMIT
    open_loop_limit: int = DEFAULT_BRAIN_LIMIT
    artifact_limit: int = DEFAULT_ARTIFACT_LIMIT
    discover_open_loops: bool = True
    create_candidate_memories: bool = True
    generated_by: str = "system"
    actor_id: str | None = None
    trace_id: str | None = None
    run_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    metadata_json: JsonObject = field(default_factory=dict)


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _iso_week_label(day: date) -> str:
    year, week, _weekday = day.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_generated_for(value: str | None) -> date:
    if value is None:
        return datetime.now(UTC).date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise VNextBrainValidationError("generated_for must be an ISO date in YYYY-MM-DD format") from exc


def _validate_request(request: BrainArtifactRequest) -> None:
    if not request.sensitivity_allowed:
        raise VNextBrainValidationError("sensitivity_allowed must not be empty")
    for field_name in ("source_limit", "memory_limit", "open_loop_limit", "artifact_limit"):
        value = getattr(request, field_name)
        if value < 1 or value > 50:
            raise VNextBrainValidationError(f"{field_name} must be between 1 and 50")
    _parse_generated_for(request.generated_for)


def _allowed_domains(request: BrainArtifactRequest) -> list[str] | None:
    return list(request.domains) if request.domains else None


def _allowed_sensitivity(request: BrainArtifactRequest) -> list[str]:
    return list(request.sensitivity_allowed)


def _compact_row(row: JsonObject) -> JsonObject:
    return {key: value for key, value in row.items() if key != "deleted_at"}


def _title(row: JsonObject, fallback: str) -> str:
    value = row.get("title")
    if isinstance(value, str) and value.strip():
        return " ".join(value.split())
    return fallback


def _memory_text(row: JsonObject) -> str:
    for key in ("canonical_text", "summary", "title", "memory_key"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    value = row.get("value")
    if isinstance(value, dict):
        text = " ".join(str(child) for child in value.values() if isinstance(child, (str, int, float, bool)))
        if text.strip():
            return " ".join(text.split())
    return str(row.get("id", "memory"))


def _source_text(row: JsonObject) -> str:
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        raw_text = metadata.get("raw_text")
        if isinstance(raw_text, str):
            return raw_text
    return _title(row, str(row.get("source_type", "source")))


def _source_ref(row: JsonObject) -> str:
    return f"[source:{row.get('id')}]"


def _memory_ref(row: JsonObject) -> str:
    return f"[memory:{row.get('id')}]"


def _artifact_ref(row: JsonObject) -> str:
    return f"[artifact:{row.get('id')}]"


def _highest_sensitivity(rows: list[JsonObject]) -> str:
    sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
    if not sensitivities:
        return "unknown"
    return max(sensitivities, key=lambda value: SENSITIVITY_RANK.get(value, SENSITIVITY_RANK["unknown"]))


def _artifact_domain(request: BrainArtifactRequest, rows: list[JsonObject]) -> str:
    if len(request.domains) == 1:
        return request.domains[0]
    domains = {row.get("domain") for row in rows if isinstance(row.get("domain"), str)}
    if len(domains) == 1:
        return str(next(iter(domains)))
    return "unknown"


def _section(title: str, lines: list[str]) -> str:
    body = lines or ["- No matching input was available."]
    return "\n".join([f"## {title}", *body])


def _input_summary(
    *,
    sources: list[JsonObject],
    memories: list[JsonObject],
    open_loops: list[JsonObject],
    artifacts: list[JsonObject],
) -> JsonObject:
    return {
        "source_ids": [str(row.get("id")) for row in sources],
        "memory_ids": [str(row.get("id")) for row in memories],
        "open_loop_ids": [str(row.get("id")) for row in open_loops],
        "artifact_ids": [str(row.get("id")) for row in artifacts],
        "counts": {
            "sources": len(sources),
            "memories": len(memories),
            "open_loops": len(open_loops),
            "artifacts": len(artifacts),
        },
    }


def _candidate_open_loop_titles(sources: list[JsonObject]) -> list[tuple[str, JsonObject]]:
    candidates: list[tuple[str, JsonObject]] = []
    pattern = re.compile(r"^\s*(?:todo|follow up|waiting on|question|ask)\s*:?\s*(.+)$", re.IGNORECASE)
    for source in sources:
        for line in _source_text(source).splitlines():
            match = pattern.match(line)
            if match is None:
                continue
            title = " ".join(match.group(1).split())
            if title:
                candidates.append((title[:240], source))
    return candidates[:5]


class VNextBrainService:
    def __init__(self, store: VNextBrainStore) -> None:
        self.store = store

    def generate_daily_brief(self, request: BrainArtifactRequest | None = None) -> JsonObject:
        request = request or BrainArtifactRequest()
        _validate_request(request)
        day = _parse_generated_for(request.generated_for)
        sources, memories, open_loops, artifacts = self._load_inputs(request)
        candidate_open_loops = self._create_candidate_open_loops(request, sources)
        all_rows = [*sources, *memories, *open_loops, *artifacts]
        content = self._daily_markdown(
            generated_for=day.isoformat(),
            sources=sources,
            memories=memories,
            open_loops=[*open_loops, *candidate_open_loops],
            artifacts=artifacts,
        )
        artifact = self.store.create_artifact(
            {
                "artifact_type": "daily_brief",
                "title": f"Daily Brief - {day.isoformat()}",
                "content_markdown": content,
                "status": "needs_review",
                "domain": _artifact_domain(request, all_rows),
                "sensitivity": _highest_sensitivity(all_rows),
                "generated_by": request.generated_by if request.generated_by != "system" else "vnext_daily_brief",
                "metadata_json": {
                    "workflow": "daily_brief",
                    "generated_by": request.generated_by,
                    "agent_identity": request.agent_identity,
                    "agent_id": request.agent_identity.get("agent_id") if isinstance(request.agent_identity, dict) else None,
                    "agent_run_id": request.agent_identity.get("agent_run_id") if isinstance(request.agent_identity, dict) else None,
                    "scheduler_run_id": request.run_id if request.generated_by == "scheduler" else None,
                    "trace_id": request.trace_id,
                    "policy_decision": request.policy_decision,
                    "generated_for": day.isoformat(),
                    "input_summary": _input_summary(
                        sources=sources,
                        memories=memories,
                        open_loops=open_loops,
                        artifacts=artifacts,
                    ),
                    "candidate_open_loop_ids": [str(row.get("id")) for row in candidate_open_loops],
                    **request.metadata_json,
                },
            },
            actor_type=request.generated_by,
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
                "workflow": "daily_brief",
                "generated_for": day.isoformat(),
                "artifact_type": "daily_brief",
                "candidate_open_loop_count": len(candidate_open_loops),
                "agent_identity": request.agent_identity,
                "policy_decision": request.policy_decision,
            },
        )
        if request.generated_by == "agent" and request.actor_id is not None:
            append_event(
                self.store,
                event_type="agent.artifact_generated",
                actor_type="agent",
                actor_id=request.actor_id,
                target_type="artifact",
                target_id=str(artifact["id"]),
                trace_id=request.trace_id,
                run_id=request.run_id,
                payload={"workflow": "daily_brief", "agent_identity": request.agent_identity},
            )
        return artifact

    def generate_weekly_synthesis(self, request: BrainArtifactRequest | None = None) -> JsonObject:
        request = request or BrainArtifactRequest()
        _validate_request(request)
        day = _parse_generated_for(request.generated_for)
        week_label = _iso_week_label(day)
        sources, memories, open_loops, artifacts = self._load_inputs(request)
        candidate_memories = self._create_weekly_candidate_memories(request, sources, memories, open_loops)
        all_rows = [*sources, *memories, *open_loops, *artifacts]
        content = self._weekly_markdown(
            week_label=week_label,
            sources=sources,
            memories=memories,
            open_loops=open_loops,
            artifacts=artifacts,
            candidate_memories=candidate_memories,
        )
        artifact = self.store.create_artifact(
            {
                "artifact_type": "weekly_synthesis",
                "title": f"Weekly Synthesis - {week_label}",
                "content_markdown": content,
                "status": "needs_review",
                "domain": _artifact_domain(request, all_rows),
                "sensitivity": _highest_sensitivity(all_rows),
                "generated_by": request.generated_by if request.generated_by != "system" else "vnext_weekly_synthesis",
                "metadata_json": {
                    "workflow": "weekly_synthesis",
                    "generated_by": request.generated_by,
                    "agent_identity": request.agent_identity,
                    "agent_id": request.agent_identity.get("agent_id") if isinstance(request.agent_identity, dict) else None,
                    "agent_run_id": request.agent_identity.get("agent_run_id") if isinstance(request.agent_identity, dict) else None,
                    "scheduler_run_id": request.run_id if request.generated_by == "scheduler" else None,
                    "trace_id": request.trace_id,
                    "policy_decision": request.policy_decision,
                    "generated_for": day.isoformat(),
                    "week": week_label,
                    "input_summary": _input_summary(
                        sources=sources,
                        memories=memories,
                        open_loops=open_loops,
                        artifacts=artifacts,
                    ),
                    "candidate_memory_ids": [str(row.get("id")) for row in candidate_memories],
                    **request.metadata_json,
                },
            },
            actor_type=request.generated_by,
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
                "workflow": "weekly_synthesis",
                "generated_for": day.isoformat(),
                "week": week_label,
                "artifact_type": "weekly_synthesis",
                "candidate_memory_count": len(candidate_memories),
                "agent_identity": request.agent_identity,
                "policy_decision": request.policy_decision,
            },
        )
        if request.generated_by == "agent" and request.actor_id is not None:
            append_event(
                self.store,
                event_type="agent.artifact_generated",
                actor_type="agent",
                actor_id=request.actor_id,
                target_type="artifact",
                target_id=str(artifact["id"]),
                trace_id=request.trace_id,
                run_id=request.run_id,
                payload={"workflow": "weekly_synthesis", "agent_identity": request.agent_identity},
            )
        return artifact

    def _load_inputs(
        self,
        request: BrainArtifactRequest,
    ) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], list[JsonObject]]:
        domains = _allowed_domains(request)
        sensitivity_allowed = _allowed_sensitivity(request)
        sources = [
            _compact_row(row)
            for row in self.store.search_sources(
                query="",
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=request.source_limit,
            )
        ]
        memories = [
            _compact_row(row)
            for row in self.store.search_memories(
                query="",
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=request.memory_limit,
            )
        ]
        open_loops = [
            _compact_row(row)
            for row in self.store.list_open_loops(
                status="open",
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=request.open_loop_limit,
            )
        ]
        artifacts = [
            _compact_row(row)
            for row in self.store.list_artifacts(
                artifact_type=None,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=request.artifact_limit,
            )
        ]
        return sources, memories, open_loops, artifacts

    def _create_candidate_open_loops(
        self,
        request: BrainArtifactRequest,
        sources: list[JsonObject],
    ) -> list[JsonObject]:
        if not request.discover_open_loops:
            return []
        created: list[JsonObject] = []
        for title, source in _candidate_open_loop_titles(sources):
            created.append(
                self.store.create_open_loop(
                    {
                        "title": title,
                        "description": f"Candidate open loop discovered in {_title(source, 'source')}.",
                        "status": "open",
                        "priority": "normal",
                        "source_id": source.get("id"),
                        "domain": source.get("domain", "unknown"),
                        "sensitivity": source.get("sensitivity", "unknown"),
                        "metadata_json": {
                            "candidate": True,
                            "discovered_by": "vnext_daily_brief",
                            "source_id": source.get("id"),
                        },
                    },
                    actor_type=request.generated_by,
                )
            )
        return created

    def _create_weekly_candidate_memories(
        self,
        request: BrainArtifactRequest,
        sources: list[JsonObject],
        memories: list[JsonObject],
        open_loops: list[JsonObject],
    ) -> list[JsonObject]:
        if not request.create_candidate_memories or not (sources or memories or open_loops):
            return []
        insight = self._weekly_pattern_line(sources=sources, memories=memories, open_loops=open_loops)
        return [
            self.store.create_memory(
                {
                    "memory_type": "artifact_summary",
                    "memory_key": f"weekly_synthesis.{uuid4()}",
                    "value": {"insight": insight},
                    "status": "candidate",
                    "confidence": 0.6,
                    "canonical_text": insight,
                    "summary": insight,
                    "domain": _artifact_domain(request, [*sources, *memories, *open_loops]),
                    "sensitivity": _highest_sensitivity([*sources, *memories, *open_loops]),
                    "metadata_json": {
                        "candidate": True,
                        "discovered_by": "vnext_weekly_synthesis",
                        "generated_by": request.generated_by,
                        "agent_identity": request.agent_identity,
                        "scheduler_run_id": request.run_id if request.generated_by == "scheduler" else None,
                        "trace_id": request.trace_id,
                    },
                },
                actor_type=request.generated_by,
            )
        ]

    def _daily_markdown(
        self,
        *,
        generated_for: str,
        sources: list[JsonObject],
        memories: list[JsonObject],
        open_loops: list[JsonObject],
        artifacts: list[JsonObject],
    ) -> str:
        source_lines = [
            f"- Fact: {_title(source, 'Untitled source')} was captured for review. {_source_ref(source)}"
            for source in sources[:3]
        ]
        memory_lines = [
            f"- Fact: {_memory_text(memory)} {_memory_ref(memory)}"
            for memory in memories[:3]
        ]
        loop_lines = [
            f"- Action: {_title(loop, 'Open loop')} [open_loop:{loop.get('id')}]"
            for loop in open_loops[:5]
        ]
        connection_lines = self._connection_lines(sources=sources, memories=memories, artifacts=artifacts)
        sources_used = [
            f"- {_source_ref(source)} {_title(source, 'Untitled source')}"
            for source in sources
        ] or ["- No source records were available."]
        return "\n\n".join(
            [
                f"# Daily Brief - {generated_for}",
                _section("1. Executive Summary", source_lines or memory_lines),
                _section("2. Project Status", memory_lines),
                _section("3. Open Loops", loop_lines),
                _section("4. New Connections", connection_lines),
                _section("5. Contradictions / Tensions", ["- Inference: No contradiction scan is enabled in this Sprint 5 scaffold."]),
                _section("6. Emerging Pattern", [f"- Inference: {self._daily_pattern_line(sources, memories)}"]),
                _section("7. Suggested Focus", self._suggested_focus_lines(open_loops=open_loops, memories=memories)),
                _section("8. People to Follow Up With", ["- Inference: No person-specific follow-up was detected."]),
                _section("9. Sources Used", sources_used),
            ]
        )

    def _weekly_markdown(
        self,
        *,
        week_label: str,
        sources: list[JsonObject],
        memories: list[JsonObject],
        open_loops: list[JsonObject],
        artifacts: list[JsonObject],
        candidate_memories: list[JsonObject],
    ) -> str:
        moved = [
            f"- Fact: {_memory_text(memory)} {_memory_ref(memory)}"
            for memory in memories[:5]
        ] or [
            f"- Fact: {_title(source, 'Untitled source')} entered the evidence archive. {_source_ref(source)}"
            for source in sources[:5]
        ]
        blocked = [
            f"- Action: {_title(loop, 'Open loop')} remains open. [open_loop:{loop.get('id')}]"
            for loop in open_loops[:5]
        ]
        links = self._weekly_link_lines(sources=sources, memories=memories, artifacts=artifacts)
        candidate_lines = [
            f"- Candidate memory: {_memory_text(memory)} {_memory_ref(memory)}"
            for memory in candidate_memories
        ] or ["- No candidate memory was created because no meaningful weekly input was available."]
        sources_used = [
            f"- {_source_ref(source)} {_title(source, 'Untitled source')}"
            for source in sources
        ] or ["- No source records were available."]
        return "\n\n".join(
            [
                f"# Weekly Synthesis - {week_label}",
                _section("1. What moved forward", moved),
                _section("2. What did not move", blocked or ["- Inference: No unresolved open loops were selected."]),
                _section("3. Recurring patterns", [f"- Inference: {self._weekly_pattern_line(sources=sources, memories=memories, open_loops=open_loops)}"]),
                _section("4. Contradictions or changed assumptions", ["- Inference: No contradiction scan is enabled in this Sprint 5 scaffold."]),
                _section("5. Emerging thesis", candidate_lines),
                _section("6. Highest-leverage next actions", self._suggested_focus_lines(open_loops=open_loops, memories=memories)),
                _section("7. What to stop doing / thinking about", ["- Inference: Stop treating generated synthesis as durable memory until reviewed."]),
                _section("Project / Person / Concept Links", links),
                _section("8. Sources Used", sources_used),
            ]
        )

    @staticmethod
    def _connection_lines(
        *,
        sources: list[JsonObject],
        memories: list[JsonObject],
        artifacts: list[JsonObject],
    ) -> list[str]:
        lines: list[str] = []
        if sources and memories:
            lines.append(
                f"- Inference: {_title(sources[0], 'Source')} may relate to {_memory_text(memories[0])}. "
                f"{_source_ref(sources[0])} {_memory_ref(memories[0])}"
            )
        if artifacts and sources:
            lines.append(
                f"- Inference: {_title(artifacts[0], 'Artifact')} should be reviewed against new source "
                f"{_title(sources[0], 'Source')}. {_artifact_ref(artifacts[0])} {_source_ref(sources[0])}"
            )
        return lines or ["- Inference: No non-obvious connection was detected from the selected inputs."]

    @staticmethod
    def _weekly_link_lines(
        *,
        sources: list[JsonObject],
        memories: list[JsonObject],
        artifacts: list[JsonObject],
    ) -> list[str]:
        rows = [*memories, *sources, *artifacts]
        labels: list[str] = []
        for row in rows[:3]:
            if "canonical_text" in row:
                labels.append(f"- Link: {_memory_text(row)} {_memory_ref(row)}")
            elif "content_hash" in row:
                labels.append(f"- Link: {_title(row, 'Source')} {_source_ref(row)}")
            else:
                labels.append(f"- Link: {_title(row, 'Artifact')} {_artifact_ref(row)}")
        if labels:
            return labels
        return ["- No project/person/concept links were available from the selected inputs."]

    @staticmethod
    def _daily_pattern_line(sources: list[JsonObject], memories: list[JsonObject]) -> str:
        if len(sources) + len(memories) >= 2:
            return "Recent inputs cluster around the selected domain and should be reviewed together."
        return "No strong pattern found from the selected daily inputs."

    @staticmethod
    def _weekly_pattern_line(
        *,
        sources: list[JsonObject],
        memories: list[JsonObject],
        open_loops: list[JsonObject],
    ) -> str:
        if len(open_loops) >= 2:
            return "Multiple open loops remained active across the weekly window."
        if len(sources) + len(memories) >= 2:
            return "Evidence and memories repeated across the weekly window."
        return "No strong pattern found from the selected weekly inputs."

    @staticmethod
    def _suggested_focus_lines(*, open_loops: list[JsonObject], memories: list[JsonObject]) -> list[str]:
        if open_loops:
            return [f"- Action: Resolve or clarify {_title(open_loops[0], 'the highest-priority open loop')}."]
        if memories:
            return [f"- Action: Review {_memory_text(memories[0])} for promotion or follow-up."]
        return ["- Action: Capture more evidence before making a planning decision."]


__all__ = [
    "BrainArtifactRequest",
    "DEFAULT_ARTIFACT_LIMIT",
    "DEFAULT_BRAIN_LIMIT",
    "DEFAULT_SENSITIVITY_ALLOWED",
    "VNextBrainService",
    "VNextBrainStore",
    "VNextBrainValidationError",
]
