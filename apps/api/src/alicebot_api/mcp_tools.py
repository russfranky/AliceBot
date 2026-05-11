from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError,
    capture_continuity_candidates,
    capture_continuity_input,
    commit_continuity_captures,
)
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError,
    compile_continuity_brief,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError,
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopValidationError,
    compile_continuity_open_loop_dashboard,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    RetrievalTraceNotFoundError,
    get_retrieval_trace,
    query_continuity_recall,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_COMMIT_MODES,
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTINUITY_BRIEF_TYPE_ORDER,
    CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_REVIEW_QUEUE_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    ContinuityCaptureCreateInput,
    ContinuityBriefRequestInput,
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
    ContinuityCorrectionInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TaskBriefCompileRequestInput,
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TrustSignalListQueryInput,
)
from alicebot_api.config import get_settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.temporal_state import (
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentIdentityValidationError,
    PolicyDecision,
    agent_metadata,
    append_policy_events,
    evaluate_agent_policy,
)
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService
from alicebot_api.vnext_capture import VNextCaptureService
from alicebot_api.vnext_connections import ConnectionFinderRequest, VNextConnectionService
from alicebot_api.vnext_connectors import VNextConnectorService
from alicebot_api.vnext_contradictions import ContradictionFinderRequest, VNextContradictionService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_projects import ProjectAutomationRequest, VNextProjectService
from alicebot_api.vnext_queue import QueueTaskRequest, VNextQueueService
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService
from alicebot_api.vnext_scheduler import SchedulerRunRequest, VNextSchedulerService
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_store import PostgresVNextStore


_REVIEW_STATUS_CHOICES = (
    "pending_review",
    "correction_ready",
    "active",
    "stale",
    "superseded",
    "deleted",
    "all",
)
_REVIEW_STATUS_ALIASES = {
    "pending": "pending_review",
}
_REVIEW_APPLY_ACTION_CHOICES = (
    "approve",
    "edit-and-approve",
    "reject",
    "supersede-existing",
)
_REVIEW_APPLY_ACTION_ALIASES = {
    "edit_and_approve": "edit-and-approve",
    "supersede_existing": "supersede-existing",
}
_REVIEW_APPLY_TO_CORRECTION_ACTION = {
    "approve": "confirm",
    "edit-and-approve": "edit",
    "reject": "delete",
    "supersede-existing": "supersede",
}
_CONTEXT_PACK_ASSEMBLY_VERSION_V0 = "alice_context_pack_v0"
_PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0 = "alice_prefetch_context_v0"
_MODEL_GENERATION_MODES = ("deterministic", "model_backed")
_MODEL_ROUTE_MODES = ("local_only", "cloud_allowed", "cloud_requires_approval", "model_disabled")
_MODEL_GENERATION_SCHEMA_PROPERTIES: dict[str, object] = {
    "generation_mode": {"type": "string", "enum": list(_MODEL_GENERATION_MODES)},
    "model_route_mode": {"type": "string", "enum": list(_MODEL_ROUTE_MODES)},
    "model_provider": {"type": "string"},
    "model": {"type": "string"},
    "model_temperature": {"type": "number", "minimum": 0.0, "maximum": 2.0},
    "allow_cloud_private": {"type": "boolean"},
}


class MCPToolError(ValueError):
    """Raised when MCP tool input or execution fails."""


class MCPToolNotFoundError(LookupError):
    """Raised when an MCP tool name is not supported."""


@dataclass(frozen=True, slots=True)
class MCPRuntimeContext:
    database_url: str
    user_id: UUID


@contextmanager
def _store_context(context: MCPRuntimeContext):
    with user_connection(context.database_url, context.user_id) as conn:
        yield ContinuityStore(conn)


@contextmanager
def _vnext_store_context(context: MCPRuntimeContext):
    with user_connection(context.database_url, context.user_id) as conn:
        yield PostgresVNextStore(conn)


def _normalize_arguments(arguments: object) -> Mapping[str, object]:
    if arguments is None:
        return {}
    if not isinstance(arguments, Mapping):
        raise MCPToolError("tool arguments must be a JSON object")
    return arguments


