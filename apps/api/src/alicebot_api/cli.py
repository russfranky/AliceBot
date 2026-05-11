from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import UUID, uuid4

import psycopg

from alicebot_api.cli_formatting import (
    format_artifact_detail_output,
    format_capture_output,
    format_continuity_brief_output,
    format_contradiction_case_detail_output,
    format_contradiction_case_list_output,
    format_contradiction_sync_output,
    format_explain_output,
    format_lifecycle_detail_output,
    format_lifecycle_list_output,
    format_memory_operation_candidates_output,
    format_memory_operation_commit_output,
    format_memory_operations_output,
    format_open_loops_output,
    format_recall_output,
    format_resume_output,
    format_review_apply_output,
    format_review_detail_output,
    format_review_queue_output,
    format_status_output,
    format_task_brief_comparison_output,
    format_task_brief_output,
    format_temporal_explain_output,
    format_temporal_state_output,
    format_temporal_timeline_output,
    format_trust_signals_output,
    format_trusted_fact_pattern_explain_output,
    format_trusted_fact_pattern_list_output,
    format_trusted_fact_playbook_explain_output,
    format_trusted_fact_playbook_list_output,
)
from alicebot_api.config import Settings, get_settings
from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError,
    capture_continuity_input,
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
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.continuity_objects import (
    default_continuity_promotable,
    default_continuity_searchable,
)
from alicebot_api.continuity_lifecycle import (
    ContinuityLifecycleNotFoundError,
    ContinuityLifecycleValidationError,
    get_continuity_lifecycle_state,
    list_continuity_lifecycle_state,
)
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopValidationError,
    compile_continuity_open_loop_dashboard,
)
from alicebot_api.conversation_health import get_thread_health_dashboard
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
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
from alicebot_api.memory import get_memory_hygiene_dashboard_summary
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_BRIEF_TYPE_ORDER,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
    ContinuityCaptureCreateInput,
    ContinuityBriefRequestInput,
    ContinuityCorrectionInput,
    ContinuityLifecycleQueryInput,
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
    TrustedFactPatternListQueryInput,
    TrustedFactPlaybookListQueryInput,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.db import ping_database, user_connection
from alicebot_api.public_evals import (
    get_public_eval_run,
    list_public_eval_runs,
    list_public_eval_suites,
    run_public_evals,
    write_public_eval_report,
)
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.temporal_state import (
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.trusted_fact_promotions import (
    TrustedFactPromotionNotFoundError,
    get_trusted_fact_pattern,
    get_trusted_fact_playbook,
    list_trusted_fact_patterns,
    list_trusted_fact_playbooks,
)
from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    agent_metadata,
    append_policy_events,
    ensure_policy_allowed,
    evaluate_agent_policy,
    summarize_agent_policy_telemetry,
)
from alicebot_api.vnext_capture import VNextCaptureService, VNextCaptureValidationError
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService, VNextBrainValidationError
from alicebot_api.vnext_connections import (
    ConnectionFinderRequest,
    VNextConnectionService,
    VNextConnectionValidationError,
)
from alicebot_api.vnext_connectors import (
    VNextConnectorService,
    VNextConnectorValidationError,
    list_connector_definitions,
    load_connector_items_from_file,
)
from alicebot_api.vnext_contradictions import (
    ContradictionFinderRequest,
    VNextContradictionService,
    VNextContradictionValidationError,
)
from alicebot_api.vnext_evals import (
    run_vnext_evals,
    write_vnext_benchmark_corpus,
    write_vnext_eval_report,
)
from alicebot_api.vnext_projects import ProjectAutomationRequest, VNextProjectService, VNextProjectValidationError
from alicebot_api.vnext_queue import QueueTaskRequest, VNextQueueService, VNextQueueValidationError
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService, VNextRetrievalValidationError
from alicebot_api.vnext_scheduler import SchedulerRunRequest, VNextSchedulerService, VNextSchedulerValidationError, WORKFLOW_TYPES, default_schedule
from alicebot_api.vnext_scheduler_runtime import (
    DEFAULT_LOG_FILE,
    DEFAULT_PID_FILE,
    DEFAULT_STATUS_FILE,
    SchedulerRuntimeConfig,
    daemon_status,
    run_foreground_daemon,
    start_background_daemon,
    stop_daemon,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_store import PostgresVNextStore

DEFAULT_CLI_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_VNEXT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
MAINTENANCE_REPORT_PATH_ENV = "ALICEBOT_MAINTENANCE_REPORT_PATH"
DEFAULT_MAINTENANCE_REPORT_PATH = (
    Path(__file__).resolve().parents[4] / "artifacts" / "ops" / "maintenance_status_latest.json"
)
REVIEW_STATUS_CHOICES = ("correction_ready", "active", "stale", "superseded", "deleted", "all")


@dataclass(frozen=True, slots=True)
class CLIContext:
    settings: Settings
    database_url: str
    user_id: UUID


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID value: {value}") from exc


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid datetime value '{value}'. Use ISO-8601 format."
        ) from exc


def _parse_optional_json_object(raw_value: str | None, *, option_name: str) -> JsonObject | None:
    if raw_value is None:
        return None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{option_name} must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{option_name} must be a JSON object")
    return payload


def _add_scope_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", default=None, help="Optional query text.")
    parser.add_argument("--thread-id", type=_parse_uuid, default=None, help="Optional thread UUID scope.")
    parser.add_argument("--task-id", type=_parse_uuid, default=None, help="Optional task UUID scope.")
    parser.add_argument("--project", default=None, help="Optional project scope.")
    parser.add_argument("--person", default=None, help="Optional person scope.")
    parser.add_argument("--since", type=_parse_datetime, default=None, help="Optional start time (ISO-8601).")
    parser.add_argument("--until", type=_parse_datetime, default=None, help="Optional end time (ISO-8601).")


def _add_vnext_agent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent-id", default=None, help="Agent id for agent-originated vNext actions.")
    parser.add_argument("--agent-type", default="unknown", help="Agent type.")
    parser.add_argument("--agent-run-id", default=None, help="Agent run id.")
    parser.add_argument("--agent-task-id", default=None, help="Agent task id.")
    parser.add_argument("--project-scope", action="append", default=[], help="Allowed project scope. Repeatable.")
    parser.add_argument("--permission-profile", default="read_only_agent", help="Agent permission profile.")


def _add_task_brief_arguments(parser: argparse.ArgumentParser) -> None:
    _add_scope_filter_arguments(parser)
    parser.add_argument(
        "--workspace-id",
        type=_parse_uuid,
        default=None,
        help="Optional workspace UUID used to resolve model-pack briefing defaults.",
    )
    parser.add_argument(
        "--pack-id",
        default=None,
        help="Optional model-pack id to resolve within the workspace.",
    )
    parser.add_argument(
        "--pack-version",
        default=None,
        help="Optional model-pack version to resolve within the workspace.",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("user_recall", "resume", "worker_subtask", "agent_handoff"),
        help="Task brief mode.",
    )
    parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts where the mode allows it.",
    )
    parser.add_argument(
        "--provider-strategy",
        default=None,
        help="Optional provider briefing strategy label.",
    )
    parser.add_argument(
        "--model-pack-strategy",
        default=None,
        help="Optional model-pack briefing strategy override.",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help=f"Optional explicit token budget (1-{MAX_TASK_BRIEF_TOKEN_BUDGET}).",
    )


def _add_continuity_brief_arguments(parser: argparse.ArgumentParser) -> None:
    _add_scope_filter_arguments(parser)
    parser.add_argument(
        "--brief-type",
        choices=CONTINUITY_BRIEF_TYPE_ORDER,
        default="general",
        help="One-call continuity brief type.",
    )
    parser.add_argument(
        "--max-relevant-facts",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        help=f"Maximum relevant facts ({0}-{MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT}).",
    )
    parser.add_argument(
        "--max-recent-changes",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        help=f"Maximum recent changes ({0}-{MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}).",
    )
    parser.add_argument(
        "--max-open-loops",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        help=f"Maximum open loops ({0}-{MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}).",
    )
    parser.add_argument(
        "--max-conflicts",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        help=f"Maximum open conflicts ({0}-{MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT}).",
    )
    parser.add_argument(
        "--max-timeline-highlights",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        help=f"Maximum timeline highlights ({0}-{MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT}).",
    )
    parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts where the brief type allows it.",
    )


def _resolve_user_id(settings: Settings, user_id_flag: str | None) -> UUID:
    if user_id_flag is not None:
        return _parse_uuid(user_id_flag)
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)
    return UUID(os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_CLI_USER_ID))


def _build_context(args: argparse.Namespace) -> CLIContext:
    settings = get_settings()
    database_url = args.database_url if args.database_url is not None else settings.database_url
    user_id = _resolve_user_id(settings, args.user_id)
    return CLIContext(settings=settings, database_url=database_url, user_id=user_id)


@contextmanager
def _store_context(ctx: CLIContext) -> Iterator[ContinuityStore]:
    with user_connection(ctx.database_url, ctx.user_id) as conn:
        yield ContinuityStore(conn)


@contextmanager
def _vnext_store_context(ctx: CLIContext) -> Iterator[PostgresVNextStore]:
    with user_connection(ctx.database_url, ctx.user_id) as conn:
        yield PostgresVNextStore(conn)


def _parse_maintenance_status_payload(payload: object) -> dict[str, object]:
    default_snapshot: dict[str, object] = {
        "maintenance_status": "unknown",
        "maintenance_schedule": "unknown",
        "maintenance_last_run_at": "unknown",
        "maintenance_failure_count": 0,
        "maintenance_warning_count": 0,
        "maintenance_stale_fact_count": 0,
        "maintenance_reembedded_segment_count": 0,
        "maintenance_pattern_candidate_count": 0,
        "maintenance_benchmark_status": "unknown",
    }

    if not isinstance(payload, dict):
        return default_snapshot

    summary = payload.get("summary")
    if isinstance(summary, dict):
        status = summary.get("status")
        if isinstance(status, str):
            default_snapshot["maintenance_status"] = status
        schedule = summary.get("schedule")
        if isinstance(schedule, str):
            default_snapshot["maintenance_schedule"] = schedule
        completed_at = summary.get("run_completed_at")
        if isinstance(completed_at, str):
            default_snapshot["maintenance_last_run_at"] = completed_at
        failure_count = summary.get("failure_count")
        if isinstance(failure_count, int):
            default_snapshot["maintenance_failure_count"] = failure_count
        warning_count = summary.get("warning_count")
        if isinstance(warning_count, int):
            default_snapshot["maintenance_warning_count"] = warning_count

    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return default_snapshot

    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_key = job.get("job_key")
        details = job.get("details")
        if not isinstance(job_key, str) or not isinstance(details, dict):
            continue
        if job_key == "stale_fact_marking":
            stale_fact_count = details.get("stale_fact_count")
            if isinstance(stale_fact_count, int):
                default_snapshot["maintenance_stale_fact_count"] = stale_fact_count
        elif job_key == "reembed_missing_segments":
            reembedded_segment_count = details.get("reembedded_segment_count")
            if isinstance(reembedded_segment_count, int):
                default_snapshot["maintenance_reembedded_segment_count"] = reembedded_segment_count
        elif job_key == "pattern_candidate_recompute":
            pattern_candidate_count = details.get("pattern_candidate_count")
            if isinstance(pattern_candidate_count, int):
                default_snapshot["maintenance_pattern_candidate_count"] = pattern_candidate_count
        elif job_key == "benchmark_regeneration":
            benchmark_status = details.get("benchmark_status")
            if isinstance(benchmark_status, str):
                default_snapshot["maintenance_benchmark_status"] = benchmark_status

    return default_snapshot


def _load_maintenance_status_snapshot() -> dict[str, object]:
    raw_path = os.getenv(MAINTENANCE_REPORT_PATH_ENV)
    if raw_path is None or raw_path.strip() == "":
        report_path = DEFAULT_MAINTENANCE_REPORT_PATH
    else:
        candidate = Path(raw_path.strip()).expanduser()
        report_path = candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()

    if not report_path.exists():
        return _parse_maintenance_status_payload({})

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _parse_maintenance_status_payload({})

    return _parse_maintenance_status_payload(payload)


def _run_capture(ctx: CLIContext, args: argparse.Namespace) -> str:
    raw_content = " ".join(args.raw_content).strip()
    with _store_context(ctx) as store:
        payload = capture_continuity_input(
            store,
            user_id=ctx.user_id,
            request=ContinuityCaptureCreateInput(
                raw_content=raw_content,
                explicit_signal=args.explicit_signal,
            ),
        )
    return format_capture_output(payload)


def _json_dumps(value: object) -> str:
    return json.dumps(json_safe(value), indent=2, sort_keys=True)


def _vnext_sensitivity_allowed(args: argparse.Namespace) -> tuple[str, ...]:
    values = getattr(args, "sensitivity_allowed", None)
    return tuple(values) if values else DEFAULT_VNEXT_SENSITIVITY_ALLOWED


