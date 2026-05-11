from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Protocol

from alicebot_api.vnext_connectors import VNextConnectorService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


class VNextDogfoodingStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def list_events(self, *, target_type: str | None = None, target_id: str | None = None) -> list[JsonObject]: ...

    def list_sources(
        self,
        *,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 20,
    ) -> list[JsonObject]: ...

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]: ...

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[JsonObject]: ...

    def list_artifact_quality_ratings(
        self,
        *,
        artifact_id: str | None = None,
        limit: int = 100,
    ) -> list[JsonObject]: ...

    def list_open_loops(self, *, status: str | None = None, limit: int = 20) -> list[JsonObject]: ...

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[JsonObject]: ...


def _event_payload(event: JsonObject) -> JsonObject:
    payload = event.get("payload_json")
    return payload if isinstance(payload, dict) else {}


def _connector_name_from_source(source: JsonObject) -> str:
    return str(source.get("connector_name") or source.get("source_type") or "unknown")


def _status_counts(rows: list[JsonObject], field: str = "status") -> dict[str, int]:
    counter = Counter(str(row.get(field) or "unknown") for row in rows)
    return dict(sorted(counter.items()))


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _record_timestamp(row: JsonObject) -> datetime | None:
    for key in ("captured_at", "created_at", "occurred_at"):
        parsed = _parse_datetime(row.get(key))
        if parsed is not None:
            return parsed.astimezone(UTC)
    return None


def _count_since(rows: list[JsonObject], cutoff: datetime) -> int:
    return sum(1 for row in rows if (timestamp := _record_timestamp(row)) is not None and timestamp >= cutoff)


class VNextDogfoodingService:
    def __init__(self, store: VNextDogfoodingStore) -> None:
        self.store = store

    def dashboard(self) -> JsonObject:
        sources = self.store.list_sources(limit=500)
        memories = self.store.list_memories(status=None)
        candidate_memories = [memory for memory in memories if memory.get("status") == "candidate"]
        artifacts = self.store.list_artifacts(limit=500)
        ratings = self.store.list_artifact_quality_ratings(limit=500)
        open_loops = self.store.list_open_loops(status=None, limit=500)
        events = self.store.list_events()
        scheduler_runs = self.store.list_scheduler_runs(limit=20)
        now = datetime.now(UTC)
        today_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_cutoff = now - timedelta(days=7)

        connector_counts = Counter(_connector_name_from_source(source) for source in sources)
        event_types = Counter(str(event.get("event_type") or "unknown") for event in events)
        policy_events = [
            event
            for event in events
            if str(event.get("event_type") or "") in {"agent.policy_blocked", "agent.policy_filtered"}
        ]
        feedback_events = [
            event
            for event in events
            if event.get("event_type") == "artifact.insight_feedback_recorded"
        ]
        quality_scores = [
            float(rating["usefulness"])
            for rating in ratings
            if isinstance(rating.get("usefulness"), int | float) and not isinstance(rating.get("usefulness"), bool)
        ]
        last_successful_scheduler_run = next(
            (run for run in scheduler_runs if run.get("status") == "succeeded"),
            None,
        )

        return {
            "captures_by_connector": [
                {"connector_name": name, "count": count}
                for name, count in sorted(connector_counts.items())
            ],
            "captures_today": _count_since(sources, today_cutoff),
            "captures_this_week": _count_since(sources, week_cutoff),
            "candidate_memories_created": len(candidate_memories),
            "memory_status_counts": _status_counts(memories),
            "generated_artifacts_created": len(artifacts),
            "artifact_status_counts": _status_counts(artifacts),
            "artifact_quality_average": round(mean(quality_scores), 2) if quality_scores else None,
            "artifact_quality_rating_count": len(ratings),
            "daily_brief_review_status": _latest_artifact_status(artifacts, "daily_brief"),
            "weekly_synthesis_review_status": _latest_artifact_status(artifacts, "weekly_synthesis"),
            "connections_surfaced": event_types.get("graph_edge.created", 0),
            "contradictions_surfaced": event_types.get("belief.challenge_created", 0)
            + event_types.get("contradiction_report.generated", 0),
            "open_loop_status_counts": _status_counts(open_loops),
            "open_loops_created": len(open_loops),
            "open_loops_closed": sum(1 for loop in open_loops if loop.get("status") == "resolved"),
            "agent_context_packs_requested": event_types.get("context_pack.created", 0),
            "agent_memory_proposals": event_types.get("memory.candidate_created", 0),
            "policy_blocks_filters": len(policy_events),
            "connector_failures": event_types.get("connector.item_failed", 0)
            + event_types.get("connector.sync_failed", 0),
            "last_successful_scheduler_run": last_successful_scheduler_run,
            "connector_health": VNextConnectorService(self.store).connector_health_all(),
            "insight_feedback": {
                "count": len(feedback_events),
                "useful_yes": _feedback_count(feedback_events, "yes"),
                "useful_no": _feedback_count(feedback_events, "no"),
                "useful_not_sure": _feedback_count(feedback_events, "not_sure"),
                "missed_something_yes": _missed_count(feedback_events, "yes"),
            },
        }

    def record_insight_feedback(
        self,
        *,
        artifact_id: str,
        useful_insight: str,
        surfaced_missed: str | None = None,
        comments: str | None = None,
        actor_type: str = "user",
        actor_id: str | None = None,
    ) -> JsonObject:
        if useful_insight not in {"yes", "no", "not_sure"}:
            raise ValueError("useful_insight must be yes, no, or not_sure")
        if surfaced_missed is not None and surfaced_missed not in {"yes", "no", "not_sure"}:
            raise ValueError("surfaced_missed must be yes, no, or not_sure")
        return append_event(
            self.store,
            event_type="artifact.insight_feedback_recorded",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="artifact",
            target_id=artifact_id,
            payload={
                "artifact_id": artifact_id,
                "useful_insight": useful_insight,
                "surfaced_missed": surfaced_missed,
                "comments": comments,
            },
        )


def _latest_artifact_status(artifacts: list[JsonObject], artifact_type: str) -> str | None:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return str(artifact.get("status") or "unknown")
    return None


def _feedback_count(events: list[JsonObject], value: str) -> int:
    return sum(1 for event in events if _event_payload(event).get("useful_insight") == value)


def _missed_count(events: list[JsonObject], value: str) -> int:
    return sum(1 for event in events if _event_payload(event).get("surfaced_missed") == value)


__all__ = ["VNextDogfoodingService", "VNextDogfoodingStore"]