def _parse_optional_text(arguments: Mapping[str, object], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be a string")
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        return None
    return normalized


def _parse_required_text(arguments: Mapping[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise MCPToolError(f"{key} is required and must be a string")
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        raise MCPToolError(f"{key} must not be empty")
    return normalized


def _parse_optional_uuid(arguments: Mapping[str, object], key: str) -> UUID | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise MCPToolError(f"{key} must be a valid UUID") from exc


def _parse_required_uuid(arguments: Mapping[str, object], key: str) -> UUID:
    value = _parse_optional_uuid(arguments, key)
    if value is None:
        raise MCPToolError(f"{key} is required and must be a UUID string")
    return value


def _parse_optional_datetime(arguments: Mapping[str, object], key: str) -> datetime | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be an ISO-8601 datetime string")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MCPToolError(f"{key} must be an ISO-8601 datetime string") from exc


def _parse_int(
    arguments: Mapping[str, object],
    *,
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = arguments.get(key, default)
    if isinstance(value, bool):
        raise MCPToolError(f"{key} must be an integer")

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            raise MCPToolError(f"{key} must be an integer")
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise MCPToolError(f"{key} must be an integer") from exc
    else:
        raise MCPToolError(f"{key} must be an integer")

    if parsed < minimum or parsed > maximum:
        raise MCPToolError(f"{key} must be between {minimum} and {maximum}")
    return parsed


def _parse_optional_json_object(arguments: Mapping[str, object], key: str) -> JsonObject | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MCPToolError(f"{key} must be a JSON object")
    return value


def _parse_string_list(arguments: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = arguments.get(key)
    if value is None:
        return ()
    if isinstance(value, str):
        normalized = " ".join(value.split()).strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, list):
        raise MCPToolError(f"{key} must be a string array")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise MCPToolError(f"{key} must be a string array")
        normalized = " ".join(item.split()).strip()
        if normalized:
            output.append(normalized)
    return tuple(output)


def _agent_identity_from_arguments(arguments: Mapping[str, object]) -> AgentIdentity | None:
    try:
        return AgentIdentity.from_payload(arguments)
    except AgentIdentityValidationError as exc:
        raise MCPToolError(str(exc)) from exc


def _policy_checked(
    store: PostgresVNextStore,
    *,
    identity: AgentIdentity | None,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
) -> tuple[str, str | None, object]:
    if identity is not None:
        store.upsert_agent_identity(
            {
                "agent_id": identity.agent_id,
                "agent_type": identity.agent_type,
                "permission_profile": identity.permission_profile,
                "project_scope_json": list(identity.project_scope),
                "metadata_json": {"last_agent_run_id": identity.agent_run_id, "last_task_id": identity.task_id},
            },
            actor_type="agent",
        )
    decision = evaluate_agent_policy(
        identity=identity,
        action=action,
        domains=domains,
        sensitivity_allowed=sensitivity_allowed,
        project_scope=project_scope,
        workflow_type=workflow_type,
        write_policy=write_policy,
    )
    append_policy_events(store, identity=identity, decision=decision)
    return ("agent", identity.agent_id, decision) if identity is not None else ("system", None, decision)


def _raise_mcp_policy_blocked(decision: PolicyDecision) -> None:
    raise MCPToolError(f"agent policy blocked: {', '.join(decision.reasons) or decision.action}")


def _mcp_agent_policy_preflight(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
) -> PolicyDecision:
    identity = _agent_identity_from_arguments(arguments)
    blocked_decision: PolicyDecision | None = None
    decision: PolicyDecision | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action=action,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            project_scope=project_scope,
            workflow_type=workflow_type,
            write_policy=write_policy,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if decision is None:
        raise MCPToolError("agent policy preflight did not complete")
    return decision


def _parse_task_brief_request(arguments: Mapping[str, object], *, mode_key: str = "mode") -> TaskBriefCompileRequestInput:
    mode_value = arguments.get(mode_key)
    if not isinstance(mode_value, str):
        raise MCPToolError(f"{mode_key} is required and must be a string")
    normalized_mode = mode_value.strip()
    if normalized_mode == "":
        raise MCPToolError(f"{mode_key} must not be empty")
    token_budget = arguments.get("token_budget")
    parsed_token_budget: int | None
    if token_budget is None:
        parsed_token_budget = None
    else:
        parsed_token_budget = _parse_int(
            arguments,
            key="token_budget",
            default=DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
            minimum=1,
            maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
        )
    return TaskBriefCompileRequestInput(
        mode=normalized_mode,  # type: ignore[arg-type]
        query=_parse_optional_text(arguments, "query"),
        workspace_id=_parse_optional_uuid(arguments, "workspace_id"),
        pack_id=_parse_optional_text(arguments, "pack_id"),
        pack_version=_parse_optional_text(arguments, "pack_version"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        include_non_promotable_facts=_parse_bool(
            arguments,
            key="include_non_promotable_facts",
            default=False,
        ),
        provider_strategy=_parse_optional_text(arguments, "provider_strategy"),
        model_pack_strategy=_parse_optional_text(arguments, "model_pack_strategy"),
        token_budget=parsed_token_budget,
    )


def _parse_continuity_brief_request(arguments: Mapping[str, object]) -> ContinuityBriefRequestInput:
    brief_type_value = arguments.get("brief_type", "general")
    if not isinstance(brief_type_value, str) or brief_type_value.strip() == "":
        raise MCPToolError("brief_type must be a string")
    brief_type = brief_type_value.strip()
    if brief_type not in CONTINUITY_BRIEF_TYPE_ORDER:
        raise MCPToolError("brief_type must be one of: " + ", ".join(CONTINUITY_BRIEF_TYPE_ORDER))
    return ContinuityBriefRequestInput(
        brief_type=brief_type,  # type: ignore[arg-type]
        query=_parse_optional_text(arguments, "query"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        max_relevant_facts=_parse_int(
            arguments,
            key="max_relevant_facts",
            default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        ),
        max_recent_changes=_parse_int(
            arguments,
            key="max_recent_changes",
            default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ),
        max_open_loops=_parse_int(
            arguments,
            key="max_open_loops",
            default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ),
        max_conflicts=_parse_int(
            arguments,
            key="max_conflicts",
            default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        ),
        max_timeline_highlights=_parse_int(
            arguments,
            key="max_timeline_highlights",
            default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        ),
        include_non_promotable_facts=_parse_bool(
            arguments,
            key="include_non_promotable_facts",
            default=False,
        ),
    )


def _parse_optional_float(arguments: Mapping[str, object], key: str) -> float | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise MCPToolError(f"{key} must be a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:
            raise MCPToolError(f"{key} must be a number") from exc
    raise MCPToolError(f"{key} must be a number")


def _parse_bool(arguments: Mapping[str, object], *, key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise MCPToolError(f"{key} must be a boolean")


def _parse_model_generation_kwargs(arguments: Mapping[str, object]) -> JsonObject:
    generation_mode = _parse_optional_text(arguments, "generation_mode") or "deterministic"
    if generation_mode not in _MODEL_GENERATION_MODES:
        raise MCPToolError("generation_mode must be deterministic or model_backed")
    route_mode = _parse_optional_text(arguments, "model_route_mode")
    if route_mode is not None and route_mode not in _MODEL_ROUTE_MODES:
        raise MCPToolError(
            "model_route_mode must be local_only, cloud_allowed, cloud_requires_approval, or model_disabled"
        )
    temperature = _parse_optional_float(arguments, "model_temperature")
    if temperature is None:
        temperature = 0.2
    if temperature < 0.0 or temperature > 2.0:
        raise MCPToolError("model_temperature must be between 0.0 and 2.0")
    return {
        "generation_mode": generation_mode,
        "model_route_mode": route_mode,
        "model_provider": _parse_optional_text(arguments, "model_provider"),
        "model": _parse_optional_text(arguments, "model"),
        "model_temperature": temperature,
        "allow_cloud_private": _parse_bool(arguments, key="allow_cloud_private", default=False),
    }


def _parse_review_status(
    arguments: Mapping[str, object],
    *,
    default: str,
) -> str:
    raw_status = arguments.get("status", default)
    if not isinstance(raw_status, str):
        raise MCPToolError("status must be a string")
    normalized = raw_status.strip()
    if normalized in _REVIEW_STATUS_ALIASES:
        normalized = _REVIEW_STATUS_ALIASES[normalized]
    if normalized not in _REVIEW_STATUS_CHOICES:
        allowed = ", ".join(_REVIEW_STATUS_CHOICES)
        raise MCPToolError(f"status must be one of: {allowed}")
    if normalized == "pending_review":
        return "stale"
    return normalized


def _parse_review_item_id(arguments: Mapping[str, object], *, required: bool) -> UUID | None:
    review_item_id = _parse_optional_uuid(arguments, "review_item_id")
    continuity_object_id = _parse_optional_uuid(arguments, "continuity_object_id")
    if review_item_id is not None and continuity_object_id is not None and review_item_id != continuity_object_id:
        raise MCPToolError("review_item_id and continuity_object_id must match when both are provided")
    resolved = review_item_id or continuity_object_id
    if required and resolved is None:
        raise MCPToolError("review_item_id or continuity_object_id is required and must be a UUID string")
    return resolved


def _resolve_review_apply_action(raw_action: str, *, allow_legacy: bool) -> str:
    normalized = raw_action.strip()
    if normalized in _REVIEW_APPLY_ACTION_ALIASES:
        normalized = _REVIEW_APPLY_ACTION_ALIASES[normalized]
    mapped = _REVIEW_APPLY_TO_CORRECTION_ACTION.get(normalized)
    if mapped is not None:
        return mapped
    if allow_legacy and normalized in CONTINUITY_CORRECTION_ACTIONS:
        return normalized
    allowed = list(_REVIEW_APPLY_ACTION_CHOICES)
    if allow_legacy:
        allowed.extend(CONTINUITY_CORRECTION_ACTIONS)
    raise MCPToolError(f"action must be one of: {', '.join(allowed)}")


def _build_recall_query(arguments: Mapping[str, object], *, limit: int) -> ContinuityRecallQueryInput:
    return ContinuityRecallQueryInput(
        query=_parse_optional_text(arguments, "query"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        limit=limit,
    )


def _canonicalize_json(value: object) -> object:
    value = json_safe(value)
    if isinstance(value, dict):
        return {
            key: _canonicalize_json(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [_canonicalize_json(item) for item in value]
    return value


def _recency_sort_key(item: Mapping[str, object]) -> tuple[str, str]:
    created_at = str(item.get("created_at", ""))
    item_id = str(item.get("id", ""))
    return created_at, item_id


def _extract_prefetch_single_title(section: object) -> str:
    if not isinstance(section, Mapping):
        return ""
    item = section.get("item")
    if not isinstance(item, Mapping):
        return ""
    title = item.get("title")
    if not isinstance(title, str):
        return ""
    return title.strip()


def _extract_prefetch_titles(section: object, *, limit: int) -> list[str]:
    if not isinstance(section, Mapping):
        return []
    items = section.get("items")
    if not isinstance(items, list):
        return []

    titles: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        title = item.get("title")
        if not isinstance(title, str):
            continue
        normalized = title.strip()
        if normalized == "":
            continue
        titles.append(normalized)
        if len(titles) >= limit:
            break
    return titles


def _render_prefetch_context_text(
    *,
    brief: Mapping[str, object],
    open_loops_limit: int,
    recent_changes_limit: int,
) -> str:
    lines: list[str] = ["## Alice Continuity Prefetch"]

    last_decision = _extract_prefetch_single_title(brief.get("last_decision"))
    if last_decision:
        lines.append(f"- Last decision: {last_decision}")

    next_action = _extract_prefetch_single_title(brief.get("next_action"))
    if next_action:
        lines.append(f"- Next action: {next_action}")

    open_loop_titles = _extract_prefetch_titles(brief.get("open_loops"), limit=open_loops_limit)
    if open_loop_titles:
        lines.append("- Open loops:")
        lines.extend([f"  - {title}" for title in open_loop_titles])

    recent_change_titles = _extract_prefetch_titles(brief.get("recent_changes"), limit=recent_changes_limit)
    if recent_change_titles:
        lines.append("- Recent changes:")
        lines.extend([f"  - {title}" for title in recent_change_titles])

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _handle_alice_capture(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    explicit_signal = arguments.get("explicit_signal")
    if explicit_signal is not None and not isinstance(explicit_signal, str):
        raise MCPToolError("explicit_signal must be a string when provided")

    with _store_context(context) as store:
        return capture_continuity_input(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCreateInput(
                raw_content=_parse_required_text(arguments, "raw_content"),
                explicit_signal=explicit_signal,
            ),
        )


def _handle_alice_capture_candidates(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return capture_continuity_candidates(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCandidatesInput(
                user_content=_parse_optional_text(arguments, "user_content") or "",
                assistant_content=_parse_optional_text(arguments, "assistant_content") or "",
                session_id=_parse_optional_text(arguments, "session_id"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
            ),
        )


def _handle_alice_commit_captures(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_mode = _parse_optional_text(arguments, "mode") or "assist"
    mode = raw_mode.lower()
    if mode not in CONTINUITY_CAPTURE_COMMIT_MODES:
        allowed = ", ".join(CONTINUITY_CAPTURE_COMMIT_MODES)
        raise MCPToolError(f"mode must be one of: {allowed}")

    raw_candidates = arguments.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise MCPToolError("candidates must be a JSON array")
    for item in raw_candidates:
        if not isinstance(item, dict):
            raise MCPToolError("each candidate must be a JSON object")

    with _store_context(context) as store:
        return commit_continuity_captures(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCommitInput(
                mode=mode,  # type: ignore[arg-type]
                candidates=list(raw_candidates),
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
            ),
        )


def _handle_alice_memory_mutations_generate(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_mode = _parse_optional_text(arguments, "mode") or "assist"
    mode = raw_mode.lower()
    if mode not in CONTINUITY_CAPTURE_COMMIT_MODES:
        allowed = ", ".join(CONTINUITY_CAPTURE_COMMIT_MODES)
        raise MCPToolError(f"mode must be one of: {allowed}")

    with _store_context(context) as store:
        return generate_memory_operation_candidates(
            store,
            user_id=context.user_id,
            request=MemoryOperationGenerateInput(
                user_content=_parse_optional_text(arguments, "user_content") or "",
                assistant_content=_parse_optional_text(arguments, "assistant_content") or "",
                mode=mode,  # type: ignore[arg-type]
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
                session_id=_parse_optional_text(arguments, "session_id"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                target_continuity_object_id=_parse_optional_uuid(arguments, "target_continuity_object_id"),
            ),
        )


def _handle_alice_memory_mutations_list_candidates(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)
    with _store_context(context) as store:
        return list_memory_operation_candidates(
            store,
            user_id=context.user_id,
            request=MemoryOperationListInput(
                limit=limit,
                policy_action=_parse_optional_text(arguments, "policy_action"),  # type: ignore[arg-type]
                operation_type=_parse_optional_text(arguments, "operation_type"),  # type: ignore[arg-type]
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
            ),
        )


def _handle_alice_memory_mutations_commit(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_candidate_ids = arguments.get("candidate_ids", [])
    if not isinstance(raw_candidate_ids, list):
        raise MCPToolError("candidate_ids must be a JSON array")
    candidate_ids: list[UUID] = []
    for item in raw_candidate_ids:
        if not isinstance(item, str):
            raise MCPToolError("candidate_ids must contain UUID strings")
        try:
            candidate_ids.append(UUID(item))
        except ValueError as exc:
            raise MCPToolError("candidate_ids must contain UUID strings") from exc

    with _store_context(context) as store:
        return commit_memory_operations(
            store,
            user_id=context.user_id,
            request=MemoryOperationCommitInput(
                candidate_ids=candidate_ids,
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                include_review_required=_parse_bool(arguments, key="include_review_required", default=False),
            ),
        )


def _handle_alice_memory_mutations_list_operations(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)
    with _store_context(context) as store:
        return list_memory_operations(
            store,
            user_id=context.user_id,
            request=MemoryOperationListInput(
                limit=limit,
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
            ),
        )


def _handle_alice_recall(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )

    with _store_context(context) as store:
        return query_continuity_recall(
            store,
            user_id=context.user_id,
            request=_build_recall_query(arguments, limit=limit),
        )


def _handle_alice_recall_debug(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )

    with _store_context(context) as store:
        return query_continuity_recall(
            store,
            user_id=context.user_id,
            request=ContinuityRecallQueryInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
                debug=True,
            ),
        )


def _handle_alice_state_at(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return get_temporal_state_at(
            store,
            user_id=context.user_id,
            request=TemporalStateAtQueryInput(
                entity_id=_parse_required_uuid(arguments, "entity_id"),
                at=_parse_optional_datetime(arguments, "at"),
            ),
        )


def _handle_alice_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
            ),
        )


def _handle_alice_resume_debug(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
                debug=True,
            ),
        )


def _handle_alice_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return compile_continuity_brief(
            store,
            user_id=context.user_id,
            request=_parse_continuity_brief_request(arguments),
        )


def _handle_alice_task_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return compile_and_persist_task_brief(
            store,
            user_id=context.user_id,
            request=_parse_task_brief_request(arguments),
        )


def _handle_alice_task_brief_show(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return get_persisted_task_brief(
            store,
            task_brief_id=_parse_required_uuid(arguments, "task_brief_id"),
        )


def _handle_alice_task_brief_compare(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    compare_to_mode = arguments.get("compare_to_mode")
    if not isinstance(compare_to_mode, str) or compare_to_mode.strip() == "":
        raise MCPToolError("compare_to_mode is required and must be a string")

    primary_request = _parse_task_brief_request(arguments)
    secondary_arguments = dict(arguments)
    secondary_arguments["mode"] = compare_to_mode
    if "compare_model_pack_strategy" in arguments:
        secondary_arguments["model_pack_strategy"] = arguments["compare_model_pack_strategy"]
    if "compare_token_budget" in arguments:
        secondary_arguments["token_budget"] = arguments["compare_token_budget"]

    with _store_context(context) as store:
        return compare_task_briefs(
            store,
            user_id=context.user_id,
            primary_request=primary_request,
            secondary_request=_parse_task_brief_request(secondary_arguments),
        )


def _handle_alice_retrieval_trace(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return get_retrieval_trace(
            store,
            user_id=context.user_id,
            retrieval_run_id=_parse_required_uuid(arguments, "retrieval_run_id"),
        )


def _handle_alice_prefetch_context(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        resumption_payload = compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
            ),
        )

    brief = resumption_payload["brief"]
    return {
        "prefetch_context": {
            "assembly_version": _PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0,
            "text": _render_prefetch_context_text(
                brief=brief,
                open_loops_limit=max_open_loops,
                recent_changes_limit=max_recent_changes,
            ),
            "scope": brief["scope"],
            "last_decision": brief["last_decision"],
            "next_action": brief["next_action"],
            "open_loops": brief["open_loops"],
            "recent_changes": brief["recent_changes"],
            "sources": brief["sources"],
        }
    }


def _handle_alice_open_loops(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_open_loop_dashboard(
            store,
            user_id=context.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
            ),
        )


def _recent_decisions_payload(
    context: MCPRuntimeContext,
    *,
    arguments: Mapping[str, object],
    limit: int,
) -> JsonObject:
    with _store_context(context) as store:
        recall_payload = query_continuity_recall(
            store,
            user_id=context.user_id,
            request=_build_recall_query(arguments, limit=MAX_CONTINUITY_RECALL_LIMIT),
            apply_limit=False,
        )

    all_decisions = [
        item
        for item in recall_payload["items"]
        if item["object_type"] == "Decision"
    ]
    ordered = sorted(all_decisions, key=_recency_sort_key, reverse=True)
    items = ordered[:limit]
    return {
        "items": items,
        "summary": {
            "scope": recall_payload["summary"]["filters"],
            "limit": limit,
            "returned_count": len(items),
            "total_count": len(all_decisions),
            "order": ["created_at_desc", "id_desc"],
        },
    }


def _handle_alice_recent_decisions(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )
    _mcp_agent_policy_preflight(
        context,
        arguments,
        action="recent_decisions.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=_parse_string_list(arguments, "sensitivity_allowed")
        or ("public", "internal", "private", "unknown"),
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    return _recent_decisions_payload(context, arguments=arguments, limit=limit)


def _handle_alice_recent_changes(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    _mcp_agent_policy_preflight(
        context,
        arguments,
        action="recent_changes.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=_parse_string_list(arguments, "sensitivity_allowed")
        or ("public", "internal", "private", "unknown"),
        project_scope=_parse_string_list(arguments, "project_scope"),
    )

    with _store_context(context) as store:
        resumption_payload = compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=0,
            ),
        )

    brief = resumption_payload["brief"]
    return {
        "recent_changes": brief["recent_changes"],
        "scope": brief["scope"],
        "sources": brief["sources"],
        "order": list(CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER),
    }


def _handle_alice_timeline(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_TEMPORAL_TIMELINE_LIMIT,
        minimum=1,
        maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
    )
    with _store_context(context) as store:
        return get_temporal_timeline(
            store,
            user_id=context.user_id,
            request=TemporalTimelineQueryInput(
                entity_id=_parse_required_uuid(arguments, "entity_id"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
            ),
        )


def _review_queue_payload(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    default_status: str,
) -> JsonObject:
    continuity_object_id = _parse_review_item_id(arguments, required=False)
    if continuity_object_id is not None:
        with _store_context(context) as store:
            payload = get_continuity_review_detail(
                store,
                user_id=context.user_id,
                continuity_object_id=continuity_object_id,
            )
        return {
            "mode": "detail",
            "review": payload["review"],
        }

    status = _parse_review_status(arguments, default=default_status)
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )

    with _store_context(context) as store:
        payload = list_continuity_review_queue(
            store,
            user_id=context.user_id,
            request=ContinuityReviewQueueQueryInput(
                status=status,
                limit=limit,
            ),
        )
    return {
        "mode": "queue",
        "items": payload["items"],
        "summary": {
            **payload["summary"],
            "order": list(CONTINUITY_REVIEW_QUEUE_ORDER),
        },
    }


def _handle_alice_review_queue(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_queue_payload(
        context,
        arguments,
        default_status="pending_review",
    )


def _handle_alice_memory_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_queue_payload(
        context,
        arguments,
        default_status="correction_ready",
    )


def _review_apply_payload(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    allow_legacy_actions: bool,
    include_action_resolution: bool,
) -> JsonObject:
    requested_action = _parse_required_text(arguments, "action")
    resolved_action = _resolve_review_apply_action(
        requested_action,
        allow_legacy=allow_legacy_actions,
    )
    continuity_object_id = cast(UUID, _parse_review_item_id(arguments, required=True))

    with _store_context(context) as store:
        payload = apply_continuity_correction(
            store,
            user_id=context.user_id,
            continuity_object_id=continuity_object_id,
            request=ContinuityCorrectionInput(
                action=resolved_action,
                reason=_parse_optional_text(arguments, "reason"),
                title=_parse_optional_text(arguments, "title"),
                body=_parse_optional_json_object(arguments, "body"),
                provenance=_parse_optional_json_object(arguments, "provenance"),
                confidence=_parse_optional_float(arguments, "confidence"),
                replacement_title=_parse_optional_text(arguments, "replacement_title"),
                replacement_body=_parse_optional_json_object(arguments, "replacement_body"),
                replacement_provenance=_parse_optional_json_object(arguments, "replacement_provenance"),
                replacement_confidence=_parse_optional_float(arguments, "replacement_confidence"),
            ),
        )

    if not include_action_resolution:
        return payload
    return {
        "review_action": {
            "requested_action": requested_action,
            "resolved_action": resolved_action,
        },
        **payload,
    }


def _handle_alice_review_apply(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_apply_payload(
        context,
        arguments,
        allow_legacy_actions=True,
        include_action_resolution=True,
    )


def _handle_alice_memory_correct(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_apply_payload(
        context,
        arguments,
        allow_legacy_actions=True,
        include_action_resolution=False,
    )


def _handle_alice_contradictions_detect(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    with _store_context(context) as store:
        return sync_contradictions(
            store,
            user_id=context.user_id,
            request=ContradictionSyncInput(
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
                limit=limit,
            ),
        )


def _handle_alice_contradictions_list(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    contradiction_case_id = _parse_optional_uuid(arguments, "contradiction_case_id")
    if contradiction_case_id is not None:
        with _store_context(context) as store:
            return get_contradiction_case(
                store,
                user_id=context.user_id,
                contradiction_case_id=contradiction_case_id,
            )
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    raw_status = _parse_optional_text(arguments, "status") or "open"
    with _store_context(context) as store:
        return list_contradiction_cases(
            store,
            user_id=context.user_id,
            request=ContradictionCaseListQueryInput(
                status=cast("ContradictionStatus", raw_status),
                limit=limit,
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
            ),
        )


def _handle_alice_contradictions_resolve(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    contradiction_case_id = _parse_required_uuid(arguments, "contradiction_case_id")
    action = _parse_required_text(arguments, "action")
    with _store_context(context) as store:
        return resolve_contradiction_case(
            store,
            user_id=context.user_id,
            contradiction_case_id=contradiction_case_id,
            request=ContradictionResolveInput(
                action=cast("ContradictionResolutionAction", action),
                note=_parse_optional_text(arguments, "note"),
            ),
        )


def _handle_alice_trust_signals(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    with _store_context(context) as store:
        return list_trust_signals(
            store,
            user_id=context.user_id,
            request=TrustSignalListQueryInput(
                limit=limit,
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
                signal_state=cast("TrustSignalState", _parse_optional_text(arguments, "signal_state") or "active"),
                signal_type=cast("TrustSignalType | None", _parse_optional_text(arguments, "signal_type")),
            ),
        )


def _handle_alice_explain(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    continuity_object_id = _parse_optional_uuid(arguments, "continuity_object_id")
    entity_id = _parse_optional_uuid(arguments, "entity_id")
    if continuity_object_id is not None and entity_id is not None:
        raise MCPToolError("alice_explain accepts either continuity_object_id or entity_id, not both")
    if entity_id is not None:
        with _store_context(context) as store:
            return get_temporal_explain(
                store,
                user_id=context.user_id,
                request=TemporalExplainQueryInput(
                    entity_id=entity_id,
                    at=_parse_optional_datetime(arguments, "at"),
                ),
            )
    if continuity_object_id is None:
        raise MCPToolError("alice_explain requires continuity_object_id or entity_id")

    include_raw_content = _parse_bool(arguments, key="include_raw_content", default=False)
    if include_raw_content and get_settings().app_env not in {"development", "test"}:
        raise MCPToolError("include_raw_content is restricted to development/test environments")

    with _store_context(context) as store:
        return build_continuity_explain(
            store,
            user_id=context.user_id,
            continuity_object_id=continuity_object_id,
            include_raw_content=include_raw_content,
        )


def _handle_alice_artifact_inspect(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    include_raw_content = _parse_bool(arguments, key="include_raw_content", default=False)
    if include_raw_content and get_settings().app_env not in {"development", "test"}:
        raise MCPToolError("include_raw_content is restricted to development/test environments")

    with _store_context(context) as store:
        return get_continuity_artifact_detail(
            store,
            user_id=context.user_id,
            artifact_id=_parse_required_uuid(arguments, "artifact_id"),
            include_raw_content=include_raw_content,
        )


def _handle_alice_context_pack(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    open_loops_limit = _parse_int(
        arguments,
        key="open_loops_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
    recent_changes_limit = _parse_int(
        arguments,
        key="recent_changes_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    recent_decisions_limit = _parse_int(
        arguments,
        key="recent_decisions_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )

    with _store_context(context) as store:
        resumption_payload = compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=recent_changes_limit,
                max_open_loops=open_loops_limit,
            ),
        )

    brief = resumption_payload["brief"]
    recent_decisions = _recent_decisions_payload(
        context,
        arguments=arguments,
        limit=recent_decisions_limit,
    )
    return {
        "context_pack": {
            "assembly_version": _CONTEXT_PACK_ASSEMBLY_VERSION_V0,
            "scope": brief["scope"],
            "last_decision": brief["last_decision"],
            "next_action": brief["next_action"],
            "open_loops": brief["open_loops"],
            "recent_changes": brief["recent_changes"],
            "recent_decisions": recent_decisions,
            "sources": [
                "continuity_capture_events",
                "continuity_objects",
                "continuity_correction_events",
            ],
        }
    }


def _handle_alice_vnext_context_pack(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_items = _parse_int(
        arguments,
        key="max_items",
        default=8,
        minimum=1,
        maximum=50,
    )
    max_tokens = _parse_int(
        arguments,
        key="max_tokens",
        default=8000,
        minimum=500,
        maximum=50_000,
    )
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    identity = _agent_identity_from_arguments(arguments)

    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="context_pack.request",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextRetrievalService(store).compile_context_pack(
                VNextRetrievalRequest(
                    query=_parse_required_text(arguments, "query"),
                    domains=decision.effective_domains,
                    projects=_parse_string_list(arguments, "projects"),
                    people=_parse_string_list(arguments, "people"),
                    time_window=_parse_optional_text(arguments, "time_window") or "all",
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    include_sources=_parse_bool(arguments, key="include_sources", default=True),
                    include_contradictions=_parse_bool(arguments, key="include_contradictions", default=True),
                    max_items=max_items,
                    max_tokens=max_tokens,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext context-pack request did not complete")
    return payload


def _brain_artifact_request_from_arguments(arguments: Mapping[str, object]) -> BrainArtifactRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return BrainArtifactRequest(
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        generated_for=_parse_optional_text(arguments, "generated_for"),
        source_limit=_parse_int(arguments, key="source_limit", default=8, minimum=1, maximum=50),
        memory_limit=_parse_int(arguments, key="memory_limit", default=8, minimum=1, maximum=50),
        open_loop_limit=_parse_int(arguments, key="open_loop_limit", default=8, minimum=1, maximum=50),
        artifact_limit=_parse_int(arguments, key="artifact_limit", default=4, minimum=1, maximum=50),
        discover_open_loops=_parse_bool(arguments, key="discover_open_loops", default=True),
        create_candidate_memories=_parse_bool(arguments, key="create_candidate_memories", default=True),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_daily_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextBrainService(store).generate_daily_brief(_brain_artifact_request_from_arguments(arguments))


def _handle_alice_generate_weekly_synthesis(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextBrainService(store).generate_weekly_synthesis(_brain_artifact_request_from_arguments(arguments))


def _connection_request_from_arguments(arguments: Mapping[str, object]) -> ConnectionFinderRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    auto_accept_threshold = _parse_optional_float(arguments, "auto_accept_threshold")
    return ConnectionFinderRequest(
        query=_parse_optional_text(arguments, "query") or "",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        max_connections=_parse_int(arguments, key="max_connections", default=8, minimum=1, maximum=50),
        auto_accept_threshold=auto_accept_threshold,
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_connections(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _connection_request_from_arguments(arguments)
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="artifact.generate",
        domains=request.domains,
        sensitivity_allowed=request.sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
    )
    request = ConnectionFinderRequest(
        query=request.query,
        domains=decision.effective_domains,
        sensitivity_allowed=decision.effective_sensitivity_allowed,
        max_connections=request.max_connections,
        auto_accept_threshold=request.auto_accept_threshold,
        generation_mode=request.generation_mode,
        model_route_mode=request.model_route_mode,
        model_provider=request.model_provider,
        model=request.model,
        model_temperature=request.model_temperature,
        allow_cloud_private=request.allow_cloud_private,
    )
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).generate_connection_report(request)


def _handle_alice_graph_edge_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).review_edge(
            edge_id=_parse_required_text(arguments, "edge_id"),
            action=_parse_required_text(arguments, "action"),
        )


def _handle_alice_graph_neighborhood(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).graph_neighborhood(
            target_id=_parse_required_text(arguments, "target_id"),
        )


def _contradiction_request_from_arguments(arguments: Mapping[str, object]) -> ContradictionFinderRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return ContradictionFinderRequest(
        query=_parse_optional_text(arguments, "query") or "",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        max_contradictions=_parse_int(arguments, key="max_contradictions", default=8, minimum=1, maximum=50),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_contradictions(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _contradiction_request_from_arguments(arguments)
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="artifact.generate",
        domains=request.domains,
        sensitivity_allowed=request.sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
    )
    request = ContradictionFinderRequest(
        query=request.query,
        domains=decision.effective_domains,
        sensitivity_allowed=decision.effective_sensitivity_allowed,
        max_contradictions=request.max_contradictions,
        generation_mode=request.generation_mode,
        model_route_mode=request.model_route_mode,
        model_provider=request.model_provider,
        model=request.model,
        model_temperature=request.model_temperature,
        allow_cloud_private=request.allow_cloud_private,
    )
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).generate_contradiction_report(request)


def _handle_alice_belief_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).review_belief(
            belief_id=_parse_required_text(arguments, "belief_id"),
            action=_parse_required_text(arguments, "action"),
            confidence=_parse_optional_float(arguments, "confidence"),
            superseded_by=_parse_optional_text(arguments, "superseded_by"),
        )


def _handle_alice_belief_state(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).belief_state(
            belief_id=_parse_required_text(arguments, "belief_id"),
        )


def _project_request_from_arguments(arguments: Mapping[str, object]) -> ProjectAutomationRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return ProjectAutomationRequest(
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        project_id=_parse_optional_text(arguments, "project_id"),
        person_id=_parse_optional_text(arguments, "person_id"),
        max_items=_parse_int(arguments, key="max_items", default=8, minimum=1, maximum=50),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_project_update_candidate(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _project_request_from_arguments(arguments)
    identity = _agent_identity_from_arguments(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="artifact.generate",
            domains=request.domains,
            sensitivity_allowed=request.sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
            workflow_type="project_update_scan",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextProjectService(store).generate_project_update_candidate(
                ProjectAutomationRequest(
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    project_id=request.project_id,
                    person_id=request.person_id,
                    max_items=request.max_items,
                    generated_by=actor_type,
                    actor_id=actor_id,
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    metadata_json=agent_metadata(identity, decision),
                    generation_mode=request.generation_mode,
                    model_route_mode=request.model_route_mode,
                    model_provider=request.model_provider,
                    model=request.model,
                    model_temperature=request.model_temperature,
                    allow_cloud_private=request.allow_cloud_private,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext project update candidate generation did not complete")
    return payload


def _handle_alice_project_update_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).review_project_update(
            artifact_id=_parse_required_text(arguments, "artifact_id"),
            action=_parse_required_text(arguments, "action"),
            edited_current_state=_parse_optional_text(arguments, "edited_current_state"),
        )


def _handle_alice_project_dashboard(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="project.dashboard",
        sensitivity_allowed=sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).project_dashboard(
            project_id=_parse_required_text(arguments, "project_id"),
            sensitivity_allowed=decision.effective_sensitivity_allowed,
        )


def _handle_alice_open_loop_extract(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        loops = VNextProjectService(store).extract_open_loops(_project_request_from_arguments(arguments))
    return {"open_loops": loops, "created_count": len(loops)}


def _handle_alice_open_loop_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).review_open_loop(
            loop_id=_parse_required_text(arguments, "loop_id"),
            action=_parse_required_text(arguments, "action"),
            title=_parse_optional_text(arguments, "title"),
            description=_parse_optional_text(arguments, "description"),
            due_at=_parse_optional_text(arguments, "due_at"),
            priority=_parse_optional_text(arguments, "priority"),
            resolution_note=_parse_optional_text(arguments, "resolution_note"),
        )


def _handle_alice_vnext_capture(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="source.capture",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextCaptureService(
                store,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
            ).capture_text(
                _parse_required_text(arguments, "raw_text"),
                title=_parse_optional_text(arguments, "title"),
                domain=domain,
                sensitivity=sensitivity,
            ).to_record()
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext source capture did not complete")
    return payload


def _handle_alice_vnext_ingest_agent_output(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    if identity is None:
        raise MCPToolError("agent_id is required for alice_vnext_ingest_agent_output")
    domain = _parse_optional_text(arguments, "domain") or "project"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "private"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="source.capture",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
            write_policy="proposal_only" if _parse_bool(arguments, key="propose_memory", default=False) else None,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextConnectorService(store).ingest_agent_output(
                {
                    "agent_id": identity.agent_id,
                    "agent_type": identity.agent_type,
                    "agent_run_id": identity.agent_run_id,
                    "task_id": identity.task_id,
                    "project_scope": list(identity.project_scope or _parse_string_list(arguments, "project_scope")),
                    "title": _parse_required_text(arguments, "title"),
                    "content": _parse_required_text(arguments, "content"),
                    "output_type": _parse_optional_text(arguments, "output_type") or "general",
                    "domain": domain,
                    "sensitivity": sensitivity,
                    "source_refs": list(_parse_string_list(arguments, "source_refs")),
                    "rationale": _parse_optional_text(arguments, "rationale"),
                    "propose_memory": _parse_bool(arguments, key="propose_memory", default=False),
                },
                policy_decision=decision.to_record(),
            ).to_record()
            append_policy_events(store, identity=identity, decision=decision, target_type="connector", target_id="agent_output")
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("agent output ingestion did not complete")
    return payload


def _handle_alice_vnext_queue_task(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    write_policy = _parse_optional_text(arguments, "write_policy") or "proposal_only"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="queue_task.create",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
            write_policy=write_policy,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextQueueService(store).enqueue_task(
                QueueTaskRequest(
                    title=_parse_required_text(arguments, "title"),
                    task_type=_parse_required_text(arguments, "task_type"),
                    instructions=_parse_required_text(arguments, "instructions"),
                    requested_by=identity.agent_id if identity is not None else "mcp",
                    domain=domain,
                    sensitivity=sensitivity,
                    write_policy=write_policy,
                    scope_json={"project_scope": list(_parse_string_list(arguments, "project_scope"))},
                    actor_type=actor_type,
                    actor_id=actor_id,
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext queue task did not complete")
    return payload


def _handle_alice_vnext_generate_artifact(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    workflow_type = _parse_optional_text(arguments, "workflow_type") or "daily_brief"
    if workflow_type in {"connection_report", "connections"}:
        return _handle_alice_generate_connections(context, arguments)
    if workflow_type in {"contradiction_report", "contradictions"}:
        return _handle_alice_generate_contradictions(context, arguments)
    if workflow_type in {"open_loop_review", "project_update_scan"}:
        scheduler_arguments = dict(arguments)
        scheduler_arguments["workflow_type"] = workflow_type
        return _handle_alice_vnext_scheduler_run_now(context, scheduler_arguments)
    if workflow_type not in {"daily_brief", "weekly_synthesis"}:
        raise MCPToolError(
            "workflow_type must be daily_brief, weekly_synthesis, connection_report, "
            "contradiction_report, open_loop_review, or project_update_scan"
        )
    identity = _agent_identity_from_arguments(arguments)
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    generation_kwargs = _parse_model_generation_kwargs(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="artifact.generate",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            request = BrainArtifactRequest(
                domains=decision.effective_domains,
                sensitivity_allowed=decision.effective_sensitivity_allowed,
                generated_for=_parse_optional_text(arguments, "generated_for"),
                source_limit=_parse_int(arguments, key="source_limit", default=8, minimum=1, maximum=50),
                memory_limit=_parse_int(arguments, key="memory_limit", default=8, minimum=1, maximum=50),
                open_loop_limit=_parse_int(arguments, key="open_loop_limit", default=8, minimum=1, maximum=50),
                artifact_limit=_parse_int(arguments, key="artifact_limit", default=4, minimum=1, maximum=50),
                discover_open_loops=_parse_bool(arguments, key="discover_open_loops", default=True),
                create_candidate_memories=_parse_bool(arguments, key="create_candidate_memories", default=True),
                generated_by=actor_type,
                actor_id=actor_id,
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
                metadata_json=agent_metadata(identity, decision),
                **generation_kwargs,
            )
            service = VNextBrainService(store)
            payload = (
                service.generate_weekly_synthesis(request)
                if workflow_type == "weekly_synthesis"
                else service.generate_daily_brief(request)
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext artifact generation did not complete")
    return payload


def _handle_alice_vnext_open_loops(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    status = _parse_optional_text(arguments, "status") or "open"
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="open_loop.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    with _vnext_store_context(context) as store:
        loops = store.list_open_loops(
            status=status if status != "all" else None,
            domains=list(decision.effective_domains) or None,
            sensitivity_allowed=list(decision.effective_sensitivity_allowed),
            limit=_parse_int(arguments, key="limit", default=20, minimum=1, maximum=100),
        )
    return {"items": loops, "count": len(loops)}


def _handle_alice_vnext_propose_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    if identity is None:
        raise MCPToolError("agent_id is required for alice_vnext_propose_memory")
    proposal_type = _parse_optional_text(arguments, "proposal_type") or "candidate_memory"
    canonical_text = _parse_required_text(arguments, "canonical_text")
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    blocked_decision: PolicyDecision | None = None
    memory: JsonObject | None = None
    decision: PolicyDecision | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="memory.propose",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            proposal_id = _parse_optional_text(arguments, "proposal_id") or str(uuid4())
            memory = store.create_memory(
                {
                    "memory_type": {
                        "decision": "decision",
                        "project_update": "project_state",
                        "belief_update": "belief",
                        "contradiction": "contradiction",
                        "artifact_summary": "artifact_summary",
                        "open_loop": "open_loop",
                    }.get(proposal_type, "semantic"),
                    "memory_key": f"agent_proposal.{proposal_type}.{proposal_id}",
                    "value": {"proposal_type": proposal_type, "text": canonical_text},
                    "status": "candidate",
                    "confidence": _parse_optional_float(arguments, "confidence") or 0.5,
                    "title": _parse_optional_text(arguments, "title") or canonical_text[:120],
                    "canonical_text": canonical_text,
                    "summary": canonical_text[:280],
                    "domain": domain,
                    "sensitivity": sensitivity,
                    "metadata_json": {
                        "proposal_type": proposal_type,
                        "review_required": True,
                        **agent_metadata(identity, decision),
                    },
                },
                actor_type="agent",
            )
            append_event(
                store,
                event_type="agent.memory_proposed",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"proposal_type": proposal_type, "agent_identity": identity.to_record()},
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if memory is None or decision is None:
        raise MCPToolError("vNext memory proposal did not complete")
    return {"proposal": memory, "policy_decision": decision.to_record(), "review_required": True}


def _handle_alice_vnext_review_items(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        items = [
            row
            for row in store.list_memories(status=None)
            if str(row.get("status")) in {"candidate", "needs_review", "private_only"}
        ][:_parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)]
    return {"items": items, "count": len(items)}


def _handle_alice_vnext_artifact_get(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    artifact_id = _parse_required_text(arguments, "artifact_id")
    with _vnext_store_context(context) as store:
        artifact = store.get_artifact(artifact_id)
    if artifact is None:
        raise MCPToolError(f"artifact {artifact_id} was not found")
    return artifact


def _handle_alice_vnext_artifact_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    artifact_id = _parse_required_text(arguments, "artifact_id")
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="artifact.review")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextQueueService(store).review_artifact(
                artifact_id=artifact_id,
                action=_parse_required_text(arguments, "action"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext artifact review did not complete")
    return payload


def _handle_alice_vnext_scheduler_status(context: MCPRuntimeContext, _arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextSchedulerService(store).status()


def _handle_alice_vnext_scheduler_run_now(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    workflow_type = _parse_required_text(arguments, "workflow_type")
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    generation_kwargs = _parse_model_generation_kwargs(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="scheduler.run_now",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
            workflow_type=workflow_type,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_now(
                SchedulerRunRequest(
                    workflow_type=workflow_type,
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    generated_for=_parse_optional_text(arguments, "generated_for"),
                    triggered_by="agent" if identity is not None else "user",
                    agent_identity=identity,
                    policy_decision=decision,
                    options=generation_kwargs,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler run-now did not complete")
    return payload


def _handle_alice_vnext_scheduler_run_due(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    limit_value = arguments.get("limit", 10)
    if not isinstance(limit_value, int):
        raise MCPToolError("limit must be an integer")
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.run_due")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_due_workflows(
                limit=limit_value,
                triggered_by=actor_type if identity is not None else "scheduler",
                agent_identity=identity,
                policy_decision=decision,
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler run-due did not complete")
    return payload


def _handle_alice_vnext_scheduler_pause(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.pause")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).pause_all(actor_type=actor_type)
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler pause did not complete")
    return payload


def _handle_alice_vnext_scheduler_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.resume")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).resume_all(actor_type=actor_type)
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler resume did not complete")
    return payload


_VNEXT_AGENT_SCHEMA_PROPERTIES: dict[str, object] = {
    "agent_id": {"type": "string"},
    "agent_type": {"type": "string"},
    "agent_run_id": {"type": "string"},
    "task_id": {"type": "string"},
    "project_scope": {"type": "array", "items": {"type": "string"}},
    "permission_profile": {"type": "string"},
    "trace_id": {"type": "string"},
    "domains": {"type": "array", "items": {"type": "string"}},
    "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
}


def _vnext_agent_tool_schema(
    properties: dict[str, object] | None = None,
    *,
    required: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required or [],
        "properties": {**_VNEXT_AGENT_SCHEMA_PROPERTIES, **(properties or {})},
    }


_TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "alice_capture",
        "description": "Capture continuity input into deterministic continuity objects.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["raw_content"],
            "properties": {
                "raw_content": {"type": "string"},
                "explicit_signal": {"type": "string", "enum": list(CONTINUITY_CAPTURE_EXPLICIT_SIGNALS)},
            },
        },
    },
    {
        "name": "alice_capture_candidates",
        "description": "Extract continuity candidates from one user/assistant turn without writing memory.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "user_content": {"type": "string"},
                "assistant_content": {"type": "string"},
                "session_id": {"type": "string"},
                "source_kind": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_commit_captures",
        "description": "Commit extracted continuity candidates using manual/assist/auto bridge policy.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "mode": {"type": "string", "enum": list(CONTINUITY_CAPTURE_COMMIT_MODES)},
                "sync_fingerprint": {"type": "string"},
                "source_kind": {"type": "string"},
                "candidates": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        },
    },
    {
        "name": "alice_memory_mutations_generate",
        "description": "Generate explicit memory mutation candidates with ADD/UPDATE/SUPERSEDE/DELETE/NOOP classification.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "user_content": {"type": "string"},
                "assistant_content": {"type": "string"},
                "mode": {"type": "string", "enum": list(CONTINUITY_CAPTURE_COMMIT_MODES)},
                "sync_fingerprint": {"type": "string"},
                "source_kind": {"type": "string"},
                "session_id": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "target_continuity_object_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_list_candidates",
        "description": "Inspect generated explicit memory mutation candidates.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "policy_action": {"type": "string", "enum": ["auto_apply", "review_required", "skip"]},
                "operation_type": {"type": "string", "enum": ["ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"]},
                "sync_fingerprint": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_commit",
        "description": "Apply explicit memory mutation candidates with idempotent audit records.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "candidate_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "sync_fingerprint": {"type": "string"},
                "include_review_required": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_list_operations",
        "description": "Inspect committed explicit memory operations and their result links.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "sync_fingerprint": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_recall",
        "description": "Recall continuity objects with deterministic ranking and provenance fields.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_RECALL_LIMIT},
            },
        },
    },
    {
        "name": "alice_recall_debug",
        "description": "Run hybrid continuity retrieval with per-candidate stage scores and exclusion reasons.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_RECALL_LIMIT},
            },
        },
    },
    {
        "name": "alice_state_at",
        "description": "Show entity facts and edges that were effective at a specific point in time.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["entity_id"],
            "properties": {
                "entity_id": {"type": "string", "format": "uuid"},
                "at": {"type": "string", "format": "date-time"},
            },
        },
    },
    {
        "name": "alice_resume",
        "description": "Compile continuity resumption brief for decisions, open loops, and next action.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_resume_debug",
        "description": "Compile a resumption brief with the underlying hybrid retrieval trace attached.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_brief",
        "description": "Compile the primary one-call continuity brief for general, resume, handoff, coding, or operator contexts.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "brief_type": {
                    "type": "string",
                    "enum": CONTINUITY_BRIEF_TYPE_ORDER,
                },
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_relevant_facts": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
                },
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "max_conflicts": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
                },
                "max_timeline_highlights": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_task_brief",
        "description": "Compile and persist one task-adaptive brief for recall, resume, worker, or handoff workloads.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "query": {"type": "string"},
                "workspace_id": {"type": "string", "format": "uuid"},
                "pack_id": {"type": "string"},
                "pack_version": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "include_non_promotable_facts": {"type": "boolean"},
                "provider_strategy": {"type": "string"},
                "model_pack_strategy": {"type": "string"},
                "token_budget": {"type": "integer", "minimum": 1, "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET},
            },
        },
    },
    {
        "name": "alice_task_brief_show",
        "description": "Load one persisted task-adaptive brief by id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["task_brief_id"],
            "properties": {
                "task_brief_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_task_brief_compare",
        "description": "Compare two task-brief modes for the same scope and show which one is smaller.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["mode", "compare_to_mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "compare_to_mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "query": {"type": "string"},
                "workspace_id": {"type": "string", "format": "uuid"},
                "pack_id": {"type": "string"},
                "pack_version": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "include_non_promotable_facts": {"type": "boolean"},
                "provider_strategy": {"type": "string"},
                "model_pack_strategy": {"type": "string"},
                "compare_model_pack_strategy": {"type": "string"},
                "token_budget": {"type": "integer", "minimum": 1, "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET},
                "compare_token_budget": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET,
                },
            },
        },
    },
    {
        "name": "alice_retrieval_trace",
        "description": "Load one persisted retrieval trace by run id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["retrieval_run_id"],
            "properties": {
                "retrieval_run_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_prefetch_context",
        "description": "Assemble deterministic pre-turn prefetch context text from continuity resumption state.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_open_loops",
        "description": "List continuity open loops grouped by deterministic posture sections.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 0, "maximum": MAX_CONTINUITY_OPEN_LOOP_LIMIT},
            },
        },
    },
    {
        "name": "alice_recent_decisions",
        "description": "List most recent continuity decisions in deterministic recency order.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_RECALL_LIMIT},
            },
        },
    },
    {
        "name": "alice_recent_changes",
        "description": "List recent continuity changes from the shipped resumption assembly logic.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
            },
        },
    },
    {
        "name": "alice_timeline",
        "description": "List chronological temporal history for one entity.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["entity_id"],
            "properties": {
                "entity_id": {"type": "string", "format": "uuid"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TEMPORAL_TIMELINE_LIMIT},
            },
        },
    },
    {
        "name": "alice_review_queue",
        "description": "List pending review queue items or fetch one review item detail with explanation metadata.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": list(_REVIEW_STATUS_CHOICES)},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_review_apply",
        "description": "Apply approve/reject/edit-and-approve/supersede-existing review actions deterministically.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(_REVIEW_APPLY_ACTION_CHOICES)},
                "reason": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "object"},
                "provenance": {"type": "object"},
                "confidence": {"type": "number"},
                "replacement_title": {"type": "string"},
                "replacement_body": {"type": "object"},
                "replacement_provenance": {"type": "object"},
                "replacement_confidence": {"type": "number"},
            },
        },
    },
    {
        "name": "alice_contradictions_detect",
        "description": "Run contradiction detection and persist current contradiction and trust state.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_contradictions_list",
        "description": "List contradiction cases or fetch one contradiction case detail.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "contradiction_case_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": ["open", "resolved", "dismissed"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_contradictions_resolve",
        "description": "Resolve one contradiction case with an explicit audit action.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["contradiction_case_id", "action"],
            "properties": {
                "contradiction_case_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(CONTRADICTION_RESOLUTION_ACTIONS)},
                "note": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_trust_signals",
        "description": "Inspect current stored trust signals for continuity objects.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "signal_state": {"type": "string", "enum": ["active", "inactive"]},
                "signal_type": {
                    "type": "string",
                    "enum": ["correction", "corroboration", "contradiction", "weak_inference"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_memory_review",
        "description": "Legacy alias for review queue/detail (use alice_review_queue).",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": list(_REVIEW_STATUS_CHOICES)},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_memory_correct",
        "description": "Legacy alias for review apply (use alice_review_apply).",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["continuity_object_id", "action"],
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(CONTINUITY_CORRECTION_ACTIONS)},
                "reason": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "object"},
                "provenance": {"type": "object"},
                "confidence": {"type": "number"},
                "replacement_title": {"type": "string"},
                "replacement_body": {"type": "object"},
                "replacement_provenance": {"type": "object"},
                "replacement_confidence": {"type": "number"},
            },
        },
    },
    {
        "name": "alice_explain",
        "description": "Show continuity evidence for one continuity object or temporal explain output for one entity.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "entity_id": {"type": "string", "format": "uuid"},
                "at": {"type": "string", "format": "date-time"},
                "include_raw_content": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_artifact_inspect",
        "description": "Inspect one archived artifact with copies and extracted segments.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["artifact_id"],
            "properties": {
                "artifact_id": {"type": "string", "format": "uuid"},
                "include_raw_content": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_context_pack",
        "description": "Assemble a deterministic continuity context pack for scoped external-agent use.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "recent_decisions_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_CONTINUITY_RECALL_LIMIT,
                },
                "recent_changes_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "open_loops_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
            },
        },
    },
    {
        "name": "alice_vnext_context_pack",
        "description": "Compile a vNext provenance-aware context pack with retrieval trace metadata.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "projects": {"type": "array", "items": {"type": "string"}},
                "people": {"type": "array", "items": {"type": "string"}},
                "time_window": {"type": "string"},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "include_sources": {"type": "boolean"},
                "include_contradictions": {"type": "boolean"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                "max_tokens": {"type": "integer", "minimum": 500, "maximum": 50000},
            },
        },
    },
    {
        "name": "alice_generate_daily_brief",
        "description": "Generate a vNext daily brief artifact with provenance and review status.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "generated_for": {"type": "string", "format": "date"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "open_loop_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "discover_open_loops": {"type": "boolean"},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_generate_weekly_synthesis",
        "description": "Generate a vNext weekly synthesis artifact and candidate insight memories.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "generated_for": {"type": "string", "format": "date"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "open_loop_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "discover_open_loops": {"type": "boolean"},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_generate_connections",
        "description": "Generate a vNext connection report and candidate graph edges.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_connections": {"type": "integer", "minimum": 1, "maximum": 50},
                "auto_accept_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_graph_edge_review",
        "description": "Review, accept, or reject a vNext candidate graph edge.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["edge_id", "action"],
            "properties": {
                "edge_id": {"type": "string"},
                "action": {"type": "string", "enum": ["review", "accept", "reject"]},
            },
        },
    },
    {
        "name": "alice_graph_neighborhood",
        "description": "Return active vNext graph edges around a target id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["target_id"],
            "properties": {
                "target_id": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_generate_contradictions",
        "description": "Generate a vNext contradiction report and candidate contradiction graph edges.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_contradictions": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_belief_review",
        "description": "Reinforce, challenge, supersede, or retire a vNext belief.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["belief_id", "action"],
            "properties": {
                "belief_id": {"type": "string"},
                "action": {"type": "string", "enum": ["reinforce", "challenge", "supersede", "retire"]},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "superseded_by": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_belief_state",
        "description": "Return current and historical state for a vNext belief.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["belief_id"],
            "properties": {
                "belief_id": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_project_update_candidate",
        "description": "Generate a vNext project update candidate artifact.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_id": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_project_update_review",
        "description": "Accept, edit, or reject a vNext project update candidate artifact.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["artifact_id", "action"],
            "properties": {
                "artifact_id": {"type": "string"},
                "action": {"type": "string", "enum": ["accept", "edit", "reject"]},
                "edited_current_state": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_project_dashboard",
        "description": "Return vNext project dashboard state, memories, open loops, and artifacts.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["project_id"],
            "properties": {
                "project_id": {"type": "string"},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "alice_open_loop_extract",
        "description": "Extract vNext candidate open loops from selected sources.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_id": {"type": "string"},
                "person_id": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        },
    },
    {
        "name": "alice_open_loop_review",
        "description": "Close, snooze, edit, or reopen a vNext open loop.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["loop_id", "action"],
            "properties": {
                "loop_id": {"type": "string"},
                "action": {"type": "string", "enum": ["close", "snooze", "edit", "reopen"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_at": {"type": "string"},
                "priority": {"type": "string"},
                "resolution_note": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_vnext_capture",
        "description": "Capture a vNext source with optional agent identity and policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "raw_text": {"type": "string"},
                "title": {"type": "string"},
                "source_type": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
            },
            required=["raw_text"],
        ),
    },
    {
        "name": "alice_vnext_ingest_agent_output",
        "description": "Capture Hermes/OpenClaw agent output as source/artifact evidence with optional review-only memory proposal.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "output_type": {
                    "type": "string",
                    "enum": ["sprint_summary", "research_summary", "code_review", "project_update", "decision", "general"],
                },
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
                "propose_memory": {"type": "boolean"},
            },
            required=["agent_id", "title", "content"],
        ),
    },
    {
        "name": "alice_vnext_queue_task",
        "description": "Create a vNext queue task with optional agent identity and policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "task_type": {"type": "string"},
                "instructions": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "scheduled_for": {"type": "string"},
            },
            required=["title", "task_type", "instructions"],
        ),
    },
    {
        "name": "alice_vnext_generate_artifact",
        "description": "Generate a vNext artifact workflow such as daily_brief or weekly_synthesis.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "artifact_type": {"type": "string"},
                "workflow_type": {"type": "string"},
                "generated_for": {"type": "string"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        ),
    },
    {
        "name": "alice_vnext_project_dashboard",
        "description": "Return vNext project dashboard state.",
        "inputSchema": _vnext_agent_tool_schema({"project_id": {"type": "string"}}, required=["project_id"]),
    },
    {
        "name": "alice_vnext_open_loops",
        "description": "List vNext open loops with domain and sensitivity filters.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "project_id": {"type": "string"},
                "source_id": {"type": "string"},
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "due_at": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        ),
    },
    {
        "name": "alice_vnext_recent_decisions",
        "description": "Return recent decision context through the existing continuity lookup.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_recent_changes",
        "description": "Return recent change context through the existing continuity lookup.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_find_connections",
        "description": "Generate a vNext connection report.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "max_connections": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            }
        ),
    },
    {
        "name": "alice_vnext_find_contradictions",
        "description": "Generate a vNext contradiction report.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "max_contradictions": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            }
        ),
    },
    {
        "name": "alice_vnext_propose_memory",
        "description": "Submit an agent memory proposal for human review.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "proposal_type": {"type": "string"},
                "title": {"type": "string"},
                "canonical_text": {"type": "string"},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
            },
            required=["agent_id", "canonical_text"],
        ),
    },
    {
        "name": "alice_vnext_review_items",
        "description": "List pending vNext memory review items.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "status": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        ),
    },
    {
        "name": "alice_vnext_artifact_get",
        "description": "Get one vNext generated artifact.",
        "inputSchema": _vnext_agent_tool_schema({"artifact_id": {"type": "string"}}, required=["artifact_id"]),
    },
    {
        "name": "alice_vnext_artifact_review",
        "description": "Review a vNext artifact; agent callers are policy checked.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "artifact_id": {"type": "string"},
                "action": {"type": "string"},
                "reason": {"type": "string"},
            },
            required=["artifact_id", "action"],
        ),
    },
    {
        "name": "alice_vnext_scheduler_status",
        "description": "Return governed local scheduler status.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
    {
        "name": "alice_vnext_scheduler_run_now",
        "description": "Run a governed scheduler workflow now with policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "workflow_type": {"type": "string"},
                "generated_for": {"type": "string"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
            required=["workflow_type"],
        ),
    },
    {
        "name": "alice_vnext_scheduler_run_due",
        "description": "Run enabled governed scheduler workflows whose next_run_at is due.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_scheduler_pause",
        "description": "Pause all governed scheduler workflows.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
    {
        "name": "alice_vnext_scheduler_resume",
        "description": "Resume all governed scheduler workflows.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
]

_TOOL_HANDLERS = {
    "alice_capture": _handle_alice_capture,
    "alice_capture_candidates": _handle_alice_capture_candidates,
    "alice_commit_captures": _handle_alice_commit_captures,
    "alice_memory_mutations_generate": _handle_alice_memory_mutations_generate,
    "alice_memory_mutations_list_candidates": _handle_alice_memory_mutations_list_candidates,
    "alice_memory_mutations_commit": _handle_alice_memory_mutations_commit,
    "alice_memory_mutations_list_operations": _handle_alice_memory_mutations_list_operations,
    "alice_recall": _handle_alice_recall,
    "alice_recall_debug": _handle_alice_recall_debug,
    "alice_state_at": _handle_alice_state_at,
    "alice_resume": _handle_alice_resume,
    "alice_resume_debug": _handle_alice_resume_debug,
    "alice_brief": _handle_alice_brief,
    "alice_task_brief": _handle_alice_task_brief,
    "alice_task_brief_show": _handle_alice_task_brief_show,
    "alice_task_brief_compare": _handle_alice_task_brief_compare,
    "alice_retrieval_trace": _handle_alice_retrieval_trace,
    "alice_prefetch_context": _handle_alice_prefetch_context,
    "alice_open_loops": _handle_alice_open_loops,
    "alice_recent_decisions": _handle_alice_recent_decisions,
    "alice_recent_changes": _handle_alice_recent_changes,
    "alice_timeline": _handle_alice_timeline,
    "alice_review_queue": _handle_alice_review_queue,
    "alice_review_apply": _handle_alice_review_apply,
    "alice_contradictions_detect": _handle_alice_contradictions_detect,
    "alice_contradictions_list": _handle_alice_contradictions_list,
    "alice_contradictions_resolve": _handle_alice_contradictions_resolve,
    "alice_trust_signals": _handle_alice_trust_signals,
    "alice_memory_review": _handle_alice_memory_review,
    "alice_memory_correct": _handle_alice_memory_correct,
    "alice_explain": _handle_alice_explain,
    "alice_artifact_inspect": _handle_alice_artifact_inspect,
    "alice_context_pack": _handle_alice_context_pack,
    "alice_vnext_context_pack": _handle_alice_vnext_context_pack,
    "alice_generate_daily_brief": _handle_alice_generate_daily_brief,
    "alice_generate_weekly_synthesis": _handle_alice_generate_weekly_synthesis,
    "alice_generate_connections": _handle_alice_generate_connections,
    "alice_graph_edge_review": _handle_alice_graph_edge_review,
    "alice_graph_neighborhood": _handle_alice_graph_neighborhood,
    "alice_generate_contradictions": _handle_alice_generate_contradictions,
    "alice_belief_review": _handle_alice_belief_review,
    "alice_belief_state": _handle_alice_belief_state,
    "alice_project_update_candidate": _handle_alice_project_update_candidate,
    "alice_project_update_review": _handle_alice_project_update_review,
    "alice_project_dashboard": _handle_alice_project_dashboard,
    "alice_open_loop_extract": _handle_alice_open_loop_extract,
    "alice_open_loop_review": _handle_alice_open_loop_review,
    "alice_vnext_capture": _handle_alice_vnext_capture,
    "alice_vnext_ingest_agent_output": _handle_alice_vnext_ingest_agent_output,
    "alice_vnext_queue_task": _handle_alice_vnext_queue_task,
    "alice_vnext_generate_artifact": _handle_alice_vnext_generate_artifact,
    "alice_vnext_project_dashboard": _handle_alice_project_dashboard,
    "alice_vnext_open_loops": _handle_alice_vnext_open_loops,
    "alice_vnext_recent_decisions": _handle_alice_recent_decisions,
    "alice_vnext_recent_changes": _handle_alice_recent_changes,
    "alice_vnext_find_connections": _handle_alice_generate_connections,
    "alice_vnext_find_contradictions": _handle_alice_generate_contradictions,
    "alice_vnext_propose_memory": _handle_alice_vnext_propose_memory,
    "alice_vnext_review_items": _handle_alice_vnext_review_items,
    "alice_vnext_artifact_get": _handle_alice_vnext_artifact_get,
    "alice_vnext_artifact_review": _handle_alice_vnext_artifact_review,
    "alice_vnext_scheduler_status": _handle_alice_vnext_scheduler_status,
    "alice_vnext_scheduler_run_now": _handle_alice_vnext_scheduler_run_now,
    "alice_vnext_scheduler_run_due": _handle_alice_vnext_scheduler_run_due,
    "alice_vnext_scheduler_pause": _handle_alice_vnext_scheduler_pause,
    "alice_vnext_scheduler_resume": _handle_alice_vnext_scheduler_resume,
}


def list_mcp_tools() -> list[dict[str, object]]:
    return _canonicalize_json(_TOOL_DEFINITIONS)  # type: ignore[return-value]


def call_mcp_tool(
    context: MCPRuntimeContext,
    *,
    name: str,
    arguments: object,
) -> JsonObject:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise MCPToolNotFoundError(f"unknown tool '{name}'")

    parsed_arguments = _normalize_arguments(arguments)
    try:
        payload = handler(context, parsed_arguments)
    except (
        ContinuityCaptureValidationError,
        ContinuityRecallValidationError,
        ContinuityBriefValidationError,
        ContinuityResumptionValidationError,
        ContinuityOpenLoopValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityContradictionValidationError,
        ContinuityContradictionNotFoundError,
        RetrievalTraceNotFoundError,
        ContinuityEvidenceNotFoundError,
        MemoryMutationValidationError,
        TaskBriefNotFoundError,
        TaskBriefValidationError,
        TemporalStateValidationError,
    ) as exc:
        raise MCPToolError(str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise MCPToolError(str(exc)) from exc

    return _canonicalize_json(payload)  # type: ignore[return-value]


__all__ = [
    "MCPRuntimeContext",
    "MCPToolError",
    "MCPToolNotFoundError",
    "call_mcp_tool",
    "list_mcp_tools",
]