def _vnext_agent_identity_from_args(args: argparse.Namespace) -> AgentIdentity | None:
    agent_id = getattr(args, "agent_id", None)
    if not agent_id:
        return None
    return AgentIdentity(
        agent_id=agent_id,
        agent_type=getattr(args, "agent_type", None) or "unknown",
        agent_run_id=getattr(args, "agent_run_id", None),
        task_id=getattr(args, "agent_task_id", None),
        project_scope=tuple(getattr(args, "project_scope", None) or ()),
        permission_profile=getattr(args, "permission_profile", None) or "read_only_agent",
    )


def _vnext_policy_checked_for_args(
    store: PostgresVNextStore,
    args: argparse.Namespace,
    *,
    action: str,
    domains: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
) -> tuple[AgentIdentity | None, str, str | None, object]:
    identity = _vnext_agent_identity_from_args(args)
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
        sensitivity_allowed=_vnext_sensitivity_allowed(args),
        project_scope=tuple(getattr(args, "project_scope", None) or ()),
        workflow_type=workflow_type,
        write_policy=write_policy,
    )
    append_policy_events(store, identity=identity, decision=decision)
    return identity, ("agent" if identity is not None else "user"), identity.agent_id if identity is not None else None, decision


def _run_vnext_sources_capture_text(ctx: CLIContext, args: argparse.Namespace) -> str:
    raw_text = " ".join(args.raw_text).strip()
    with _vnext_store_context(ctx) as store:
        result = VNextCaptureService(store).capture_text(
            raw_text,
            title=args.title,
            domain=args.domain,
            sensitivity=args.sensitivity,
        )
    return _json_dumps(result.to_record())


def _run_vnext_sources_capture_file(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        result = VNextCaptureService(store).capture_file(
            args.path,
            domain=args.domain,
            sensitivity=args.sensitivity,
        )
    return _json_dumps(result.to_record())


def _run_vnext_sources_import_markdown(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        result = VNextCaptureService(store).import_markdown_folder(
            args.folder,
            domain=args.domain,
            sensitivity=args.sensitivity,
        )
    return _json_dumps(result.to_record())


def _run_vnext_sources_import_chatgpt(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        result = VNextCaptureService(store).import_chatgpt_export_file(
            args.path,
            domain=args.domain,
            sensitivity=args.sensitivity,
        )
    return _json_dumps(result.to_record())


def _run_vnext_connectors_list(_ctx: CLIContext, _args: argparse.Namespace) -> str:
    payload = {
        "items": [definition.to_record() for definition in list_connector_definitions()],
        "count": len(list_connector_definitions()),
        "order": [definition.name for definition in list_connector_definitions()],
    }
    return _json_dumps(payload)


def _run_vnext_connectors_ingest(ctx: CLIContext, args: argparse.Namespace) -> str:
    items = load_connector_items_from_file(args.payload_path)
    with _vnext_store_context(ctx) as store:
        result = VNextConnectorService(store).sync_items(
            args.connector_name,
            items,
            default_domain=args.domain,
            default_sensitivity=args.sensitivity,
        )
    return _json_dumps(result.to_record())


def _run_context_pack(ctx: CLIContext, args: argparse.Namespace) -> str:
    query = " ".join(args.query).strip()
    with _vnext_store_context(ctx) as store:
        payload = VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query=query,
                domains=tuple(args.domain),
                projects=tuple(args.project),
                people=tuple(args.person),
                sensitivity_allowed=_vnext_sensitivity_allowed(args),
                include_sources=not args.no_sources,
                include_contradictions=not args.no_contradictions,
                max_items=args.max_items,
                max_tokens=args.max_tokens,
            )
        )
    return _json_dumps(payload)


def _brain_artifact_request_from_args(args: argparse.Namespace) -> BrainArtifactRequest:
    return BrainArtifactRequest(
        domains=tuple(args.domain),
        sensitivity_allowed=_vnext_sensitivity_allowed(args),
        generated_for=args.generated_for,
        source_limit=args.source_limit,
        memory_limit=args.memory_limit,
        open_loop_limit=args.open_loop_limit,
        artifact_limit=args.artifact_limit,
        discover_open_loops=not args.no_discover_open_loops,
        create_candidate_memories=not args.no_candidate_memories,
    )


def _run_daily_brief(ctx: CLIContext, args: argparse.Namespace) -> str:
    del args.generate
    with _vnext_store_context(ctx) as store:
        artifact = VNextBrainService(store).generate_daily_brief(_brain_artifact_request_from_args(args))
    return _json_dumps(artifact)


def _run_weekly_synthesis(ctx: CLIContext, args: argparse.Namespace) -> str:
    del args.generate
    with _vnext_store_context(ctx) as store:
        artifact = VNextBrainService(store).generate_weekly_synthesis(_brain_artifact_request_from_args(args))
    return _json_dumps(artifact)


def _run_vnext_agent_propose_memory(ctx: CLIContext, args: argparse.Namespace) -> str:
    if not getattr(args, "agent_id", None):
        raise ValueError("--agent-id is required")
    blocked_decision = None
    memory: JsonObject | None = None
    decision = None
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.propose",
            domains=(args.domain,),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            if identity is None:
                raise ValueError("--agent-id is required")
            memory = store.create_memory(
                {
                    "memory_type": args.memory_type,
                    "memory_key": f"agent_proposal.{args.proposal_type}.{uuid4()}",
                    "value": {"proposal_type": args.proposal_type, "text": args.canonical_text, "rationale": args.rationale},
                    "status": "candidate",
                    "confidence": args.confidence,
                    "title": args.title,
                    "canonical_text": args.canonical_text,
                    "summary": args.canonical_text[:280],
                    "domain": args.domain,
                    "sensitivity": args.sensitivity,
                    "metadata_json": {
                        "proposal_type": args.proposal_type,
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
                trace_id=decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"proposal_type": args.proposal_type, "agent_identity": identity.to_record()},
            )
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if memory is None or decision is None:
        raise RuntimeError("agent memory proposal did not complete")
    return _json_dumps({"proposal": memory, "policy_decision": decision.to_record(), "review_required": True})


def _run_vnext_agent_policy_telemetry(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        events = store.list_agent_events(agent_id=args.agent_id, limit=args.limit)
        artifacts = store.list_artifacts(limit=args.limit)
        memories = store.list_memories(status=None)
    return _json_dumps(
        {
            "summary": summarize_agent_policy_telemetry(
                agent_events=events,
                artifacts=artifacts,
                memories=memories,
            )
        }
    )


def _run_vnext_scheduler_status(ctx: CLIContext, _args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        payload = VNextSchedulerService(store).status()
    return _json_dumps(payload)


def _run_vnext_scheduler_runs(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        runs = store.list_scheduler_runs(workflow_type=args.workflow_type, limit=args.limit)
    return _json_dumps({"items": runs, "count": len(runs)})


def _run_vnext_scheduler_failures(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        runs = [
            run
            for run in store.list_scheduler_runs(workflow_type=args.workflow_type, limit=max(args.limit * 4, args.limit))
            if run.get("status") == "failed"
        ][: args.limit]
    return _json_dumps({"items": runs, "count": len(runs)})


def _run_vnext_scheduler_run_now(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.run_now",
            domains=tuple(args.domain),
            workflow_type=args.workflow_type,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_now(
                SchedulerRunRequest(
                    workflow_type=args.workflow_type,
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    generated_for=args.generated_for,
                    triggered_by=actor_type,
                    agent_identity=identity,
                    policy_decision=decision,
                )
            )
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler run-now did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})


def _run_vnext_scheduler_run_due(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.run_due",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_due_workflows(
                limit=args.limit,
                triggered_by=actor_type if identity is not None else "scheduler",
                agent_identity=identity,
                policy_decision=decision,
            )
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler run-due did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})


def _scheduler_runtime_config(ctx: CLIContext, args: argparse.Namespace) -> SchedulerRuntimeConfig:
    return SchedulerRuntimeConfig(
        database_url=ctx.database_url,
        user_id=ctx.user_id,
        interval_seconds=args.interval_seconds,
        limit=args.limit,
        pid_file=Path(args.pid_file),
        status_file=Path(args.status_file),
        log_file=Path(args.log_file),
        once=getattr(args, "once", False),
    )


def _run_vnext_scheduler_daemon_start(ctx: CLIContext, args: argparse.Namespace) -> str:
    config = _scheduler_runtime_config(ctx, args)
    if args.foreground:
        return _json_dumps(run_foreground_daemon(config))
    return _json_dumps(start_background_daemon(config))


def _run_vnext_scheduler_daemon_status(_ctx: CLIContext, args: argparse.Namespace) -> str:
    return _json_dumps(daemon_status(pid_file=Path(args.pid_file), status_file=Path(args.status_file)))


def _run_vnext_scheduler_daemon_stop(_ctx: CLIContext, args: argparse.Namespace) -> str:
    return _json_dumps(stop_daemon(pid_file=Path(args.pid_file), status_file=Path(args.status_file)))


def _run_vnext_scheduler_pause(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        _identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.pause",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).pause_all(actor_type=actor_type)
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler pause did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})


def _run_vnext_scheduler_resume(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        _identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.resume",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).resume_all(actor_type=actor_type)
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler resume did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})


def _run_vnext_smoke_agentic_scheduler(ctx: CLIContext, _args: argparse.Namespace) -> str:
    smoke_run_id = f"cli-agentic-scheduler-smoke-{uuid4()}"
    with _vnext_store_context(ctx) as store:
        service = VNextSchedulerService(store)
        initial_status = service.status()
        daily_workflow = service.configure_workflow(
            workflow_type="daily_brief",
            enabled=True,
            paused=False,
            schedule_json={"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
            timezone="UTC",
            actor_type="user",
        )
        weekly_workflow = service.configure_workflow(
            workflow_type="weekly_synthesis",
            enabled=True,
            paused=False,
            schedule_json={"kind": "weekly", "day_of_week": "monday", "time_of_day": "09:00"},
            timezone="UTC",
            actor_type="user",
        )
        identity = AgentIdentity(
            agent_id="hermes",
            agent_type="personal_assistant",
            agent_run_id=smoke_run_id,
            project_scope=("Alice",),
            permission_profile="trusted_local_agent",
        )
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
        proposal_decision = evaluate_agent_policy(
            identity=identity,
            action="memory.propose",
            domains=("project",),
            sensitivity_allowed=("private",),
            project_scope=identity.project_scope,
        )
        append_policy_events(store, identity=identity, decision=proposal_decision)
        ensure_policy_allowed(proposal_decision)
        proposal = store.create_memory(
            {
                "memory_type": "semantic",
                "memory_key": f"agent_proposal.smoke.{uuid4()}",
                "value": {
                    "proposal_type": "candidate_memory",
                    "text": "Agentic scheduler smoke validates proposal-only memory writes.",
                },
                "status": "candidate",
                "confidence": 0.5,
                "title": "Agentic scheduler smoke proposal",
                "canonical_text": "Agentic scheduler smoke validates proposal-only memory writes.",
                "summary": "Agentic scheduler smoke validates proposal-only memory writes.",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "proposal_type": "candidate_memory",
                    "review_required": True,
                    **agent_metadata(identity, proposal_decision),
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
            target_id=str(proposal["id"]),
            trace_id=proposal_decision.trace_id,
            run_id=identity.agent_run_id,
            payload={"proposal_type": "candidate_memory", "agent_identity": identity.to_record()},
        )
        daily_decision = evaluate_agent_policy(
            identity=identity,
            action="scheduler.run_now",
            domains=("project",),
            sensitivity_allowed=("public", "internal", "private", "unknown"),
            project_scope=identity.project_scope,
            workflow_type="daily_brief",
        )
        append_policy_events(store, identity=identity, decision=daily_decision)
        ensure_policy_allowed(daily_decision)
        daily_run = service.run_now(
            SchedulerRunRequest(
                workflow_type="daily_brief",
                domains=daily_decision.effective_domains,
                sensitivity_allowed=daily_decision.effective_sensitivity_allowed,
                triggered_by="agent",
                agent_identity=identity,
                policy_decision=daily_decision,
            )
        )
        weekly_decision = evaluate_agent_policy(
            identity=identity,
            action="scheduler.run_now",
            domains=("project",),
            sensitivity_allowed=("public", "internal", "private", "unknown"),
            project_scope=identity.project_scope,
            workflow_type="weekly_synthesis",
        )
        append_policy_events(store, identity=identity, decision=weekly_decision)
        ensure_policy_allowed(weekly_decision)
        weekly_run = service.run_now(
            SchedulerRunRequest(
                workflow_type="weekly_synthesis",
                domains=weekly_decision.effective_domains,
                sensitivity_allowed=weekly_decision.effective_sensitivity_allowed,
                triggered_by="agent",
                agent_identity=identity,
                policy_decision=weekly_decision,
            )
        )
        due_decision = evaluate_agent_policy(
            identity=identity,
            action="scheduler.run_due",
            project_scope=identity.project_scope,
        )
        append_policy_events(store, identity=identity, decision=due_decision)
        ensure_policy_allowed(due_decision)
        store.update_scheduler_workflow(
            workflow_type="daily_brief",
            patch={"enabled": True, "paused": False, "next_run_at": "2000-01-01T00:00:00+00:00"},
            actor_type="system",
        )
        due_payload = service.run_due_workflows(
            limit=1,
            triggered_by="agent",
            agent_identity=identity,
            policy_decision=due_decision,
        )
        readonly_identity = AgentIdentity(
            agent_id="readonly-smoke",
            agent_type="unknown",
            agent_run_id=smoke_run_id,
            permission_profile="read_only_agent",
        )
        blocked_decision = evaluate_agent_policy(identity=readonly_identity, action="scheduler.pause")
        append_policy_events(store, identity=readonly_identity, decision=blocked_decision)
        pause_payload = service.pause_all(actor_type="user")
        resume_payload = service.resume_all(actor_type="user")
        final_status = service.status()

    gates = {
        "scheduler_defaults_exist": len(initial_status.get("workflows", [])) >= 6,
        "scheduler_disabled_by_default": initial_status.get("disabled_by_default") is True,
        "daily_workflow_enabled": daily_workflow.get("enabled") is True,
        "weekly_workflow_enabled": weekly_workflow.get("enabled") is True,
        "memory_proposal_candidate": proposal.get("status") == "candidate",
        "daily_run_succeeded": (daily_run.get("run") or {}).get("status") == "succeeded",
        "weekly_run_succeeded": (weekly_run.get("run") or {}).get("status") == "succeeded",
        "due_scan_executed": due_payload.get("due_count") == 1
        and ((due_payload.get("runs") or [{}])[0].get("run") or {}).get("status") == "succeeded",
        "scheduler_artifacts_reviewable": (daily_run.get("artifact") or {}).get("status") == "needs_review"
        and (weekly_run.get("artifact") or {}).get("status") == "needs_review",
        "blocked_policy_recorded": blocked_decision.decision == "blocked",
        "pause_resume_completed": pause_payload.get("paused_count", 0) >= 6 and resume_payload.get("resumed_count", 0) >= 6,
        "run_history_visible": len(final_status.get("recent_runs", [])) >= 2,
    }
    payload = {
        "status": "passed" if all(gates.values()) else "failed",
        "smoke": "agentic-scheduler",
        "gates": gates,
        "agent_identity": identity.to_record(),
        "proposal_id": str(proposal.get("id")),
        "daily_run_id": str((daily_run.get("run") or {}).get("id")),
        "weekly_run_id": str((weekly_run.get("run") or {}).get("id")),
        "due_run_id": str((((due_payload.get("runs") or [{}])[0].get("run") or {}).get("id"))),
        "policy_decisions": {
            "proposal": proposal_decision.to_record(),
            "daily_run": daily_decision.to_record(),
            "weekly_run": weekly_decision.to_record(),
            "due_run": due_decision.to_record(),
            "blocked": blocked_decision.to_record(),
        },
    }
    if payload["status"] != "passed":
        raise RuntimeError(_json_dumps(payload))
    return _json_dumps(payload)


def _seed_local_runtime_smoke_inputs(store, smoke_id: str) -> None:
    source = store.create_source(
        {
            "source_type": "manual_text",
            "title": f"Local runtime smoke source {smoke_id}",
            "content_hash": f"sha256:local-runtime-smoke-{smoke_id}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "raw_text": (
                    "Decision: Local runtime smoke should keep scheduled artifacts reviewable. "
                    "TODO: inspect scheduler failures and policy telemetry after daemon scans."
                ),
                "smoke": "local-runtime",
            },
        },
        actor_type="system",
    )
    memory = store.create_memory(
        {
            "memory_type": "project_state",
            "memory_key": f"local_runtime_smoke.{smoke_id}",
            "value": {"text": "The local runtime daemon runs governed scheduler workflows into reviewable artifacts."},
            "status": "active",
            "confidence": 0.8,
            "title": "Local runtime smoke state",
            "canonical_text": "The local runtime daemon runs governed scheduler workflows into reviewable artifacts.",
            "summary": "Local runtime daemon smoke state.",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"source_id": str(source["id"]), "smoke": "local-runtime"},
        },
        actor_type="system",
    )
    project = store.create_project(
        {
            "name": f"Local Runtime Smoke {smoke_id[:8]}",
            "slug": f"local-runtime-smoke-{smoke_id[:8]}",
            "status": "active",
            "description": "Project used by the vNext local runtime smoke.",
            "current_state": "Needs scheduled project update scan validation.",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"smoke": "local-runtime"},
        },
        actor_type="system",
    )
    store.create_open_loop(
        {
            "memory_id": str(memory["id"]),
            "title": "Inspect local runtime smoke output",
            "status": "open",
            "description": "Confirm daemon due scans appear in scheduler history and event logs.",
            "priority": "normal",
            "project_id": str(project["id"]),
            "source_id": str(source["id"]),
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"smoke": "local-runtime"},
        },
        actor_type="system",
    )


