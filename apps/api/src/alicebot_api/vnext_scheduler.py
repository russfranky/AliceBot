from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from typing import Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alicebot_api.vnext_agent_control import AgentIdentity, PolicyDecision
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


WORKFLOW_TYPES = (
    "daily_brief",
    "weekly_synthesis",
    "connection_report",
    "contradiction_report",
    "open_loop_review",
    "project_update_scan",
)
PRIMARY_WORKFLOWS = ("daily_brief", "weekly_synthesis")
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class VNextSchedulerValidationError(ValueError):
    """Raised when scheduler configuration or execution input is invalid."""


class VNextSchedulerStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def upsert_scheduler_workflow(self, workflow: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def update_scheduler_workflow(
        self,
        *,
        workflow_type: str,
        patch: JsonObject,
        actor_type: str = "system",
    ) -> JsonObject: ...

    def get_scheduler_workflow(self, workflow_type: str) -> JsonObject | None: ...

    def list_scheduler_workflows(self) -> list[JsonObject]: ...

    def create_scheduler_run(self, run: JsonObject, *, actor_type: str = "scheduler") -> JsonObject: ...

    def update_scheduler_run(self, *, run_id: str, patch: JsonObject, actor_type: str = "scheduler") -> JsonObject: ...

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[JsonObject]: ...

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def search_sources(self, **kwargs) -> list[JsonObject]: ...

    def search_memories(self, **kwargs) -> list[JsonObject]: ...

    def list_open_loops(self, **kwargs) -> list[JsonObject]: ...

    def list_artifacts(self, **kwargs) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class SchedulerRunRequest:
    workflow_type: str
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown")
    generated_for: str | None = None
    triggered_by: str = "user"
    agent_identity: AgentIdentity | None = None
    policy_decision: PolicyDecision | None = None
    options: JsonObject = field(default_factory=dict)


def default_schedule(workflow_type: str) -> JsonObject:
    if workflow_type == "daily_brief":
        return {"kind": "daily", "time_of_day": "08:00", "days_of_week": list(DAY_NAMES)}
    if workflow_type == "weekly_synthesis":
        return {"kind": "weekly", "day_of_week": "monday", "time_of_day": "09:00"}
    return {"kind": "manual"}


def _parse_time_of_day(value: object) -> time:
    if not isinstance(value, str):
        raise VNextSchedulerValidationError("time_of_day must be HH:MM")
    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (TypeError, ValueError) as exc:
        raise VNextSchedulerValidationError("time_of_day must be HH:MM") from exc


def _day_index(value: object) -> int:
    if isinstance(value, int) and 0 <= value <= 6:
        return value
    if isinstance(value, str):
        normalized = value.casefold().strip()
        if normalized in DAY_NAMES:
            return DAY_NAMES.index(normalized)
    raise VNextSchedulerValidationError("day_of_week must be a weekday name or integer 0-6")


def validate_schedule(workflow_type: str, schedule_json: JsonObject) -> JsonObject:
    if workflow_type not in WORKFLOW_TYPES:
        raise VNextSchedulerValidationError(f"workflow_type must be one of {', '.join(WORKFLOW_TYPES)}")
    if not isinstance(schedule_json, dict):
        raise VNextSchedulerValidationError("schedule_json must be an object")

    kind = schedule_json.get("kind") or ("daily" if workflow_type == "daily_brief" else "weekly" if workflow_type == "weekly_synthesis" else "manual")
    if kind == "manual":
        return {"kind": "manual"}
    if workflow_type == "daily_brief":
        when = _parse_time_of_day(schedule_json.get("time_of_day", "08:00"))
        days = schedule_json.get("days_of_week", list(DAY_NAMES))
        if not isinstance(days, list) or not days:
            raise VNextSchedulerValidationError("days_of_week must be a non-empty list")
        day_values = sorted(dict.fromkeys(_day_index(day) for day in days))
        return {
            "kind": "daily",
            "time_of_day": f"{when.hour:02d}:{when.minute:02d}",
            "days_of_week": [DAY_NAMES[index] for index in day_values],
        }
    if workflow_type == "weekly_synthesis":
        when = _parse_time_of_day(schedule_json.get("time_of_day", "09:00"))
        day = DAY_NAMES[_day_index(schedule_json.get("day_of_week", "monday"))]
        return {"kind": "weekly", "day_of_week": day, "time_of_day": f"{when.hour:02d}:{when.minute:02d}"}
    return {"kind": "manual"}


def compute_next_run_at(
    *,
    workflow_type: str,
    enabled: bool,
    paused: bool,
    schedule_json: JsonObject,
    timezone: str,
    now: datetime | None = None,
) -> str | None:
    if not enabled or paused:
        return None
    schedule = validate_schedule(workflow_type, schedule_json)
    if schedule.get("kind") == "manual":
        return None
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise VNextSchedulerValidationError("timezone must be a valid IANA timezone") from exc
    local_now = (now or datetime.now(UTC)).astimezone(zone)
    run_time = _parse_time_of_day(schedule["time_of_day"])
    if schedule["kind"] == "daily":
        allowed_days = {_day_index(day) for day in schedule["days_of_week"]}  # type: ignore[index]
    else:
        allowed_days = {_day_index(schedule["day_of_week"])}
    for offset in range(8):
        candidate_date = (local_now + timedelta(days=offset)).date()
        if candidate_date.weekday() not in allowed_days:
            continue
        candidate = datetime.combine(candidate_date, run_time, tzinfo=zone)
        if candidate > local_now:
            return candidate.astimezone(UTC).isoformat()
    raise VNextSchedulerValidationError("could not compute next scheduler run")


def _coerce_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise VNextSchedulerValidationError("next_run_at must be an ISO datetime") from exc
    else:
        raise VNextSchedulerValidationError("next_run_at must be an ISO datetime")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class VNextSchedulerService:
    def __init__(self, store: VNextSchedulerStore) -> None:
        self.store = store

    def ensure_default_workflows(self) -> list[JsonObject]:
        existing = {str(row["workflow_type"]): row for row in self.store.list_scheduler_workflows()}
        workflows: list[JsonObject] = []
        for workflow_type in WORKFLOW_TYPES:
            if workflow_type in existing:
                workflows.append(existing[workflow_type])
                continue
            workflows.append(
                self.store.upsert_scheduler_workflow(
                    {
                        "workflow_type": workflow_type,
                        "enabled": False,
                        "paused": False,
                        "schedule_json": default_schedule(workflow_type),
                        "timezone": "UTC",
                        "next_run_at": None,
                        "metadata_json": {"created_by": "vnext_scheduler_defaults"},
                    }
                )
            )
        return workflows

    def status(self) -> JsonObject:
        workflows = self.ensure_default_workflows()
        runs = self.store.list_scheduler_runs(limit=20)
        return {
            "mode": "local_governed",
            "disabled_by_default": True,
            "workflows": workflows,
            "recent_runs": runs,
            "enabled_count": sum(1 for row in workflows if row.get("enabled") is True),
            "paused_count": sum(1 for row in workflows if row.get("paused") is True),
            "last_failure": next((run for run in runs if run.get("status") == "failed"), None),
        }

    def configure_workflow(
        self,
        *,
        workflow_type: str,
        enabled: bool | None = None,
        paused: bool | None = None,
        schedule_json: JsonObject | None = None,
        timezone: str | None = None,
        actor_type: str = "user",
    ) -> JsonObject:
        current = self._ensure_workflow(workflow_type)
        next_enabled = bool(current.get("enabled")) if enabled is None else enabled
        next_paused = bool(current.get("paused")) if paused is None else paused
        next_schedule = validate_schedule(workflow_type, schedule_json or current.get("schedule_json") or default_schedule(workflow_type))
        next_timezone = timezone or str(current.get("timezone") or "UTC")
        next_run_at = compute_next_run_at(
            workflow_type=workflow_type,
            enabled=next_enabled,
            paused=next_paused,
            schedule_json=next_schedule,
            timezone=next_timezone,
        )
        row = self.store.update_scheduler_workflow(
            workflow_type=workflow_type,
            patch={
                "enabled": next_enabled,
                "paused": next_paused,
                "schedule_json": next_schedule,
                "timezone": next_timezone,
                "next_run_at": next_run_at,
                "last_error": None,
            },
            actor_type=actor_type,
        )
        event_type = "scheduler.workflow_enabled" if next_enabled else "scheduler.workflow_disabled"
        if paused is True:
            event_type = "scheduler.workflow_paused"
        elif paused is False:
            event_type = "scheduler.workflow_resumed"
        append_event(
            self.store,
            event_type=event_type,
            actor_type=actor_type,
            target_type="scheduler_workflow",
            target_id=str(row["id"]),
            payload={"workflow_type": workflow_type, "enabled": next_enabled, "paused": next_paused},
        )
        return row

    def pause_all(self, *, actor_type: str = "user") -> JsonObject:
        workflows = [self.configure_workflow(workflow_type=workflow_type, paused=True, actor_type=actor_type) for workflow_type in WORKFLOW_TYPES]
        return {"workflows": workflows, "paused_count": len(workflows)}

    def resume_all(self, *, actor_type: str = "user") -> JsonObject:
        workflows = [self.configure_workflow(workflow_type=workflow_type, paused=False, actor_type=actor_type) for workflow_type in WORKFLOW_TYPES]
        return {"workflows": workflows, "resumed_count": len(workflows)}

    def run_due_workflows(
        self,
        *,
        now: datetime | None = None,
        limit: int = 10,
        triggered_by: str = "scheduler",
        agent_identity: AgentIdentity | None = None,
        policy_decision: PolicyDecision | None = None,
    ) -> JsonObject:
        if limit < 1:
            raise VNextSchedulerValidationError("limit must be at least 1")
        checked_at = _coerce_datetime(now or datetime.now(UTC)) or datetime.now(UTC)
        due_runs: list[JsonObject] = []
        for workflow in self.ensure_default_workflows():
            if len(due_runs) >= limit:
                break
            if workflow.get("enabled") is not True or workflow.get("paused") is True:
                continue
            next_run_at = _coerce_datetime(workflow.get("next_run_at"))
            if next_run_at is None or next_run_at > checked_at:
                continue
            workflow_type = str(workflow["workflow_type"])
            result = self.run_now(
                SchedulerRunRequest(
                    workflow_type=workflow_type,
                    generated_for=self._generated_for(workflow, checked_at),
                    triggered_by=triggered_by,
                    agent_identity=agent_identity,
                    policy_decision=policy_decision,
                    options={
                        "scheduled_for": next_run_at.isoformat(),
                        "due_scan_checked_at": checked_at.isoformat(),
                    },
                )
            )
            due_runs.append(
                {
                    "workflow_type": workflow_type,
                    "scheduled_for": next_run_at.isoformat(),
                    "run": result["run"],
                    "artifact": result["artifact"],
                }
            )
        append_event(
            self.store,
            event_type="scheduler.due_scan",
            actor_type=triggered_by,
            payload={"checked_at": checked_at.isoformat(), "due_count": len(due_runs), "limit": limit},
        )
        return {"checked_at": checked_at.isoformat(), "due_count": len(due_runs), "runs": due_runs}

    def run_now(self, request: SchedulerRunRequest) -> JsonObject:
        if request.workflow_type not in WORKFLOW_TYPES:
            raise VNextSchedulerValidationError(f"workflow_type must be one of {', '.join(WORKFLOW_TYPES)}")
        workflow = self._ensure_workflow(request.workflow_type)
        trace_id = str(uuid4())
        actor_type = request.triggered_by
        run = self.store.create_scheduler_run(
            {
                "workflow_id": workflow.get("id"),
                "workflow_type": request.workflow_type,
                "status": "started",
                "triggered_by": request.triggered_by,
                "trace_id": trace_id,
                "policy_decision_json": request.policy_decision.to_record() if request.policy_decision else {},
                "agent_identity_json": request.agent_identity.to_record() if request.agent_identity else {},
                "metadata_json": {"manual_run": request.triggered_by != "scheduler"},
            },
            actor_type=actor_type,
        )
        run_id = str(run["id"])
        try:
            artifact = self._run_workflow(request, scheduler_run_id=run_id, trace_id=trace_id)
            artifact_id = str(artifact["id"])
            updated_run = self.store.update_scheduler_run(
                run_id=run_id,
                patch={"status": "succeeded", "artifact_id": artifact_id, "metadata_json": {"artifact_id": artifact_id}},
                actor_type=actor_type,
            )
            self.store.update_scheduler_workflow(
                workflow_type=request.workflow_type,
                patch={
                    "last_run_id": run_id,
                    "last_run_at": updated_run.get("finished_at"),
                    "last_result": "succeeded",
                    "last_error": None,
                    "next_run_at": self._next_run_after(workflow),
                },
                actor_type=actor_type,
            )
            append_event(
                self.store,
                event_type="scheduler.artifact_created",
                actor_type=actor_type,
                target_type="artifact",
                target_id=artifact_id,
                trace_id=trace_id,
                run_id=run_id,
                payload={"workflow_type": request.workflow_type, "scheduler_run_id": run_id},
            )
            return {"run": updated_run, "artifact": artifact}
        except Exception as exc:
            updated_run = self.store.update_scheduler_run(
                run_id=run_id,
                patch={"status": "failed", "error_message": str(exc), "metadata_json": {"error_type": type(exc).__name__}},
                actor_type=actor_type,
            )
            self.store.update_scheduler_workflow(
                workflow_type=request.workflow_type,
                patch={
                    "last_run_id": run_id,
                    "last_run_at": updated_run.get("finished_at"),
                    "last_result": "failed",
                    "last_error": str(exc),
                    "next_run_at": self._next_run_after(workflow),
                },
                actor_type=actor_type,
            )
            return {"run": updated_run, "artifact": None}

    def _ensure_workflow(self, workflow_type: str) -> JsonObject:
        if workflow_type not in WORKFLOW_TYPES:
            raise VNextSchedulerValidationError(f"workflow_type must be one of {', '.join(WORKFLOW_TYPES)}")
        workflow = self.store.get_scheduler_workflow(workflow_type)
        if workflow is not None:
            return workflow
        return self.store.upsert_scheduler_workflow(
            {
                "workflow_type": workflow_type,
                "enabled": False,
                "paused": False,
                "schedule_json": default_schedule(workflow_type),
                "timezone": "UTC",
                "next_run_at": None,
                "metadata_json": {"created_by": "vnext_scheduler_defaults"},
            }
        )

    def _run_workflow(self, request: SchedulerRunRequest, *, scheduler_run_id: str, trace_id: str) -> JsonObject:
        metadata = {
            "generated_by": "scheduler",
            "workflow": request.workflow_type,
            "scheduler_run_id": scheduler_run_id,
            "trace_id": trace_id,
            "policy_decision": request.policy_decision.to_record() if request.policy_decision else None,
            "agent_identity": request.agent_identity.to_record() if request.agent_identity else None,
        }
        brain_request = BrainArtifactRequest(
            domains=request.domains,
            sensitivity_allowed=request.sensitivity_allowed,
            generated_for=request.generated_for,
            discover_open_loops=False,
            create_candidate_memories=False,
            generated_by="scheduler",
            trace_id=trace_id,
            run_id=scheduler_run_id,
            metadata_json=metadata,
        )
        brain = VNextBrainService(self.store)
        if request.workflow_type == "daily_brief":
            return brain.generate_daily_brief(brain_request)
        if request.workflow_type == "weekly_synthesis":
            return brain.generate_weekly_synthesis(brain_request)
        artifact_type = {
            "connection_report": "connection_report",
            "contradiction_report": "contradiction_report",
            "open_loop_review": "open_loop_report",
            "project_update_scan": "project_update",
        }.get(request.workflow_type, "system_report")
        return self.store.create_artifact(
            {
                "artifact_type": artifact_type,
                "title": f"{request.workflow_type.replace('_', ' ').title()} - {datetime.now(UTC).date().isoformat()}",
                "content_markdown": "\n".join(
                    [
                        f"# {request.workflow_type.replace('_', ' ').title()}",
                        "",
                        "This governed scheduler workflow is configured but has only a deterministic local scaffold in this sprint.",
                    ]
                ),
                "status": "needs_review",
                "domain": request.domains[0] if len(request.domains) == 1 else "unknown",
                "sensitivity": "unknown",
                "generated_by": "scheduler",
                "metadata_json": metadata,
            },
            actor_type="scheduler",
        )

    def _next_run_after(self, workflow: JsonObject) -> str | None:
        workflow_type = str(workflow["workflow_type"])
        return compute_next_run_at(
            workflow_type=workflow_type,
            enabled=bool(workflow.get("enabled")),
            paused=bool(workflow.get("paused")),
            schedule_json=workflow.get("schedule_json") or default_schedule(workflow_type),
            timezone=str(workflow.get("timezone") or "UTC"),
        )

    def _generated_for(self, workflow: JsonObject, checked_at: datetime) -> str:
        try:
            zone = ZoneInfo(str(workflow.get("timezone") or "UTC"))
        except ZoneInfoNotFoundError:
            zone = UTC
        return checked_at.astimezone(zone).date().isoformat()


__all__ = [
    "PRIMARY_WORKFLOWS",
    "SchedulerRunRequest",
    "VNextSchedulerService",
    "VNextSchedulerStore",
    "VNextSchedulerValidationError",
    "WORKFLOW_TYPES",
    "compute_next_run_at",
    "default_schedule",
    "validate_schedule",
]