def _run_vnext_smoke_local_runtime(ctx: CLIContext, _args: argparse.Namespace) -> str:
    smoke_id = str(uuid4())
    due_at = "2000-01-01T00:00:00+00:00"
    with tempfile.TemporaryDirectory(prefix="alicebot-vnext-scheduler-") as tmpdir:
        runtime_dir = Path(tmpdir)
        with _vnext_store_context(ctx) as store:
            service = VNextSchedulerService(store)
            service.ensure_default_workflows()
            _seed_local_runtime_smoke_inputs(store, smoke_id)
            for workflow_type in WORKFLOW_TYPES:
                store.update_scheduler_workflow(
                    workflow_type=workflow_type,
                    patch={
                        "enabled": True,
                        "paused": False,
                        "schedule_json": default_schedule(workflow_type),
                        "timezone": "UTC",
                        "next_run_at": due_at,
                        "last_error": None,
                    },
                    actor_type="system",
                )

        daemon_payload = run_foreground_daemon(
            SchedulerRuntimeConfig(
                database_url=ctx.database_url,
                user_id=ctx.user_id,
                interval_seconds=0.1,
                limit=len(WORKFLOW_TYPES),
                pid_file=runtime_dir / "scheduler.pid",
                status_file=runtime_dir / "scheduler-status.json",
                log_file=runtime_dir / "scheduler.log",
                once=True,
            )
        )

    last_due_scan = daemon_payload.get("last_due_scan") if isinstance(daemon_payload.get("last_due_scan"), dict) else {}
    due_runs = last_due_scan.get("runs") if isinstance(last_due_scan, dict) and isinstance(last_due_scan.get("runs"), list) else []
    artifacts = [run.get("artifact") for run in due_runs if isinstance(run, dict) and isinstance(run.get("artifact"), dict)]
    required_metadata = {"workflow_type", "scheduler_run_id", "trace_id", "source_refs", "generated_by", "review_status"}
    observed_workflows = {str(run.get("workflow_type")) for run in due_runs if isinstance(run, dict)}
    metadata_complete = all(
        artifact.get("generated_by") == "scheduler"
        and artifact.get("status") == "needs_review"
        and artifact.get("domain") is not None
        and artifact.get("sensitivity") is not None
        and required_metadata.issubset(set((artifact.get("metadata_json") or {}).keys()))
        for artifact in artifacts
        if isinstance(artifact, dict)
    )
    gates = {
        "daemon_once_completed": daemon_payload.get("running") is False and daemon_payload.get("last_error") is None,
        "due_scan_executed_all_workflows": observed_workflows == set(WORKFLOW_TYPES),
        "daily_brief_scheduled": "daily_brief" in observed_workflows,
        "weekly_synthesis_scheduled": "weekly_synthesis" in observed_workflows,
        "connection_report_scheduled": "connection_report" in observed_workflows,
        "contradiction_report_scheduled": "contradiction_report" in observed_workflows,
        "open_loop_review_scheduled": "open_loop_review" in observed_workflows,
        "project_update_scan_scheduled": "project_update_scan" in observed_workflows,
        "scheduled_artifacts_reviewable": len(artifacts) == len(WORKFLOW_TYPES)
        and all(isinstance(artifact, dict) and artifact.get("status") == "needs_review" for artifact in artifacts),
        "scheduled_artifact_metadata_complete": metadata_complete,
    }
    daemon_summary = {
        key: daemon_payload.get(key)
        for key in (
            "configured",
            "running",
            "mode",
            "pid",
            "started_at",
            "stopped_at",
            "last_heartbeat_at",
            "last_due_scan_at",
            "last_due_count",
            "last_error",
            "last_error_type",
        )
        if key in daemon_payload
    }
    run_summaries = [
        {
            "workflow_type": run.get("workflow_type"),
            "run_id": ((run.get("run") or {}).get("id") if isinstance(run.get("run"), dict) else None),
            "status": ((run.get("run") or {}).get("status") if isinstance(run.get("run"), dict) else None),
            "artifact_id": ((run.get("artifact") or {}).get("id") if isinstance(run.get("artifact"), dict) else None),
            "artifact_type": ((run.get("artifact") or {}).get("artifact_type") if isinstance(run.get("artifact"), dict) else None),
        }
        for run in due_runs
        if isinstance(run, dict)
    ]
    payload = {
        "status": "passed" if all(gates.values()) else "failed",
        "smoke": "local-runtime",
        "gates": gates,
        "daemon": daemon_summary,
        "runs": run_summaries,
    }
    if payload["status"] != "passed":
        raise RuntimeError(_json_dumps(payload))
    return _json_dumps(payload)


def _connection_finder_request_from_args(args: argparse.Namespace) -> ConnectionFinderRequest:
    return ConnectionFinderRequest(
        query=getattr(args, "query", "") or "",
        domains=tuple(args.domain),
        sensitivity_allowed=_vnext_sensitivity_allowed(args),
        max_connections=args.max_connections,
        auto_accept_threshold=args.auto_accept_threshold,
    )


def _run_connections_generate(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        artifact = VNextConnectionService(store).generate_connection_report(_connection_finder_request_from_args(args))
    return _json_dumps(artifact)


def _run_vnext_graph_review(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        edge = VNextConnectionService(store).review_edge(edge_id=args.edge_id, action=args.action)
    return _json_dumps(edge)


def _run_vnext_graph_neighborhood(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        payload = VNextConnectionService(store).graph_neighborhood(target_id=args.target_id)
    return _json_dumps(payload)


def _contradiction_finder_request_from_args(args: argparse.Namespace) -> ContradictionFinderRequest:
    return ContradictionFinderRequest(
        query=getattr(args, "query", "") or "",
        domains=tuple(args.domain),
        sensitivity_allowed=_vnext_sensitivity_allowed(args),
        max_contradictions=args.max_contradictions,
    )


def _run_vnext_contradictions_generate(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        artifact = VNextContradictionService(store).generate_contradiction_report(
            _contradiction_finder_request_from_args(args)
        )
    return _json_dumps(artifact)


def _run_vnext_belief_review(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        belief = VNextContradictionService(store).review_belief(
            belief_id=args.belief_id,
            action=args.action,
            confidence=args.confidence,
            superseded_by=args.superseded_by,
        )
    return _json_dumps(belief)


def _run_vnext_belief_state(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        payload = VNextContradictionService(store).belief_state(belief_id=args.belief_id)
    return _json_dumps(payload)


def _project_automation_request_from_args(args: argparse.Namespace) -> ProjectAutomationRequest:
    return ProjectAutomationRequest(
        domains=tuple(args.domain),
        sensitivity_allowed=_vnext_sensitivity_allowed(args),
        project_id=getattr(args, "project_id", None),
        person_id=getattr(args, "person_id", None),
        max_items=args.max_items,
    )


def _run_vnext_project_update_candidate(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        artifact = VNextProjectService(store).generate_project_update_candidate(_project_automation_request_from_args(args))
    return _json_dumps(artifact)


def _run_vnext_project_update_review(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        artifact = VNextProjectService(store).review_project_update(
            artifact_id=args.artifact_id,
            action=args.action,
            edited_current_state=args.edited_current_state,
        )
    return _json_dumps(artifact)


def _run_vnext_project_dashboard(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        payload = VNextProjectService(store).project_dashboard(
            project_id=args.project_id,
            sensitivity_allowed=_vnext_sensitivity_allowed(args),
        )
    return _json_dumps(payload)


def _run_vnext_open_loops_extract(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        loops = VNextProjectService(store).extract_open_loops(_project_automation_request_from_args(args))
    return _json_dumps({"open_loops": loops, "created_count": len(loops)})


def _run_vnext_open_loop_review(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        loop = VNextProjectService(store).review_open_loop(
            loop_id=args.loop_id,
            action=args.action,
            title=args.title,
            description=args.description,
            due_at=args.due_at,
            priority=args.priority,
            resolution_note=args.resolution_note,
        )
    return _json_dumps(loop)


def _run_vnext_queue_add(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        task = VNextQueueService(store).enqueue_task(
            QueueTaskRequest(
                title=args.title,
                task_type=args.type,
                instructions=args.instructions,
                requested_by="cli",
                domain=args.domain,
                sensitivity=args.sensitivity,
                write_policy=args.write_policy,
            )
        )
    return _json_dumps(task)


def _run_vnext_queue_process_next(ctx: CLIContext, _args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        result = VNextQueueService(store).process_next_task()
    return _json_dumps(result.to_record())


def _run_vnext_artifact_review(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        artifact = VNextQueueService(store).review_artifact(
            artifact_id=args.artifact_id,
            action=args.action,
        )
    return _json_dumps(artifact)


def _run_vnext_artifact_export(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        output_path = VNextQueueService(store).export_artifact_markdown(
            artifact_id=args.artifact_id,
            output_dir=args.output_dir,
        )
    return _json_dumps({"artifact_id": args.artifact_id, "output_path": str(output_path)})


def _run_mutation_generate(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = generate_memory_operation_candidates(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationGenerateInput(
                user_content=args.user_content or "",
                assistant_content=args.assistant_content or "",
                mode=args.mode,
                sync_fingerprint=args.sync_fingerprint,
                source_kind=args.source_kind,
                session_id=args.session_id,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                target_continuity_object_id=args.target_continuity_object_id,
            ),
        )
    return format_memory_operation_candidates_output(payload)


def _run_mutation_candidates(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_memory_operation_candidates(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationListInput(
                limit=args.limit,
                policy_action=args.policy_action,
                operation_type=args.operation_type,
                sync_fingerprint=args.sync_fingerprint,
            ),
        )
    return format_memory_operation_candidates_output(payload)


def _run_mutation_commit(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = commit_memory_operations(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationCommitInput(
                candidate_ids=args.candidate_ids,
                sync_fingerprint=args.sync_fingerprint,
                include_review_required=args.include_review_required,
            ),
        )
    return format_memory_operation_commit_output(payload)


def _run_mutation_operations(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_memory_operations(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationListInput(
                limit=args.limit,
                sync_fingerprint=args.sync_fingerprint,
            ),
        )
    return format_memory_operations_output(payload)


def _run_recall(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = query_continuity_recall(
            store,
            user_id=ctx.user_id,
            request=ContinuityRecallQueryInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                limit=args.limit,
                debug=args.debug,
            ),
        )
    return format_recall_output(payload)


def _run_state_at(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_temporal_state_at(
            store,
            user_id=ctx.user_id,
            request=TemporalStateAtQueryInput(
                entity_id=args.entity_id,
                at=args.at,
            ),
        )
    return format_temporal_state_output(payload)


def _run_timeline(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_temporal_timeline(
            store,
            user_id=ctx.user_id,
            request=TemporalTimelineQueryInput(
                entity_id=args.entity_id,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        )
    return format_temporal_timeline_output(payload)


def _run_lifecycle_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_continuity_lifecycle_state(
            store,
            user_id=ctx.user_id,
            request=ContinuityLifecycleQueryInput(limit=args.limit),
        )
    return format_lifecycle_list_output(payload)


def _run_lifecycle_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_lifecycle_state(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_lifecycle_detail_output(payload)


def _run_resume(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_resumption_brief(
            store,
            user_id=ctx.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
                include_non_promotable_facts=args.include_non_promotable_facts,
                debug=args.debug,
            ),
        )
    return format_resume_output(payload)


def _run_brief(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_brief(
            store,
            user_id=ctx.user_id,
            request=ContinuityBriefRequestInput(
                brief_type=args.brief_type,
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                max_relevant_facts=args.max_relevant_facts,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
                max_conflicts=args.max_conflicts,
                max_timeline_highlights=args.max_timeline_highlights,
                include_non_promotable_facts=args.include_non_promotable_facts,
            ),
        )
    return format_continuity_brief_output(payload)


def _task_brief_request_from_args(args: argparse.Namespace) -> TaskBriefCompileRequestInput:
    return TaskBriefCompileRequestInput(
        mode=args.mode,
        query=args.query,
        workspace_id=args.workspace_id,
        pack_id=args.pack_id,
        pack_version=args.pack_version,
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        model_pack_strategy=args.model_pack_strategy,
        token_budget=args.token_budget,
    )


def _run_task_brief_compile(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_and_persist_task_brief(
            store,
            user_id=ctx.user_id,
            request=_task_brief_request_from_args(args),
        )
    return format_task_brief_output(payload)


def _run_task_brief_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_persisted_task_brief(
            store,
            task_brief_id=args.task_brief_id,
        )
    return format_task_brief_output(payload)


def _run_task_brief_compare(ctx: CLIContext, args: argparse.Namespace) -> str:
    primary_request = _task_brief_request_from_args(args)
    secondary_request = TaskBriefCompileRequestInput(
        mode=args.compare_to_mode,
        query=args.query,
        workspace_id=args.workspace_id,
        pack_id=args.pack_id,
        pack_version=args.pack_version,
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        model_pack_strategy=args.compare_model_pack_strategy or args.model_pack_strategy,
        token_budget=args.compare_token_budget,
    )
    with _store_context(ctx) as store:
        payload = compare_task_briefs(
            store,
            user_id=ctx.user_id,
            primary_request=primary_request,
            secondary_request=secondary_request,
        )
    return format_task_brief_comparison_output(payload)


def _run_open_loops(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_open_loop_dashboard(
            store,
            user_id=ctx.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        )
    return format_open_loops_output(payload)


def _run_review_queue(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_continuity_review_queue(
            store,
            user_id=ctx.user_id,
            request=ContinuityReviewQueueQueryInput(
                status=args.status,
                limit=args.limit,
            ),
        )
    return format_review_queue_output(payload)


def _run_review_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_review_detail(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_review_detail_output(payload)


def _run_review_apply(ctx: CLIContext, args: argparse.Namespace) -> str:
    body = _parse_optional_json_object(args.body_json, option_name="--body-json")
    provenance = _parse_optional_json_object(args.provenance_json, option_name="--provenance-json")
    replacement_body = _parse_optional_json_object(
        args.replacement_body_json,
        option_name="--replacement-body-json",
    )
    replacement_provenance = _parse_optional_json_object(
        args.replacement_provenance_json,
        option_name="--replacement-provenance-json",
    )

    with _store_context(ctx) as store:
        payload = apply_continuity_correction(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
            request=ContinuityCorrectionInput(
                action=args.action,
                reason=args.reason,
                title=args.title,
                body=body,
                provenance=provenance,
                confidence=args.confidence,
                replacement_title=args.replacement_title,
                replacement_body=replacement_body,
                replacement_provenance=replacement_provenance,
                replacement_confidence=args.replacement_confidence,
            ),
        )
    return format_review_apply_output(payload)


def _run_contradictions_detect(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = sync_contradictions(
            store,
            user_id=ctx.user_id,
            request=ContradictionSyncInput(
                continuity_object_id=args.continuity_object_id,
                limit=args.limit,
            ),
        )
    return format_contradiction_sync_output(payload)


def _run_contradictions_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_contradiction_cases(
            store,
            user_id=ctx.user_id,
            request=ContradictionCaseListQueryInput(
                status=args.status,
                limit=args.limit,
                continuity_object_id=args.continuity_object_id,
            ),
        )
    return format_contradiction_case_list_output(payload)


def _run_contradictions_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_contradiction_case(
            store,
            user_id=ctx.user_id,
            contradiction_case_id=args.contradiction_case_id,
        )
    return format_contradiction_case_detail_output(payload)


def _run_contradictions_resolve(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = resolve_contradiction_case(
            store,
            user_id=ctx.user_id,
            contradiction_case_id=args.contradiction_case_id,
            request=ContradictionResolveInput(
                action=args.action,
                note=args.note,
            ),
        )
    return format_contradiction_case_detail_output(
        {"contradiction_case": payload["contradiction_case"]}
    )


def _run_trust_signals(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trust_signals(
            store,
            user_id=ctx.user_id,
            request=TrustSignalListQueryInput(
                limit=args.limit,
                continuity_object_id=args.continuity_object_id,
                signal_state=args.signal_state,
                signal_type=args.signal_type,
            ),
        )
    return format_trust_signals_output(payload)


def _run_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    if args.entity_id is not None:
        with _store_context(ctx) as store:
            payload = get_temporal_explain(
                store,
                user_id=ctx.user_id,
                request=TemporalExplainQueryInput(
                    entity_id=args.entity_id,
                    at=args.at,
                ),
            )
        return format_temporal_explain_output(payload)

    if args.continuity_object_id is None:
        raise ValueError("explain requires either a continuity_object_id or --entity-id")

    with _store_context(ctx) as store:
        payload = build_continuity_explain(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_explain_output(payload)


def _run_evidence_artifact(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_artifact_detail(
            store,
            user_id=ctx.user_id,
            artifact_id=args.artifact_id,
        )
    return format_artifact_detail_output(payload)


def _run_pattern_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trusted_fact_patterns(
            store,
            user_id=ctx.user_id,
            request=TrustedFactPatternListQueryInput(limit=args.limit),
        )
    return format_trusted_fact_pattern_list_output(payload)


def _run_pattern_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_trusted_fact_pattern(
            store,
            user_id=ctx.user_id,
            pattern_id=args.pattern_id,
        )
    return format_trusted_fact_pattern_explain_output(payload)


def _run_playbook_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trusted_fact_playbooks(
            store,
            user_id=ctx.user_id,
            request=TrustedFactPlaybookListQueryInput(limit=args.limit),
        )
    return format_trusted_fact_playbook_list_output(payload)


def _run_playbook_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_trusted_fact_playbook(
            store,
            user_id=ctx.user_id,
            playbook_id=args.playbook_id,
        )
    return format_trusted_fact_playbook_explain_output(payload)


def _run_status(ctx: CLIContext, _args: argparse.Namespace) -> str:
    database_reachable = ping_database(
        ctx.database_url,
        timeout_seconds=ctx.settings.healthcheck_timeout_seconds,
    )
    maintenance_status = _load_maintenance_status_snapshot()

    status_payload: dict[str, object] = {
        "user_id": str(ctx.user_id),
        "database_status": "reachable" if database_reachable else "unreachable",
        "memory_hygiene_posture": "unknown",
        "memory_duplicate_groups": 0,
        "memory_stale_facts": 0,
        "memory_unresolved_contradictions": 0,
        "memory_weak_trust": 0,
        "memory_review_queue_pressure": "unknown",
        "continuity_capture_events": 0,
        "continuity_objects_total": 0,
        "continuity_objects_active": 0,
        "continuity_objects_stale": 0,
        "continuity_objects_superseded": 0,
        "continuity_objects_deleted": 0,
        "continuity_objects_searchable": 0,
        "continuity_objects_non_searchable": 0,
        "continuity_objects_promotable": 0,
        "continuity_objects_non_promotable": 0,
        "thread_health_posture": "unknown",
        "threads_recent": 0,
        "threads_stale": 0,
        "threads_risky": 0,
        "threads_watch": 0,
        "review_correction_ready": 0,
        "review_active": 0,
        "review_stale": 0,
        "review_superseded": 0,
        "review_deleted": 0,
        "open_loops_total": 0,
        "open_loops_waiting_for": 0,
        "open_loops_blocker": 0,
        "open_loops_stale": 0,
        "open_loops_next_action": 0,
        "retrieval_eval_status": "unknown",
        "retrieval_precision_at_k_mean": "0.000",
        "retrieval_precision_at_1_mean": "0.000",
        "maintenance_status": maintenance_status["maintenance_status"],
        "maintenance_schedule": maintenance_status["maintenance_schedule"],
        "maintenance_last_run_at": maintenance_status["maintenance_last_run_at"],
        "maintenance_failure_count": maintenance_status["maintenance_failure_count"],
        "maintenance_warning_count": maintenance_status["maintenance_warning_count"],
        "maintenance_stale_fact_count": maintenance_status["maintenance_stale_fact_count"],
        "maintenance_reembedded_segment_count": maintenance_status["maintenance_reembedded_segment_count"],
        "maintenance_pattern_candidate_count": maintenance_status["maintenance_pattern_candidate_count"],
        "maintenance_benchmark_status": maintenance_status["maintenance_benchmark_status"],
    }
    if not database_reachable:
        return format_status_output(status_payload)

    with _store_context(ctx) as store:
        review_counts = {
            "active": store.count_continuity_review_queue(statuses=["active"]),
            "stale": store.count_continuity_review_queue(statuses=["stale"]),
            "superseded": store.count_continuity_review_queue(statuses=["superseded"]),
            "deleted": store.count_continuity_review_queue(statuses=["deleted"]),
        }

        recall_candidates = store.list_continuity_recall_candidates()
        object_status_counts = {
            "active": 0,
            "stale": 0,
            "superseded": 0,
            "deleted": 0,
        }
        for candidate in recall_candidates:
            status = str(candidate["status"])
            if status in object_status_counts:
                object_status_counts[status] += 1

        open_loops = compile_continuity_open_loop_dashboard(
            store,
            user_id=ctx.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(limit=0),
        )
        open_loop_dashboard = open_loops["dashboard"]

        retrieval_summary = get_retrieval_evaluation_summary(
            store,
            user_id=ctx.user_id,
        )["summary"]
        memory_hygiene = get_memory_hygiene_dashboard_summary(
            store,
            user_id=ctx.user_id,
        )["dashboard"]
        thread_health = get_thread_health_dashboard(
            store,
            user_id=ctx.user_id,
        )["dashboard"]

        status_payload.update(
            {
                "memory_hygiene_posture": memory_hygiene["posture"],
                "memory_duplicate_groups": memory_hygiene["duplicate_group_count"],
                "memory_stale_facts": memory_hygiene["stale_fact_count"],
                "memory_unresolved_contradictions": memory_hygiene["unresolved_contradiction_count"],
                "memory_weak_trust": memory_hygiene["weak_trust_count"],
                "memory_review_queue_pressure": memory_hygiene["review_queue_pressure"]["posture"],
                "continuity_capture_events": store.count_continuity_capture_events(),
                "continuity_objects_total": len(recall_candidates),
                "continuity_objects_active": object_status_counts["active"],
                "continuity_objects_stale": object_status_counts["stale"],
                "continuity_objects_superseded": object_status_counts["superseded"],
                "continuity_objects_deleted": object_status_counts["deleted"],
                "continuity_objects_searchable": sum(
                    1
                    for candidate in recall_candidates
                    if bool(
                        candidate.get(
                            "is_searchable",
                            default_continuity_searchable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_non_searchable": sum(
                    1
                    for candidate in recall_candidates
                    if not bool(
                        candidate.get(
                            "is_searchable",
                            default_continuity_searchable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_promotable": sum(
                    1
                    for candidate in recall_candidates
                    if bool(
                        candidate.get(
                            "is_promotable",
                            default_continuity_promotable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_non_promotable": sum(
                    1
                    for candidate in recall_candidates
                    if not bool(
                        candidate.get(
                            "is_promotable",
                            default_continuity_promotable(str(candidate["object_type"])),
                        )
                    )
                ),
                "thread_health_posture": thread_health["posture"],
                "threads_recent": thread_health["recent_thread_count"],
                "threads_stale": thread_health["stale_thread_count"],
                "threads_risky": thread_health["risky_thread_count"],
                "threads_watch": thread_health["watch_thread_count"],
                "review_correction_ready": review_counts["active"] + review_counts["stale"],
                "review_active": review_counts["active"],
                "review_stale": review_counts["stale"],
                "review_superseded": review_counts["superseded"],
                "review_deleted": review_counts["deleted"],
                "open_loops_total": open_loop_dashboard["summary"]["total_count"],
                "open_loops_waiting_for": open_loop_dashboard["waiting_for"]["summary"]["total_count"],
                "open_loops_blocker": open_loop_dashboard["blocker"]["summary"]["total_count"],
                "open_loops_stale": open_loop_dashboard["stale"]["summary"]["total_count"],
                "open_loops_next_action": open_loop_dashboard["next_action"]["summary"]["total_count"],
                "retrieval_eval_status": retrieval_summary["status"],
                "retrieval_precision_at_k_mean": f"{retrieval_summary['precision_at_k_mean']:.3f}",
                "retrieval_precision_at_1_mean": f"{retrieval_summary['precision_at_1_mean']:.3f}",
            }
        )

    return format_status_output(status_payload)


def _run_eval_suites(ctx: CLIContext, _args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_public_eval_suites(
            store,
            user_id=ctx.user_id,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_runs(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_public_eval_runs(
            store,
            user_id=ctx.user_id,
            limit=args.limit,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_public_eval_run(
            store,
            user_id=ctx.user_id,
            eval_run_id=args.eval_run_id,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_run(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = run_public_evals(
            store,
            user_id=ctx.user_id,
            suite_keys=args.suite_key,
        )
    if args.report_path is not None:
        written_path = write_public_eval_report(
            report=payload["report"],
            report_path=args.report_path,
        )
        payload["written_report_path"] = str(written_path)
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_vnext_eval_seed(_ctx: CLIContext, args: argparse.Namespace) -> str:
    written_path = write_vnext_benchmark_corpus(args.output_path)
    return json.dumps(
        {
            "status": "seeded",
            "written_corpus_path": str(written_path),
        },
        indent=2,
        sort_keys=True,
    )


def _run_vnext_eval_run(_ctx: CLIContext, args: argparse.Namespace) -> str:
    report = run_vnext_evals(
        suite=args.suite,
        corpus_path=args.corpus_path,
    )
    payload: dict[str, object] = {"report": report}
    if args.report_path is not None:
        payload["written_report_path"] = str(
            write_vnext_eval_report(
                report=report,
                report_path=args.report_path,
            )
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_vnext_eval_report(_ctx: CLIContext, args: argparse.Namespace) -> str:
    report = run_vnext_evals(
        suite=args.suite,
        corpus_path=args.corpus_path,
    )
    written_path = write_vnext_eval_report(
        report=report,
        report_path=args.report_path,
    )
    return json.dumps(
        {
            "report": report,
            "written_report_path": str(written_path),
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alicebot",
        description="Deterministic local CLI for Alice continuity workflows.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override database URL. Defaults to settings/env DATABASE_URL.",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help=(
            "Override acting user UUID. Defaults to ALICEBOT_AUTH_USER_ID when set, "
            f"otherwise {DEFAULT_CLI_USER_ID}."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="Capture continuity input.")
    capture_parser.add_argument("raw_content", nargs="+", help="Raw continuity text to capture.")
    capture_parser.add_argument(
        "--explicit-signal",
        choices=CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
        default=None,
        help="Optional explicit signal for deterministic derivation.",
    )
    capture_parser.set_defaults(handler=_run_capture)

    context_pack_parser = subparsers.add_parser("context-pack", help="Compile an Alice vNext context pack.")
    context_pack_parser.add_argument("query", nargs="+", help="Query to compile context for.")
    context_pack_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    context_pack_parser.add_argument("--project", action="append", default=[], help="Project scope. Repeatable.")
    context_pack_parser.add_argument("--person", action="append", default=[], help="People scope. Repeatable.")
    context_pack_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    context_pack_parser.add_argument("--max-items", type=int, default=8, help="Maximum selected memories.")
    context_pack_parser.add_argument("--max-tokens", type=int, default=8000, help="Approximate context token budget.")
    context_pack_parser.add_argument("--no-sources", action="store_true", help="Do not require source references.")
    context_pack_parser.add_argument(
        "--no-contradictions",
        action="store_true",
        help="Do not request contradiction placeholders by default.",
    )
    context_pack_parser.set_defaults(handler=_run_context_pack)

    daily_brief_parser = subparsers.add_parser("daily-brief", help="Generate a vNext daily brief artifact.")
    daily_brief_parser.add_argument("--generate", action="store_true", help="Generate the daily brief now.")
    daily_brief_parser.add_argument("--generated-for", default=None, help="ISO date for the brief.")
    daily_brief_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    daily_brief_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    daily_brief_parser.add_argument("--source-limit", type=int, default=8, help="Maximum source inputs.")
    daily_brief_parser.add_argument("--memory-limit", type=int, default=8, help="Maximum memory inputs.")
    daily_brief_parser.add_argument("--open-loop-limit", type=int, default=8, help="Maximum open-loop inputs.")
    daily_brief_parser.add_argument("--artifact-limit", type=int, default=4, help="Maximum recent artifact inputs.")
    daily_brief_parser.add_argument(
        "--no-discover-open-loops",
        action="store_true",
        help="Skip candidate open-loop discovery from source text.",
    )
    daily_brief_parser.add_argument(
        "--no-candidate-memories",
        action="store_true",
        help="Do not create candidate memories for workflows that support them.",
    )
    daily_brief_parser.set_defaults(handler=_run_daily_brief)

    weekly_synthesis_parser = subparsers.add_parser(
        "weekly-synthesis",
        help="Generate a vNext weekly synthesis artifact.",
    )
    weekly_synthesis_parser.add_argument("--generate", action="store_true", help="Generate the weekly synthesis now.")
    weekly_synthesis_parser.add_argument("--generated-for", default=None, help="ISO date inside the target week.")
    weekly_synthesis_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    weekly_synthesis_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    weekly_synthesis_parser.add_argument("--source-limit", type=int, default=8, help="Maximum source inputs.")
    weekly_synthesis_parser.add_argument("--memory-limit", type=int, default=8, help="Maximum memory inputs.")
    weekly_synthesis_parser.add_argument("--open-loop-limit", type=int, default=8, help="Maximum open-loop inputs.")
    weekly_synthesis_parser.add_argument("--artifact-limit", type=int, default=4, help="Maximum recent artifact inputs.")
    weekly_synthesis_parser.add_argument(
        "--no-discover-open-loops",
        action="store_true",
        help="Skip candidate open-loop discovery from source text.",
    )
    weekly_synthesis_parser.add_argument(
        "--no-candidate-memories",
        action="store_true",
        help="Do not create candidate memories from weekly insights.",
    )
    weekly_synthesis_parser.set_defaults(handler=_run_weekly_synthesis)

    connections_parser = subparsers.add_parser("connections", help="Generate vNext connection reports.")
    connections_subparsers = connections_parser.add_subparsers(dest="connections_command", required=True)
    connections_generate_parser = connections_subparsers.add_parser(
        "generate",
        help="Generate a vNext connection report and candidate graph edges.",
    )
    connections_generate_parser.add_argument("--query", default="", help="Optional search query for candidate inputs.")
    connections_generate_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    connections_generate_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    connections_generate_parser.add_argument(
        "--max-connections",
        type=int,
        default=8,
        help="Maximum candidate connections.",
    )
    connections_generate_parser.add_argument(
        "--auto-accept-threshold",
        type=float,
        default=None,
        help="Optional confidence threshold for auto-accepted edges.",
    )
    connections_generate_parser.set_defaults(handler=_run_connections_generate)

    vnext_parser = subparsers.add_parser("vnext", help="Alice vNext workflows.")
    vnext_subparsers = vnext_parser.add_subparsers(dest="vnext_command", required=True)

    vnext_connectors_parser = vnext_subparsers.add_parser("connectors", help="List and ingest vNext connectors.")
    vnext_connectors_subparsers = vnext_connectors_parser.add_subparsers(
        dest="vnext_connectors_command",
        required=True,
    )

    vnext_connectors_list_parser = vnext_connectors_subparsers.add_parser(
        "list",
        help="List deterministic vNext connector definitions and defaults.",
    )
    vnext_connectors_list_parser.set_defaults(handler=_run_vnext_connectors_list)

    vnext_connectors_ingest_parser = vnext_connectors_subparsers.add_parser(
        "ingest",
        help="Ingest already-exported connector payload items into vNext sources.",
    )
    vnext_connectors_ingest_parser.add_argument("connector_name", help="Connector name, such as telegram.")
    vnext_connectors_ingest_parser.add_argument("payload_path", help="JSON payload file, or CSV for csv_table.")
    vnext_connectors_ingest_parser.add_argument("--domain", default=None, help="Connector default domain override.")
    vnext_connectors_ingest_parser.add_argument(
        "--sensitivity",
        default=None,
        help="Connector default sensitivity override.",
    )
    vnext_connectors_ingest_parser.set_defaults(handler=_run_vnext_connectors_ingest)

    vnext_sources_parser = vnext_subparsers.add_parser("sources", help="Capture and import vNext sources.")
    vnext_sources_subparsers = vnext_sources_parser.add_subparsers(dest="vnext_sources_command", required=True)

    vnext_capture_text_parser = vnext_sources_subparsers.add_parser(
        "capture-text",
        help="Capture manual text into the vNext source pipeline.",
    )
    vnext_capture_text_parser.add_argument("raw_text", nargs="+", help="Raw text to capture.")
    vnext_capture_text_parser.add_argument("--title", default=None, help="Optional source title.")
    vnext_capture_text_parser.add_argument("--domain", default="unknown", help="Source domain.")
    vnext_capture_text_parser.add_argument("--sensitivity", default="unknown", help="Source sensitivity.")
    vnext_capture_text_parser.set_defaults(handler=_run_vnext_sources_capture_text)

    vnext_capture_file_parser = vnext_sources_subparsers.add_parser(
        "capture-file",
        help="Capture a local text or Markdown file into the vNext source pipeline.",
    )
    vnext_capture_file_parser.add_argument("path", help="Path to a text or Markdown file.")
    vnext_capture_file_parser.add_argument("--domain", default="unknown", help="Source domain.")
    vnext_capture_file_parser.add_argument("--sensitivity", default="unknown", help="Source sensitivity.")
    vnext_capture_file_parser.set_defaults(handler=_run_vnext_sources_capture_file)

    vnext_import_markdown_parser = vnext_sources_subparsers.add_parser(
        "import-markdown",
        help="Import a Markdown/Obsidian folder into the vNext source pipeline.",
    )
    vnext_import_markdown_parser.add_argument("folder", help="Folder containing Markdown files.")
    vnext_import_markdown_parser.add_argument("--domain", default="unknown", help="Source domain.")
    vnext_import_markdown_parser.add_argument("--sensitivity", default="unknown", help="Source sensitivity.")
    vnext_import_markdown_parser.set_defaults(handler=_run_vnext_sources_import_markdown)

    vnext_import_chatgpt_parser = vnext_sources_subparsers.add_parser(
        "import-chatgpt",
        help="Import a ChatGPT export JSON file into the vNext source pipeline.",
    )
    vnext_import_chatgpt_parser.add_argument("path", help="Path to a ChatGPT export JSON file.")
    vnext_import_chatgpt_parser.add_argument("--domain", default="personal", help="Source domain.")
    vnext_import_chatgpt_parser.add_argument("--sensitivity", default="private", help="Source sensitivity.")
    vnext_import_chatgpt_parser.set_defaults(handler=_run_vnext_sources_import_chatgpt)

    vnext_queue_parser = vnext_subparsers.add_parser("queue", help="Manage the vNext task queue.")
    vnext_queue_subparsers = vnext_queue_parser.add_subparsers(dest="vnext_queue_command", required=True)

    vnext_queue_add_parser = vnext_queue_subparsers.add_parser("add", help="Add a vNext queue task.")
    vnext_queue_add_parser.add_argument("--type", required=True, help="Task type, such as synthesize or draft.")
    vnext_queue_add_parser.add_argument("--title", required=True, help="Task title.")
    vnext_queue_add_parser.add_argument("--instructions", required=True, help="Task instructions.")
    vnext_queue_add_parser.add_argument("--domain", default="unknown", help="Task domain.")
    vnext_queue_add_parser.add_argument("--sensitivity", default="unknown", help="Task sensitivity.")
    vnext_queue_add_parser.add_argument("--write-policy", default="proposal_only", help="Task write policy.")
    vnext_queue_add_parser.set_defaults(handler=_run_vnext_queue_add)

    vnext_queue_process_parser = vnext_queue_subparsers.add_parser(
        "process-next",
        help="Claim and process the next pending vNext queue task.",
    )
    vnext_queue_process_parser.set_defaults(handler=_run_vnext_queue_process_next)

    vnext_artifacts_parser = vnext_subparsers.add_parser("artifacts", help="Review and export vNext artifacts.")
    vnext_artifacts_subparsers = vnext_artifacts_parser.add_subparsers(dest="vnext_artifacts_command", required=True)

    vnext_artifact_review_parser = vnext_artifacts_subparsers.add_parser("review", help="Review a vNext artifact.")
    vnext_artifact_review_parser.add_argument("artifact_id", help="Artifact id.")
    vnext_artifact_review_parser.add_argument(
        "--action",
        choices=("review", "accept", "reject", "promote", "archive"),
        required=True,
        help="Review action.",
    )
    vnext_artifact_review_parser.set_defaults(handler=_run_vnext_artifact_review)

    vnext_artifact_export_parser = vnext_artifacts_subparsers.add_parser(
        "export",
        help="Export a vNext artifact as Markdown.",
    )
    vnext_artifact_export_parser.add_argument("artifact_id", help="Artifact id.")
    vnext_artifact_export_parser.add_argument("--output-dir", required=True, help="Directory for the Markdown file.")
    vnext_artifact_export_parser.set_defaults(handler=_run_vnext_artifact_export)

    vnext_graph_parser = vnext_subparsers.add_parser("graph", help="Review and inspect vNext graph edges.")
    vnext_graph_subparsers = vnext_graph_parser.add_subparsers(dest="vnext_graph_command", required=True)

    vnext_graph_review_parser = vnext_graph_subparsers.add_parser("review", help="Review a candidate graph edge.")
    vnext_graph_review_parser.add_argument("edge_id", help="Graph edge id.")
    vnext_graph_review_parser.add_argument(
        "--action",
        required=True,
        choices=("review", "accept", "reject"),
        help="Review action.",
    )
    vnext_graph_review_parser.set_defaults(handler=_run_vnext_graph_review)

    vnext_graph_neighborhood_parser = vnext_graph_subparsers.add_parser(
        "neighborhood",
        help="Show active graph edges around a target id.",
    )
    vnext_graph_neighborhood_parser.add_argument("target_id", help="Source, memory, artifact, project, or person id.")
    vnext_graph_neighborhood_parser.set_defaults(handler=_run_vnext_graph_neighborhood)

    vnext_contradictions_parser = vnext_subparsers.add_parser(
        "contradictions",
        help="Generate vNext contradiction reports.",
    )
    vnext_contradictions_subparsers = vnext_contradictions_parser.add_subparsers(
        dest="vnext_contradictions_command",
        required=True,
    )
    vnext_contradictions_generate_parser = vnext_contradictions_subparsers.add_parser(
        "generate",
        help="Generate a vNext contradiction report and candidate contradiction edges.",
    )
    vnext_contradictions_generate_parser.add_argument("--query", default="", help="Optional search query.")
    vnext_contradictions_generate_parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="Allowed domain. Repeatable.",
    )
    vnext_contradictions_generate_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_contradictions_generate_parser.add_argument(
        "--max-contradictions",
        type=int,
        default=8,
        help="Maximum candidate contradictions.",
    )
    vnext_contradictions_generate_parser.set_defaults(handler=_run_vnext_contradictions_generate)

    vnext_beliefs_parser = vnext_subparsers.add_parser("beliefs", help="Review and inspect vNext beliefs.")
    vnext_beliefs_subparsers = vnext_beliefs_parser.add_subparsers(dest="vnext_beliefs_command", required=True)

    vnext_belief_review_parser = vnext_beliefs_subparsers.add_parser("review", help="Review a vNext belief.")
    vnext_belief_review_parser.add_argument("belief_id", help="Belief id.")
    vnext_belief_review_parser.add_argument(
        "--action",
        required=True,
        choices=("reinforce", "challenge", "supersede", "retire"),
        help="Belief review action.",
    )
    vnext_belief_review_parser.add_argument("--confidence", type=float, default=None, help="Optional confidence.")
    vnext_belief_review_parser.add_argument("--superseded-by", default=None, help="Replacement belief id.")
    vnext_belief_review_parser.set_defaults(handler=_run_vnext_belief_review)

    vnext_belief_state_parser = vnext_beliefs_subparsers.add_parser(
        "state",
        help="Show current and historical state for a vNext belief.",
    )
    vnext_belief_state_parser.add_argument("belief_id", help="Belief id.")
    vnext_belief_state_parser.set_defaults(handler=_run_vnext_belief_state)

    vnext_projects_parser = vnext_subparsers.add_parser("projects", help="Generate and review vNext project updates.")
    vnext_projects_subparsers = vnext_projects_parser.add_subparsers(dest="vnext_projects_command", required=True)

    vnext_project_update_parser = vnext_projects_subparsers.add_parser(
        "update-candidate",
        help="Generate a project update candidate artifact.",
    )
    vnext_project_update_parser.add_argument("--project-id", default=None, help="Project id.")
    vnext_project_update_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    vnext_project_update_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_project_update_parser.add_argument("--max-items", type=int, default=8, help="Maximum selected inputs.")
    vnext_project_update_parser.set_defaults(handler=_run_vnext_project_update_candidate)

    vnext_project_review_parser = vnext_projects_subparsers.add_parser(
        "review-update",
        help="Accept, edit, or reject a project update candidate artifact.",
    )
    vnext_project_review_parser.add_argument("artifact_id", help="Project update artifact id.")
    vnext_project_review_parser.add_argument("--action", required=True, choices=("accept", "edit", "reject"))
    vnext_project_review_parser.add_argument("--edited-current-state", default=None, help="Edited current state.")
    vnext_project_review_parser.set_defaults(handler=_run_vnext_project_update_review)

    vnext_project_dashboard_parser = vnext_projects_subparsers.add_parser("dashboard", help="Show project dashboard data.")
    vnext_project_dashboard_parser.add_argument("project_id", help="Project id.")
    vnext_project_dashboard_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_project_dashboard_parser.set_defaults(handler=_run_vnext_project_dashboard)

    vnext_open_loops_parser = vnext_subparsers.add_parser("open-loops", help="Extract and review vNext open loops.")
    vnext_open_loops_subparsers = vnext_open_loops_parser.add_subparsers(
        dest="vnext_open_loops_command",
        required=True,
    )
    vnext_open_loops_extract_parser = vnext_open_loops_subparsers.add_parser(
        "extract",
        help="Extract candidate open loops from selected sources.",
    )
    vnext_open_loops_extract_parser.add_argument("--project-id", default=None, help="Project id.")
    vnext_open_loops_extract_parser.add_argument("--person-id", default=None, help="Person id.")
    vnext_open_loops_extract_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    vnext_open_loops_extract_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_open_loops_extract_parser.add_argument("--max-items", type=int, default=8, help="Maximum selected sources.")
    vnext_open_loops_extract_parser.set_defaults(handler=_run_vnext_open_loops_extract)

    vnext_open_loop_review_parser = vnext_open_loops_subparsers.add_parser(
        "review",
        help="Close, snooze, edit, or reopen a vNext open loop.",
    )
    vnext_open_loop_review_parser.add_argument("loop_id", help="Open loop id.")
    vnext_open_loop_review_parser.add_argument("--action", required=True, choices=("close", "snooze", "edit", "reopen"))
    vnext_open_loop_review_parser.add_argument("--title", default=None, help="Edited title.")
    vnext_open_loop_review_parser.add_argument("--description", default=None, help="Edited description.")
    vnext_open_loop_review_parser.add_argument("--due-at", default=None, help="ISO datetime for snooze/edit.")
    vnext_open_loop_review_parser.add_argument("--priority", default=None, help="Edited priority.")
    vnext_open_loop_review_parser.add_argument("--resolution-note", default=None, help="Resolution note for close.")
    vnext_open_loop_review_parser.set_defaults(handler=_run_vnext_open_loop_review)

    vnext_agents_parser = vnext_subparsers.add_parser("agents", help="Submit and inspect vNext agent proposals.")
    vnext_agents_subparsers = vnext_agents_parser.add_subparsers(dest="vnext_agents_command", required=True)
    vnext_agent_propose_parser = vnext_agents_subparsers.add_parser(
        "propose-memory",
        help="Submit an agent memory proposal for review.",
    )
    _add_vnext_agent_arguments(vnext_agent_propose_parser)
    vnext_agent_propose_parser.add_argument("--proposal-type", default="candidate_memory", help="Proposal type.")
    vnext_agent_propose_parser.add_argument("--memory-type", default="semantic", help="Stored candidate memory type.")
    vnext_agent_propose_parser.add_argument("--title", required=True, help="Proposal title.")
    vnext_agent_propose_parser.add_argument("--canonical-text", required=True, help="Canonical memory text.")
    vnext_agent_propose_parser.add_argument("--domain", default="unknown", help="Domain label.")
    vnext_agent_propose_parser.add_argument("--sensitivity", default="unknown", help="Sensitivity label.")
    vnext_agent_propose_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_agent_propose_parser.add_argument("--confidence", type=float, default=0.5, help="Proposal confidence.")
    vnext_agent_propose_parser.add_argument("--rationale", default=None, help="Proposal rationale.")
    vnext_agent_propose_parser.set_defaults(handler=_run_vnext_agent_propose_memory)
    vnext_agent_telemetry_parser = vnext_agents_subparsers.add_parser(
        "policy-telemetry",
        help="Summarize vNext agent policy blocks, filters, reviews, workflows, and proposals.",
    )
    vnext_agent_telemetry_parser.add_argument("--agent-id", default=None, help="Optional agent id filter.")
    vnext_agent_telemetry_parser.add_argument("--limit", type=int, default=200, help="Maximum agent events to summarize.")
    vnext_agent_telemetry_parser.set_defaults(handler=_run_vnext_agent_policy_telemetry)

    vnext_scheduler_parser = vnext_subparsers.add_parser("scheduler", help="Governed local vNext scheduler controls.")
    vnext_scheduler_subparsers = vnext_scheduler_parser.add_subparsers(dest="vnext_scheduler_command", required=True)
    vnext_scheduler_status_parser = vnext_scheduler_subparsers.add_parser("status", help="Show scheduler status.")
    vnext_scheduler_status_parser.set_defaults(handler=_run_vnext_scheduler_status)
    vnext_scheduler_runs_parser = vnext_scheduler_subparsers.add_parser("runs", help="List scheduler run history.")
    vnext_scheduler_runs_parser.add_argument("--workflow-type", default=None, help="Optional workflow type filter.")
    vnext_scheduler_runs_parser.add_argument("--limit", type=int, default=20, help="Maximum runs to return.")
    vnext_scheduler_runs_parser.set_defaults(handler=_run_vnext_scheduler_runs)
    vnext_scheduler_failures_parser = vnext_scheduler_subparsers.add_parser("failures", help="List failed scheduler runs.")
    vnext_scheduler_failures_parser.add_argument("--workflow-type", default=None, help="Optional workflow type filter.")
    vnext_scheduler_failures_parser.add_argument("--limit", type=int, default=20, help="Maximum failed runs to return.")
    vnext_scheduler_failures_parser.set_defaults(handler=_run_vnext_scheduler_failures)
    vnext_scheduler_run_parser = vnext_scheduler_subparsers.add_parser("run-now", help="Run a workflow now.")
    _add_vnext_agent_arguments(vnext_scheduler_run_parser)
    vnext_scheduler_run_parser.add_argument("workflow_type", help="Workflow type, such as daily_brief.")
    vnext_scheduler_run_parser.add_argument("--generated-for", default=None, help="YYYY-MM-DD generation date.")
    vnext_scheduler_run_parser.add_argument("--domain", action="append", default=[], help="Allowed domain. Repeatable.")
    vnext_scheduler_run_parser.add_argument(
        "--sensitivity-allowed",
        action="append",
        default=None,
        help="Allowed sensitivity. Repeatable.",
    )
    vnext_scheduler_run_parser.set_defaults(handler=_run_vnext_scheduler_run_now)
    vnext_scheduler_run_due_parser = vnext_scheduler_subparsers.add_parser("run-due", help="Run enabled workflows whose next_run_at is due.")
    _add_vnext_agent_arguments(vnext_scheduler_run_due_parser)
    vnext_scheduler_run_due_parser.add_argument("--limit", type=int, default=10, help="Maximum due workflows to run.")
    vnext_scheduler_run_due_parser.set_defaults(handler=_run_vnext_scheduler_run_due)
    vnext_scheduler_pause_parser = vnext_scheduler_subparsers.add_parser("pause", help="Pause all scheduler workflows.")
    _add_vnext_agent_arguments(vnext_scheduler_pause_parser)
    vnext_scheduler_pause_parser.set_defaults(handler=_run_vnext_scheduler_pause)
    vnext_scheduler_resume_parser = vnext_scheduler_subparsers.add_parser("resume", help="Resume all scheduler workflows.")
    _add_vnext_agent_arguments(vnext_scheduler_resume_parser)
    vnext_scheduler_resume_parser.set_defaults(handler=_run_vnext_scheduler_resume)
    vnext_scheduler_daemon_parser = vnext_scheduler_subparsers.add_parser("daemon", help="Run or inspect the local scheduler daemon.")
    vnext_scheduler_daemon_subparsers = vnext_scheduler_daemon_parser.add_subparsers(dest="vnext_scheduler_daemon_command", required=True)
    vnext_scheduler_daemon_start_parser = vnext_scheduler_daemon_subparsers.add_parser("start", help="Start the local scheduler daemon.")
    vnext_scheduler_daemon_start_parser.add_argument("--foreground", action="store_true", help="Run in the foreground instead of spawning a background process.")
    vnext_scheduler_daemon_start_parser.add_argument("--once", action="store_true", help="Run one due scan, then exit. Useful for local smoke tests.")
    vnext_scheduler_daemon_start_parser.add_argument("--interval-seconds", type=float, default=60.0, help="Due-scan polling interval.")
    vnext_scheduler_daemon_start_parser.add_argument("--limit", type=int, default=10, help="Maximum due workflows per scan.")
    vnext_scheduler_daemon_start_parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="Daemon pid file.")
    vnext_scheduler_daemon_start_parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE), help="Daemon status JSON file.")
    vnext_scheduler_daemon_start_parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE), help="Daemon log file.")
    vnext_scheduler_daemon_start_parser.set_defaults(handler=_run_vnext_scheduler_daemon_start)
    vnext_scheduler_daemon_status_parser = vnext_scheduler_daemon_subparsers.add_parser("status", help="Show local scheduler daemon process status.")
    vnext_scheduler_daemon_status_parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="Daemon pid file.")
    vnext_scheduler_daemon_status_parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE), help="Daemon status JSON file.")
    vnext_scheduler_daemon_status_parser.set_defaults(handler=_run_vnext_scheduler_daemon_status)
    vnext_scheduler_daemon_stop_parser = vnext_scheduler_daemon_subparsers.add_parser("stop", help="Stop the local scheduler daemon process.")
    vnext_scheduler_daemon_stop_parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="Daemon pid file.")
    vnext_scheduler_daemon_stop_parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE), help="Daemon status JSON file.")
    vnext_scheduler_daemon_stop_parser.set_defaults(handler=_run_vnext_scheduler_daemon_stop)

    vnext_smoke_parser = vnext_subparsers.add_parser("smoke", help="Run vNext smoke checks.")
    vnext_smoke_subparsers = vnext_smoke_parser.add_subparsers(dest="vnext_smoke_command", required=True)
    vnext_smoke_agentic_scheduler_parser = vnext_smoke_subparsers.add_parser(
        "agentic-scheduler",
        help="Run the agentic control-plane and governed scheduler smoke.",
    )
    vnext_smoke_agentic_scheduler_parser.set_defaults(handler=_run_vnext_smoke_agentic_scheduler)
    vnext_smoke_local_runtime_parser = vnext_smoke_subparsers.add_parser(
        "local-runtime",
        help="Run the local scheduler daemon and due-workflow smoke.",
    )
    vnext_smoke_local_runtime_parser.set_defaults(handler=_run_vnext_smoke_local_runtime)

    mutations_parser = subparsers.add_parser("mutations", help="Generate, inspect, and apply memory operations.")
    mutations_subparsers = mutations_parser.add_subparsers(dest="mutations_command", required=True)

    mutation_generate_parser = mutations_subparsers.add_parser(
        "generate",
        help="Generate explicit mutation candidates from a turn pair.",
    )
    mutation_generate_parser.add_argument("--user-content", default="", help="User turn content.")
    mutation_generate_parser.add_argument("--assistant-content", default="", help="Assistant turn content.")
    mutation_generate_parser.add_argument(
        "--mode",
        choices=("manual", "assist", "auto"),
        default="assist",
        help="Mutation policy mode.",
    )
    mutation_generate_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_generate_parser.add_argument("--source-kind", default="sync_turn", help="Source kind label.")
    mutation_generate_parser.add_argument("--session-id", default=None, help="Optional session id.")
    mutation_generate_parser.add_argument("--thread-id", type=_parse_uuid, default=None, help="Optional thread UUID.")
    mutation_generate_parser.add_argument("--task-id", type=_parse_uuid, default=None, help="Optional task UUID.")
    mutation_generate_parser.add_argument("--project", default=None, help="Optional project scope.")
    mutation_generate_parser.add_argument("--person", default=None, help="Optional person scope.")
    mutation_generate_parser.add_argument(
        "--target-continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional explicit target continuity object UUID.",
    )
    mutation_generate_parser.set_defaults(handler=_run_mutation_generate)

    mutation_candidates_parser = mutations_subparsers.add_parser(
        "candidates",
        help="List generated mutation candidates.",
    )
    mutation_candidates_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_CAPTURE_LIMIT,
        help="Max candidates (1-100).",
    )
    mutation_candidates_parser.add_argument(
        "--policy-action",
        choices=("auto_apply", "review_required", "skip"),
        default=None,
        help="Optional policy filter.",
    )
    mutation_candidates_parser.add_argument(
        "--operation-type",
        choices=("ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"),
        default=None,
        help="Optional operation filter.",
    )
    mutation_candidates_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_candidates_parser.set_defaults(handler=_run_mutation_candidates)

    mutation_commit_parser = mutations_subparsers.add_parser(
        "commit",
        help="Apply generated mutation candidates.",
    )
    mutation_commit_parser.add_argument(
        "candidate_ids",
        nargs="*",
        type=_parse_uuid,
        help="Candidate UUIDs to apply.",
    )
    mutation_commit_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_commit_parser.add_argument(
        "--include-review-required",
        action="store_true",
        help="Allow review-required candidates to apply.",
    )
    mutation_commit_parser.set_defaults(handler=_run_mutation_commit)

    mutation_operations_parser = mutations_subparsers.add_parser(
        "operations",
        help="List committed memory operations.",
    )
    mutation_operations_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_CAPTURE_LIMIT,
        help="Max operations (1-100).",
    )
    mutation_operations_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_operations_parser.set_defaults(handler=_run_mutation_operations)

    brief_parser = subparsers.add_parser(
        "brief",
        help="Compile the primary one-call continuity brief.",
    )
    _add_continuity_brief_arguments(brief_parser)
    brief_parser.set_defaults(handler=_run_brief)

    recall_parser = subparsers.add_parser("recall", help="Recall continuity objects.")
    _add_scope_filter_arguments(recall_parser)
    recall_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        help=f"Max results (1-{MAX_CONTINUITY_RECALL_LIMIT}).",
    )
    recall_parser.add_argument(
        "--debug",
        action="store_true",
        help="Include hybrid retrieval stage scores and exclusion reasons.",
    )
    recall_parser.set_defaults(handler=_run_recall)

    state_at_parser = subparsers.add_parser(
        "state-at",
        help="Show entity state reconstructed at a specific point in time.",
    )
    state_at_parser.add_argument("entity_id", type=_parse_uuid, help="Entity UUID.")
    state_at_parser.add_argument("--at", type=_parse_datetime, default=None, help="As-of time (ISO-8601).")
    state_at_parser.set_defaults(handler=_run_state_at)

    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Show chronological temporal history for one entity.",
    )
    timeline_parser.add_argument("entity_id", type=_parse_uuid, help="Entity UUID.")
    timeline_parser.add_argument("--since", type=_parse_datetime, default=None, help="Optional start time (ISO-8601).")
    timeline_parser.add_argument("--until", type=_parse_datetime, default=None, help="Optional end time (ISO-8601).")
    timeline_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TEMPORAL_TIMELINE_LIMIT,
        help=f"Max timeline events (1-{MAX_TEMPORAL_TIMELINE_LIMIT}).",
    )
    timeline_parser.set_defaults(handler=_run_timeline)

    lifecycle_parser = subparsers.add_parser("lifecycle", help="Inspect continuity lifecycle state.")
    lifecycle_subparsers = lifecycle_parser.add_subparsers(dest="lifecycle_command", required=True)

    lifecycle_list_parser = lifecycle_subparsers.add_parser("list", help="List lifecycle states.")
    lifecycle_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
        help=f"Max lifecycle results (1-{MAX_CONTINUITY_LIFECYCLE_LIMIT}).",
    )
    lifecycle_list_parser.set_defaults(handler=_run_lifecycle_list)

    lifecycle_show_parser = lifecycle_subparsers.add_parser("show", help="Show one lifecycle state.")
    lifecycle_show_parser.add_argument(
        "continuity_object_id",
        type=_parse_uuid,
        help="Continuity object UUID.",
    )
    lifecycle_show_parser.set_defaults(handler=_run_lifecycle_show)

    resume_parser = subparsers.add_parser("resume", help="Compile continuity resumption brief.")
    _add_scope_filter_arguments(resume_parser)
    resume_parser.add_argument(
        "--max-recent-changes",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        help=f"Recent change limit (0-{MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}).",
    )
    resume_parser.add_argument(
        "--max-open-loops",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        help=f"Open loop limit (0-{MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}).",
    )
    resume_parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts in recent changes.",
    )
    resume_parser.add_argument(
        "--debug",
        action="store_true",
        help="Include the underlying hybrid retrieval trace.",
    )
    resume_parser.set_defaults(handler=_run_resume)

    task_briefs_parser = subparsers.add_parser(
        "task-briefs",
        help="Compile, compare, and inspect task-adaptive briefs.",
    )
    task_briefs_subparsers = task_briefs_parser.add_subparsers(dest="task_briefs_command", required=True)

    task_briefs_compile_parser = task_briefs_subparsers.add_parser(
        "compile",
        help="Compile and persist one task-adaptive brief.",
    )
    _add_task_brief_arguments(task_briefs_compile_parser)
    task_briefs_compile_parser.set_defaults(handler=_run_task_brief_compile)

    task_briefs_show_parser = task_briefs_subparsers.add_parser(
        "show",
        help="Load one persisted task brief.",
    )
    task_briefs_show_parser.add_argument("task_brief_id", type=_parse_uuid, help="Task brief UUID.")
    task_briefs_show_parser.set_defaults(handler=_run_task_brief_show)

    task_briefs_compare_parser = task_briefs_subparsers.add_parser(
        "compare",
        help="Compare two task brief modes for the same scope.",
    )
    _add_task_brief_arguments(task_briefs_compare_parser)
    task_briefs_compare_parser.add_argument(
        "--compare-to-mode",
        required=True,
        choices=("user_recall", "resume", "worker_subtask", "agent_handoff"),
        help="Secondary mode for comparison.",
    )
    task_briefs_compare_parser.add_argument(
        "--compare-model-pack-strategy",
        default=None,
        help="Optional model-pack strategy override for the comparison brief.",
    )
    task_briefs_compare_parser.add_argument(
        "--compare-token-budget",
        type=int,
        default=None,
        help=f"Optional comparison token budget (1-{MAX_TASK_BRIEF_TOKEN_BUDGET}).",
    )
    task_briefs_compare_parser.set_defaults(handler=_run_task_brief_compare)

    open_loops_parser = subparsers.add_parser(
        "open-loops",
        help="List open-loop dashboard grouped by posture.",
    )
    _add_scope_filter_arguments(open_loops_parser)
    open_loops_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        help=f"Per-posture item limit (0-{MAX_CONTINUITY_OPEN_LOOP_LIMIT}).",
    )
    open_loops_parser.set_defaults(handler=_run_open_loops)

    review_parser = subparsers.add_parser("review", help="Review queue and correction commands.")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)

    review_queue_parser = review_subparsers.add_parser("queue", help="List review queue.")
    review_queue_parser.add_argument(
        "--status",
        choices=REVIEW_STATUS_CHOICES,
        default="correction_ready",
        help="Queue status filter.",
    )
    review_queue_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max queue results (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    review_queue_parser.set_defaults(handler=_run_review_queue)

    review_show_parser = review_subparsers.add_parser("show", help="Show detail for one review object.")
    review_show_parser.add_argument("continuity_object_id", type=_parse_uuid, help="Continuity object UUID.")
    review_show_parser.set_defaults(handler=_run_review_show)

    review_apply_parser = review_subparsers.add_parser("apply", help="Apply a continuity correction.")
    review_apply_parser.add_argument("continuity_object_id", type=_parse_uuid, help="Continuity object UUID.")
    review_apply_parser.add_argument(
        "--action",
        required=True,
        choices=CONTINUITY_CORRECTION_ACTIONS,
        help="Correction action.",
    )
    review_apply_parser.add_argument("--reason", default=None, help="Optional correction reason.")
    review_apply_parser.add_argument("--title", default=None, help="Replacement title for edit.")
    review_apply_parser.add_argument(
        "--body-json",
        default=None,
        help="JSON object payload for body replacement on edit.",
    )
    review_apply_parser.add_argument(
        "--provenance-json",
        default=None,
        help="JSON object payload for provenance replacement on edit.",
    )
    review_apply_parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Updated confidence for edit/supersede.",
    )
    review_apply_parser.add_argument(
        "--replacement-title",
        default=None,
        help="Replacement title for supersede.",
    )
    review_apply_parser.add_argument(
        "--replacement-body-json",
        default=None,
        help="JSON object payload for supersede replacement body.",
    )
    review_apply_parser.add_argument(
        "--replacement-provenance-json",
        default=None,
        help="JSON object payload for supersede replacement provenance.",
    )
    review_apply_parser.add_argument(
        "--replacement-confidence",
        type=float,
        default=None,
        help="Replacement confidence for supersede.",
    )
    review_apply_parser.set_defaults(handler=_run_review_apply)

    contradictions_parser = subparsers.add_parser(
        "contradictions",
        help="Detect, inspect, and resolve continuity contradictions.",
    )
    contradictions_subparsers = contradictions_parser.add_subparsers(
        dest="contradictions_command",
        required=True,
    )

    contradictions_detect_parser = contradictions_subparsers.add_parser(
        "detect",
        help="Run contradiction detection and persist current cases.",
    )
    contradictions_detect_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID to scope detection.",
    )
    contradictions_detect_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max contradiction rows to print (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    contradictions_detect_parser.set_defaults(handler=_run_contradictions_detect)

    contradictions_list_parser = contradictions_subparsers.add_parser(
        "list",
        help="List contradiction cases.",
    )
    contradictions_list_parser.add_argument(
        "--status",
        choices=("open", "resolved", "dismissed"),
        default="open",
        help="Case status filter.",
    )
    contradictions_list_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID filter.",
    )
    contradictions_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max contradiction rows (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    contradictions_list_parser.set_defaults(handler=_run_contradictions_list)

    contradictions_show_parser = contradictions_subparsers.add_parser(
        "show",
        help="Show one contradiction case.",
    )
    contradictions_show_parser.add_argument(
        "contradiction_case_id",
        type=_parse_uuid,
        help="Contradiction case UUID.",
    )
    contradictions_show_parser.set_defaults(handler=_run_contradictions_show)

    contradictions_resolve_parser = contradictions_subparsers.add_parser(
        "resolve",
        help="Resolve one contradiction case.",
    )
    contradictions_resolve_parser.add_argument(
        "contradiction_case_id",
        type=_parse_uuid,
        help="Contradiction case UUID.",
    )
    contradictions_resolve_parser.add_argument(
        "--action",
        required=True,
        choices=CONTRADICTION_RESOLUTION_ACTIONS,
        help="Resolution action.",
    )
    contradictions_resolve_parser.add_argument(
        "--note",
        default=None,
        help="Optional operator note.",
    )
    contradictions_resolve_parser.set_defaults(handler=_run_contradictions_resolve)

    trust_parser = subparsers.add_parser(
        "trust",
        help="Inspect stored trust signals.",
    )
    trust_subparsers = trust_parser.add_subparsers(dest="trust_command", required=True)
    trust_signals_parser = trust_subparsers.add_parser("signals", help="List trust signals.")
    trust_signals_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID filter.",
    )
    trust_signals_parser.add_argument(
        "--signal-state",
        choices=("active", "inactive"),
        default="active",
        help="Signal state filter.",
    )
    trust_signals_parser.add_argument(
        "--signal-type",
        choices=("correction", "corroboration", "contradiction", "weak_inference"),
        default=None,
        help="Optional signal type filter.",
    )
    trust_signals_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max trust signals (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    trust_signals_parser.set_defaults(handler=_run_trust_signals)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Show continuity evidence or temporal explain output.",
    )
    explain_parser.add_argument(
        "continuity_object_id",
        nargs="?",
        type=_parse_uuid,
        help="Continuity object UUID.",
    )
    explain_parser.add_argument("--entity-id", type=_parse_uuid, default=None, help="Entity UUID.")
    explain_parser.add_argument("--at", type=_parse_datetime, default=None, help="As-of time (ISO-8601).")
    explain_parser.set_defaults(handler=_run_explain)

    evidence_parser = subparsers.add_parser("evidence", help="Inspect archived continuity artifacts.")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_artifact_parser = evidence_subparsers.add_parser("artifact", help="Show one archived artifact.")
    evidence_artifact_parser.add_argument("artifact_id", type=_parse_uuid, help="Continuity artifact UUID.")
    evidence_artifact_parser.set_defaults(handler=_run_evidence_artifact)

    patterns_parser = subparsers.add_parser("patterns", help="List and explain trusted fact patterns.")
    patterns_subparsers = patterns_parser.add_subparsers(dest="patterns_command", required=True)
    patterns_list_parser = patterns_subparsers.add_parser("list", help="List trusted fact patterns.")
    patterns_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        help=f"Max pattern results (1-{MAX_TRUSTED_FACT_PROMOTION_LIMIT}).",
    )
    patterns_list_parser.set_defaults(handler=_run_pattern_list)
    patterns_explain_parser = patterns_subparsers.add_parser("explain", help="Explain one trusted fact pattern.")
    patterns_explain_parser.add_argument("pattern_id", type=_parse_uuid, help="Pattern UUID.")
    patterns_explain_parser.set_defaults(handler=_run_pattern_explain)

    playbooks_parser = subparsers.add_parser("playbooks", help="List and explain trusted fact playbooks.")
    playbooks_subparsers = playbooks_parser.add_subparsers(dest="playbooks_command", required=True)
    playbooks_list_parser = playbooks_subparsers.add_parser("list", help="List trusted fact playbooks.")
    playbooks_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        help=f"Max playbook results (1-{MAX_TRUSTED_FACT_PROMOTION_LIMIT}).",
    )
    playbooks_list_parser.set_defaults(handler=_run_playbook_list)
    playbooks_explain_parser = playbooks_subparsers.add_parser("explain", help="Explain one trusted fact playbook.")
    playbooks_explain_parser.add_argument("playbook_id", type=_parse_uuid, help="Playbook UUID.")
    playbooks_explain_parser.set_defaults(handler=_run_playbook_explain)

    status_parser = subparsers.add_parser("status", help="Show local continuity runtime status.")
    status_parser.set_defaults(handler=_run_status)

    vnext_eval_parser = subparsers.add_parser("eval", help="Run Alice vNext synthetic evals.")
    vnext_eval_subparsers = vnext_eval_parser.add_subparsers(dest="eval_command", required=True)

    vnext_eval_seed_parser = vnext_eval_subparsers.add_parser(
        "seed",
        help="Write the deterministic vNext synthetic benchmark corpus.",
    )
    vnext_eval_seed_parser.add_argument(
        "--output-path",
        default=None,
        help="Optional output path for the benchmark corpus JSON.",
    )
    vnext_eval_seed_parser.set_defaults(handler=_run_vnext_eval_seed)

    vnext_eval_run_parser = vnext_eval_subparsers.add_parser(
        "run",
        help="Run vNext eval suites against the synthetic corpus.",
    )
    vnext_eval_run_parser.add_argument(
        "--suite",
        default="all",
        help="Suite key to run: all, recall, temporal, contradictions, privacy, provenance, open_loops, or prompt_injection.",
    )
    vnext_eval_run_parser.add_argument(
        "--corpus-path",
        default=None,
        help="Optional benchmark corpus JSON path. Defaults to generated in-memory corpus when absent.",
    )
    vnext_eval_run_parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for the vNext eval report JSON.",
    )
    vnext_eval_run_parser.set_defaults(handler=_run_vnext_eval_run)

    vnext_eval_report_parser = vnext_eval_subparsers.add_parser(
        "report",
        help="Run vNext evals and write a canonical report artifact.",
    )
    vnext_eval_report_parser.add_argument(
        "--suite",
        default="all",
        help="Suite key to report: all, recall, temporal, contradictions, privacy, provenance, open_loops, or prompt_injection.",
    )
    vnext_eval_report_parser.add_argument(
        "--corpus-path",
        default=None,
        help="Optional benchmark corpus JSON path. Defaults to generated in-memory corpus when absent.",
    )
    vnext_eval_report_parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for the vNext eval report JSON.",
    )
    vnext_eval_report_parser.set_defaults(handler=_run_vnext_eval_report)

    evals_parser = subparsers.add_parser("evals", help="Run and inspect public eval suites.")
    evals_subparsers = evals_parser.add_subparsers(dest="evals_command", required=True)

    evals_suites_parser = evals_subparsers.add_parser("suites", help="List public eval suites.")
    evals_suites_parser.set_defaults(handler=_run_eval_suites)

    evals_run_parser = evals_subparsers.add_parser("run", help="Run the public eval harness.")
    evals_run_parser.add_argument(
        "--suite-key",
        action="append",
        default=None,
        help="Optional suite key filter. Repeat to run multiple suites.",
    )
    evals_run_parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for the canonical JSON report artifact.",
    )
    evals_run_parser.set_defaults(handler=_run_eval_run)

    evals_runs_parser = evals_subparsers.add_parser("runs", help="List persisted public eval runs.")
    evals_runs_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of eval runs to list.",
    )
    evals_runs_parser.set_defaults(handler=_run_eval_runs)

    evals_show_parser = evals_subparsers.add_parser("show", help="Show one persisted public eval run.")
    evals_show_parser.add_argument("eval_run_id", type=_parse_uuid, help="Eval run UUID.")
    evals_show_parser.set_defaults(handler=_run_eval_show)

    return parser


def _validate_limit(value: int, *, option_name: str, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{option_name} must be between {minimum} and {maximum}")


def _validate_arguments(args: argparse.Namespace) -> None:
    if args.command == "mutations" and args.mutations_command in {"candidates", "operations"}:
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=100,
        )
    elif args.command == "recall":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_RECALL_LIMIT,
        )
    elif args.command == "context-pack":
        _validate_limit(
            args.max_items,
            option_name="--max-items",
            minimum=1,
            maximum=50,
        )
        _validate_limit(
            args.max_tokens,
            option_name="--max-tokens",
            minimum=500,
            maximum=50_000,
        )
    elif args.command == "contradictions" and args.contradictions_command in {"detect", "list"}:
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "trust" and args.trust_command == "signals":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "evals" and args.evals_command == "runs":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=100,
        )
    elif args.command == "timeline":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
        )
    elif args.command == "brief":
        _validate_limit(
            args.max_relevant_facts,
            option_name="--max-relevant-facts",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        )
        _validate_limit(
            args.max_recent_changes,
            option_name="--max-recent-changes",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        )
        _validate_limit(
            args.max_open_loops,
            option_name="--max-open-loops",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        )
        _validate_limit(
            args.max_conflicts,
            option_name="--max-conflicts",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        )
        _validate_limit(
            args.max_timeline_highlights,
            option_name="--max-timeline-highlights",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        )
    elif args.command == "lifecycle" and args.lifecycle_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_LIFECYCLE_LIMIT,
        )
    elif args.command == "resume":
        _validate_limit(
            args.max_recent_changes,
            option_name="--max-recent-changes",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        )
        _validate_limit(
            args.max_open_loops,
            option_name="--max-open-loops",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        )
    elif args.command == "task-briefs" and args.task_briefs_command in {"compile", "compare"}:
        if args.token_budget is not None:
            _validate_limit(
                args.token_budget,
                option_name="--token-budget",
                minimum=1,
                maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
            )
        if args.task_briefs_command == "compare" and args.compare_token_budget is not None:
            _validate_limit(
                args.compare_token_budget,
                option_name="--compare-token-budget",
                minimum=1,
                maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
            )
    elif args.command == "open-loops":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=0,
            maximum=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
        )
    elif args.command == "review" and args.review_command == "queue":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "patterns" and args.patterns_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
        )
    elif args.command == "playbooks" and args.playbooks_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_arguments(args)
        ctx = _build_context(args)
        handler = args.handler
        output = handler(ctx, args)
    except (
        ValueError,
        PermissionError,
        psycopg.Error,
        ContinuityCaptureValidationError,
        VNextCaptureValidationError,
        VNextBrainValidationError,
        VNextConnectionValidationError,
        VNextConnectorValidationError,
        VNextContradictionValidationError,
        VNextProjectValidationError,
        VNextQueueValidationError,
        VNextRetrievalValidationError,
        VNextSchedulerValidationError,
        ContinuityLifecycleValidationError,
        ContinuityLifecycleNotFoundError,
        ContinuityRecallValidationError,
        ContinuityBriefValidationError,
        ContinuityResumptionValidationError,
        ContinuityOpenLoopValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityContradictionValidationError,
        ContinuityContradictionNotFoundError,
        ContinuityEvidenceNotFoundError,
        MemoryMutationValidationError,
        TaskBriefNotFoundError,
        TaskBriefValidationError,
        TemporalStateValidationError,
        TrustedFactPromotionNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


__all__ = ["build_parser", "main"]
