from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime
import hmac
import hashlib
import ipaddress
import json
import logging
import re
import threading
import time
from typing import Annotated, Awaitable, Callable, Literal, TypedDict
from uuid import UUID, uuid4
from fastapi import FastAPI, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi.responses import JSONResponse
import psycopg
from psycopg.rows import dict_row
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
try:
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - optional dependency for local-only test environments
    redis = None

    class RedisError(Exception):
        """Fallback Redis error used when redis package is unavailable."""

from alicebot_api.compiler import compile_and_persist_trace, compile_resumption_brief
from alicebot_api.config import Settings, get_settings
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError,
    compile_continuity_brief,
)
from alicebot_api.contracts import (
    AGENT_PROFILE_LIST_ORDER,
    ApprovalApproveInput,
    ApprovalRejectInput,
    ApprovalRequestCreateInput,
    AgentProfileListResponse,
    AgentProfileListSummary,
    ArtifactScopedSemanticArtifactChunkRetrievalInput,
    CompileContextArtifactScopedSemanticArtifactRetrievalInput,
    CompileContextArtifactScopedArtifactRetrievalInput,
    CompileContextSemanticArtifactRetrievalInput,
    CompileContextTaskScopedArtifactRetrievalInput,
    CompileContextTaskScopedSemanticArtifactRetrievalInput,
    ConsentStatus,
    ConsentUpsertInput,
    CompileContextSemanticRetrievalInput,
    DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    DEFAULT_AGENT_PROFILE_ID,
    DEFAULT_CALENDAR_EVENT_LIST_LIMIT,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
    DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_ENTITY_EDGES,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_MEMORIES,
    DEFAULT_MEMORY_REVIEW_LIMIT,
    DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE,
    DEFAULT_OPEN_LOOP_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    MAX_MEMORY_REVIEW_LIMIT,
    MAX_OPEN_LOOP_LIMIT,
    MAX_RESUMPTION_BRIEF_EVENT_LIMIT,
    MAX_RESUMPTION_BRIEF_MEMORY_LIMIT,
    MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    MAX_CALENDAR_EVENT_LIST_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_CAPTURE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_RETRIEVAL_RUN_LIST_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    ContextCompilerLimits,
    ContinuityArtifactDetailResponse,
    ContinuityBriefRequestInput,
    ContinuityBriefResponse,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    ContinuityCaptureCreateInput,
    ContradictionCaseDetailResponse,
    ContradictionCaseListQueryInput,
    ContradictionCaseListResponse,
    ContradictionResolveInput,
    ContradictionResolveResponse,
    ContradictionSyncInput,
    ContradictionSyncResponse,
    ContinuityExplainResponse,
    ContinuityLifecycleDetailResponse,
    ContinuityLifecycleListResponse,
    ContinuityLifecycleQueryInput,
    ContinuityDailyBriefRequestInput,
    ContinuityDailyBriefResponse,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopDashboardResponse,
    ContinuityOpenLoopReviewActionInput,
    ContinuityOpenLoopReviewActionResponse,
    ContinuityCorrectionInput,
    ContinuityRecallQueryInput,
    ContinuityRecallResponse,
    ContinuityReviewDetailResponse,
    ContinuityReviewQueueQueryInput,
    ContinuityReviewQueueResponse,
    ContinuityResumptionBriefRequestInput,
    ContinuityResumptionBriefResponse,
    TaskBriefComparisonRequestInput,
    TaskBriefComparisonResponse,
    TaskBriefCompileRequestInput,
    TaskBriefResponse,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TemporalExplainQueryInput,
    TemporalExplainResponse,
    TemporalStateAtQueryInput,
    TemporalStateAtResponse,
    TemporalTimelineQueryInput,
    TemporalTimelineResponse,
    TrustedFactPatternExplainResponse,
    TrustedFactPatternListQueryInput,
    TrustedFactPatternListResponse,
    TrustedFactPlaybookExplainResponse,
    TrustedFactPlaybookListQueryInput,
    TrustedFactPlaybookListResponse,
    ChiefOfStaffPriorityBriefRequestInput,
    ChiefOfStaffPriorityBriefResponse,
    ChiefOfStaffExecutionRoutingActionInput,
    ChiefOfStaffExecutionRoutingActionCaptureResponse,
    ChiefOfStaffHandoffOutcomeCaptureInput,
    ChiefOfStaffHandoffOutcomeCaptureResponse,
    ChiefOfStaffHandoffReviewActionInput,
    ChiefOfStaffHandoffReviewActionCaptureResponse,
    ChiefOfStaffRecommendationOutcomeCaptureInput,
    ChiefOfStaffRecommendationOutcomeCaptureResponse,
    ContinuityWeeklyReviewRequestInput,
    ContinuityWeeklyReviewResponse,
    MemoryHygieneDashboardResponse,
    MemoryTrustDashboardResponse,
    RetrievalEvaluationResponse,
    RetrievalRunListResponse,
    RetrievalTraceResponse,
    ThreadHealthDashboardResponse,
    TrustSignalListQueryInput,
    TrustSignalListResponse,
    EmbeddingConfigStatus,
    EmbeddingConfigCreateInput,
    ExecutionBudgetCreateInput,
    ExecutionBudgetDeactivateInput,
    ExecutionBudgetSupersedeInput,
    EntityEdgeCreateInput,
    EntityCreateInput,
    EntityType,
    ExplicitCommitmentExtractionRequestInput,
    ExplicitPreferenceExtractionRequestInput,
    ExplicitSignalCaptureRequestInput,
    CALENDAR_READONLY_SCOPE,
    GMAIL_READONLY_SCOPE,
    CalendarAccountConnectInput,
    CalendarEventListInput,
    CalendarEventIngestInput,
    GmailAccountConnectInput,
    GmailMessageIngestInput,
    MemoryCandidateInput,
    ModelInvocationRequest,
    ModelInvocationResponse,
    OpenLoopCandidateInput,
    MemoryEmbeddingUpsertInput,
    THREAD_EVENT_LIST_ORDER,
    PROVIDER_LIST_ORDER,
    MODEL_PACK_LIST_ORDER,
    THREAD_LIST_ORDER,
    THREAD_SESSION_LIST_ORDER,
    MemoryReviewLabelValue,
    MemoryReviewQueuePriorityMode,
    MemoryReviewStatusFilter,
    OpenLoopStatusFilter,
    OpenLoopCreateInput,
    OpenLoopStatusUpdateInput,
    PolicyCreateInput,
    PolicyEffect,
    PolicyEvaluationRequestInput,
    SemanticMemoryRetrievalRequestInput,
    TaskArtifactChunkEmbeddingUpsertInput,
    TOOL_METADATA_VERSION_V0,
    ApprovalStatus,
    ArtifactScopedArtifactChunkRetrievalInput,
    ProxyExecutionStatus,
    ToolAllowlistEvaluationRequestInput,
    ProxyExecutionRequestInput,
    PublicEvalRunDetailResponse,
    PublicEvalRunListResponse,
    PublicEvalSuiteDefinitionListResponse,
    TaskArtifactIngestInput,
    TaskArtifactRegisterInput,
    TaskScopedSemanticArtifactChunkRetrievalInput,
    TaskScopedArtifactChunkRetrievalInput,
    TaskStepKind,
    TaskStepLineageInput,
    TaskStepNextCreateInput,
    TaskStepStatus,
    TaskStepTransitionInput,
    TaskRunCancelInput,
    TaskRunCreateInput,
    TaskRunPauseInput,
    TaskRunResumeInput,
    TaskRunTickInput,
    TaskWorkspaceCreateInput,
    ToolRoutingDecision,
    ToolRoutingRequestInput,
    ToolCreateInput,
    ThreadCreateInput,
    ThreadCreateResponse,
    ThreadDetailResponse,
    ThreadEventListResponse,
    ThreadEventListSummary,
    ThreadEventRecord,
    ThreadListResponse,
    ThreadListSummary,
    ThreadRecord,
    ResumptionBriefRequestInput,
    ResumptionBriefResponse,
    ThreadSessionListResponse,
    ThreadSessionListSummary,
    ThreadSessionRecord,
)
from alicebot_api.phase3_profiles import (
    get_agent_profile as get_registered_agent_profile,
    list_agent_profile_ids as list_registered_agent_profile_ids,
    list_agent_profiles as list_registered_agent_profiles,
)
from alicebot_api.artifacts import (
    TaskArtifactAlreadyExistsError,
    TaskArtifactChunkRetrievalValidationError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
    get_task_artifact_record,
    ingest_task_artifact_record,
    list_task_artifact_chunk_records,
    list_task_artifact_records,
    register_task_artifact_record,
    retrieve_artifact_scoped_artifact_chunk_records,
    retrieve_task_scoped_artifact_chunk_records,
)
from alicebot_api.approvals import (
    ApprovalNotFoundError,
    ApprovalResolutionConflictError,
    approve_approval_record,
    get_approval_record,
    list_approval_records,
    reject_approval_record,
    submit_approval_request,
)
from alicebot_api.db import (
    ping_database,
    set_current_user_account,
    set_hosted_admin_bypass,
    set_hosted_service_bypass,
    user_connection,
)
from alicebot_api.executions import (
    ToolExecutionNotFoundError,
    get_tool_execution_record,
    list_tool_execution_records,
)
from alicebot_api.tasks import (
    TaskNotFoundError,
    TaskStepApprovalLinkageError,
    TaskStepExecutionLinkageError,
    TaskStepLifecycleBoundaryError,
    TaskStepSequenceError,
    TaskStepNotFoundError,
    TaskStepTransitionError,
    create_next_task_step_record,
    get_task_record,
    get_task_step_record,
    list_task_records,
    list_task_step_records,
    transition_task_step_record,
)
from alicebot_api.task_runs import (
    TaskRunNotFoundError,
    TaskRunTransitionError,
    TaskRunValidationError,
    cancel_task_run_record,
    create_task_run_record,
    get_task_run_record,
    list_task_run_records,
    pause_task_run_record,
    resume_task_run_record,
    tick_task_run_record,
)
from alicebot_api.workspaces import (
    TaskWorkspaceAlreadyExistsError,
    TaskWorkspaceNotFoundError,
    TaskWorkspaceProvisioningError,
    create_task_workspace_record,
    get_task_workspace_record,
    list_task_workspace_records,
)
from alicebot_api.execution_budgets import (
    ExecutionBudgetLifecycleError,
    ExecutionBudgetNotFoundError,
    ExecutionBudgetValidationError,
    create_execution_budget_record,
    deactivate_execution_budget_record,
    get_execution_budget_record,
    list_execution_budget_records,
    supersede_execution_budget_record,
)
from alicebot_api.gmail import (
    GmailAccountAlreadyExistsError,
    GmailCredentialInvalidError,
    GmailCredentialNotFoundError,
    GmailCredentialPersistenceError,
    GmailCredentialRefreshError,
    GmailCredentialValidationError,
    GmailAccountNotFoundError,
    GmailMessageFetchError,
    GmailMessageNotFoundError,
    GmailMessageUnsupportedError,
    create_gmail_account_record,
    get_gmail_account_record,
    ingest_gmail_message_record,
    list_gmail_account_records,
)
from alicebot_api.calendar import (
    CalendarAccountAlreadyExistsError,
    CalendarAccountNotFoundError,
    CalendarCredentialInvalidError,
    CalendarCredentialNotFoundError,
    CalendarCredentialPersistenceError,
    CalendarCredentialValidationError,
    CalendarEventFetchError,
    CalendarEventListValidationError,
    CalendarEventNotFoundError,
    CalendarEventUnsupportedError,
    create_calendar_account_record,
    get_calendar_account_record,
    ingest_calendar_event_record,
    list_calendar_account_records,
    list_calendar_event_records,
)
from alicebot_api.calendar_secret_manager import build_calendar_secret_manager
from alicebot_api.gmail_secret_manager import build_gmail_secret_manager
from alicebot_api.embedding import (
    EmbeddingConfigValidationError,
    MemoryEmbeddingNotFoundError,
    MemoryEmbeddingValidationError,
    TaskArtifactChunkEmbeddingNotFoundError,
    TaskArtifactChunkEmbeddingValidationError,
    create_embedding_config_record,
    get_memory_embedding_record,
    get_task_artifact_chunk_embedding_record,
    list_embedding_config_records,
    list_memory_embedding_records,
    list_task_artifact_chunk_embedding_records_for_artifact,
    list_task_artifact_chunk_embedding_records_for_chunk,
    upsert_task_artifact_chunk_embedding_record,
    upsert_memory_embedding_record,
)
from alicebot_api.entity import (
    EntityNotFoundError,
    EntityValidationError,
    create_entity_record,
    get_entity_record,
    list_entity_records,
)
from alicebot_api.entity_edge import (
    EntityEdgeValidationError,
    create_entity_edge_record,
    list_entity_edge_records,
)
from alicebot_api.explicit_preferences import (
    ExplicitPreferenceExtractionValidationError,
    extract_and_admit_explicit_preferences,
)
from alicebot_api.explicit_commitments import (
    ExplicitCommitmentExtractionValidationError,
    extract_and_admit_explicit_commitments,
)
from alicebot_api.explicit_signal_capture import (
    ExplicitSignalCaptureValidationError,
    extract_and_admit_explicit_signals,
)
from alicebot_api.continuity_capture import (
    ContinuityCaptureNotFoundError,
    ContinuityCaptureValidationError,
    capture_continuity_candidates,
    capture_continuity_input,
    commit_continuity_captures,
    get_continuity_capture_detail,
    list_continuity_capture_inbox,
)
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError,
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.temporal_state import (
    TemporalStateNotFoundError,
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
    AgentIdentityValidationError,
    AgentPolicyBlockedError,
    PolicyDecision,
    agent_metadata,
    append_policy_events,
    evaluate_agent_policy,
    summarize_agent_policy_telemetry,
)
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService, VNextBrainValidationError
from alicebot_api.vnext_capture import VNextCaptureService, VNextCaptureValidationError
from alicebot_api.vnext_connections import (
    ConnectionFinderRequest,
    VNextConnectionService,
    VNextConnectionValidationError,
)
from alicebot_api.vnext_connectors import (
    VNextConnectorService,
    VNextConnectorValidationError,
    list_connector_definitions,
)
from alicebot_api.vnext_contradictions import (
    ContradictionFinderRequest,
    VNextContradictionService,
    VNextContradictionValidationError,
)
from alicebot_api.vnext_dogfooding import VNextDogfoodingService
from alicebot_api.vnext_doctor import VNextDoctorService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
    memory_commit_request_from_payload,
)
from alicebot_api.vnext_projects import ProjectAutomationRequest, VNextProjectService, VNextProjectValidationError
from alicebot_api.vnext_queue import (
    QueueTaskRequest,
    VNextQueueNotFoundError,
    VNextQueueService,
    VNextQueueValidationError,
)
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService, VNextRetrievalValidationError
from alicebot_api.vnext_scheduler import (
    SchedulerRunRequest,
    VNextSchedulerService,
    VNextSchedulerValidationError,
    WORKFLOW_TYPES,
    default_schedule,
    validate_schedule,
)
from alicebot_api.vnext_scheduler_runtime import daemon_status
from alicebot_api.vnext_store import PostgresVNextStore
from alicebot_api.continuity_lifecycle import (
    ContinuityLifecycleNotFoundError,
    ContinuityLifecycleValidationError,
    get_continuity_lifecycle_state,
    list_continuity_lifecycle_state,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    RetrievalTraceNotFoundError,
    get_retrieval_trace,
    list_retrieval_runs,
    query_continuity_recall,
)
from alicebot_api.public_evals import (
    get_public_eval_run,
    list_public_eval_runs,
    list_public_eval_suites,
    run_public_evals,
)
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.hosted_auth import (
    AuthSessionExpiredError,
    AuthSessionInvalidError,
    AuthSessionRevokedDeviceError,
    MagicLinkTokenExpiredError,
    MagicLinkTokenInvalidError,
    ensure_user_preferences_row,
    list_feature_flags_for_user,
    logout_auth_session,
    resolve_auth_session,
    serialize_auth_session,
    serialize_magic_link_challenge,
    serialize_user_account,
    start_magic_link_challenge,
    verify_magic_link_challenge,
)
from alicebot_api.hosted_devices import (
    DeviceLinkTokenExpiredError,
    DeviceLinkTokenInvalidError,
    HostedDeviceNotFoundError,
    confirm_device_link_challenge,
    list_devices as list_hosted_devices,
    revoke_device as revoke_hosted_device,
    serialize_device,
    serialize_device_link_challenge,
    start_device_link_challenge,
)
from alicebot_api.hosted_preferences import (
    HostedPreferencesValidationError,
    ensure_user_preferences,
    patch_user_preferences,
    serialize_user_preferences,
)
from alicebot_api.hosted_workspace import (
    HostedWorkspaceBootstrapConflictError,
    HostedWorkspaceNotFoundError,
    complete_workspace_bootstrap,
    create_workspace,
    get_bootstrap_status,
    get_current_workspace,
    get_workspace_for_member,
    serialize_workspace,
    set_session_workspace,
)
from alicebot_api.hosted_rollout import (
    list_rollout_flags_for_admin,
    patch_rollout_flags,
    resolve_rollout_flag,
)
from alicebot_api.hosted_telemetry import (
    aggregate_chat_telemetry,
    record_chat_telemetry,
)
from alicebot_api.hosted_rate_limits import evaluate_hosted_flow_limits
from alicebot_api.hosted_admin import (
    get_hosted_overview_for_admin,
    get_hosted_rate_limits_for_admin,
    list_hosted_delivery_receipts_for_admin,
    list_hosted_incidents_for_admin,
    list_hosted_workspaces_for_admin,
)
from alicebot_api.design_partners import (
    DesignPartnerFeedbackValidationError,
    DesignPartnerNotFoundError,
    DesignPartnerWorkspaceConflictError,
    create_design_partner,
    get_design_partner_dashboard,
    get_design_partner_detail,
    link_design_partner_workspace,
    list_design_partners,
    record_design_partner_feedback,
    update_design_partner,
)
from alicebot_api.telegram_channels import (
    TelegramIdentityNotFoundError,
    TelegramLinkPendingError,
    TelegramLinkTokenExpiredError,
    TelegramLinkTokenInvalidError,
    TelegramMessageNotFoundError,
    TelegramRoutingError,
    TelegramWebhookValidationError,
    confirm_telegram_link_challenge,
    dispatch_telegram_message,
    get_telegram_link_status,
    ingest_telegram_webhook,
    list_workspace_telegram_delivery_receipts,
    list_workspace_telegram_messages,
    list_workspace_telegram_threads,
    serialize_channel_identity,
    serialize_channel_link_challenge,
    serialize_channel_message,
    serialize_channel_thread,
    serialize_delivery_receipt,
    serialize_webhook_ingest_result,
    start_telegram_link_challenge,
    unlink_telegram_identity,
)
from alicebot_api.telegram_continuity import (
    HostedUserAccountNotFoundError,
    TelegramMessageResultNotFoundError,
    apply_telegram_open_loop_review_with_log,
    approve_telegram_approval,
    get_telegram_message_result,
    handle_telegram_message,
    list_telegram_approvals,
    prepare_telegram_continuity_context,
    reject_telegram_approval,
)
from alicebot_api.telegram_notifications import (
    TelegramNotificationPreferenceValidationError,
    TelegramOpenLoopPromptNotFoundError,
    deliver_workspace_daily_brief,
    deliver_workspace_open_loop_prompt,
    get_workspace_daily_brief_preview,
    get_workspace_notification_preferences,
    list_workspace_open_loop_prompts,
    list_workspace_scheduler_jobs,
    patch_workspace_notification_subscription,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.chief_of_staff import (
    ChiefOfStaffValidationError,
    capture_chief_of_staff_execution_routing_action,
    capture_chief_of_staff_handoff_outcome,
    capture_chief_of_staff_handoff_review_action,
    capture_chief_of_staff_recommendation_outcome,
    compile_chief_of_staff_priority_brief,
)
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopNotFoundError,
    ContinuityOpenLoopValidationError,
    apply_continuity_open_loop_review_action,
    compile_continuity_daily_brief,
    compile_continuity_open_loop_dashboard,
    compile_continuity_weekly_review,
)
from alicebot_api.conversation_health import get_thread_health_dashboard
from alicebot_api.continuity_objects import ContinuityObjectValidationError
from alicebot_api.memory import (
    MemoryAdmissionValidationError,
    MemoryReviewNotFoundError,
    OpenLoopNotFoundError,
    OpenLoopValidationError,
    admit_memory_candidate,
    create_open_loop_record,
    create_memory_review_label_record,
    get_open_loop_record,
    get_memory_evaluation_summary,
    get_memory_hygiene_dashboard_summary,
    get_memory_quality_gate_summary,
    get_memory_trust_dashboard_summary,
    get_memory_review_record,
    list_open_loop_records,
    list_memory_review_queue_records,
    list_memory_review_label_records,
    list_memory_review_records,
    list_memory_revision_review_records,
    update_open_loop_status_record,
)
from alicebot_api.policy import (
    PolicyEvaluationValidationError,
    PolicyNotFoundError,
    PolicyValidationError,
    create_policy_record,
    evaluate_policy_request,
    get_policy_record,
    list_consent_records,
    list_policy_records,
    upsert_consent_record,
)
from alicebot_api.tools import (
    ToolAllowlistValidationError,
    ToolNotFoundError,
    ToolRoutingValidationError,
    ToolValidationError,
    create_tool_record,
    evaluate_tool_allowlist,
    get_tool_record,
    list_tool_records,
    route_tool_invocation,
)
from alicebot_api.semantic_retrieval import (
    SemanticArtifactChunkRetrievalValidationError,
    SemanticMemoryRetrievalValidationError,
    retrieve_artifact_scoped_semantic_artifact_chunk_records,
    retrieve_semantic_memory_records,
    retrieve_task_scoped_semantic_artifact_chunk_records,
)
from alicebot_api.response_generation import (
    DEVELOPER_INSTRUCTION,
    ModelInvocationError,
    ResponseFailure,
    SYSTEM_INSTRUCTION,
    generate_response,
)
from alicebot_api.proxy_execution import (
    ProxyExecutionApprovalStateError,
    ProxyExecutionHandlerNotFoundError,
    ProxyExecutionIdempotencyError,
    execute_approved_proxy_request,
)
from alicebot_api.azure_provider_helpers import (
    AZURE_AUTH_MODE_AD_TOKEN,
    AZURE_AUTH_MODE_API_KEY,
    DEFAULT_AZURE_API_VERSION,
)
from alicebot_api.provider_runtime import (
    AZURE_ADAPTER_KEY,
    LLAMACPP_ADAPTER_KEY,
    OLLAMA_ADAPTER_KEY,
    OPENAI_COMPATIBLE_ADAPTER_KEY,
    VLLM_ADAPTER_KEY,
    OPENAI_RESPONSES_PROVIDER,
    ProviderAdapter,
    ProviderAdapterNotFoundError,
    RuntimeProviderConfig,
    build_provider_test_model_request,
    make_provider_adapter_registry,
    normalized_capability_snapshot,
    resolve_runtime_provider_config_secrets,
)
from alicebot_api.model_packs import (
    MODEL_PACK_BINDING_SOURCE_MANUAL,
    MODEL_PACK_STATUS_ACTIVE,
    ModelPackCompatibilityError,
    ModelPackNotFoundError,
    ModelPackValidationError,
    append_instruction,
    apply_runtime_limit_caps,
    assert_model_pack_runtime_compatibility,
    build_model_pack_runtime_shape,
    ensure_tier1_model_packs_for_workspace,
    is_reserved_tier1_pack_key,
    normalize_briefing_max_tokens,
    normalize_briefing_strategy,
    normalize_model_pack_contract,
    normalize_pack_family,
    normalize_pack_id,
    normalize_pack_version,
    resolve_workspace_model_pack_selection,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.provider_secrets import (
    ProviderSecretManagerError,
    build_provider_secret_ref,
    encode_provider_secret_ref,
    write_provider_api_key,
)
from alicebot_api.provider_security import (
    sanitize_provider_error_message,
    validate_provider_base_url,
)
from alicebot_api.store import (
    ContinuityStore,
    ContinuityStoreInvariantError,
    EventRow,
    ModelPackRow,
    ModelProviderRow,
    ProviderCapabilityRow,
    SessionRow,
    ThreadRow,
    WorkspaceModelPackBindingDetailRow,
)
from alicebot_api.traces import (
    TraceNotFoundError,
    get_trace_record,
    list_trace_event_records,
    list_trace_records,
)

LOGGER = logging.getLogger(__name__)


app = FastAPI(title="AliceBot API", version="0.5.1")
provider_adapter_registry = make_provider_adapter_registry()
HealthStatus = Literal["ok", "degraded"]
ServiceStatus = Literal["ok", "unreachable", "not_checked"]


class DatabaseServicePayload(TypedDict):
    status: Literal["ok", "unreachable"]


class RedisServicePayload(TypedDict):
    status: Literal["not_checked"]
    url: str


class ObjectStorageServicePayload(TypedDict):
    status: Literal["not_checked"]
    endpoint_url: str


class HealthServicesPayload(TypedDict):
    database: DatabaseServicePayload
    redis: RedisServicePayload
    object_storage: ObjectStorageServicePayload


class HealthcheckPayload(TypedDict):
    status: HealthStatus
    environment: str
    services: HealthServicesPayload


AUTH_USER_HEADER = "X-AliceBot-User-Id"


class ResponseRateLimiter:
    def __init__(self) -> None:
        self._events_by_key: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, *, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()

        with self._lock:
            events = self._events_by_key[key]
            cutoff = now - window_seconds
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= max_requests:
                retry_after_seconds = max(1, int(events[0] + window_seconds - now))
                return False, retry_after_seconds

            events.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events_by_key.clear()


response_rate_limiter = ResponseRateLimiter()


class EntrypointRateLimiterUnavailableError(RuntimeError):
    """Raised when the configured entrypoint rate limiter backend is unavailable."""


class EntrypointRateLimiter:
    def __init__(self) -> None:
        self._memory_fallback = ResponseRateLimiter()
        self._redis_clients_by_url: dict[str, object] = {}
        self._lock = threading.Lock()

    def _get_redis_client(self, redis_url: str):
        with self._lock:
            cached_client = self._redis_clients_by_url.get(redis_url)
            if cached_client is not None:
                return cached_client

            if redis is None:
                raise EntrypointRateLimiterUnavailableError(
                    "redis backend is unavailable; install redis client dependency"
                )

            redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            self._redis_clients_by_url[redis_url] = redis_client
            return redis_client

    def allow(
        self,
        *,
        settings: Settings,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        if settings.entrypoint_rate_limit_backend == "memory":
            return self._memory_fallback.allow(
                key=key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

        try:
            redis_client = self._get_redis_client(settings.redis_url)
            redis_key = f"entrypoint_rate:{key}"
            count = int(redis_client.incr(redis_key))
            ttl = int(redis_client.ttl(redis_key))

            if count == 1 or ttl <= 0:
                redis_client.expire(redis_key, window_seconds)
                ttl = window_seconds

            if count > max_requests:
                return False, max(1, ttl if ttl > 0 else window_seconds)
            return True, 0
        except (RedisError, EntrypointRateLimiterUnavailableError) as exc:
            # Local and test workflows can continue deterministically with in-memory fallback.
            if settings.app_env in {"development", "test"}:
                return self._memory_fallback.allow(
                    key=key,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                )
            raise EntrypointRateLimiterUnavailableError(
                "redis-backed entrypoint rate limiter is unavailable"
            ) from exc

    def reset(self) -> None:
        self._memory_fallback.reset()
        with self._lock:
            self._redis_clients_by_url.clear()


entrypoint_rate_limiter = EntrypointRateLimiter()


def _resolve_authenticated_user_id(settings: Settings, request: Request) -> UUID | None:
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)

    header_value = request.headers.get(AUTH_USER_HEADER)
    if header_value is None or header_value.strip() == "":
        if settings.app_env in {"development", "test"}:
            return None
        raise ValueError(
            "request authentication is not configured; set ALICEBOT_AUTH_USER_ID "
            "or provide X-AliceBot-User-Id"
        )

    try:
        return UUID(header_value)
    except ValueError as exc:
        raise ValueError("X-AliceBot-User-Id must be a valid UUID") from exc


def _rewrite_user_id_query_param(request: Request, authenticated_user_id: UUID) -> None:
    raw_query = request.scope.get("query_string", b"")
    query_items = parse_qsl(raw_query.decode("utf-8"), keep_blank_values=True)
    expected_user_id = str(authenticated_user_id)
    for key, value in query_items:
        if key == "user_id" and value != expected_user_id:
            raise ValueError("query user_id does not match authenticated user")
    rewritten_items = [(key, value) for key, value in query_items if key != "user_id"]
    rewritten_items.append(("user_id", expected_user_id))
    request.scope["query_string"] = urlencode(rewritten_items, doseq=True).encode("utf-8")


async def _rewrite_user_id_json_body(request: Request, authenticated_user_id: UUID) -> Request:
    if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return request

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return request

    raw_body = await request.body()
    if raw_body == b"":
        return request

    try:
        parsed_body = json.loads(raw_body)
    except json.JSONDecodeError:
        return request

    if not isinstance(parsed_body, dict):
        return request

    expected_user_id = str(authenticated_user_id)
    existing_user_id = parsed_body.get("user_id")
    if existing_user_id is not None and str(existing_user_id) != expected_user_id:
        raise ValueError("request user_id does not match authenticated user")
    parsed_body["user_id"] = expected_user_id
    rewritten_body = json.dumps(parsed_body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    async def receive() -> dict[str, object]:
        return {
            "type": "http.request",
            "body": rewritten_body,
            "more_body": False,
        }

    return Request(request.scope, receive)


class CompileContextSemanticRequest(BaseModel):
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    )


class CompileContextTaskScopedArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["task"]
    task_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class CompileContextArtifactScopedArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"]
    task_artifact_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


CompileContextArtifactRetrievalRequest = Annotated[
    CompileContextTaskScopedArtifactRetrievalRequest
    | CompileContextArtifactScopedArtifactRetrievalRequest,
    Field(discriminator="kind"),
]


class CompileContextTaskScopedSemanticArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["task"]
    task_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class CompileContextArtifactScopedSemanticArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"]
    task_artifact_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


CompileContextSemanticArtifactRetrievalRequest = Annotated[
    CompileContextTaskScopedSemanticArtifactRetrievalRequest
    | CompileContextArtifactScopedSemanticArtifactRetrievalRequest,
    Field(discriminator="kind"),
]


class CompileContextRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    max_sessions: int = Field(default=DEFAULT_MAX_SESSIONS, ge=0, le=25)
    max_events: int = Field(default=DEFAULT_MAX_EVENTS, ge=0, le=200)
    max_memories: int = Field(default=DEFAULT_MAX_MEMORIES, ge=0, le=50)
    max_entities: int = Field(default=DEFAULT_MAX_ENTITIES, ge=0, le=50)
    max_entity_edges: int = Field(default=DEFAULT_MAX_ENTITY_EDGES, ge=0, le=100)
    semantic: CompileContextSemanticRequest | None = None
    artifact_retrieval: CompileContextArtifactRetrievalRequest | None = None
    semantic_artifact_retrieval: CompileContextSemanticArtifactRetrievalRequest | None = None


class GenerateResponseRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    message: str = Field(min_length=1, max_length=8000)
    max_sessions: int = Field(default=DEFAULT_MAX_SESSIONS, ge=0, le=25)
    max_events: int = Field(default=DEFAULT_MAX_EVENTS, ge=0, le=200)
    max_memories: int = Field(default=DEFAULT_MAX_MEMORIES, ge=0, le=50)
    max_entities: int = Field(default=DEFAULT_MAX_ENTITIES, ge=0, le=50)
    max_entity_edges: int = Field(default=DEFAULT_MAX_ENTITY_EDGES, ge=0, le=100)


class CreateThreadRequest(BaseModel):
    user_id: UUID
    title: str = Field(min_length=1, max_length=200)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)


class AdmitMemoryOpenLoopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=280)
    due_at: datetime | None = None


class AdmitMemoryRequest(BaseModel):
    user_id: UUID
    memory_key: str = Field(min_length=1, max_length=200)
    value: object | None = None
    source_event_ids: list[UUID] = Field(min_length=1)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)
    delete_requested: bool = False
    memory_type: str | None = Field(default=None, min_length=1, max_length=100)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    confirmation_status: str | None = Field(default=None, min_length=1, max_length=100)
    trust_class: str | None = Field(default=None, min_length=1, max_length=100)
    promotion_eligibility: str | None = Field(default=None, min_length=1, max_length=100)
    evidence_count: int | None = Field(default=None, ge=0)
    independent_source_count: int | None = Field(default=None, ge=0)
    extracted_by_model: str | None = Field(default=None, min_length=1, max_length=200)
    trust_reason: str | None = Field(default=None, min_length=1, max_length=500)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    last_confirmed_at: datetime | None = None
    open_loop: AdmitMemoryOpenLoopRequest | None = None

    @model_validator(mode="after")
    def validate_temporal_range(self) -> "AdmitMemoryRequest":
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be greater than or equal to valid_from")
        return self


class ExtractExplicitPreferencesRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class ExtractExplicitCommitmentsRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class CaptureExplicitSignalsRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class ContinuityCaptureRequest(BaseModel):
    user_id: UUID
    raw_content: str = Field(min_length=1, max_length=4000)
    explicit_signal: str | None = Field(default=None, min_length=1, max_length=100)


class VNextAgentIdentityRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    agent_type: str = Field(default="unknown", min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    permission_profile: str | None = Field(default=None, min_length=1, max_length=80)


class VNextAgentRequest(BaseModel):
    agent: VNextAgentIdentityRequest | None = None
    agent_identity: VNextAgentIdentityRequest | None = None
    agent_id: str | None = Field(default=None, min_length=1, max_length=120)
    agent_type: str | None = Field(default=None, min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    permission_profile: str | None = Field(default=None, min_length=1, max_length=80)
    trace_id: str | None = Field(default=None, min_length=1, max_length=160)


class VNextSourceCaptureRequest(VNextAgentRequest):
    user_id: UUID
    raw_text: str = Field(min_length=1, max_length=200_000)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    domain: str = Field(default="unknown", min_length=1, max_length=80)
    sensitivity: str = Field(default="unknown", min_length=1, max_length=80)


class VNextSourceReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    domain: str | None = Field(default=None, min_length=1, max_length=80)
    sensitivity: str | None = Field(default=None, min_length=1, max_length=80)
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    review_note: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextConnectorSyncRequest(VNextAgentRequest):
    user_id: UUID
    items: list[dict[str, object]] = Field(default_factory=list)
    default_domain: str | None = Field(default=None, min_length=1, max_length=80)
    default_sensitivity: str | None = Field(default=None, min_length=1, max_length=80)


class VNextConnectorConfigRequest(VNextAgentRequest):
    user_id: UUID
    enabled: bool | None = None
    default_domain: str | None = Field(default=None, min_length=1, max_length=80)
    default_sensitivity: str | None = Field(default=None, min_length=1, max_length=80)
    secret_ref: str | None = Field(default=None, min_length=1, max_length=240)
    sync_mode: str | None = Field(default=None, min_length=1, max_length=40)
    poll_interval_seconds: int | None = Field(default=None, ge=1, le=86_400)
    config_json: dict[str, object] = Field(default_factory=dict)


class VNextTelegramSyncRequest(VNextAgentRequest):
    user_id: UUID
    updates: list[dict[str, object]] = Field(default_factory=list)
    allowed_chat_ids: list[str] = Field(default_factory=list)
    default_domain: str | None = Field(default=None, min_length=1, max_length=80)
    default_sensitivity: str | None = Field(default=None, min_length=1, max_length=80)


class VNextLocalFolderSyncRequest(VNextAgentRequest):
    user_id: UUID
    paths: list[str] = Field(default_factory=list)
    recursive: bool = True
    extensions: list[str] = Field(default_factory=lambda: [".md", ".txt"])
    ignore_patterns: list[str] = Field(default_factory=list)
    default_domain: str | None = Field(default=None, min_length=1, max_length=80)
    default_sensitivity: str | None = Field(default=None, min_length=1, max_length=80)


class VNextBrowserClipperCaptureRequest(VNextAgentRequest):
    user_id: UUID
    url: str = Field(min_length=1, max_length=4000)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    selected_text: str | None = Field(default=None, min_length=1, max_length=200_000)
    page_text: str | None = Field(default=None, min_length=1, max_length=500_000)
    user_note: str | None = Field(default=None, min_length=1, max_length=20_000)
    capture_token: str | None = Field(default=None, min_length=1, max_length=500)
    captured_at: str | None = Field(default=None, min_length=1, max_length=120)
    domain: str = Field(default="professional", min_length=1, max_length=80)
    sensitivity: str = Field(default="private", min_length=1, max_length=80)


class VNextAgentOutputIngestRequest(VNextAgentRequest):
    user_id: UUID
    agent_id: str = Field(min_length=1, max_length=160)
    agent_type: str = Field(default="unknown", min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=500_000)
    output_type: str = Field(default="general", min_length=1, max_length=80)
    domain: str = Field(default="project", min_length=1, max_length=80)
    sensitivity: str = Field(default="private", min_length=1, max_length=80)
    source_refs: list[object] = Field(default_factory=list)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    propose_memory: bool = False


class VNextArtifactInsightFeedbackRequest(VNextAgentRequest):
    user_id: UUID
    useful_insight: str = Field(min_length=1, max_length=20)
    surfaced_missed: str | None = Field(default=None, min_length=1, max_length=20)
    comments: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextContextPackRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextBrainArtifactGenerateRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextConnectionReportGenerateRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(default="", max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextContradictionReportGenerateRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(default="", max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextProjectAutomationRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextProjectCreateRequest(VNextAgentRequest):
    user_id: UUID
    name: str = Field(min_length=1, max_length=280)
    slug: str | None = Field(default=None, min_length=1, max_length=280)
    status: str = Field(default="active", min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    current_state: str | None = Field(default=None, min_length=1, max_length=4000)
    domain: str = Field(default="project", min_length=1, max_length=80)
    sensitivity: str = Field(default="private", min_length=1, max_length=80)


class VNextProjectUpdateReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    edited_current_state: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextOpenLoopReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    due_at: str | None = Field(default=None, min_length=1, max_length=120)
    priority: str | None = Field(default=None, min_length=1, max_length=80)
    resolution_note: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextOpenLoopCreateRequest(VNextAgentRequest):
    user_id: UUID
    title: str = Field(min_length=1, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    due_at: str | None = Field(default=None, min_length=1, max_length=120)
    priority: str = Field(default="normal", min_length=1, max_length=80)
    memory_id: str | None = Field(default=None, min_length=1, max_length=120)
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_id: str | None = Field(default=None, min_length=1, max_length=120)
    domain: str = Field(default="unknown", min_length=1, max_length=80)
    sensitivity: str = Field(default="unknown", min_length=1, max_length=80)


class VNextMemoryReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    canonical_text: str | None = Field(default=None, min_length=1, max_length=4000)
    summary: str | None = Field(default=None, min_length=1, max_length=4000)
    domain: str | None = Field(default=None, min_length=1, max_length=80)
    sensitivity: str | None = Field(default=None, min_length=1, max_length=80)
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextQueueTaskCreateRequest(VNextAgentRequest):
    user_id: UUID
    title: str = Field(min_length=1, max_length=280)
    task_type: str = Field(min_length=1, max_length=80)
    instructions: str = Field(min_length=1, max_length=20_000)
    domain: str = Field(default="unknown", min_length=1, max_length=80)
    sensitivity: str = Field(default="unknown", min_length=1, max_length=80)
    write_policy: str = Field(default="proposal_only", min_length=1, max_length=80)
    scope_json: dict[str, object] = Field(default_factory=dict)
    allowed_sources_json: list[object] = Field(default_factory=list)


class VNextQueueProcessNextRequest(VNextAgentRequest):
    user_id: UUID


class VNextArtifactReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)


class VNextArtifactQualityRatingRequest(VNextAgentRequest):
    user_id: UUID
    reviewer_id: str | None = Field(default=None, min_length=1, max_length=120)
    usefulness: int | None = Field(default=None, ge=1, le=5)
    accuracy: int | None = Field(default=None, ge=1, le=5)
    source_grounding: int | None = Field(default=None, ge=1, le=5)
    novel_connections: int | None = Field(default=None, ge=1, le=5)
    actionability: int | None = Field(default=None, ge=1, le=5)
    hallucination_risk: int | None = Field(default=None, ge=1, le=5)
    verbosity: str = Field(default="unknown", min_length=1, max_length=40)
    missed_context: str | None = Field(default=None, min_length=1, max_length=4000)
    comments: str | None = Field(default=None, min_length=1, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class VNextGraphEdgeReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)


class VNextBeliefReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    superseded_by: str | None = Field(default=None, min_length=1, max_length=120)


class VNextArtifactExportRequest(VNextAgentRequest):
    user_id: UUID
    output_dir: str = Field(min_length=1, max_length=1000)


class VNextBrainCharterUpsertRequest(VNextAgentRequest):
    user_id: UUID
    content_markdown: str = Field(min_length=1, max_length=200_000)
    owner_json: dict[str, object] = Field(default_factory=dict)
    memory_philosophy_json: dict[str, object] = Field(default_factory=dict)
    life_domains_json: dict[str, object] = Field(default_factory=dict)
    active_projects_json: list[object] = Field(default_factory=list)
    communication_style_json: dict[str, object] = Field(default_factory=dict)
    priorities_json: dict[str, object] = Field(default_factory=dict)
    autonomous_rules_json: list[object] = Field(default_factory=list)
    quality_standard_json: list[object] = Field(default_factory=list)
    sensitivity: str = Field(default="private", min_length=1, max_length=80)


class VNextMemoryProposalRequest(VNextAgentRequest):
    user_id: UUID
    proposal_type: str = Field(default="candidate_memory", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=280)
    canonical_text: str = Field(min_length=1, max_length=20_000)
    source_refs: list[object] = Field(default_factory=list)
    domain: str = Field(default="unknown", min_length=1, max_length=80)
    sensitivity: str = Field(default="unknown", min_length=1, max_length=80)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    review_required: bool = True


class VNextMemoryCommitRequest(VNextAgentRequest):
    user_id: UUID
    intent: str = Field(default="explicit_remember", min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=280)
    canonical_text: str = Field(min_length=1, max_length=20_000)
    memory_type: str = Field(default="semantic", min_length=1, max_length=80)
    domain: str = Field(default="unknown", min_length=1, max_length=80)
    sensitivity: str = Field(default="unknown", min_length=1, max_length=80)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    source_type: str = Field(default="direct_user_instruction", min_length=1, max_length=120)
    source_refs: list[object] = Field(default_factory=list)
    conversation_excerpt: str | None = Field(default=None, min_length=1, max_length=4000)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    contradiction_refs: list[str] = Field(default_factory=list)


class VNextMemoryConfirmRequest(VNextAgentRequest):
    user_id: UUID
    confirmation_id: str = Field(min_length=1, max_length=160)
    action: str = Field(default="confirm", min_length=1, max_length=40)
    canonical_text: str | None = Field(default=None, min_length=1, max_length=20_000)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryUndoRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryCorrectRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    canonical_text: str = Field(min_length=1, max_length=20_000)
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryForgetRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextSchedulerWorkflowPatchRequest(VNextAgentRequest):
    user_id: UUID
    enabled: bool | None = None
    paused: bool | None = None
    schedule_json: dict[str, object] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=120)
    model_options: dict[str, object] = Field(default_factory=dict)


class VNextSchedulerRunNowRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextSchedulerRunDueRequest(VNextAgentRequest):
    user_id: UUID
    limit: int = Field(default=10, ge=1, le=50)


class VNextSchedulerControlRequest(VNextAgentRequest):
    user_id: UUID


class VNextDoctorRunRequest(BaseModel):
    user_id: UUID
    fix_safe: bool = False
    ci: bool = True


def _vnext_public_error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def _vnext_string_list(mapping: dict[str, object], key: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, list):
        return ()
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped:
            output.append(stripped)
    return tuple(output)


def _vnext_bool(mapping: dict[str, object], key: str, default: bool) -> bool:
    value = mapping.get(key)
    return value if isinstance(value, bool) else default


def _vnext_int(mapping: dict[str, object], key: str, default: int) -> int:
    value = mapping.get(key)
    return value if isinstance(value, int) else default


def _vnext_float(mapping: dict[str, object], key: str) -> float | None:
    value = mapping.get(key)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _vnext_model_generation_options(options: dict[str, object]) -> dict[str, object]:
    generation_mode = options.get("generation_mode")
    route_mode = options.get("model_route_mode")
    provider = options.get("model_provider")
    model = options.get("model")
    temperature = _vnext_float(options, "model_temperature")
    if temperature is None or temperature < 0.0 or temperature > 2.0:
        temperature = 0.2
    return {
        "generation_mode": generation_mode if generation_mode in {"deterministic", "model_backed"} else "deterministic",
        "model_route_mode": route_mode
        if route_mode in {"local_only", "cloud_allowed", "cloud_requires_approval", "model_disabled"}
        else None,
        "model_provider": provider if isinstance(provider, str) else None,
        "model": model if isinstance(model, str) else None,
        "model_temperature": temperature,
        "allow_cloud_private": _vnext_bool(options, "allow_cloud_private", False),
    }


def _vnext_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "project"


def _vnext_status_counts(rows: list[dict[str, object]], *, field: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get(field, "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _vnext_metadata(row: dict[str, object] | None) -> dict[str, object]:
    if row is None:
        return {}
    value = row.get("metadata_json")
    return value if isinstance(value, dict) else {}


def _vnext_payload(row: dict[str, object]) -> dict[str, object]:
    value = row.get("payload_json")
    return value if isinstance(value, dict) else {}


def _vnext_ref_values(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, str):
        if value.strip():
            refs.append(value.strip())
    elif isinstance(value, dict):
        for key in ("source_id", "id", "ref", "source_ref"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int)):
                refs.append(str(candidate))
        for nested_key in ("source_ids", "source_refs", "sources"):
            refs.extend(_vnext_ref_values(value.get(nested_key)))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_vnext_ref_values(item))
    return refs


def _vnext_ref_matches_source(value: object, source_id: str) -> bool:
    normalized = str(source_id)
    return any(ref == normalized or ref == f"source:{normalized}" for ref in _vnext_ref_values(value))


def _vnext_row_references_source(row: dict[str, object], source_id: str) -> bool:
    if str(row.get("source_id") or "") == str(source_id):
        return True
    metadata = _vnext_metadata(row)
    for key in ("source_id", "source_ids", "source_ref", "source_refs", "source_references", "selected_source_ids"):
        if _vnext_ref_matches_source(metadata.get(key), source_id):
            return True
    return _vnext_ref_matches_source(row.get("source_event_ids"), source_id)


def _vnext_event_references(
    event: dict[str, object],
    *,
    source_id: str,
    memory_ids: set[str],
    artifact_ids: set[str],
    open_loop_ids: set[str],
) -> bool:
    target_type = str(event.get("target_type") or "")
    target_id = str(event.get("target_id") or "")
    if target_type == "source" and target_id == source_id:
        return True
    if target_type == "memory" and target_id in memory_ids:
        return True
    if target_type == "artifact" and target_id in artifact_ids:
        return True
    if target_type == "open_loop" and target_id in open_loop_ids:
        return True
    payload = _vnext_payload(event)
    return any(
        _vnext_ref_matches_source(payload.get(key), source_id)
        for key in ("source_id", "source_ids", "source_ref", "source_refs", "source_references", "selected_source_ids")
    )


def _vnext_source_chunks(store: PostgresVNextStore, source_id: str) -> list[dict[str, object]]:
    if not hasattr(store, "list_source_chunks"):
        return []
    return list(store.list_source_chunks(source_id))


def _vnext_source_trace(
    *,
    store: PostgresVNextStore,
    source: dict[str, object],
    memories: list[dict[str, object]],
    artifacts: list[dict[str, object]],
    open_loops: list[dict[str, object]],
    events: list[dict[str, object]],
) -> dict[str, object]:
    source_id = str(source["id"])
    related_memories = [memory for memory in memories if _vnext_row_references_source(memory, source_id)]
    related_artifacts = [artifact for artifact in artifacts if _vnext_row_references_source(artifact, source_id)]
    related_open_loops = [loop for loop in open_loops if _vnext_row_references_source(loop, source_id)]
    memory_ids = {str(memory["id"]) for memory in related_memories}
    artifact_ids = {str(artifact["id"]) for artifact in related_artifacts}
    open_loop_ids = {str(loop["id"]) for loop in related_open_loops}
    related_events = [
        event
        for event in events
        if _vnext_event_references(
            event,
            source_id=source_id,
            memory_ids=memory_ids,
            artifact_ids=artifact_ids,
            open_loop_ids=open_loop_ids,
        )
    ]
    trace_id = next((str(event.get("trace_id")) for event in related_events if event.get("trace_id")), None)
    chunks = _vnext_source_chunks(store, source_id)
    return {
        "trace_id": trace_id or f"source:{source_id}",
        "trace_kind": "capture_to_brief",
        "source": source,
        "chunks": chunks,
        "candidate_memories": related_memories,
        "artifacts": related_artifacts,
        "open_loops": related_open_loops,
        "events": related_events,
        "summary": {
            "source_id": source_id,
            "chunk_count": len(chunks),
            "candidate_memory_count": len(related_memories),
            "artifact_count": len(related_artifacts),
            "open_loop_count": len(related_open_loops),
            "event_count": len(related_events),
        },
    }


def _vnext_artifact_trace(
    *,
    artifact: dict[str, object],
    sources: list[dict[str, object]],
    quality_evals: list[dict[str, object]],
    events: list[dict[str, object]],
) -> dict[str, object]:
    artifact_id = str(artifact["id"])
    metadata = _vnext_metadata(artifact)
    source_refs = _vnext_ref_values(metadata.get("source_refs")) + _vnext_ref_values(metadata.get("source_ids"))
    related_sources = [
        source
        for source in sources
        if str(source.get("id")) in source_refs or f"source:{source.get('id')}" in source_refs
    ]
    related_evals = [rating for rating in quality_evals if str(rating.get("artifact_id")) == artifact_id]
    related_events = [
        event
        for event in events
        if str(event.get("target_type") or "") == "artifact" and str(event.get("target_id") or "") == artifact_id
    ]
    return {
        "trace_id": metadata.get("trace_id") or metadata.get("scheduler_run_id") or f"artifact:{artifact_id}",
        "trace_kind": "artifact_review",
        "artifact": artifact,
        "sources": related_sources,
        "quality_evals": related_evals,
        "events": related_events,
        "summary": {
            "artifact_id": artifact_id,
            "source_count": len(related_sources),
            "quality_eval_count": len(related_evals),
            "event_count": len(related_events),
            "scheduler_run_id": metadata.get("scheduler_run_id"),
            "agent_run_id": metadata.get("agent_run_id"),
        },
    }


def _vnext_agent_identity(request: VNextAgentRequest) -> AgentIdentity | None:
    payload = request.model_dump(mode="json")
    if payload.get("agent_identity") is None and isinstance(payload.get("agent"), dict):
        payload["agent_identity"] = payload["agent"]
    return AgentIdentity.from_payload(payload)


def _vnext_permission_response(decision: PolicyDecision) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=jsonable_encoder(
            {
                "detail": "agent policy blocked this action",
                "policy_decision": decision.to_record(),
            }
        ),
    )


def _vnext_agent_actor(identity: AgentIdentity | None, *, fallback: str = "user") -> tuple[str, str | None]:
    if identity is None:
        return fallback, None
    return identity.actor_type, identity.agent_id


def _vnext_agent_record(store: PostgresVNextStore, identity: AgentIdentity | None) -> None:
    if identity is None:
        return
    store.upsert_agent_identity(
        {
            "agent_id": identity.agent_id,
            "agent_type": identity.agent_type,
            "permission_profile": identity.permission_profile,
            "project_scope_json": list(identity.project_scope),
            "metadata_json": {
                "last_agent_run_id": identity.agent_run_id,
                "last_task_id": identity.task_id,
            },
        },
        actor_type="agent",
    )


def _vnext_policy_checked(
    *,
    store: PostgresVNextStore,
    identity: AgentIdentity | None,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> PolicyDecision:
    _vnext_agent_record(store, identity)
    decision = evaluate_agent_policy(
        identity=identity,
        action=action,
        domains=domains,
        sensitivity_allowed=sensitivity_allowed,
        project_scope=project_scope,
        workflow_type=workflow_type,
        write_policy=write_policy,
    )
    append_policy_events(store, identity=identity, decision=decision, target_type=target_type, target_id=target_id)
    return decision


def _vnext_workspace_payload(store: PostgresVNextStore) -> dict[str, object]:
    sensitivity_allowed = ["public", "internal", "private", "unknown"]
    sources = store.list_sources(sensitivity_allowed=sensitivity_allowed, limit=20)
    memories = store.list_memories(status=None)
    review_memories = [
        memory
        for memory in memories
        if str(memory.get("status")) in {"candidate", "needs_review", "private_only", "accepted", "rejected"}
    ][:30]
    artifacts = store.list_artifacts(sensitivity_allowed=sensitivity_allowed, limit=30)
    quality_evals = store.list_artifact_quality_ratings(limit=50)
    projects = store.list_projects(status=None, sensitivity_allowed=sensitivity_allowed, limit=20)
    open_loops = store.list_open_loops(status=None, sensitivity_allowed=sensitivity_allowed, limit=30)
    people = store.list_people(sensitivity_allowed=sensitivity_allowed, limit=12)
    beliefs = store.list_beliefs(status=None, sensitivity_allowed=sensitivity_allowed, limit=12)
    tasks = store.list_tasks(status=None, limit=12)
    recent_events = store.list_events(limit=20)
    agent_identities = store.list_agent_identities(limit=20)
    agent_events = store.list_agent_events(limit=50)
    memory_commit_service = VNextMemoryCommitService(store)
    recent_memory_commits = memory_commit_service.recent_commits(limit=20)["recent_commits"]
    inline_confirmations = memory_commit_service.inline_confirmations(limit=20)
    scheduler_status = VNextSchedulerService(store).status()
    scheduler_status = {**scheduler_status, "daemon": daemon_status()}
    connector_health = VNextConnectorService(store).connector_health_all()
    dogfooding = VNextDogfoodingService(store).dashboard()
    doctor = VNextDoctorService(store).run(ci=True)
    policy_telemetry = summarize_agent_policy_telemetry(
        agent_events=agent_events,
        artifacts=artifacts,
        memories=review_memories,
    )
    project_service = VNextProjectService(store)
    project_dashboards: list[dict[str, object]] = []
    for project in projects[:5]:
        try:
            project_dashboards.append(project_service.project_dashboard(project_id=str(project["id"])))
        except VNextProjectValidationError:
            continue
    trace_items = [
        _vnext_source_trace(
            store=store,
            source=source,
            memories=memories,
            artifacts=artifacts,
            open_loops=open_loops,
            events=recent_events,
        )
        for source in sources[:8]
    ]
    return {
        "mode": "live",
        "summary": {
            "source_count": len(sources),
            "candidate_memory_count": len([memory for memory in memories if memory.get("status") == "candidate"]),
            "review_memory_count": len(review_memories),
            "artifact_count": len(artifacts),
            "open_loop_count": len([loop for loop in open_loops if loop.get("status") == "open"]),
            "project_count": len(projects),
            "event_count": len(recent_events),
            "agent_count": len(agent_identities),
            "scheduler_enabled_count": int(scheduler_status["enabled_count"]),
            "memory_status_counts": _vnext_status_counts(memories),
            "artifact_status_counts": _vnext_status_counts(artifacts),
            "quality_eval_count": len(quality_evals),
            "open_loop_status_counts": _vnext_status_counts(open_loops),
        },
        "sources": sources,
        "review_memories": review_memories,
        "artifacts": artifacts,
        "quality_evals": quality_evals,
        "connector_health": connector_health,
        "dogfooding": dogfooding,
        "doctor": doctor,
        "traceability": {
            "items": trace_items,
            "count": len(trace_items),
            "order": [str(trace.get("trace_id")) for trace in trace_items],
        },
        "projects": projects,
        "project_dashboards": project_dashboards,
        "open_loops": open_loops,
        "people": people,
        "beliefs": beliefs,
        "tasks": tasks,
        "recent_events": recent_events,
        "agent_activity": {
            "agents": agent_identities,
            "recent_events": agent_events,
            "policy_blocks": [
                event
                for event in agent_events
                if event.get("event_type") in {"agent.policy_blocked", "agent.policy_filtered"}
            ],
            "generated_artifacts": [
                artifact
                for artifact in artifacts
                if isinstance(artifact.get("metadata_json"), dict)
                and artifact["metadata_json"].get("generated_by") == "agent"
            ],
            "pending_review_items": [
                memory
                for memory in review_memories
                if isinstance(memory.get("metadata_json"), dict)
                and memory["metadata_json"].get("agent_id") is not None
            ],
            "recent_commits": recent_memory_commits,
            "inline_confirmations": inline_confirmations,
        },
        "policy_telemetry": policy_telemetry,
        "scheduler": scheduler_status,
        "brain_charter": store.get_brain_charter(),
    }


def _vnext_brain_artifact_request(
    request: VNextBrainArtifactGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> BrainArtifactRequest:
    scope = request.scope
    options = request.options
    generated_for = options.get("generated_for") or scope.get("generated_for")
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return BrainArtifactRequest(
        domains=decision.effective_domains if decision is not None else _vnext_string_list(scope, "domains"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        generated_for=str(generated_for) if isinstance(generated_for, str) else None,
        source_limit=_vnext_int(options, "source_limit", 8),
        memory_limit=_vnext_int(options, "memory_limit", 8),
        open_loop_limit=_vnext_int(options, "open_loop_limit", 8),
        artifact_limit=_vnext_int(options, "artifact_limit", 4),
        discover_open_loops=_vnext_bool(options, "discover_open_loops", True),
        create_candidate_memories=_vnext_bool(options, "create_candidate_memories", True),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_connection_request(
    request: VNextConnectionReportGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ConnectionFinderRequest:
    options = request.options
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ConnectionFinderRequest(
        query=request.query,
        domains=decision.effective_domains if decision is not None else _vnext_string_list(request.scope, "domains"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        max_connections=_vnext_int(options, "max_connections", 8),
        auto_accept_threshold=_vnext_float(options, "auto_accept_threshold"),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_contradiction_request(
    request: VNextContradictionReportGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ContradictionFinderRequest:
    options = request.options
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ContradictionFinderRequest(
        query=request.query,
        domains=decision.effective_domains if decision is not None else _vnext_string_list(request.scope, "domains"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        max_contradictions=_vnext_int(options, "max_contradictions", 8),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_project_automation_request(
    request: VNextProjectAutomationRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ProjectAutomationRequest:
    options = request.options
    scope = request.scope
    project_id = options.get("project_id") or scope.get("project_id")
    person_id = options.get("person_id") or scope.get("person_id")
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ProjectAutomationRequest(
        domains=decision.effective_domains if decision is not None else _vnext_string_list(scope, "domains"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        project_id=str(project_id) if isinstance(project_id, str) else None,
        person_id=str(person_id) if isinstance(person_id, str) else None,
        max_items=_vnext_int(options, "max_items", 8),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


class ContinuityCaptureCandidatesRequest(BaseModel):
    user_id: UUID
    user_content: str = Field(default="", max_length=4000)
    assistant_content: str = Field(default="", max_length=4000)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)


class ContinuityCaptureCommitRequest(BaseModel):
    user_id: UUID
    mode: str = Field(default="assist", min_length=1, max_length=20)
    candidates: list[dict[str, object]] = Field(default_factory=list)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)


class MemoryOperationGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_content: str = Field(default="", max_length=4000)
    assistant_content: str = Field(default="", max_length=4000)
    mode: str = Field(default="assist", min_length=1, max_length=20)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    target_continuity_object_id: UUID | None = None


class MemoryOperationCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(default_factory=list)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    include_review_required: bool = False


class ContinuityBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief_type: str = Field(default="general", min_length=1, max_length=40)
    query: str | None = Field(default=None, min_length=1, max_length=4000)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    since: datetime | None = None
    until: datetime | None = None
    max_relevant_facts: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    )
    max_recent_changes: int = Field(
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops: int = Field(
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
    max_conflicts: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    )
    max_timeline_highlights: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    )
    include_non_promotable_facts: bool = False


class ContinuityCorrectionRequest(BaseModel):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    body: dict[str, object] | None = None
    provenance: dict[str, object] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    replacement_title: str | None = Field(default=None, min_length=1, max_length=280)
    replacement_body: dict[str, object] | None = None
    replacement_provenance: dict[str, object] | None = None
    replacement_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ContradictionDetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity_object_id: UUID | None = None
    limit: int = Field(default=DEFAULT_CONTINUITY_REVIEW_LIMIT, ge=1, le=MAX_CONTINUITY_REVIEW_LIMIT)


class ContradictionResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, min_length=1, max_length=1000)


class ContinuityOpenLoopReviewActionRequest(BaseModel):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, min_length=1, max_length=500)


class ChiefOfStaffRecommendationOutcomeCaptureRequest(BaseModel):
    user_id: UUID
    outcome: str = Field(min_length=1, max_length=40)
    recommendation_action_type: str = Field(min_length=1, max_length=60)
    recommendation_title: str = Field(min_length=1, max_length=280)
    rationale: str | None = Field(default=None, min_length=1, max_length=500)
    rewritten_title: str | None = Field(default=None, min_length=1, max_length=280)
    target_priority_id: UUID | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)


class ChiefOfStaffHandoffReviewActionCaptureRequest(BaseModel):
    user_id: UUID
    handoff_item_id: str = Field(min_length=1, max_length=200)
    review_action: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, min_length=1, max_length=500)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)


class ChiefOfStaffExecutionRoutingActionCaptureRequest(BaseModel):
    user_id: UUID
    handoff_item_id: str = Field(min_length=1, max_length=200)
    route_target: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, min_length=1, max_length=500)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)


class ChiefOfStaffHandoffOutcomeCaptureRequest(BaseModel):
    user_id: UUID
    handoff_item_id: str = Field(min_length=1, max_length=200)
    outcome_status: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, min_length=1, max_length=500)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)


class CreateMemoryReviewLabelRequest(BaseModel):
    user_id: UUID
    label: MemoryReviewLabelValue
    note: str | None = Field(default=None, min_length=1, max_length=280)


class CreateOpenLoopRequest(BaseModel):
    user_id: UUID
    memory_id: UUID | None = None
    title: str = Field(min_length=1, max_length=280)
    due_at: datetime | None = None


class UpdateOpenLoopStatusRequest(BaseModel):
    user_id: UUID
    status: str = Field(min_length=1, max_length=100)
    resolution_note: str | None = Field(default=None, min_length=1, max_length=2000)


class CreateEntityRequest(BaseModel):
    user_id: UUID
    entity_type: EntityType
    name: str = Field(min_length=1, max_length=200)
    source_memory_ids: list[UUID] = Field(min_length=1)


class CreateEntityEdgeRequest(BaseModel):
    user_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str = Field(min_length=1, max_length=100)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_memory_ids: list[UUID] = Field(min_length=1)


class CreateEmbeddingConfigRequest(BaseModel):
    user_id: UUID
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    dimensions: int = Field(ge=1, le=20000)
    status: EmbeddingConfigStatus = "active"
    metadata: dict[str, object] = Field(default_factory=dict)


class UpsertMemoryEmbeddingRequest(BaseModel):
    user_id: UUID
    memory_id: UUID
    embedding_config_id: UUID
    vector: list[float] = Field(min_length=1, max_length=20000)


class UpsertTaskArtifactChunkEmbeddingRequest(BaseModel):
    user_id: UUID
    task_artifact_chunk_id: UUID
    embedding_config_id: UUID
    vector: list[float] = Field(min_length=1, max_length=20000)


class RetrieveSemanticMemoriesRequest(BaseModel):
    user_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    )


class RetrieveSemanticArtifactChunksRequest(BaseModel):
    user_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class UpsertConsentRequest(BaseModel):
    user_id: UUID
    consent_key: str = Field(min_length=1, max_length=200)
    status: ConsentStatus
    metadata: dict[str, object] = Field(default_factory=dict)


class CreatePolicyRequest(BaseModel):
    user_id: UUID
    name: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    effect: PolicyEffect
    priority: int = Field(ge=0, le=1000000)
    active: bool = True
    conditions: dict[str, object] = Field(default_factory=dict)
    required_consents: list[str] = Field(default_factory=list)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)


class EvaluatePolicyRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    attributes: dict[str, object] = Field(default_factory=dict)


class CreateToolRequest(BaseModel):
    user_id: UUID
    tool_key: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    version: str = Field(min_length=1, max_length=100)
    metadata_version: str = Field(default=TOOL_METADATA_VERSION_V0, pattern=f"^{TOOL_METADATA_VERSION_V0}$")
    active: bool = True
    tags: list[str] = Field(default_factory=list)
    action_hints: list[str] = Field(default_factory=list, min_length=1)
    scope_hints: list[str] = Field(default_factory=list, min_length=1)
    domain_hints: list[str] = Field(default_factory=list)
    risk_hints: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class EvaluateToolAllowlistRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class RouteToolRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class CreateApprovalRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    task_run_id: UUID | None = None
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class ResolveApprovalRequest(BaseModel):
    user_id: UUID


class ExecuteApprovedProxyRequest(BaseModel):
    user_id: UUID
    task_run_id: UUID | None = None


class ConnectGmailAccountRequest(BaseModel):
    user_id: UUID
    provider_account_id: str = Field(min_length=1, max_length=320)
    email_address: str = Field(min_length=1, max_length=320)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: Literal["https://www.googleapis.com/auth/gmail.readonly"] = GMAIL_READONLY_SCOPE
    access_token: str = Field(min_length=1, max_length=8000)
    refresh_token: str | None = Field(default=None, min_length=1, max_length=8000)
    client_id: str | None = Field(default=None, min_length=1, max_length=2000)
    client_secret: str | None = Field(default=None, min_length=1, max_length=8000)
    access_token_expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_refresh_bundle(self) -> ConnectGmailAccountRequest:
        refresh_bundle = (
            self.refresh_token,
            self.client_id,
            self.client_secret,
            self.access_token_expires_at,
        )
        if all(value is None for value in refresh_bundle):
            return self
        if any(value is None for value in refresh_bundle):
            raise ValueError(
                "gmail refresh credentials must include refresh_token, client_id, "
                "client_secret, and access_token_expires_at"
            )
        return self


class IngestGmailMessageRequest(BaseModel):
    user_id: UUID
    task_workspace_id: UUID


class ConnectCalendarAccountRequest(BaseModel):
    user_id: UUID
    provider_account_id: str = Field(min_length=1, max_length=320)
    email_address: str = Field(min_length=1, max_length=320)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: Literal["https://www.googleapis.com/auth/calendar.readonly"] = CALENDAR_READONLY_SCOPE
    access_token: str = Field(min_length=1, max_length=8000)


class IngestCalendarEventRequest(BaseModel):
    user_id: UUID
    task_workspace_id: UUID


class CreateTaskWorkspaceRequest(BaseModel):
    user_id: UUID


class RegisterTaskArtifactRequest(BaseModel):
    user_id: UUID
    local_path: str = Field(min_length=1, max_length=4000)
    media_type_hint: str | None = Field(default=None, min_length=1, max_length=200)


class IngestTaskArtifactRequest(BaseModel):
    user_id: UUID


class RetrieveArtifactChunksRequest(BaseModel):
    user_id: UUID
    query: str = Field(min_length=1, max_length=1000)


class TaskStepRequestSnapshot(BaseModel):
    thread_id: UUID
    tool_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class TaskStepOutcomeRequest(BaseModel):
    routing_decision: ToolRoutingDecision
    approval_id: UUID | None = None
    approval_status: ApprovalStatus | None = None
    execution_id: UUID | None = None
    execution_status: ProxyExecutionStatus | None = None
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=500)


class TaskStepLineageRequest(BaseModel):
    parent_step_id: UUID
    source_approval_id: UUID | None = None
    source_execution_id: UUID | None = None


class CreateNextTaskStepRequest(BaseModel):
    user_id: UUID
    kind: TaskStepKind = "governed_request"
    status: TaskStepStatus
    request: TaskStepRequestSnapshot
    outcome: TaskStepOutcomeRequest
    lineage: TaskStepLineageRequest


class TransitionTaskStepRequest(BaseModel):
    user_id: UUID
    status: TaskStepStatus
    outcome: TaskStepOutcomeRequest


class CreateTaskRunRequest(BaseModel):
    user_id: UUID
    max_ticks: int = Field(default=1, ge=1, le=1_000_000)
    retry_cap: int | None = Field(default=None, ge=1, le=1_000_000)
    checkpoint: dict[str, object] = Field(default_factory=dict)


class MutateTaskRunRequest(BaseModel):
    user_id: UUID


class CreateExecutionBudgetRequest(BaseModel):
    user_id: UUID
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)
    tool_key: str | None = Field(default=None, min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    max_completed_executions: int = Field(ge=1, le=1000000)
    rolling_window_seconds: int | None = Field(default=None, ge=1)


class DeactivateExecutionBudgetRequest(BaseModel):
    user_id: UUID
    thread_id: UUID


class SupersedeExecutionBudgetRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    max_completed_executions: int = Field(ge=1, le=1000000)


def _serialize_thread(thread: ThreadRow) -> ThreadRecord:
    agent_profile_id = _thread_agent_profile_id(thread)
    return {
        "id": str(thread["id"]),
        "title": thread["title"],
        "agent_profile_id": agent_profile_id,
        "created_at": thread["created_at"].isoformat(),
        "updated_at": thread["updated_at"].isoformat(),
    }


def _thread_agent_profile_id(thread: ThreadRow) -> str:
    return str(thread.get("agent_profile_id", DEFAULT_AGENT_PROFILE_ID))


def _serialize_thread_session(session: SessionRow) -> ThreadSessionRecord:
    return {
        "id": str(session["id"]),
        "thread_id": str(session["thread_id"]),
        "status": session["status"],
        "started_at": None if session["started_at"] is None else session["started_at"].isoformat(),
        "ended_at": None if session["ended_at"] is None else session["ended_at"].isoformat(),
        "created_at": session["created_at"].isoformat(),
    }


def _serialize_thread_event(event: EventRow) -> ThreadEventRecord:
    return {
        "id": str(event["id"]),
        "thread_id": str(event["thread_id"]),
        "session_id": None if event["session_id"] is None else str(event["session_id"]),
        "sequence_no": event["sequence_no"],
        "kind": event["kind"],
        "payload": event["payload"],
        "created_at": event["created_at"].isoformat(),
    }


def _serialize_model_provider(provider: ModelProviderRow) -> dict[str, object]:
    return {
        "id": str(provider["id"]),
        "workspace_id": str(provider["workspace_id"]),
        "created_by_user_account_id": str(provider["created_by_user_account_id"]),
        "provider_key": provider["provider_key"],
        "model_provider": provider["model_provider"],
        "display_name": provider["display_name"],
        "base_url": redact_url_credentials(provider["base_url"]),
        "auth_mode": provider["auth_mode"],
        "default_model": provider["default_model"],
        "status": provider["status"],
        "model_list_path": provider["model_list_path"],
        "healthcheck_path": provider["healthcheck_path"],
        "invoke_path": provider["invoke_path"],
        "azure_api_version": provider["azure_api_version"],
        "metadata": provider["metadata"],
        "created_at": provider["created_at"].isoformat(),
        "updated_at": provider["updated_at"].isoformat(),
    }


def _serialize_provider_capability(capability: ProviderCapabilityRow) -> dict[str, object]:
    snapshot = capability["capability_snapshot"]
    capability_version = snapshot.get("capability_version")
    if not isinstance(capability_version, str) or capability_version == "":
        capability_version = "provider_capability_v1"
    return {
        "provider_id": str(capability["provider_id"]),
        "adapter_key": capability["adapter_key"],
        "discovery_status": capability["discovery_status"],
        "capability_version": capability_version,
        "snapshot": snapshot,
        "discovery_error": capability["discovery_error"],
        "discovered_at": capability["discovered_at"].isoformat(),
    }


def _serialize_model_pack(pack: ModelPackRow) -> dict[str, object]:
    return {
        "id": str(pack["id"]),
        "workspace_id": str(pack["workspace_id"]),
        "created_by_user_account_id": str(pack["created_by_user_account_id"]),
        "pack_id": pack["pack_id"],
        "pack_version": pack["pack_version"],
        "display_name": pack["display_name"],
        "family": pack["family"],
        "description": pack["description"],
        "status": pack["status"],
        "briefing_strategy": pack["briefing_strategy"],
        "briefing_max_tokens": pack["briefing_max_tokens"],
        "contract": pack["contract"],
        "metadata": pack["metadata"],
        "created_at": pack["created_at"].isoformat(),
        "updated_at": pack["updated_at"].isoformat(),
    }


def _serialize_workspace_model_pack_binding(
    binding: WorkspaceModelPackBindingDetailRow,
) -> dict[str, object]:
    model_pack: ModelPackRow = {
        "id": binding["model_pack_id"],
        "workspace_id": binding["workspace_id"],
        "created_by_user_account_id": binding["pack_created_by_user_account_id"],
        "pack_id": binding["pack_id"],
        "pack_version": binding["pack_version"],
        "display_name": binding["pack_display_name"],
        "family": binding["pack_family"],
        "description": binding["pack_description"],
        "status": binding["pack_status"],
        "briefing_strategy": binding["pack_briefing_strategy"],
        "briefing_max_tokens": binding["pack_briefing_max_tokens"],
        "contract": binding["pack_contract"],
        "metadata": binding["pack_metadata"],
        "created_at": binding["pack_created_at"],
        "updated_at": binding["pack_updated_at"],
    }
    return {
        "id": str(binding["id"]),
        "workspace_id": str(binding["workspace_id"]),
        "provider_id": None if binding["provider_id"] is None else str(binding["provider_id"]),
        "model_pack_id": str(binding["model_pack_id"]),
        "bound_by_user_account_id": str(binding["bound_by_user_account_id"]),
        "binding_source": binding["binding_source"],
        "metadata": binding["metadata"],
        "created_at": binding["created_at"].isoformat(),
        "model_pack": _serialize_model_pack(model_pack),
    }


def _runtime_provider_config_or_none(
    *,
    store: ContinuityStore,
    provider_id: UUID,
    workspace_id: UUID,
    settings: Settings,
) -> RuntimeProviderConfig | None:
    row = store.get_model_provider_for_workspace_optional(
        provider_id=provider_id,
        workspace_id=workspace_id,
    )
    if row is None:
        return None
    validate_provider_base_url(row["base_url"])
    return resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(row),
        settings=settings,
    )


def _normalize_provider_path(*, field_name: str, value: str) -> str:
    path = value.strip()
    if path == "":
        raise ValueError(f"{field_name} is required")
    return path if path.startswith("/") else f"/{path}"


def _fallback_provider_capability_snapshot(
    *,
    adapter_key: str,
    runtime_provider: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    extra_snapshot_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    snapshot = normalized_capability_snapshot(
        adapter_key=adapter_key,
        runtime_provider=runtime_provider,
        supports_tool_calls=False,
        supports_reasoning=False,
        supports_streaming=False,
        supports_store=False,
        supports_vision_input=False,
        supports_audio_input=False,
    )
    snapshot.update(
        {
            "health_status": "unreachable",
            "health_endpoint": healthcheck_path,
            "models_endpoint": model_list_path,
            "invoke_endpoint": invoke_path,
            "model_count": 0,
            "models": [],
        }
    )
    if extra_snapshot_fields:
        snapshot.update(extra_snapshot_fields)
    return snapshot


def _invoke_runtime_provider_model(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    invoked_by_user_account_id: UUID,
    thread_id: UUID | None,
    invocation_kind: str,
    adapter: ProviderAdapter,
    runtime_provider: RuntimeProviderConfig,
    settings: Settings,
    model_request: ModelInvocationRequest,
) -> ModelInvocationResponse:
    started_at = time.monotonic()
    try:
        model_response = adapter.invoke(
            config=runtime_provider,
            settings=settings,
            request=model_request,
        )
    except ValueError as exc:
        error_detail = str(exc)
        store.record_provider_invocation_telemetry(
            workspace_id=workspace_id,
            provider_id=runtime_provider.provider_id,
            thread_id=thread_id,
            invoked_by_user_account_id=invoked_by_user_account_id,
            invocation_kind=invocation_kind,
            adapter_key=adapter.adapter_key,
            runtime_provider=runtime_provider.model_provider,
            requested_model=model_request.model,
            response_model=None,
            response_id=None,
            status="failed",
            latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            usage={"input_tokens": None, "output_tokens": None, "total_tokens": None},
            error_detail=error_detail,
        )
        raise ModelInvocationError(error_detail) from exc
    except ModelInvocationError as exc:
        sanitized_error = sanitize_provider_error_message(str(exc))
        store.record_provider_invocation_telemetry(
            workspace_id=workspace_id,
            provider_id=runtime_provider.provider_id,
            thread_id=thread_id,
            invoked_by_user_account_id=invoked_by_user_account_id,
            invocation_kind=invocation_kind,
            adapter_key=adapter.adapter_key,
            runtime_provider=runtime_provider.model_provider,
            requested_model=model_request.model,
            response_model=None,
            response_id=None,
            status="failed",
            latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            usage={"input_tokens": None, "output_tokens": None, "total_tokens": None},
            error_detail=sanitized_error,
        )
        raise ModelInvocationError(sanitized_error) from exc

    store.record_provider_invocation_telemetry(
        workspace_id=workspace_id,
        provider_id=runtime_provider.provider_id,
        thread_id=thread_id,
        invoked_by_user_account_id=invoked_by_user_account_id,
        invocation_kind=invocation_kind,
        adapter_key=adapter.adapter_key,
        runtime_provider=runtime_provider.model_provider,
        requested_model=model_request.model,
        response_model=model_response.model,
        response_id=model_response.response_id,
        status="succeeded",
        latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        usage=dict(model_response.usage),
        error_detail=None,
    )
    return model_response


def _seed_workspace_provider_configs(
    *,
    settings: Settings,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
) -> None:
    if len(settings.workspace_provider_configs) == 0:
        return

    existing_provider_keys = {
        (provider["provider_key"], provider["display_name"])
        for provider in store.list_model_providers_for_workspace(workspace_id=workspace_id)
    }
    for provider_config in settings.workspace_provider_configs:
        provider_identity = (provider_config.provider_key, provider_config.display_name)
        if provider_identity in existing_provider_keys:
            continue
        _register_workspace_provider(
            settings=settings,
            store=store,
            workspace_id=workspace_id,
            created_by_user_account_id=created_by_user_account_id,
            provider_key=provider_config.provider_key,
            display_name=provider_config.display_name,
            base_url=provider_config.base_url,
            api_key=provider_config.api_key,
            auth_mode=provider_config.auth_mode,
            default_model=provider_config.default_model,
            model_list_path=provider_config.model_list_path,
            healthcheck_path=provider_config.healthcheck_path,
            invoke_path=provider_config.invoke_path,
            metadata={} if provider_config.metadata is None else dict(provider_config.metadata),
        )
        existing_provider_keys.add(provider_identity)


def _register_workspace_provider(
    *,
    settings: Settings,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
    provider_key: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    normalized_display_name = display_name.strip()
    normalized_base_url = base_url.strip()
    normalized_api_key = api_key.strip()
    normalized_default_model = default_model.strip()
    normalized_auth_mode = auth_mode.strip().lower()
    normalized_model_list_path = _normalize_provider_path(
        field_name="model_list_path",
        value=model_list_path,
    )
    normalized_healthcheck_path = _normalize_provider_path(
        field_name="healthcheck_path",
        value=healthcheck_path,
    )
    normalized_invoke_path = _normalize_provider_path(
        field_name="invoke_path",
        value=invoke_path,
    )

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")
    if normalized_auth_mode not in {"bearer", "none"}:
        raise ValueError(f"unsupported auth_mode: {auth_mode}")
    if normalized_auth_mode == "bearer" and normalized_api_key == "":
        raise ValueError("api_key is required when auth_mode is bearer")
    if normalized_auth_mode == "none" and normalized_api_key != "":
        raise ValueError("api_key must be empty when auth_mode is none")

    encoded_api_key = "auth_mode_none"
    if normalized_auth_mode == "bearer":
        secret_ref = build_provider_secret_ref(workspace_id=workspace_id)
        write_provider_api_key(
            settings=settings,
            secret_ref=secret_ref,
            api_key=normalized_api_key,
        )
        encoded_api_key = encode_provider_secret_ref(secret_ref=secret_ref)

    provider = store.create_model_provider(
        workspace_id=workspace_id,
        created_by_user_account_id=created_by_user_account_id,
        provider_key=provider_key,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        default_model=normalized_default_model,
        status="active",
        metadata=metadata,
        auth_mode=normalized_auth_mode,
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version="",
        # Non-Azure providers intentionally store an empty Azure secret ref.
        azure_auth_secret_ref="",  # nosec B106
    )

    runtime_provider = resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(provider),
        settings=settings,
    )
    adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    discovery_status: str = "ready"
    discovery_error: str | None = None

    try:
        capability_snapshot = adapter.discover_capabilities(
            config=runtime_provider,
            settings=settings,
        )
    except ModelInvocationError as exc:
        sanitized_discovery_error = sanitize_provider_error_message(str(exc))
        capability_snapshot = _fallback_provider_capability_snapshot(
            adapter_key=adapter.adapter_key,
            runtime_provider=adapter.runtime_provider,
            model_list_path=normalized_model_list_path,
            healthcheck_path=normalized_healthcheck_path,
            invoke_path=normalized_invoke_path,
        )
        discovery_status = "failed"
        discovery_error = sanitized_discovery_error

    capability = store.upsert_provider_capability(
        workspace_id=workspace_id,
        provider_id=provider["id"],
        discovered_by_user_account_id=created_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status=discovery_status,
        capability_snapshot=capability_snapshot,
        discovery_error=discovery_error,
    )
    return provider, capability


def _normalize_azure_api_version(value: str) -> str:
    api_version = value.strip()
    if api_version == "":
        raise ValueError("api_version is required")
    return api_version


def _register_workspace_azure_provider(
    *,
    settings: Settings,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
    display_name: str,
    base_url: str,
    credential: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    api_version: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    normalized_display_name = display_name.strip()
    normalized_base_url = base_url.strip()
    normalized_credential = credential.strip()
    normalized_default_model = default_model.strip()
    normalized_auth_mode = auth_mode.strip().lower()
    normalized_api_version = _normalize_azure_api_version(api_version)
    normalized_model_list_path = _normalize_provider_path(
        field_name="model_list_path",
        value=model_list_path,
    )
    normalized_healthcheck_path = _normalize_provider_path(
        field_name="healthcheck_path",
        value=healthcheck_path,
    )
    normalized_invoke_path = _normalize_provider_path(
        field_name="invoke_path",
        value=invoke_path,
    )

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")
    if normalized_auth_mode not in {AZURE_AUTH_MODE_API_KEY, AZURE_AUTH_MODE_AD_TOKEN}:
        raise ValueError(f"unsupported auth_mode: {auth_mode}")
    if normalized_credential == "":
        raise ValueError("azure credential is required")

    secret_ref = build_provider_secret_ref(workspace_id=workspace_id)
    write_provider_api_key(
        settings=settings,
        secret_ref=secret_ref,
        api_key=normalized_credential,
    )
    encoded_secret_ref = encode_provider_secret_ref(secret_ref=secret_ref)

    provider = store.create_model_provider(
        workspace_id=workspace_id,
        created_by_user_account_id=created_by_user_account_id,
        provider_key=AZURE_ADAPTER_KEY,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key="auth_mode_azure_secret_ref",
        default_model=normalized_default_model,
        status="active",
        metadata=metadata,
        auth_mode=normalized_auth_mode,
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=encoded_secret_ref,
    )

    runtime_provider = resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(provider),
        settings=settings,
    )
    adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    discovery_status: str = "ready"
    discovery_error: str | None = None

    try:
        capability_snapshot = adapter.discover_capabilities(
            config=runtime_provider,
            settings=settings,
        )
    except ModelInvocationError as exc:
        sanitized_discovery_error = sanitize_provider_error_message(str(exc))
        capability_snapshot = _fallback_provider_capability_snapshot(
            adapter_key=adapter.adapter_key,
            runtime_provider=adapter.runtime_provider,
            model_list_path=normalized_model_list_path,
            healthcheck_path=normalized_healthcheck_path,
            invoke_path=normalized_invoke_path,
            extra_snapshot_fields={
                "azure_api_version": normalized_api_version,
                "azure_auth_mode": normalized_auth_mode,
            },
        )
        discovery_status = "failed"
        discovery_error = sanitized_discovery_error

    capability = store.upsert_provider_capability(
        workspace_id=workspace_id,
        provider_id=provider["id"],
        discovered_by_user_account_id=created_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status=discovery_status,
        capability_snapshot=capability_snapshot,
        discovery_error=discovery_error,
    )
    return provider, capability


def _update_workspace_provider(
    *,
    settings: Settings,
    store: ContinuityStore,
    existing_provider: ModelProviderRow,
    updated_by_user_account_id: UUID,
    display_name: str | None,
    base_url: str | None,
    api_key: str | None,
    ad_token: str | None,
    auth_mode: str | None,
    default_model: str | None,
    model_list_path: str | None,
    healthcheck_path: str | None,
    invoke_path: str | None,
    api_version: str | None,
    metadata: dict[str, object] | None,
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    provider_key = existing_provider["provider_key"]
    normalized_display_name = (
        existing_provider["display_name"] if display_name is None else display_name.strip()
    )
    normalized_base_url = existing_provider["base_url"] if base_url is None else base_url.strip()
    normalized_default_model = (
        existing_provider["default_model"] if default_model is None else default_model.strip()
    )
    normalized_model_list_path = (
        existing_provider["model_list_path"]
        if model_list_path is None
        else _normalize_provider_path(field_name="model_list_path", value=model_list_path)
    )
    normalized_healthcheck_path = (
        existing_provider["healthcheck_path"]
        if healthcheck_path is None
        else _normalize_provider_path(field_name="healthcheck_path", value=healthcheck_path)
    )
    normalized_invoke_path = (
        existing_provider["invoke_path"]
        if invoke_path is None
        else _normalize_provider_path(field_name="invoke_path", value=invoke_path)
    )
    normalized_metadata = (
        existing_provider["metadata"] if metadata is None else metadata
    )

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")

    encoded_api_key = existing_provider["api_key"]
    normalized_auth_mode = existing_provider["auth_mode"] if auth_mode is None else auth_mode.strip().lower()
    normalized_api_version = existing_provider["azure_api_version"]
    normalized_azure_secret_ref = existing_provider["azure_auth_secret_ref"]

    if provider_key == AZURE_ADAPTER_KEY:
        if normalized_auth_mode not in {AZURE_AUTH_MODE_API_KEY, AZURE_AUTH_MODE_AD_TOKEN}:
            raise ValueError(f"unsupported auth_mode: {normalized_auth_mode}")
        if api_version is not None:
            normalized_api_version = _normalize_azure_api_version(api_version)
        credential_update = api_key if normalized_auth_mode == AZURE_AUTH_MODE_API_KEY else ad_token
        if credential_update is not None and credential_update.strip() != "":
            secret_ref = build_provider_secret_ref(workspace_id=existing_provider["workspace_id"])
            write_provider_api_key(
                settings=settings,
                secret_ref=secret_ref,
                api_key=credential_update.strip(),
            )
            encoded_api_key = "auth_mode_azure_secret_ref"
            normalized_azure_secret_ref = encode_provider_secret_ref(secret_ref=secret_ref)
    else:
        if normalized_auth_mode not in {"bearer", "none"}:
            raise ValueError(f"unsupported auth_mode: {normalized_auth_mode}")
        if normalized_auth_mode == "none":
            if api_key is not None and api_key.strip() != "":
                raise ValueError("api_key must be empty when auth_mode is none")
            encoded_api_key = "auth_mode_none"
        else:
            if api_key is not None:
                if api_key.strip() == "":
                    raise ValueError("api_key is required when auth_mode is bearer")
                secret_ref = build_provider_secret_ref(workspace_id=existing_provider["workspace_id"])
                write_provider_api_key(
                    settings=settings,
                    secret_ref=secret_ref,
                    api_key=api_key.strip(),
                )
                encoded_api_key = encode_provider_secret_ref(secret_ref=secret_ref)
            elif existing_provider["auth_mode"] != "bearer":
                raise ValueError("api_key is required when auth_mode is bearer")
        normalized_api_version = ""
        normalized_azure_secret_ref = ""

    provider = store.update_model_provider(
        provider_id=existing_provider["id"],
        workspace_id=existing_provider["workspace_id"],
        provider_key=provider_key,
        model_provider=existing_provider["model_provider"],
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        auth_mode=normalized_auth_mode,
        default_model=normalized_default_model,
        status=existing_provider["status"],
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=normalized_azure_secret_ref,
        metadata=normalized_metadata,
    )

    runtime_provider = resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(provider),
        settings=settings,
    )
    adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    discovery_status: str = "ready"
    discovery_error: str | None = None
    try:
        capability_snapshot = adapter.discover_capabilities(
            config=runtime_provider,
            settings=settings,
        )
    except ModelInvocationError as exc:
        sanitized_discovery_error = sanitize_provider_error_message(str(exc))
        extra_snapshot_fields = None
        if runtime_provider.provider_key == AZURE_ADAPTER_KEY:
            extra_snapshot_fields = {
                "azure_api_version": runtime_provider.azure_api_version.strip()
                or DEFAULT_AZURE_API_VERSION,
                "azure_auth_mode": runtime_provider.auth_mode,
            }
        capability_snapshot = _fallback_provider_capability_snapshot(
            adapter_key=adapter.adapter_key,
            runtime_provider=adapter.runtime_provider,
            model_list_path=normalized_model_list_path,
            healthcheck_path=normalized_healthcheck_path,
            invoke_path=normalized_invoke_path,
            extra_snapshot_fields=extra_snapshot_fields,
        )
        discovery_status = "failed"
        discovery_error = sanitized_discovery_error

    capability = store.upsert_provider_capability(
        workspace_id=existing_provider["workspace_id"],
        provider_id=provider["id"],
        discovered_by_user_account_id=updated_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status=discovery_status,
        capability_snapshot=capability_snapshot,
        discovery_error=discovery_error,
    )
    return provider, capability


def redact_url_credentials(raw_url: str) -> str:
    parsed = urlsplit(raw_url)

    if parsed.hostname is None or (parsed.username is None and parsed.password is None):
        return raw_url

    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    netloc = hostname
    if parsed.port is not None:
        netloc = f"{hostname}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def build_healthcheck_payload(settings: Settings, database_ok: bool) -> HealthcheckPayload:
    status: HealthStatus = "ok" if database_ok else "degraded"
    database_status: Literal["ok", "unreachable"] = "ok" if database_ok else "unreachable"

    return {
        "status": status,
        "environment": settings.app_env,
        "services": {
            "database": {
                "status": database_status,
            },
            "redis": {
                "status": "not_checked",
                "url": redact_url_credentials(settings.redis_url),
            },
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": settings.s3_endpoint_url,
            },
        },
    }


def _response_rate_limit_error(
    *,
    max_requests: int,
    window_seconds: int,
    retry_after_seconds: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after_seconds)},
        content={
            "detail": {
                "code": "response_rate_limit_exceeded",
                "message": (
                    "response generation rate limit exceeded; "
                    f"max {max_requests} requests per {window_seconds} seconds"
                ),
                "retry_after_seconds": retry_after_seconds,
            }
        },
    )


def _enforce_response_rate_limit(settings: Settings, user_id: UUID) -> JSONResponse | None:
    allowed, retry_after_seconds = response_rate_limiter.allow(
        key=f"responses:{user_id}",
        max_requests=settings.response_rate_limit_max_requests,
        window_seconds=settings.response_rate_limit_window_seconds,
    )
    if allowed:
        return None
    return _response_rate_limit_error(
        max_requests=settings.response_rate_limit_max_requests,
        window_seconds=settings.response_rate_limit_window_seconds,
        retry_after_seconds=retry_after_seconds,
    )


def _request_client_identifier(request: Request, settings: Settings) -> str:
    peer_host = ""
    if request.client is not None:
        peer_host = (request.client.host or "").strip()

    if (
        settings.trust_proxy_headers
        and peer_host != ""
        and peer_host in settings.trusted_proxy_ips
    ):
        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for != "":
            first_hop = forwarded_for.split(",", maxsplit=1)[0].strip()
            if first_hop != "":
                return first_hop

    if peer_host == "":
        return "unknown"
    return peer_host


def _request_client_is_loopback(request: Request, settings: Settings) -> bool:
    client_identifier = _request_client_identifier(request, settings)
    try:
        client_ip = ipaddress.ip_address(client_identifier)
    except ValueError:
        return client_identifier in {"localhost", "localhost.localdomain"}
    return client_ip.is_loopback


def _entrypoint_rate_limit_error(
    *,
    detail_code: str,
    message: str,
    max_requests: int,
    window_seconds: int,
    retry_after_seconds: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after_seconds)},
        content={
            "detail": {
                "code": detail_code,
                "message": message,
                "retry_after_seconds": retry_after_seconds,
                "window_seconds": window_seconds,
                "max_requests": max_requests,
            }
        },
    )


def _enforce_entrypoint_rate_limit(
    *,
    settings: Settings,
    key: str,
    max_requests: int,
    window_seconds: int,
    detail_code: str,
    message: str,
) -> JSONResponse | None:
    try:
        allowed, retry_after_seconds = entrypoint_rate_limiter.allow(
            settings=settings,
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
    except EntrypointRateLimiterUnavailableError:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "entrypoint_rate_limiter_unavailable",
                    "message": "entrypoint rate limiter backend is unavailable",
                }
            },
        )
    if allowed:
        return None
    return _entrypoint_rate_limit_error(
        detail_code=detail_code,
        message=message,
        max_requests=max_requests,
        window_seconds=window_seconds,
        retry_after_seconds=retry_after_seconds,
    )


def _append_vary_header(response: Response, value: str) -> None:
    existing = response.headers.get("Vary", "")
    values = [item.strip() for item in existing.split(",") if item.strip() != ""]
    if value not in values:
        values.append(value)
    response.headers["Vary"] = ", ".join(values)


def _cors_origin_allowed(origin: str, allowed_origins: tuple[str, ...]) -> bool:
    if len(allowed_origins) == 0:
        return False
    if "*" in allowed_origins:
        return True
    return origin in allowed_origins


def _resolve_cors_allow_origin_value(settings: Settings, origin: str) -> str:
    if "*" in settings.cors_allowed_origins and not settings.cors_allow_credentials:
        return "*"
    return origin


def _apply_cors_headers(
    *,
    response: Response,
    settings: Settings,
    origin: str,
    preflight: bool,
) -> None:
    allow_origin = _resolve_cors_allow_origin_value(settings, origin)
    response.headers["Access-Control-Allow-Origin"] = allow_origin
    if allow_origin != "*":
        _append_vary_header(response, "Origin")
    if settings.cors_allow_credentials:
        response.headers["Access-Control-Allow-Credentials"] = "true"

    if not preflight:
        return

    response.headers["Access-Control-Allow-Methods"] = ", ".join(settings.cors_allowed_methods)
    response.headers["Access-Control-Allow-Headers"] = ", ".join(settings.cors_allowed_headers)
    response.headers["Access-Control-Max-Age"] = str(settings.cors_preflight_max_age_seconds)
    _append_vary_header(response, "Access-Control-Request-Method")
    _append_vary_header(response, "Access-Control-Request-Headers")


def _apply_security_headers(*, response: Response, settings: Settings, request: Request) -> None:
    if not settings.security_headers_enabled:
        return

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), "
            "microphone=(), payment=(), usb=()"
        ),
    )

    if request.url.scheme != "https" or settings.app_env in {"development", "test"}:
        return

    hsts_value = f"max-age={settings.security_headers_hsts_max_age_seconds}"
    if settings.security_headers_hsts_include_subdomains:
        hsts_value += "; includeSubDomains"
    response.headers.setdefault("Strict-Transport-Security", hsts_value)


@app.middleware("http")
async def apply_http_security_posture(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    origin = request.headers.get("origin", "").strip()
    is_preflight = (
        request.method.upper() == "OPTIONS"
        and request.headers.get("access-control-request-method", "").strip() != ""
    )

    if is_preflight:
        if origin == "" or not _cors_origin_allowed(origin, settings.cors_allowed_origins):
            response = JSONResponse(status_code=403, content={"detail": "CORS origin is not allowed"})
            _apply_security_headers(response=response, settings=settings, request=request)
            return response
        response = Response(status_code=204)
        _apply_cors_headers(response=response, settings=settings, origin=origin, preflight=True)
        _apply_security_headers(response=response, settings=settings, request=request)
        return response

    response = await call_next(request)
    if origin != "" and _cors_origin_allowed(origin, settings.cors_allowed_origins):
        _apply_cors_headers(response=response, settings=settings, origin=origin, preflight=False)
    _apply_security_headers(response=response, settings=settings, request=request)
    return response


@app.middleware("http")
async def enforce_authenticated_user_identity(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not request.url.path.startswith("/v0/"):
        return await call_next(request)

    settings = get_settings()

    if settings.app_env not in {"development", "test"}:
        if not settings.legacy_v0_enabled_outside_dev:
            return JSONResponse(
                status_code=404,
                content={"detail": "legacy v0 API is disabled outside development and test"},
            )
        if not _request_client_is_loopback(request, settings):
            return JSONResponse(
                status_code=403,
                content={"detail": "legacy v0 API is restricted to loopback clients"},
            )

    try:
        authenticated_user_id = _resolve_authenticated_user_id(settings, request)
        if authenticated_user_id is not None:
            request.scope.setdefault("state", {})["authenticated_user_id"] = str(authenticated_user_id)
            _rewrite_user_id_query_param(request, authenticated_user_id)
            request = await _rewrite_user_id_json_body(request, authenticated_user_id)
    except ValueError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return await call_next(request)


class MagicLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)


class MagicLinkVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str = Field(min_length=16, max_length=256)
    device_label: str = Field(default="Primary device", min_length=1, max_length=120)
    device_key: str | None = Field(default=None, min_length=1, max_length=160)


class HostedWorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    slug: str | None = Field(default=None, min_length=1, max_length=120)


class HostedWorkspaceBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID | None = None


class DeviceLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_key: str = Field(min_length=1, max_length=160)
    device_label: str = Field(min_length=1, max_length=120)
    workspace_id: UUID | None = None


class DeviceLinkConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str = Field(min_length=16, max_length=256)


class HostedPreferencesPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str | None = Field(default=None, min_length=1, max_length=120)
    brief_preferences: dict[str, object] | None = None
    quiet_hours: dict[str, object] | None = None


class TelegramLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID | None = None


class TelegramLinkConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str = Field(min_length=16, max_length=256)


class TelegramUnlinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID | None = None


class TelegramDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4096)
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=160)


class TelegramMessageHandleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_hint: str | None = Field(default=None, min_length=1, max_length=40)


class TelegramOpenLoopReviewActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, min_length=1, max_length=500)


class TelegramApprovalResolveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, min_length=1, max_length=500)


class TelegramNotificationPreferencesPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notifications_enabled: bool | None = None
    daily_brief_enabled: bool | None = None
    daily_brief_window_start: str | None = Field(default=None, min_length=5, max_length=5)
    open_loop_prompts_enabled: bool | None = None
    waiting_for_prompts_enabled: bool | None = None
    stale_prompts_enabled: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=120)
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = Field(default=None, min_length=5, max_length=5)
    quiet_hours_end: str | None = Field(default=None, min_length=5, max_length=5)


class TelegramScheduledDeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class HostedRolloutFlagPatchItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag_key: str = Field(min_length=1, max_length=120)
    enabled: bool
    cohort_key: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class HostedRolloutFlagsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updates: list[HostedRolloutFlagPatchItemRequest] = Field(min_length=1, max_length=100)


class DesignPartnerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    partner_key: str | None = Field(default=None, min_length=1, max_length=120)
    lifecycle_stage: Literal["onboarding", "pilot", "active", "paused", "completed"] = "onboarding"
    onboarding_status: Literal["pending", "in_progress", "completed", "blocked"] = "pending"
    support_status: Literal["green", "watch", "needs_attention", "blocked"] = "green"
    instrumentation_status: Literal["not_ready", "partial", "ready"] = "not_ready"
    case_study_status: Literal["not_started", "candidate", "drafting", "approved", "published"] = (
        "not_started"
    )
    target_outcome: str | None = Field(default=None, min_length=1, max_length=500)
    launch_notes: str | None = Field(default=None, min_length=1, max_length=2000)
    onboarding_checklist: dict[str, object] | None = None
    support_checklist: dict[str, object] | None = None
    success_metrics: dict[str, object] | None = None


class DesignPartnerPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lifecycle_stage: Literal["onboarding", "pilot", "active", "paused", "completed"] | None = None
    onboarding_status: Literal["pending", "in_progress", "completed", "blocked"] | None = None
    support_status: Literal["green", "watch", "needs_attention", "blocked"] | None = None
    instrumentation_status: Literal["not_ready", "partial", "ready"] | None = None
    case_study_status: Literal["not_started", "candidate", "drafting", "approved", "published"] | None = None
    target_outcome: str | None = Field(default=None, min_length=1, max_length=500)
    launch_notes: str | None = Field(default=None, min_length=1, max_length=2000)
    onboarding_checklist: dict[str, object] | None = None
    support_checklist: dict[str, object] | None = None
    success_metrics: dict[str, object] | None = None


class DesignPartnerWorkspaceLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    linkage_status: Literal["pilot", "active", "paused"] = "pilot"
    environment_label: str = Field(default="pilot", min_length=1, max_length=80)
    instrumentation_ready: bool = False
    notes: str | None = Field(default=None, min_length=1, max_length=1000)


class DesignPartnerFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID | None = None
    source_kind: Literal["partner_call", "email", "slack", "operator_note", "survey", "support_review"]
    category: Literal["bug", "ux", "capability_gap", "onboarding", "support", "win"]
    sentiment: Literal["positive", "neutral", "negative"]
    urgency: Literal["low", "medium", "high"]
    feedback_status: Literal["new", "triaged", "actioned", "closed"] = "new"
    case_study_signal: bool = False
    summary: str = Field(min_length=1, max_length=400)
    detail: str | None = Field(default=None, min_length=1, max_length=2000)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_key: Literal["openai_compatible"] = OPENAI_COMPATIBLE_ADAPTER_KEY
    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=8000)
    auth_mode: Literal["bearer"] = "bearer"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/models", min_length=1, max_length=200)
    invoke_path: str = Field(default="/responses", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterOllamaProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:11434", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/api/tags", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/api/version", min_length=1, max_length=200)
    invoke_path: str = Field(default="/api/chat", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterLlamaCppProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:8080", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/v1/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/health", min_length=1, max_length=200)
    invoke_path: str = Field(default="/v1/chat/completions", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterVllmProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:8001", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/v1/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/health", min_length=1, max_length=200)
    invoke_path: str = Field(default="/v1/chat/completions", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterAzureProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=500)
    auth_mode: Literal["azure_api_key", "azure_ad_token"] = AZURE_AUTH_MODE_API_KEY
    api_key: str | None = Field(default=None, max_length=8000)
    ad_token: str | None = Field(default=None, max_length=16000)
    api_version: str = Field(default=DEFAULT_AZURE_API_VERSION, min_length=1, max_length=40)
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/openai/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/openai/models", min_length=1, max_length=200)
    invoke_path: str = Field(default="/openai/responses", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_auth_payload(self) -> "RegisterAzureProviderRequest":
        api_key = None if self.api_key is None else self.api_key.strip()
        ad_token = None if self.ad_token is None else self.ad_token.strip()

        if self.auth_mode == AZURE_AUTH_MODE_API_KEY:
            if api_key in (None, ""):
                raise ValueError("api_key is required when auth_mode is azure_api_key")
            if ad_token not in (None, ""):
                raise ValueError("ad_token must be empty when auth_mode is azure_api_key")
            return self

        if ad_token in (None, ""):
            raise ValueError("ad_token is required when auth_mode is azure_ad_token")
        if api_key not in (None, ""):
            raise ValueError("api_key must be empty when auth_mode is azure_ad_token")
        return self


class TestProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: UUID
    model: str | None = Field(default=None, min_length=1, max_length=200)
    prompt: str = Field(
        default="Reply with a concise provider connectivity confirmation.",
        min_length=1,
        max_length=1000,
    )


class UpdateProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_mode: str | None = Field(default=None, min_length=1, max_length=40)
    api_key: str | None = Field(default=None, max_length=8000)
    ad_token: str | None = Field(default=None, max_length=16000)
    api_version: str | None = Field(default=None, min_length=1, max_length=40)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    model_list_path: str | None = Field(default=None, min_length=1, max_length=200)
    healthcheck_path: str | None = Field(default=None, min_length=1, max_length=200)
    invoke_path: str | None = Field(default=None, min_length=1, max_length=200)
    metadata: dict[str, object] | None = None


class CreateModelPackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str = Field(min_length=1, max_length=80)
    pack_version: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    family: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=1000)
    briefing_strategy: str = Field(default="balanced", min_length=1, max_length=40)
    briefing_max_tokens: int | None = Field(default=None, ge=32, le=4000)
    contract: dict[str, object]
    metadata: dict[str, object] = Field(default_factory=dict)


class BindModelPackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: UUID | None = None
    pack_version: str | None = Field(default=None, min_length=1, max_length=40)
    metadata: dict[str, object] = Field(default_factory=dict)


class TaskBriefCompileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["user_recall", "resume", "worker_subtask", "agent_handoff"]
    query: str | None = Field(default=None, min_length=1, max_length=4000)
    workspace_id: UUID | None = None
    pack_id: str | None = Field(default=None, min_length=1, max_length=80)
    pack_version: str | None = Field(default=None, min_length=1, max_length=40)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    since: datetime | None = None
    until: datetime | None = None
    include_non_promotable_facts: bool = False
    provider_strategy: str | None = Field(default=None, min_length=1, max_length=80)
    model_pack_strategy: str | None = Field(default=None, min_length=1, max_length=40)
    token_budget: int | None = Field(default=None, ge=1, le=MAX_TASK_BRIEF_TOKEN_BUDGET)


class TaskBriefCompileRequest(TaskBriefCompileSpec):
    user_id: UUID


class TaskBriefCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    primary: TaskBriefCompileSpec
    secondary: TaskBriefCompileSpec


class RuntimeInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: UUID
    thread_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    pack_id: str | None = Field(default=None, min_length=1, max_length=80)
    pack_version: str | None = Field(default=None, min_length=1, max_length=40)
    max_sessions: int = Field(default=DEFAULT_MAX_SESSIONS, ge=1, le=50)
    max_events: int = Field(default=DEFAULT_MAX_EVENTS, ge=1, le=200)
    max_memories: int = Field(default=DEFAULT_MAX_MEMORIES, ge=1, le=200)
    max_entities: int = Field(default=DEFAULT_MAX_ENTITIES, ge=1, le=200)
    max_entity_edges: int = Field(default=DEFAULT_MAX_ENTITY_EDGES, ge=1, le=400)


def _extract_bearer_token(request: Request) -> str:
    raw_authorization = request.headers.get("authorization", "").strip()
    if raw_authorization == "":
        raise AuthSessionInvalidError("authorization bearer token is required")

    scheme, _, token = raw_authorization.partition(" ")
    if scheme.lower() != "bearer" or token.strip() == "":
        raise AuthSessionInvalidError("authorization header must use Bearer token format")
    return token.strip()


def _resolve_authenticated_v1_user_id(settings: Settings, request: Request) -> UUID:
    session_token = _extract_bearer_token(request)
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            resolution = resolve_auth_session(conn, session_token=session_token)
    user_account_id = resolution["user_account"]["id"]
    if not isinstance(user_account_id, UUID):
        raise RuntimeError("authenticated hosted user context is invalid")
    return user_account_id


def _serialize_hosted_session_payload(
    *,
    session: dict[str, object],
    user_account: dict[str, object],
    workspace: dict[str, object] | None,
    preferences: dict[str, object],
    feature_flags: list[str],
) -> dict[str, object]:
    return {
        "session": session,
        "user_account": user_account,
        "workspace": workspace,
        "preferences": preferences,
        "feature_flags": feature_flags,
        "telegram_state": "available_in_p10_s2_transport",
    }


def _resolve_workspace_for_hosted_channel_request(
    conn,
    *,
    user_account_id: UUID,
    session_id: UUID,
    preferred_workspace_id: UUID | None,
    requested_workspace_id: UUID | None,
):
    if requested_workspace_id is not None:
        workspace = get_workspace_for_member(
            conn,
            workspace_id=requested_workspace_id,
            user_account_id=user_account_id,
        )
        if workspace is None:
            raise HostedWorkspaceNotFoundError(f"workspace {requested_workspace_id} was not found")
        if preferred_workspace_id != workspace["id"]:
            set_session_workspace(
                conn,
                session_id=session_id,
                user_account_id=user_account_id,
                workspace_id=workspace["id"],
            )
        return workspace

    workspace = get_current_workspace(
        conn,
        user_account_id=user_account_id,
        preferred_workspace_id=preferred_workspace_id,
    )
    if workspace is None:
        return None
    if preferred_workspace_id != workspace["id"]:
        set_session_workspace(
            conn,
            session_id=session_id,
            user_account_id=user_account_id,
            workspace_id=workspace["id"],
        )
    return workspace


def _ensure_hosted_admin_access(conn, *, user_account_id: UUID) -> None:
    enabled_flags = set(list_feature_flags_for_user(conn, user_account_id=user_account_id))
    required_flags = {"hosted_admin_read", "hosted_admin_operator"}
    missing_flags = sorted(required_flags - enabled_flags)
    if missing_flags:
        raise PermissionError(
            "hosted admin access requires hosted_admin_read and hosted_admin_operator flags"
        )
    set_hosted_admin_bypass(conn, True)


def _ensure_workspace_owner_access(*, workspace, user_account_id: UUID) -> None:
    if workspace["owner_user_account_id"] != user_account_id:
        raise PermissionError("workspace owner access is required")


def _allow_raw_evidence_debug_access(settings: Settings) -> bool:
    return settings.app_env in {"development", "test"}


def _audit_raw_evidence_access(
    *,
    request: Request,
    settings: Settings,
    route: str,
    user_id: UUID,
) -> None:
    LOGGER.info(
        "raw evidence content requested route=%s user_id=%s client=%s",
        route,
        user_id,
        _request_client_identifier(request, settings),
    )


def _record_workspace_onboarding_failure(
    conn,
    *,
    workspace_id: UUID,
    error_code: str,
    error_detail: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE workspaces
            SET support_status = CASE WHEN support_status = 'blocked' THEN support_status ELSE 'needs_attention' END,
                onboarding_last_error_code = %s,
                onboarding_last_error_detail = %s,
                onboarding_last_error_at = clock_timestamp(),
                onboarding_error_count = onboarding_error_count + 1,
                support_notes = COALESCE(support_notes, '{}'::jsonb) || jsonb_build_object(
                    'last_onboarding_error_code', %s::text,
                    'last_onboarding_error_detail', %s::text,
                    'last_onboarding_error_at', clock_timestamp()
                ),
                incident_evidence = COALESCE(incident_evidence, '{}'::jsonb) || jsonb_build_object(
                    'last_onboarding_error_code', %s::text,
                    'last_onboarding_error_detail', %s::text
                )
            WHERE id = %s
            """,
            (
                error_code,
                error_detail,
                error_code,
                error_detail,
                error_code,
                error_detail,
                workspace_id,
            ),
        )


def _hosted_rollout_block_error(
    *,
    flag_key: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "detail": {
                "code": "hosted_rollout_blocked",
                "message": f"hosted flow is blocked by rollout flag {flag_key}",
                "flag_key": flag_key,
            }
        },
    )


def _hosted_rate_limit_error(
    *,
    detail_code: str,
    message: str,
    retry_after_seconds: int,
    rate_limit_key: str,
    window_seconds: int,
    max_requests: int,
    observed_requests: int,
    abuse_signal: str | None,
) -> JSONResponse:
    payload: dict[str, object] = {
        "code": detail_code,
        "message": message,
        "retry_after_seconds": retry_after_seconds,
        "rate_limit_key": rate_limit_key,
        "window_seconds": window_seconds,
        "max_requests": max_requests,
        "observed_requests": observed_requests,
    }
    if abuse_signal is not None:
        payload["abuse_signal"] = abuse_signal

    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after_seconds)},
        content={"detail": payload},
    )


@app.get("/healthz")
def healthcheck() -> JSONResponse:
    settings = get_settings()
    database_ok = ping_database(
        settings.database_url,
        settings.healthcheck_timeout_seconds,
    )
    payload = build_healthcheck_payload(settings, database_ok)
    status_code = 200 if payload["status"] == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


@app.get("/v0/agent-profiles")
def list_agent_profiles() -> JSONResponse:
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        items = list_registered_agent_profiles(ContinuityStore(conn))
    summary: AgentProfileListSummary = {
        "total_count": len(items),
        "order": list(AGENT_PROFILE_LIST_ORDER),
    }
    payload: AgentProfileListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/context/compile")
def compile_context(request: CompileContextRequest) -> JSONResponse:
    settings = get_settings()
    artifact_retrieval = None
    semantic_artifact_retrieval = None
    if isinstance(request.artifact_retrieval, CompileContextTaskScopedArtifactRetrievalRequest):
        artifact_retrieval = CompileContextTaskScopedArtifactRetrievalInput(
            task_id=request.artifact_retrieval.task_id,
            query=request.artifact_retrieval.query,
            limit=request.artifact_retrieval.limit,
        )
    elif isinstance(
        request.artifact_retrieval,
        CompileContextArtifactScopedArtifactRetrievalRequest,
    ):
        artifact_retrieval = CompileContextArtifactScopedArtifactRetrievalInput(
            task_artifact_id=request.artifact_retrieval.task_artifact_id,
            query=request.artifact_retrieval.query,
            limit=request.artifact_retrieval.limit,
        )
    if isinstance(
        request.semantic_artifact_retrieval,
        CompileContextTaskScopedSemanticArtifactRetrievalRequest,
    ):
        semantic_artifact_retrieval = CompileContextTaskScopedSemanticArtifactRetrievalInput(
            task_id=request.semantic_artifact_retrieval.task_id,
            embedding_config_id=request.semantic_artifact_retrieval.embedding_config_id,
            query_vector=tuple(request.semantic_artifact_retrieval.query_vector),
            limit=request.semantic_artifact_retrieval.limit,
        )
    elif isinstance(
        request.semantic_artifact_retrieval,
        CompileContextArtifactScopedSemanticArtifactRetrievalRequest,
    ):
        semantic_artifact_retrieval = (
            CompileContextArtifactScopedSemanticArtifactRetrievalInput(
                task_artifact_id=request.semantic_artifact_retrieval.task_artifact_id,
                embedding_config_id=request.semantic_artifact_retrieval.embedding_config_id,
                query_vector=tuple(request.semantic_artifact_retrieval.query_vector),
                limit=request.semantic_artifact_retrieval.limit,
            )
        )

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = ContinuityStore(conn)
            thread = store.get_thread(request.thread_id)
            result = compile_and_persist_trace(
                store,
                user_id=request.user_id,
                thread_id=request.thread_id,
                limits=ContextCompilerLimits(
                    max_sessions=request.max_sessions,
                    max_events=request.max_events,
                    max_memories=request.max_memories,
                    max_entities=request.max_entities,
                    max_entity_edges=request.max_entity_edges,
                ),
                semantic_retrieval=(
                    None
                    if request.semantic is None
                    else CompileContextSemanticRetrievalInput(
                        embedding_config_id=request.semantic.embedding_config_id,
                        query_vector=tuple(request.semantic.query_vector),
                        limit=request.semantic.limit,
                    )
                ),
                artifact_retrieval=artifact_retrieval,
                semantic_artifact_retrieval=semantic_artifact_retrieval,
            )
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except SemanticMemoryRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (TaskNotFoundError, TaskArtifactNotFoundError) as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "trace_id": result.trace_id,
                "trace_event_count": result.trace_event_count,
                "context_pack": result.context_pack,
                "metadata": {"agent_profile_id": _thread_agent_profile_id(thread)},
            }
        ),
    )


@app.post("/v0/responses")
def generate_assistant_response(request: GenerateResponseRequest) -> JSONResponse:
    settings = get_settings()
    rate_limit_error = _enforce_response_rate_limit(settings, request.user_id)
    if rate_limit_error is not None:
        return rate_limit_error

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = ContinuityStore(conn)
            thread = store.get_thread(request.thread_id)
            result = generate_response(
                store=store,
                settings=settings,
                user_id=request.user_id,
                thread_id=request.thread_id,
                message_text=request.message,
                limits=ContextCompilerLimits(
                    max_sessions=request.max_sessions,
                    max_events=request.max_events,
                    max_memories=request.max_memories,
                    max_entities=request.max_entities,
                    max_entity_edges=request.max_entity_edges,
                ),
            )
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if isinstance(result, ResponseFailure):
        return JSONResponse(
            status_code=502,
            content=jsonable_encoder(
                {
                    "detail": result.detail,
                    "trace": result.trace,
                    "metadata": {"agent_profile_id": _thread_agent_profile_id(thread)},
                }
            ),
        )

    response_payload = dict(result)
    response_payload["metadata"] = {"agent_profile_id": _thread_agent_profile_id(thread)}
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(response_payload),
    )


@app.post("/v0/threads")
def create_thread(request: CreateThreadRequest) -> JSONResponse:
    settings = get_settings()
    agent_profile_id = (
        request.agent_profile_id
        if request.agent_profile_id is not None
        else DEFAULT_AGENT_PROFILE_ID
    )
    thread_input = ThreadCreateInput(
        title=request.title,
        agent_profile_id=agent_profile_id,
    )

    with user_connection(settings.database_url, request.user_id) as conn:
        store = ContinuityStore(conn)
        if get_registered_agent_profile(store, agent_profile_id) is None:
            allowed_agent_profile_ids = list_registered_agent_profile_ids(store)
            return JSONResponse(
                status_code=422,
                content={
                    "detail": {
                        "code": "invalid_agent_profile_id",
                        "message": (
                            "agent_profile_id must be one of: "
                            + ", ".join(allowed_agent_profile_ids)
                        ),
                        "allowed_agent_profile_ids": allowed_agent_profile_ids,
                    }
                },
            )

        created = store.create_thread(
            thread_input.title,
            thread_input.agent_profile_id,
        )

    payload: ThreadCreateResponse = {"thread": _serialize_thread(created)}
    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads")
def list_threads(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        items = [_serialize_thread(thread) for thread in ContinuityStore(conn).list_threads()]

    summary: ThreadListSummary = {
        "total_count": len(items),
        "order": list(THREAD_LIST_ORDER),
    }
    payload: ThreadListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/health-dashboard")
def get_threads_health_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: ThreadHealthDashboardResponse = get_thread_health_dashboard(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}")
def get_thread(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        thread = ContinuityStore(conn).get_thread_optional(thread_id)

    if thread is None:
        return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})

    payload: ThreadDetailResponse = {"thread": _serialize_thread(thread)}
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/sessions")
def list_thread_sessions(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        items = [_serialize_thread_session(session) for session in store.list_thread_sessions(thread_id)]

    summary: ThreadSessionListSummary = {
        "thread_id": str(thread["id"]),
        "total_count": len(items),
        "order": list(THREAD_SESSION_LIST_ORDER),
    }
    payload: ThreadSessionListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/events")
def list_thread_events(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        items = [_serialize_thread_event(event) for event in store.list_thread_events(thread_id)]

    summary: ThreadEventListSummary = {
        "thread_id": str(thread["id"]),
        "total_count": len(items),
        "order": list(THREAD_EVENT_LIST_ORDER),
    }
    payload: ThreadEventListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/resumption-brief")
def get_thread_resumption_brief(
    thread_id: UUID,
    user_id: UUID,
    max_events: Annotated[
        int,
        Query(ge=0, le=MAX_RESUMPTION_BRIEF_EVENT_LIMIT),
    ] = DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    max_open_loops: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
        ),
    ] = DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    max_memories: Annotated[
        int,
        Query(ge=0, le=MAX_RESUMPTION_BRIEF_MEMORY_LIMIT),
    ] = DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
) -> JSONResponse:
    settings = get_settings()
    request = ResumptionBriefRequestInput(
        thread_id=thread_id,
        max_events=max_events,
        max_open_loops=max_open_loops,
        max_memories=max_memories,
    )

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        brief = compile_resumption_brief(
            store,
            thread=thread,
            event_limit=request.max_events,
            open_loop_limit=request.max_open_loops,
            memory_limit=request.max_memories,
        )

    payload: ResumptionBriefResponse = {"brief": brief}
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces")
def list_traces(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_trace_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces/{trace_id}")
def get_trace(trace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_trace_record(
                ContinuityStore(conn),
                user_id=user_id,
                trace_id=trace_id,
            )
    except TraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces/{trace_id}/events")
def list_trace_events(trace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_trace_event_records(
                ContinuityStore(conn),
                user_id=user_id,
                trace_id=trace_id,
            )
    except TraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/admit")
def admit_memory(request: AdmitMemoryRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            decision = admit_memory_candidate(
                ContinuityStore(conn),
                user_id=request.user_id,
                candidate=MemoryCandidateInput(
                    memory_key=request.memory_key,
                    value=request.value,
                    source_event_ids=tuple(request.source_event_ids),
                    agent_profile_id=request.agent_profile_id,
                    delete_requested=request.delete_requested,
                    memory_type=request.memory_type,
                    confidence=request.confidence,
                    salience=request.salience,
                    confirmation_status=request.confirmation_status,
                    trust_class=request.trust_class,
                    promotion_eligibility=request.promotion_eligibility,
                    evidence_count=request.evidence_count,
                    independent_source_count=request.independent_source_count,
                    extracted_by_model=request.extracted_by_model,
                    trust_reason=request.trust_reason,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                    last_confirmed_at=request.last_confirmed_at,
                    open_loop=(
                        None
                        if request.open_loop is None
                        else OpenLoopCandidateInput(
                            title=request.open_loop.title,
                            due_at=request.open_loop.due_at,
                        )
                    ),
                ),
            )
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    payload = {
        "decision": decision.action,
        "reason": decision.reason,
        "memory": decision.memory,
        "revision": decision.revision,
    }
    if decision.open_loop is not None:
        payload["open_loop"] = decision.open_loop

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/open-loops")
def list_open_loops(
    user_id: UUID,
    status: OpenLoopStatusFilter = Query(default="open"),
    limit: int = Query(default=DEFAULT_OPEN_LOOP_LIMIT, ge=1, le=MAX_OPEN_LOOP_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_open_loop_records(
            ContinuityStore(conn),
            user_id=user_id,
            status=status,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/open-loops/{open_loop_id}")
def get_open_loop(
    open_loop_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_open_loop_record(
                ContinuityStore(conn),
                user_id=user_id,
                open_loop_id=open_loop_id,
            )
    except OpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops")
def create_open_loop(request: CreateOpenLoopRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_open_loop_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                open_loop=OpenLoopCreateInput(
                    memory_id=request.memory_id,
                    title=request.title,
                    due_at=request.due_at,
                ),
            )
    except OpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops/{open_loop_id}/status")
def update_open_loop_status(
    open_loop_id: UUID,
    request: UpdateOpenLoopStatusRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = update_open_loop_status_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                open_loop_id=open_loop_id,
                request=OpenLoopStatusUpdateInput(
                    status=request.status,  # type: ignore[arg-type]
                    resolution_note=request.resolution_note,
                ),
            )
    except OpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except OpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/consents")
def upsert_consent(request: UpsertConsentRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_consent_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                consent=ConsentUpsertInput(
                    consent_key=request.consent_key,
                    status=request.status,
                    metadata=request.metadata,
                ),
            )
    except PolicyValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    status_code = 201 if payload["write_mode"] == "created" else 200
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/consents")
def list_consents(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_consent_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/policies")
def create_policy(request: CreatePolicyRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = ContinuityStore(conn)
            if (
                request.agent_profile_id is not None
                and get_registered_agent_profile(store, request.agent_profile_id) is None
            ):
                allowed_agent_profile_ids = list_registered_agent_profile_ids(store)
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": {
                            "code": "invalid_agent_profile_id",
                            "message": (
                                "agent_profile_id must be one of: "
                                + ", ".join(allowed_agent_profile_ids)
                            ),
                            "allowed_agent_profile_ids": allowed_agent_profile_ids,
                        }
                    },
                )

            payload = create_policy_record(
                store,
                user_id=request.user_id,
                policy=PolicyCreateInput(
                    name=request.name,
                    action=request.action,
                    scope=request.scope,
                    effect=request.effect,
                    priority=request.priority,
                    active=request.active,
                    conditions=request.conditions,
                    required_consents=tuple(request.required_consents),
                    agent_profile_id=request.agent_profile_id,
                ),
            )
    except PolicyValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/policies")
def list_policies(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_policy_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/policies/{policy_id}")
def get_policy(policy_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_policy_record(
                ContinuityStore(conn),
                user_id=user_id,
                policy_id=policy_id,
            )
    except PolicyNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/policies/evaluate")
def evaluate_policy(request: EvaluatePolicyRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = evaluate_policy_request(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=PolicyEvaluationRequestInput(
                    thread_id=request.thread_id,
                    action=request.action,
                    scope=request.scope,
                    attributes=request.attributes,
                ),
            )
    except PolicyEvaluationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools")
def create_tool(request: CreateToolRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_tool_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                tool=ToolCreateInput(
                    tool_key=request.tool_key,
                    name=request.name,
                    description=request.description,
                    version=request.version,
                    metadata_version=request.metadata_version,
                    active=request.active,
                    tags=tuple(request.tags),
                    action_hints=tuple(request.action_hints),
                    scope_hints=tuple(request.scope_hints),
                    domain_hints=tuple(request.domain_hints),
                    risk_hints=tuple(request.risk_hints),
                    metadata=request.metadata,
                ),
            )
    except ToolValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tools")
def list_tools(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_tool_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools/allowlist/evaluate")
def evaluate_tools_allowlist(request: EvaluateToolAllowlistRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = evaluate_tool_allowlist(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ToolAllowlistEvaluationRequestInput(
                    thread_id=request.thread_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=request.attributes,
                ),
            )
    except ToolAllowlistValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools/route")
def route_tool(request: RouteToolRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = route_tool_invocation(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ToolRoutingRequestInput(
                    thread_id=request.thread_id,
                    tool_id=request.tool_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=request.attributes,
                ),
            )
    except ToolRoutingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/requests")
def create_approval_request(request: CreateApprovalRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = submit_approval_request(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ApprovalRequestCreateInput(
                    thread_id=request.thread_id,
                    tool_id=request.tool_id,
                    task_run_id=request.task_run_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=request.attributes,
                ),
            )
    except ToolRoutingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/approvals")
def list_approvals(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_approval_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/approvals/{approval_id}")
def get_approval(approval_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_approval_record(
                ContinuityStore(conn),
                user_id=user_id,
                approval_id=approval_id,
            )
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/approve")
def approve_approval(approval_id: UUID, request: ResolveApprovalRequest) -> JSONResponse:
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = approve_approval_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ApprovalApproveInput(approval_id=approval_id),
                )
            except (
                ApprovalResolutionConflictError,
                TaskStepApprovalLinkageError,
                TaskStepLifecycleBoundaryError,
            ) as exc:
                resolution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/reject")
def reject_approval(approval_id: UUID, request: ResolveApprovalRequest) -> JSONResponse:
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = reject_approval_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ApprovalRejectInput(approval_id=approval_id),
                )
            except (
                ApprovalResolutionConflictError,
                TaskStepApprovalLinkageError,
                TaskStepLifecycleBoundaryError,
            ) as exc:
                resolution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/execute")
def execute_approved_proxy(approval_id: UUID, request: ExecuteApprovedProxyRequest) -> JSONResponse:
    settings = get_settings()
    execution_error: (
        ProxyExecutionApprovalStateError
        | ProxyExecutionHandlerNotFoundError
        | ProxyExecutionIdempotencyError
        | TaskStepApprovalLinkageError
        | TaskStepExecutionLinkageError
        | None
    ) = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = execute_approved_proxy_request(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ProxyExecutionRequestInput(
                        approval_id=approval_id,
                        task_run_id=request.task_run_id,
                    ),
                )
            except (
                ProxyExecutionApprovalStateError,
                ProxyExecutionHandlerNotFoundError,
                ProxyExecutionIdempotencyError,
                TaskStepApprovalLinkageError,
                TaskStepExecutionLinkageError,
            ) as exc:
                execution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if execution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(execution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks")
def list_tasks(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}")
def get_task(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/runs")
def create_task_run(task_id: UUID, request: CreateTaskRunRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_task_run_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskRunCreateInput(
                    task_id=task_id,
                    max_ticks=request.max_ticks,
                    retry_cap=request.retry_cap,
                    checkpoint=request.checkpoint,
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskRunValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}/runs")
def list_task_runs(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_run_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-runs/{task_run_id}")
def get_task_run(task_run_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_run_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_run_id=task_run_id,
            )
    except TaskRunNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


def _mutate_task_run(
    *,
    task_run_id: UUID,
    request: MutateTaskRunRequest,
    mutation_handler: Callable[..., object],
    mutation_input_model: type[TaskRunTickInput]
    | type[TaskRunPauseInput]
    | type[TaskRunResumeInput]
    | type[TaskRunCancelInput],
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = mutation_handler(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=mutation_input_model(task_run_id=task_run_id),
            )
    except TaskRunValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except TaskRunNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskRunTransitionError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-runs/{task_run_id}/tick")
def tick_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=tick_task_run_record,
        mutation_input_model=TaskRunTickInput,
    )


@app.post("/v0/task-runs/{task_run_id}/pause")
def pause_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=pause_task_run_record,
        mutation_input_model=TaskRunPauseInput,
    )


@app.post("/v0/task-runs/{task_run_id}/resume")
def resume_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=resume_task_run_record,
        mutation_input_model=TaskRunResumeInput,
    )


@app.post("/v0/task-runs/{task_run_id}/cancel")
def cancel_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=cancel_task_run_record,
        mutation_input_model=TaskRunCancelInput,
    )


@app.post("/v0/gmail-accounts")
def connect_gmail_account(request: ConnectGmailAccountRequest) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_gmail_secret_manager(settings.gmail_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_gmail_account_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=GmailAccountConnectInput(
                    provider_account_id=request.provider_account_id,
                    email_address=request.email_address,
                    display_name=request.display_name,
                    scope=request.scope,
                    access_token=request.access_token,
                    refresh_token=request.refresh_token,
                    client_id=request.client_id,
                    client_secret=request.client_secret,
                    access_token_expires_at=request.access_token_expires_at,
                ),
            )
    except GmailCredentialValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except GmailCredentialPersistenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except GmailAccountAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/gmail-accounts")
def list_gmail_accounts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_gmail_account_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/gmail-accounts/{gmail_account_id}")
def get_gmail_account(gmail_account_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_gmail_account_record(
                ContinuityStore(conn),
                user_id=user_id,
                gmail_account_id=gmail_account_id,
            )
    except GmailAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest")
def ingest_gmail_message(
    gmail_account_id: UUID,
    provider_message_id: str,
    request: IngestGmailMessageRequest,
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_gmail_secret_manager(settings.gmail_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_gmail_message_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=GmailMessageIngestInput(
                    gmail_account_id=gmail_account_id,
                    task_workspace_id=request.task_workspace_id,
                    provider_message_id=provider_message_id,
                ),
            )
    except GmailAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except GmailMessageNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except GmailMessageUnsupportedError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (
        GmailCredentialNotFoundError,
        GmailCredentialInvalidError,
        GmailCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (GmailMessageFetchError, GmailCredentialRefreshError) as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/calendar-accounts")
def connect_calendar_account(request: ConnectCalendarAccountRequest) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_calendar_account_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=CalendarAccountConnectInput(
                    provider_account_id=request.provider_account_id,
                    email_address=request.email_address,
                    display_name=request.display_name,
                    scope=request.scope,
                    access_token=request.access_token,
                ),
            )
    except CalendarCredentialValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarCredentialPersistenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except CalendarAccountAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts")
def list_calendar_accounts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_calendar_account_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts/{calendar_account_id}")
def get_calendar_account(calendar_account_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_calendar_account_record(
                ContinuityStore(conn),
                user_id=user_id,
                calendar_account_id=calendar_account_id,
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts/{calendar_account_id}/events")
def list_calendar_events(
    calendar_account_id: UUID,
    user_id: UUID,
    limit: int = Query(default=DEFAULT_CALENDAR_EVENT_LIST_LIMIT, ge=1, le=MAX_CALENDAR_EVENT_LIST_LIMIT),
    time_min: datetime | None = Query(default=None),
    time_max: datetime | None = Query(default=None),
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_calendar_event_records(
                ContinuityStore(conn),
                secret_manager,
                user_id=user_id,
                request=CalendarEventListInput(
                    calendar_account_id=calendar_account_id,
                    limit=limit,
                    time_min=time_min,
                    time_max=time_max,
                ),
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except (
        CalendarCredentialNotFoundError,
        CalendarCredentialInvalidError,
        CalendarCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except CalendarEventListValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarEventFetchError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest")
def ingest_calendar_event(
    calendar_account_id: UUID,
    provider_event_id: str,
    request: IngestCalendarEventRequest,
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_calendar_event_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=CalendarEventIngestInput(
                    calendar_account_id=calendar_account_id,
                    task_workspace_id=request.task_workspace_id,
                    provider_event_id=provider_event_id,
                ),
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except CalendarEventNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except CalendarEventUnsupportedError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (
        CalendarCredentialNotFoundError,
        CalendarCredentialInvalidError,
        CalendarCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarEventFetchError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/workspace")
def create_task_workspace(task_id: UUID, request: CreateTaskWorkspaceRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_task_workspace_record(
                ContinuityStore(conn),
                settings=settings,
                user_id=request.user_id,
                request=TaskWorkspaceCreateInput(
                    task_id=task_id,
                    status="active",
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except (TaskWorkspaceAlreadyExistsError, TaskWorkspaceProvisioningError) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-workspaces")
def list_task_workspaces(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_workspace_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-workspaces/{task_workspace_id}")
def get_task_workspace(task_workspace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_workspace_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_workspace_id=task_workspace_id,
            )
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}/steps")
def list_task_steps(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_step_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-steps/{task_step_id}")
def get_task_step(task_step_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_step_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_step_id=task_step_id,
            )
    except TaskStepNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-workspaces/{task_workspace_id}/artifacts")
def register_task_artifact(
    task_workspace_id: UUID,
    request: RegisterTaskArtifactRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = register_task_artifact_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactRegisterInput(
                    task_workspace_id=task_workspace_id,
                    local_path=request.local_path,
                    media_type_hint=request.media_type_hint,
                ),
            )
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts")
def list_task_artifacts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_artifact_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}")
def get_task_artifact(task_artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_artifact_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/ingest")
def ingest_task_artifact(
    task_artifact_id: UUID,
    request: IngestTaskArtifactRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_task_artifact_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactIngestInput(task_artifact_id=task_artifact_id),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}/chunks")
def list_task_artifact_chunks(task_artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/artifact-chunks/retrieve")
def retrieve_task_artifact_chunks(
    task_id: UUID,
    request: RetrieveArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_task_scoped_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskScopedArtifactChunkRetrievalInput(
                    task_id=task_id,
                    query=request.query,
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/chunks/retrieve")
def retrieve_task_artifact_chunks_for_artifact(
    task_artifact_id: UUID,
    request: RetrieveArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_artifact_scoped_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ArtifactScopedArtifactChunkRetrievalInput(
                    task_artifact_id=task_artifact_id,
                    query=request.query,
                ),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval")
def retrieve_semantic_task_artifact_chunks(
    task_id: UUID,
    request: RetrieveSemanticArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_task_scoped_semantic_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskScopedSemanticArtifactChunkRetrievalInput(
                    task_id=task_id,
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval")
def retrieve_semantic_artifact_chunks_for_artifact(
    task_artifact_id: UUID,
    request: RetrieveSemanticArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_artifact_scoped_semantic_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ArtifactScopedSemanticArtifactChunkRetrievalInput(
                    task_artifact_id=task_artifact_id,
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/steps")
def create_next_task_step(task_id: UUID, request: CreateNextTaskStepRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_next_task_step_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskStepNextCreateInput(
                    task_id=task_id,
                    kind=request.kind,
                    status=request.status,
                    request=request.request.model_dump(mode="json"),
                    outcome=request.outcome.model_dump(mode="json"),
                    lineage=TaskStepLineageInput(
                        parent_step_id=request.lineage.parent_step_id,
                        source_approval_id=request.lineage.source_approval_id,
                        source_execution_id=request.lineage.source_execution_id,
                    ),
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskStepSequenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-steps/{task_step_id}/transition")
def transition_task_step(task_step_id: UUID, request: TransitionTaskStepRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = transition_task_step_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskStepTransitionInput(
                    task_step_id=task_step_id,
                    status=request.status,
                    outcome=request.outcome.model_dump(mode="json"),
                ),
            )
    except TaskStepNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskStepTransitionError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets")
def create_execution_budget(request: CreateExecutionBudgetRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_execution_budget_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExecutionBudgetCreateInput(
                    agent_profile_id=request.agent_profile_id,
                    tool_key=request.tool_key,
                    domain_hint=request.domain_hint,
                    max_completed_executions=request.max_completed_executions,
                    rolling_window_seconds=request.rolling_window_seconds,
                ),
            )
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/execution-budgets")
def list_execution_budgets(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_execution_budget_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/execution-budgets/{execution_budget_id}")
def get_execution_budget(execution_budget_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_execution_budget_record(
                ContinuityStore(conn),
                user_id=user_id,
                execution_budget_id=execution_budget_id,
            )
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets/{execution_budget_id}/deactivate")
def deactivate_execution_budget(
    execution_budget_id: UUID,
    request: DeactivateExecutionBudgetRequest,
) -> JSONResponse:
    settings = get_settings()
    lifecycle_error: ExecutionBudgetLifecycleError | None = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = deactivate_execution_budget_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ExecutionBudgetDeactivateInput(
                        thread_id=request.thread_id,
                        execution_budget_id=execution_budget_id,
                    ),
                )
            except ExecutionBudgetLifecycleError as exc:
                lifecycle_error = exc
                payload = None
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if lifecycle_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(lifecycle_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets/{execution_budget_id}/supersede")
def supersede_execution_budget(
    execution_budget_id: UUID,
    request: SupersedeExecutionBudgetRequest,
) -> JSONResponse:
    settings = get_settings()
    lifecycle_error: ExecutionBudgetLifecycleError | None = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = supersede_execution_budget_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ExecutionBudgetSupersedeInput(
                        thread_id=request.thread_id,
                        execution_budget_id=execution_budget_id,
                        max_completed_executions=request.max_completed_executions,
                    ),
                )
            except ExecutionBudgetLifecycleError as exc:
                lifecycle_error = exc
                payload = None
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if lifecycle_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(lifecycle_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tool-executions")
def list_tool_executions(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_tool_execution_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tool-executions/{execution_id}")
def get_tool_execution(execution_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_tool_execution_record(
                ContinuityStore(conn),
                user_id=user_id,
                execution_id=execution_id,
            )
    except ToolExecutionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tools/{tool_id}")
def get_tool(tool_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_tool_record(
                ContinuityStore(conn),
                user_id=user_id,
                tool_id=tool_id,
            )
    except ToolNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/extract-explicit-preferences")
def extract_explicit_preferences(request: ExtractExplicitPreferencesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_preferences(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitPreferenceExtractionRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitPreferenceExtractionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops/extract-explicit-commitments")
def extract_explicit_commitments(request: ExtractExplicitCommitmentsRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_commitments(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitCommitmentExtractionRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitCommitmentExtractionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/capture-explicit-signals")
def capture_explicit_signals(request: CaptureExplicitSignalsRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_signals(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitSignalCaptureRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitSignalCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/captures")
def create_continuity_capture(request: ContinuityCaptureRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = capture_continuity_input(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCreateInput(
                    raw_content=request.raw_content,
                    explicit_signal=request.explicit_signal,
                ),
            )
    except (ContinuityCaptureValidationError, ContinuityObjectValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/workspace")
def get_vnext_workspace(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = _vnext_workspace_payload(PostgresVNextStore(conn))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/sources")
def create_vnext_source(request: VNextSourceCaptureRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="source.capture",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = VNextCaptureService(
                store,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
            ).capture_text(
                request.raw_text,
                title=request.title,
                domain=request.domain,
                sensitivity=request.sensitivity,
            ).to_record()
            if identity is not None:
                append_policy_events(store, identity=identity, decision=decision, target_type="source", target_id=str(payload.get("source_id")))
    except VNextCaptureValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext source capture request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/projects")
def create_vnext_project(request: VNextProjectCreateRequest) -> JSONResponse:
    settings = get_settings()
    slug = request.slug or _vnext_slug(request.name)

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = PostgresVNextStore(conn).create_project(
            {
                "name": request.name.strip(),
                "slug": slug,
                "status": request.status,
                "description": request.description,
                "current_state": request.current_state,
                "domain": request.domain,
                "sensitivity": request.sensitivity,
                "metadata_json": {"created_from": "vnext_workspace"},
            },
            actor_type="user",
        )

    return JSONResponse(status_code=201, content=jsonable_encoder({"project": payload}))


@app.get("/v0/vnext/projects")
def list_vnext_projects(user_id: UUID, status: str | None = "active", limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_projects(status=status, limit=limit)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"items": payload, "count": len(payload), "order": ["updated_at_desc", "id_desc"]}),
    )


@app.get("/v0/vnext/connectors")
def list_vnext_connectors(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        service = VNextConnectorService(PostgresVNextStore(conn))
        definitions = list_connector_definitions()
        payload = {
            "items": [
                {
                    **definition.to_record(),
                    "config": service.get_config(definition.name),
                    "health": service.connector_health(definition.name),
                }
                for definition in definitions
            ],
            "count": len(definitions),
            "order": [definition.name for definition in definitions],
        }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/connectors/health")
def get_vnext_connectors_health(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextConnectorService(PostgresVNextStore(conn)).connector_health_all()
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/connectors/{connector_name}/status")
def get_vnext_connector_status(connector_name: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            service = VNextConnectorService(store)
            sources = [
                source
                for source in store.list_sources(limit=50)
                if source.get("connector_name") == connector_name
            ]
            failures = [
                event
                for event in store.list_events(target_type="connector", target_id=connector_name, limit=50)
                if event.get("event_type") in {"connector.item_failed", "connector.sync_failed"}
            ]
            payload = {
                "config": service.get_config(connector_name),
                "health": service.connector_health(connector_name),
                "recent_captures": sources[:10],
                "recent_failures": failures[:10],
            }
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext connector was not found")
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.patch("/v0/vnext/connectors/{connector_name}/config")
def update_vnext_connector_config(connector_name: str, request: VNextConnectorConfigRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectorService(PostgresVNextStore(conn)).update_config(
                connector_name,
                enabled=request.enabled,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
                secret_ref=request.secret_ref,
                sync_mode=request.sync_mode,
                poll_interval_seconds=request.poll_interval_seconds,
                config_json=request.config_json,
            )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connector config request is invalid")
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/{connector_name}/sync")
def sync_vnext_connector(connector_name: str, request: VNextConnectorSyncRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectorService(PostgresVNextStore(conn)).sync_items(
                connector_name,
                request.items,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            ).to_record()
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connector sync request is invalid")

    status_code = 201
    if payload["status"] == "partial":
        status_code = 207
    elif payload["status"] == "failed":
        status_code = 400
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/telegram/sync")
def sync_vnext_telegram_connector(request: VNextTelegramSyncRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            service = VNextConnectorService(store)
            config = service.get_config("telegram")
            config_json = config.get("config_json") if isinstance(config.get("config_json"), dict) else {}
            configured_allowed = config_json.get("allowed_chat_ids") if isinstance(config_json, dict) else []
            allowed_chat_ids = request.allowed_chat_ids or [
                str(value) for value in configured_allowed if isinstance(value, (str, int))
            ]
            updates = request.updates or service.fetch_telegram_updates(timeout=10, limit=100)
            payload = service.sync_telegram_updates(
                updates,
                allowed_chat_ids=allowed_chat_ids,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            ).to_record()
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext Telegram sync request is invalid")
    return JSONResponse(status_code=201 if payload["status"] in {"ok", "partial"} else 400, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/local-folder/sync")
def sync_vnext_local_folder_connector(request: VNextLocalFolderSyncRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            service = VNextConnectorService(store)
            paths = list(request.paths)
            if not paths:
                config = service.get_config("local_folder")
                config_json = config.get("config_json") if isinstance(config.get("config_json"), dict) else {}
                configured_paths = config_json.get("paths") if isinstance(config_json, dict) else []
                paths = [str(path) for path in configured_paths if isinstance(path, str)]
            payload = service.sync_local_folder(
                paths,
                recursive=request.recursive,
                extensions=request.extensions,
                ignore_patterns=request.ignore_patterns,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            ).to_record()
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext local folder sync request is invalid")
    return JSONResponse(status_code=201 if payload["status"] in {"ok", "partial", "duplicate"} else 400, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/browser-clipper/capture")
def capture_vnext_browser_clip(request: VNextBrowserClipperCaptureRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectorService(PostgresVNextStore(conn)).capture_browser_clip(
                request.model_dump(mode="json"),
                default_domain=request.domain,
                default_sensitivity=request.sensitivity,
            ).to_record()
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext browser clip capture request is invalid")
    return JSONResponse(status_code=201 if payload["status"] in {"ok", "partial", "duplicate"} else 400, content=jsonable_encoder(payload))


@app.post("/v0/vnext/agents/ingest-output")
def ingest_vnext_agent_output(request: VNextAgentOutputIngestRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            _vnext_agent_record(store, identity)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="source.capture",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
                target_type="connector",
                target_id="agent_output",
                write_policy="proposal_only" if request.propose_memory else None,
            )
            payload = VNextConnectorService(store).ingest_agent_output(
                request.model_dump(mode="json"),
                policy_decision=decision.to_record(),
            ).to_record()
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except (AgentIdentityValidationError, VNextConnectorValidationError):
        return _vnext_public_error_response(status_code=400, detail="vNext agent output ingest request is invalid")
    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/dogfooding")
def get_vnext_dogfooding_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextDogfoodingService(PostgresVNextStore(conn)).dashboard()
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/doctor")
def get_vnext_doctor(user_id: UUID, ci: bool = True) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextDoctorService(PostgresVNextStore(conn)).run(ci=ci)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/doctor/run")
def run_vnext_doctor(request: VNextDoctorRunRequest) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, request.user_id) as conn:
        payload = VNextDoctorService(PostgresVNextStore(conn)).run(fix_safe=request.fix_safe, ci=request.ci)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/artifacts/{artifact_id}/insight-feedback")
def record_vnext_artifact_insight_feedback(
    artifact_id: UUID,
    request: VNextArtifactInsightFeedbackRequest,
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        actor_type, actor_id = _vnext_agent_actor(identity)
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            _vnext_agent_record(store, identity)
            payload = VNextDogfoodingService(store).record_insight_feedback(
                artifact_id=str(artifact_id),
                useful_insight=request.useful_insight,
                surfaced_missed=request.surfaced_missed,
                comments=request.comments,
                actor_type=actor_type,
                actor_id=actor_id,
            )
    except ValueError:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact insight feedback request is invalid")
    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/sources/{source_id}")
def get_vnext_source(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).get_source(str(source_id))

    if payload is None:
        return JSONResponse(status_code=404, content={"detail": f"vNext source {source_id} was not found"})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/sources/{source_id}/review")
def review_vnext_source(source_id: UUID, request: VNextSourceReviewRequest) -> JSONResponse:
    settings = get_settings()
    action = request.action.strip().casefold()
    if action not in {"review", "update", "assign_project", "archive"}:
        return _vnext_public_error_response(status_code=400, detail="vNext source review action is invalid")

    with user_connection(settings.database_url, request.user_id) as conn:
        store = PostgresVNextStore(conn)
        existing = store.get_source(str(source_id))
        if existing is None:
            return _vnext_public_error_response(status_code=404, detail="vNext source was not found")
        if action == "archive":
            archived = store.delete_source(source_id=str(source_id), actor_type="user")
            append_event(
                store,
                event_type="source.archived",
                actor_type="user",
                target_type="source",
                target_id=str(source_id),
                payload={"action": action, "review_note": request.review_note},
            )
            trace = _vnext_source_trace(
                store=store,
                source=archived,
                memories=store.list_memories(status=None),
                artifacts=store.list_artifacts(limit=100),
                open_loops=store.list_open_loops(status=None, limit=100),
                events=store.list_events(limit=100),
            )
            return JSONResponse(status_code=200, content=jsonable_encoder({"source": archived, "archived": True, "trace": trace}))

        if action == "assign_project" and request.project_id is None:
            return _vnext_public_error_response(status_code=400, detail="project_id is required")

        metadata = {
            **_vnext_metadata(existing),
            "review_status": "reviewed" if action == "review" else "updated",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "review_note": request.review_note,
            "updated_from": "vnext_workspace",
        }
        if request.project_id is not None:
            metadata["project_id"] = request.project_id
        patch: dict[str, object] = {"metadata_json": metadata}
        if request.title is not None:
            patch["title"] = request.title
        if request.domain is not None:
            patch["domain"] = request.domain
        if request.sensitivity is not None:
            patch["sensitivity"] = request.sensitivity
        updated = store.update_source(source_id=str(source_id), patch=patch, actor_type="user")
        if action == "assign_project":
            store.create_edge(
                {
                    "from_type": "source",
                    "from_id": str(source_id),
                    "to_type": "project",
                    "to_id": request.project_id,
                    "edge_type": "belongs_to_project",
                    "confidence": 1.0,
                    "explanation": "Assigned from live /vnext source review.",
                    "created_by": "user",
                    "metadata_json": {"review_action": action},
                },
                actor_type="user",
            )
        append_event(
            store,
            event_type={
                "review": "source.reviewed",
                "update": "source.updated_from_workspace",
                "assign_project": "source.assigned_project",
            }[action],
            actor_type="user",
            target_type="source",
            target_id=str(source_id),
            payload={"action": action, "project_id": request.project_id, "review_note": request.review_note},
        )
        trace = _vnext_source_trace(
            store=store,
            source=updated,
            memories=store.list_memories(status=None),
            artifacts=store.list_artifacts(limit=100),
            open_loops=store.list_open_loops(status=None, limit=100),
            events=store.list_events(limit=100),
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"source": updated, "archived": False, "trace": trace}))


@app.get("/v0/vnext/traces/sources/{source_id}")
def get_vnext_source_trace(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.get_source(str(source_id))
        if source is None:
            return _vnext_public_error_response(status_code=404, detail="vNext source was not found")
        payload = _vnext_source_trace(
            store=store,
            source=source,
            memories=store.list_memories(status=None),
            artifacts=store.list_artifacts(limit=100),
            open_loops=store.list_open_loops(status=None, limit=100),
            events=store.list_events(limit=100),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/traces/artifacts/{artifact_id}")
def get_vnext_artifact_trace(artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        artifact = store.get_artifact(str(artifact_id))
        if artifact is None:
            return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
        payload = _vnext_artifact_trace(
            artifact=artifact,
            sources=store.list_sources(limit=100),
            quality_evals=store.list_artifact_quality_ratings(artifact_id=str(artifact_id), limit=100),
            events=store.list_events(limit=100),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.delete("/v0/vnext/sources/{source_id}")
def delete_vnext_source(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        existing = store.get_source(str(source_id))
        if existing is None:
            return JSONResponse(status_code=404, content={"detail": f"vNext source {source_id} was not found"})
        payload = store.delete_source(source_id=str(source_id))

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/context-packs")
def create_vnext_context_pack(request: VNextContextPackRequest) -> JSONResponse:
    settings = get_settings()
    scope = request.scope
    options = request.options
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        requested_domains = _vnext_string_list(scope, "domains")
        requested_sensitivity = _vnext_string_list(options, "sensitivity_allowed") or (
            "public",
            "internal",
            "private",
            "unknown",
        )
        retrieval_request = VNextRetrievalRequest(
            query=request.query,
            domains=requested_domains,
            projects=_vnext_string_list(scope, "projects"),
            people=_vnext_string_list(scope, "people"),
            time_window=str(scope.get("time_window", "all")),
            sensitivity_allowed=requested_sensitivity,
            include_sources=_vnext_bool(options, "include_sources", True),
            include_contradictions=_vnext_bool(options, "include_contradictions", True),
            max_items=_vnext_int(options, "max_items", 8),
            max_tokens=_vnext_int(options, "max_tokens", 8000),
        )
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="context_pack.request",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
            payload = VNextRetrievalService(store).compile_context_pack(
                VNextRetrievalRequest(
                    query=retrieval_request.query,
                    domains=decision.effective_domains,
                    projects=retrieval_request.projects,
                    people=retrieval_request.people,
                    time_window=retrieval_request.time_window,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    include_sources=retrieval_request.include_sources,
                    include_contradictions=retrieval_request.include_contradictions,
                    max_items=retrieval_request.max_items,
                    max_tokens=retrieval_request.max_tokens,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                )
            )
    except VNextRetrievalValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext context-pack request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/memories/{memory_id}/review")
def review_vnext_memory(memory_id: UUID, request: VNextMemoryReviewRequest) -> JSONResponse:
    settings = get_settings()
    action = request.action.strip().casefold()
    if action not in {"accept", "edit", "reject", "private", "assign_project", "promote"}:
        return _vnext_public_error_response(status_code=400, detail="vNext memory review action is invalid")

    with user_connection(settings.database_url, request.user_id) as conn:
        store = PostgresVNextStore(conn)
        existing = store.get_memory(str(memory_id))
        if existing is None:
            return _vnext_public_error_response(status_code=404, detail="vNext memory was not found")

        existing_metadata = existing.get("metadata_json") if isinstance(existing.get("metadata_json"), dict) else {}
        patch: dict[str, object] = {
            "last_reviewed_at": datetime.now(UTC).isoformat(),
        }
        revision_type = "edited"
        if action == "accept":
            patch["status"] = "active"
            revision_type = "promoted"
        elif action == "reject":
            patch["status"] = "rejected"
            revision_type = "rejected"
        elif action == "private":
            patch["status"] = "private_only"
            patch["sensitivity"] = "private"
        elif action == "promote":
            patch["status"] = "active"
            patch["confirmation_status"] = "confirmed"
            revision_type = "promoted"
        elif action == "assign_project":
            if request.project_id is None:
                return _vnext_public_error_response(status_code=400, detail="project_id is required")
            patch["metadata_json"] = {
                **existing_metadata,
                "project_id": request.project_id,
                "assigned_from": "vnext_workspace",
            }
        else:
            patch["status"] = "active"

        if request.title is not None:
            patch["title"] = request.title
        if request.canonical_text is not None:
            patch["canonical_text"] = request.canonical_text
            patch["value"] = {
                **(existing.get("value") if isinstance(existing.get("value"), dict) else {}),
                "text": request.canonical_text,
            }
        if request.summary is not None:
            patch["summary"] = request.summary
        if request.domain is not None:
            patch["domain"] = request.domain
        if request.sensitivity is not None:
            patch["sensitivity"] = request.sensitivity

        updated = store.update_memory(memory_id=str(memory_id), patch=patch, actor_type="user")
        if action == "assign_project" and request.project_id is not None:
            store.create_edge(
                {
                    "from_type": "memory",
                    "from_id": str(memory_id),
                    "to_type": "project",
                    "to_id": request.project_id,
                    "edge_type": "belongs_to_project",
                    "confidence": 1.0,
                    "explanation": "Assigned from live /vnext memory review.",
                    "created_by": "user",
                    "metadata_json": {"review_action": action},
                },
                actor_type="user",
            )
        store.append_revision(
            {
                "memory_id": str(memory_id),
                "memory_key": str(updated["memory_key"]),
                "previous_value": existing.get("value"),
                "new_value": updated.get("value"),
                "source_event_ids": updated.get("source_event_ids"),
                "revision_type": revision_type,
                "action": f"memory_review_{action}",
                "text_before": existing.get("canonical_text"),
                "text_after": str(updated.get("canonical_text", "")),
                "reason": request.reason or f"vNext workspace memory review action: {action}",
                "actor_type": "user",
                "metadata_json": {"action": action, "project_id": request.project_id},
            },
            actor_type="user",
        )
        review_event = {
            "accept": "review.item_accepted",
            "promote": "review.item_accepted",
            "reject": "review.item_rejected",
            "edit": "review.item_edited",
            "private": "review.item_edited",
            "assign_project": "review.item_edited",
        }[action]
        append_event(
            store,
            event_type=review_event,
            actor_type="user",
            target_type="memory",
            target_id=str(memory_id),
            payload={"action": action, "project_id": request.project_id},
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"memory": updated}))


def _vnext_memory_type_for_proposal(proposal_type: str) -> str:
    mapping = {
        "candidate_memory": "semantic",
        "project_update": "project_state",
        "open_loop": "open_loop",
        "belief_update": "belief",
        "contradiction": "contradiction",
        "graph_edge": "semantic",
        "artifact_summary": "artifact_summary",
        "decision": "decision",
        "recent_change": "semantic",
    }
    return mapping.get(proposal_type, "semantic")


@app.post("/v0/vnext/memory-proposals")
def create_vnext_memory_proposal(request: VNextMemoryProposalRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    if identity is None:
        return _vnext_public_error_response(status_code=400, detail="agent identity is required for memory proposals")

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.propose",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            proposal_id = str(uuid4())
            metadata = {
                "proposal_id": proposal_id,
                "proposal_type": request.proposal_type,
                "source_refs": request.source_refs,
                "project_scope": list(request.project_scope),
                "rationale": request.rationale,
                "review_required": True,
                **agent_metadata(identity, decision),
            }
            memory = store.create_memory(
                {
                    "memory_type": _vnext_memory_type_for_proposal(request.proposal_type),
                    "memory_key": f"agent_proposal.{request.proposal_type}.{proposal_id}",
                    "value": {
                        "proposal_type": request.proposal_type,
                        "text": request.canonical_text,
                        "source_refs": request.source_refs,
                        "rationale": request.rationale,
                    },
                    "status": "candidate",
                    "confidence": request.confidence,
                    "title": request.title,
                    "canonical_text": request.canonical_text,
                    "summary": request.canonical_text[:280],
                    "domain": request.domain,
                    "sensitivity": request.sensitivity,
                    "metadata_json": metadata,
                },
                actor_type="agent",
            )
            store.append_revision(
                {
                    "memory_id": str(memory["id"]),
                    "memory_key": str(memory["memory_key"]),
                    "new_value": memory.get("value"),
                    "revision_type": "created",
                    "action": "agent_memory_proposal",
                    "text_after": request.canonical_text,
                    "reason": request.rationale or "Agent proposed memory for human review.",
                    "actor_type": "agent",
                    "actor_id": identity.agent_id,
                    "metadata_json": metadata,
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
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"proposal_type": request.proposal_type, "agent_identity": identity.to_record(), "policy_decision": decision.to_record()},
            )
            append_event(
                store,
                event_type="review.item_created",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"review_required": True, "proposal_type": request.proposal_type},
            )
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder({"proposal": memory, "policy_decision": decision.to_record(), "review_required": True}),
    )


@app.post("/v0/vnext/memories/commit")
def commit_vnext_memory(request: VNextMemoryCommitRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        commit_request = memory_commit_request_from_payload(
            request.model_dump(mode="json", exclude={"agent", "agent_identity"}),
            user_id=request.user_id,
        )
    except (AgentIdentityValidationError, VNextMemoryCommitValidationError) as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            payload = VNextMemoryCommitService(store).commit(identity=identity, request=commit_request)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    status_code = 201 if payload.get("status") in {"committed", "confirmation_required", "review_required"} else 200
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/confirm")
def confirm_vnext_memory(request: VNextMemoryConfirmRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.confirm",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextMemoryCommitService(store).confirm(
                identity=identity,
                confirmation_id=request.confirmation_id,
                action=request.action,
                canonical_text=request.canonical_text,
                rationale=request.rationale,
            )
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/undo")
def undo_vnext_memory(request: VNextMemoryUndoRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.undo",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextMemoryCommitService(store).undo(
                identity=identity,
                memory_id=str(request.memory_id) if request.memory_id is not None else None,
                reason=request.reason,
            )
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/correct")
def correct_vnext_memory(request: VNextMemoryCorrectRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.correct",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextMemoryCommitService(store).correct(
                identity=identity,
                memory_id=str(request.memory_id),
                canonical_text=request.canonical_text,
                reason=request.reason,
            )
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/forget")
def forget_vnext_memory(request: VNextMemoryForgetRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.forget",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextMemoryCommitService(store).forget(
                identity=identity,
                memory_id=str(request.memory_id),
                reason=request.reason,
            )
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/memories/recent-commits")
def list_vnext_recent_memory_commits(user_id: UUID, limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        payload = VNextMemoryCommitService(store).recent_commits(limit=limit)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/memories/{memory_id}/audit")
def get_vnext_memory_audit(memory_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            payload = VNextMemoryCommitService(store).audit(memory_id=str(memory_id))
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=404, detail=str(exc))
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/artifacts/generate/daily-brief")
def generate_vnext_daily_brief(request: VNextBrainArtifactGenerateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextBrainService(store).generate_daily_brief(
                _vnext_brain_artifact_request(request, identity=identity, decision=decision)
            )
    except VNextBrainValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext daily brief request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/weekly-synthesis")
def generate_vnext_weekly_synthesis(request: VNextBrainArtifactGenerateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextBrainService(store).generate_weekly_synthesis(
                _vnext_brain_artifact_request(request, identity=identity, decision=decision)
            )
    except VNextBrainValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext weekly synthesis request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/connections")
def generate_vnext_connection_report(request: VNextConnectionReportGenerateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
                workflow_type="connection_report",
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextConnectionService(store).generate_connection_report(
                _vnext_connection_request(request, identity=identity, decision=decision)
            )
    except VNextConnectionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connection report request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/contradictions")
def generate_vnext_contradiction_report(request: VNextContradictionReportGenerateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
                workflow_type="contradiction_report",
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextContradictionService(store).generate_contradiction_report(
                _vnext_contradiction_request(request, identity=identity, decision=decision)
            )
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext contradiction report request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/queue/tasks")
def create_vnext_queue_task(request: VNextQueueTaskCreateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="queue_task.create",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
                write_policy=request.write_policy,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = VNextQueueService(store).enqueue_task(
                QueueTaskRequest(
                    title=request.title,
                    task_type=request.task_type,
                    instructions=request.instructions,
                    requested_by=identity.agent_id if identity is not None else "api",
                    scope_json=request.scope_json,
                    allowed_sources_json=request.allowed_sources_json,
                    domain=request.domain,
                    sensitivity=request.sensitivity,
                    write_policy=request.write_policy,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                )
            )
    except VNextQueueValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext queue task request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/queue/process-next")
def process_next_vnext_queue_task(request: VNextQueueProcessNextRequest) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = VNextQueueService(PostgresVNextStore(conn)).process_next_task().to_record()

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/artifacts")
def list_vnext_artifacts(user_id: UUID, artifact_type: str | None = None, limit: int = 30) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_artifacts(artifact_type=artifact_type, limit=limit)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"items": payload, "count": len(payload), "order": ["created_at_desc", "id_desc"]}),
    )


@app.get("/v0/vnext/artifacts/{artifact_id}")
def get_vnext_artifact(artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).get_artifact(str(artifact_id))

    if payload is None:
        return JSONResponse(status_code=404, content={"detail": f"vNext artifact {artifact_id} was not found"})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/review")
def review_vnext_artifact(artifact_id: UUID, request: VNextArtifactReviewRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.review",
                target_type="artifact",
                target_id=str(artifact_id),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextQueueService(store).review_artifact(
                artifact_id=str(artifact_id),
                action=request.action,
            )
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except VNextQueueValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact review request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/quality-ratings")
def rate_vnext_artifact_quality(artifact_id: UUID, request: VNextArtifactQualityRatingRequest) -> JSONResponse:
    settings = get_settings()
    verbosity = request.verbosity.strip().casefold()
    if verbosity not in {"too_shallow", "right_sized", "too_verbose", "unknown"}:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact quality verbosity is invalid")
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            existing = store.get_artifact(str(artifact_id))
            if existing is None:
                return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.review",
                target_type="artifact",
                target_id=str(artifact_id),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = store.create_artifact_quality_rating(
                {
                    "artifact_id": str(artifact_id),
                    "reviewer_id": request.reviewer_id or actor_id,
                    "usefulness": request.usefulness,
                    "accuracy": request.accuracy,
                    "source_grounding": request.source_grounding,
                    "novel_connections": request.novel_connections,
                    "actionability": request.actionability,
                    "hallucination_risk": request.hallucination_risk,
                    "verbosity": verbosity,
                    "missed_context": request.missed_context,
                    "comments": request.comments,
                    "metadata_json": {
                        **request.metadata_json,
                        "artifact_type": existing.get("artifact_type"),
                        "generation_mode": (existing.get("metadata_json") or {}).get("generation_mode")
                        if isinstance(existing.get("metadata_json"), dict)
                        else None,
                        "agent_identity": identity.to_record() if identity is not None else None,
                        "policy_decision": decision.to_record(),
                    },
                },
                actor_type=actor_type,
            )
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/quality-evals")
def list_vnext_quality_evals(user_id: UUID, artifact_id: UUID | None = None, limit: int = 100) -> JSONResponse:
    settings = get_settings()
    bounded_limit = max(1, min(limit, 200))
    with user_connection(settings.database_url, user_id) as conn:
        rows = PostgresVNextStore(conn).list_artifact_quality_ratings(
            artifact_id=str(artifact_id) if artifact_id is not None else None,
            limit=bounded_limit,
        )
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": rows,
                "count": len(rows),
                "order": ["created_at_desc", "id_desc"],
                "export": {
                    "format": "json",
                    "rating_fields": [
                        "usefulness",
                        "accuracy",
                        "source_grounding",
                        "novel_connections",
                        "actionability",
                        "hallucination_risk",
                        "verbosity",
                        "missed_context",
                    ],
                },
            }
        ),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/export")
def export_vnext_artifact(artifact_id: UUID, request: VNextArtifactExportRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            output_path = VNextQueueService(PostgresVNextStore(conn)).export_artifact_markdown(
                artifact_id=str(artifact_id),
                output_dir=request.output_dir,
            )
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except VNextQueueValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact export request is invalid")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"artifact_id": str(artifact_id), "output_path": str(output_path)}),
    )


@app.post("/v0/vnext/graph/edges/{edge_id}/review")
def review_vnext_graph_edge(edge_id: str, request: VNextGraphEdgeReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectionService(PostgresVNextStore(conn)).review_edge(
                edge_id=edge_id,
                action=request.action,
            )
    except VNextConnectionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext graph edge review request is invalid")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/graph/neighborhood/{target_id}")
def get_vnext_graph_neighborhood(target_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextConnectionService(PostgresVNextStore(conn)).graph_neighborhood(target_id=target_id)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/beliefs/{belief_id}/review")
def review_vnext_belief(belief_id: str, request: VNextBeliefReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextContradictionService(PostgresVNextStore(conn)).review_belief(
                belief_id=belief_id,
                action=request.action,
                confidence=request.confidence,
                superseded_by=request.superseded_by,
            )
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext belief review request is invalid")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/beliefs/{belief_id}/state")
def get_vnext_belief_state(belief_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = VNextContradictionService(PostgresVNextStore(conn)).belief_state(belief_id=belief_id)
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext belief was not found")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/projects/update-candidates")
def generate_vnext_project_update_candidate(request: VNextProjectAutomationRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextProjectService(store).generate_project_update_candidate(
                _vnext_project_automation_request(request, identity=identity, decision=decision)
            )
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext project update request is invalid")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.post("/v0/vnext/projects/update-candidates/{artifact_id}/review")
def review_vnext_project_update_candidate(artifact_id: str, request: VNextProjectUpdateReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextProjectService(PostgresVNextStore(conn)).review_project_update(
                artifact_id=artifact_id,
                action=request.action,
                edited_current_state=request.edited_current_state,
            )
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext project update review request is invalid")

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/projects/{project_id}/dashboard")
def get_vnext_project_dashboard(project_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = VNextProjectService(PostgresVNextStore(conn)).project_dashboard(project_id=project_id)
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext project was not found")

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/open-loops")
def create_vnext_open_loop(request: VNextOpenLoopCreateRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="open_loop.create",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = store.create_open_loop(
                {
                    "title": request.title.strip(),
                    "description": request.description,
                    "due_at": request.due_at,
                    "priority": request.priority,
                    "memory_id": request.memory_id,
                    "project_id": request.project_id,
                    "source_id": request.source_id,
                    "domain": request.domain,
                    "sensitivity": request.sensitivity,
                    "metadata_json": {
                        "created_from": "vnext_workspace",
                        **agent_metadata(identity, decision),
                    },
                },
                actor_type=actor_type,
            )
            if identity is not None:
                append_event(
                    store,
                    event_type="agent.open_loop_created",
                    actor_type="agent",
                    actor_id=identity.agent_id,
                    target_type="open_loop",
                    target_id=str(payload["id"]),
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id,
                    payload={"agent_identity": identity.to_record(), "policy_decision": decision.to_record()},
                )
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({"open_loop": payload}))


@app.get("/v0/vnext/settings/brain-charter")
def get_vnext_brain_charter(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).get_brain_charter()

    return JSONResponse(status_code=200, content=jsonable_encoder({"brain_charter": payload}))


@app.put("/v0/vnext/settings/brain-charter")
def upsert_vnext_brain_charter(request: VNextBrainCharterUpsertRequest) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = PostgresVNextStore(conn).upsert_brain_charter(
            {
                "content_markdown": request.content_markdown,
                "owner_json": request.owner_json,
                "memory_philosophy_json": request.memory_philosophy_json,
                "life_domains_json": request.life_domains_json,
                "active_projects_json": request.active_projects_json,
                "communication_style_json": request.communication_style_json,
                "priorities_json": request.priorities_json,
                "autonomous_rules_json": request.autonomous_rules_json,
                "quality_standard_json": request.quality_standard_json,
                "sensitivity": request.sensitivity,
            },
            actor_type="user",
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"brain_charter": payload}))


@app.get("/v0/vnext/scheduler/status")
def get_vnext_scheduler_status(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextSchedulerService(PostgresVNextStore(conn)).status()
    payload = {**payload, "daemon": daemon_status()}

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/scheduler/runs")
def list_vnext_scheduler_runs(user_id: UUID, workflow_type: str | None = None, limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_scheduler_runs(workflow_type=workflow_type, limit=limit)

    return JSONResponse(status_code=200, content=jsonable_encoder({"items": payload, "count": len(payload)}))


@app.get("/v0/vnext/scheduler/failures")
def list_vnext_scheduler_failures(user_id: UUID, workflow_type: str | None = None, limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        runs = [
            run
            for run in PostgresVNextStore(conn).list_scheduler_runs(
                workflow_type=workflow_type,
                limit=max(limit * 4, limit),
            )
            if run.get("status") == "failed"
        ][:limit]

    return JSONResponse(status_code=200, content=jsonable_encoder({"items": runs, "count": len(runs)}))


@app.get("/v0/vnext/agents/policy-telemetry")
def get_vnext_agent_policy_telemetry(user_id: UUID, agent_id: str | None = None, limit: int = 200) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        payload = summarize_agent_policy_telemetry(
            agent_events=store.list_agent_events(agent_id=agent_id, limit=limit),
            artifacts=store.list_artifacts(limit=min(limit, 200)),
            memories=store.list_memories(status=None),
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"summary": payload}))


@app.patch("/v0/vnext/scheduler/workflows/{workflow_type}")
def patch_vnext_scheduler_workflow(workflow_type: str, request: VNextSchedulerWorkflowPatchRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        if request.schedule_json is not None:
            validate_schedule(workflow_type, request.schedule_json)
    except (AgentIdentityValidationError, VNextSchedulerValidationError) as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.configure",
                workflow_type=workflow_type,
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = VNextSchedulerService(store).configure_workflow(
                workflow_type=workflow_type,
                enabled=request.enabled,
                paused=request.paused,
                schedule_json=request.schedule_json,
                timezone=request.timezone,
                metadata_json={"model_options": _vnext_model_generation_options(request.model_options)}
                if request.model_options
                else None,
                actor_type=actor_type,
            )
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=200, content=jsonable_encoder({"workflow": payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/scheduler/workflows/{workflow_type}/run-now")
def run_vnext_scheduler_workflow_now(workflow_type: str, request: VNextSchedulerRunNowRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    scope = request.scope
    options = request.options
    requested_domains = _vnext_string_list(scope, "domains")
    requested_sensitivity = _vnext_string_list(options, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.run_now",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(scope, "projects"),
                workflow_type=workflow_type,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            triggered_by = "agent" if identity is not None else "user"
            payload = VNextSchedulerService(store).run_now(
                SchedulerRunRequest(
                    workflow_type=workflow_type,
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    generated_for=str(options["generated_for"]) if isinstance(options.get("generated_for"), str) else None,
                    triggered_by=triggered_by,
                    agent_identity=identity,
                    policy_decision=decision,
                    options=options,
                )
            )
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/scheduler/run-due")
def run_vnext_scheduler_due(request: VNextSchedulerRunDueRequest) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.run_due",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="scheduler")
            payload = VNextSchedulerService(store).run_due_workflows(
                limit=request.limit,
                triggered_by=actor_type,
                agent_identity=identity,
                policy_decision=decision,
            )
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/scheduler/pause")
def pause_vnext_scheduler(request: VNextSchedulerControlRequest) -> JSONResponse:
    return _vnext_scheduler_global_control(request, action="scheduler.pause", pause=True)


@app.post("/v0/vnext/scheduler/resume")
def resume_vnext_scheduler(request: VNextSchedulerControlRequest) -> JSONResponse:
    return _vnext_scheduler_global_control(request, action="scheduler.resume", pause=False)


def _vnext_scheduler_global_control(
    request: VNextSchedulerControlRequest,
    *,
    action: str,
    pause: bool,
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action=action,
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            service = VNextSchedulerService(store)
            payload = service.pause_all(actor_type=actor_type) if pause else service.resume_all(actor_type=actor_type)
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=200, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/open-loops/extract")
def extract_vnext_open_loops(request: VNextProjectAutomationRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            loops = VNextProjectService(PostgresVNextStore(conn)).extract_open_loops(
                _vnext_project_automation_request(request)
            )
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext open-loop extraction request is invalid")

    return JSONResponse(status_code=201, content=jsonable_encoder({"open_loops": loops, "created_count": len(loops)}))


@app.post("/v0/vnext/open-loops/{loop_id}/review")
def review_vnext_open_loop(loop_id: str, request: VNextOpenLoopReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextProjectService(PostgresVNextStore(conn)).review_open_loop(
                loop_id=loop_id,
                action=request.action,
                title=request.title,
                description=request.description,
                due_at=request.due_at,
                priority=request.priority,
                resolution_note=request.resolution_note,
            )
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext open-loop review request is invalid")

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/continuity/captures/candidates")
def create_continuity_capture_candidates(request: ContinuityCaptureCandidatesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = capture_continuity_candidates(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCandidatesInput(
                    user_content=request.user_content,
                    assistant_content=request.assistant_content,
                    session_id=request.session_id,
                    source_kind=request.source_kind,
                ),
            )
    except ContinuityCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/captures/commit")
def commit_continuity_capture_candidates(request: ContinuityCaptureCommitRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = commit_continuity_captures(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCommitInput(
                    mode=request.mode,  # type: ignore[arg-type]
                    candidates=request.candidates,
                    sync_fingerprint=request.sync_fingerprint,
                    source_kind=request.source_kind,
                ),
            )
    except (ContinuityCaptureValidationError, ContinuityObjectValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/memory/operations/candidates/generate")
def generate_memory_operation_candidates_endpoint(
    http_request: Request,
    request: MemoryOperationGenerateRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = generate_memory_operation_candidates(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationGenerateInput(
                    user_content=request.user_content,
                    assistant_content=request.assistant_content,
                    mode=request.mode,  # type: ignore[arg-type]
                    sync_fingerprint=request.sync_fingerprint,
                    source_kind=request.source_kind,
                    session_id=request.session_id,
                    thread_id=request.thread_id,
                    task_id=request.task_id,
                    project=request.project,
                    person=request.person,
                    target_continuity_object_id=request.target_continuity_object_id,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/memory/operations/candidates")
def list_memory_operation_candidates_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=100),
    policy_action: str | None = Query(default=None, min_length=1, max_length=40),
    operation_type: str | None = Query(default=None, min_length=1, max_length=40),
    sync_fingerprint: str | None = Query(default=None, min_length=1, max_length=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_operation_candidates(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationListInput(
                    limit=limit,
                    policy_action=policy_action,  # type: ignore[arg-type]
                    operation_type=operation_type,  # type: ignore[arg-type]
                    sync_fingerprint=sync_fingerprint,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/memory/operations/commit")
def commit_memory_operations_endpoint(
    http_request: Request,
    request: MemoryOperationCommitRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = commit_memory_operations(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationCommitInput(
                    candidate_ids=request.candidate_ids,
                    sync_fingerprint=request.sync_fingerprint,
                    include_review_required=request.include_review_required,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/memory/operations")
def list_memory_operations_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=100),
    sync_fingerprint: str | None = Query(default=None, min_length=1, max_length=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_operations(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationListInput(
                    limit=limit,
                    sync_fingerprint=sync_fingerprint,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/captures")
def list_continuity_captures(
    user_id: UUID,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=MAX_CONTINUITY_CAPTURE_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_continuity_capture_inbox(
            ContinuityStore(conn),
            user_id=user_id,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/captures/{capture_event_id}")
def get_continuity_capture(capture_event_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_continuity_capture_detail(
                ContinuityStore(conn),
                user_id=user_id,
                capture_event_id=capture_event_id,
            )
    except ContinuityCaptureNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/admin/debug/continuity/lifecycle")
def list_continuity_lifecycle_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_LIFECYCLE_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityLifecycleListResponse = list_continuity_lifecycle_state(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityLifecycleQueryInput(limit=limit),
            )
    except ContinuityLifecycleValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/admin/debug/continuity/lifecycle/{continuity_object_id}")
def get_continuity_lifecycle_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityLifecycleDetailResponse = get_continuity_lifecycle_state(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
            )
    except ContinuityLifecycleNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/review-queue")
def list_continuity_review_queue_endpoint(
    user_id: UUID,
    status: str = Query(default="correction_ready", min_length=1, max_length=40),
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityReviewQueueResponse = list_continuity_review_queue(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityReviewQueueQueryInput(
                    status=status,  # type: ignore[arg-type]
                    limit=limit,
                ),
            )
    except ContinuityReviewValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/review-queue/{continuity_object_id}")
def get_continuity_review_detail_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityReviewDetailResponse = get_continuity_review_detail(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
            )
    except ContinuityReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/explain/{continuity_object_id}")
def get_continuity_explain_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityExplainResponse = build_continuity_explain(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
                include_raw_content=False,
            )
    except ContinuityEvidenceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/contradictions/detect")
def detect_contradictions_endpoint(
    http_request: Request,
    request: ContradictionDetectRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionSyncResponse = sync_contradictions(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContradictionSyncInput(
                    continuity_object_id=request.continuity_object_id,
                    limit=request.limit,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/contradictions/cases")
def list_contradiction_cases_endpoint(
    request: Request,
    status: str = Query(default="open", min_length=1, max_length=40),
    continuity_object_id: UUID | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionCaseListResponse = list_contradiction_cases(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContradictionCaseListQueryInput(
                    status=status,  # type: ignore[arg-type]
                    limit=limit,
                    continuity_object_id=continuity_object_id,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/contradictions/cases/{contradiction_case_id}")
def get_contradiction_case_endpoint(
    contradiction_case_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionCaseDetailResponse = get_contradiction_case(
                ContinuityStore(conn),
                user_id=user_id,
                contradiction_case_id=contradiction_case_id,
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ContinuityContradictionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/contradictions/cases/{contradiction_case_id}/resolve")
def resolve_contradiction_case_endpoint(
    contradiction_case_id: UUID,
    http_request: Request,
    request: ContradictionResolveRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionResolveResponse = resolve_contradiction_case(
                ContinuityStore(conn),
                user_id=user_id,
                contradiction_case_id=contradiction_case_id,
                request=ContradictionResolveInput(
                    action=request.action,  # type: ignore[arg-type]
                    note=request.note,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/trust/signals")
def list_trust_signals_endpoint(
    request: Request,
    continuity_object_id: UUID | None = None,
    signal_state: str = Query(default="active", min_length=1, max_length=40),
    signal_type: str | None = Query(default=None, min_length=1, max_length=40),
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustSignalListResponse = list_trust_signals(
                ContinuityStore(conn),
                user_id=user_id,
                request=TrustSignalListQueryInput(
                    limit=limit,
                    continuity_object_id=continuity_object_id,
                    signal_state=signal_state,  # type: ignore[arg-type]
                    signal_type=signal_type,  # type: ignore[arg-type]
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/state-at")
def get_temporal_state_at_endpoint(
    entity_id: UUID,
    user_id: UUID,
    at: datetime | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalStateAtResponse = get_temporal_state_at(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalStateAtQueryInput(
                    entity_id=entity_id,
                    at=at,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/timeline")
def get_temporal_timeline_endpoint(
    entity_id: UUID,
    user_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=DEFAULT_TEMPORAL_TIMELINE_LIMIT, ge=1, le=MAX_TEMPORAL_TIMELINE_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalTimelineResponse = get_temporal_timeline(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalTimelineQueryInput(
                    entity_id=entity_id,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/explain")
def get_temporal_explain_endpoint(
    entity_id: UUID,
    user_id: UUID,
    at: datetime | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalExplainResponse = get_temporal_explain(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalExplainQueryInput(
                    entity_id=entity_id,
                    at=at,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/patterns")
def list_trusted_fact_patterns_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        ge=1,
        le=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: TrustedFactPatternListResponse = list_trusted_fact_patterns(
            ContinuityStore(conn),
            user_id=user_id,
            request=TrustedFactPatternListQueryInput(limit=limit),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/patterns/{pattern_id}")
def get_trusted_fact_pattern_endpoint(
    pattern_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustedFactPatternExplainResponse = get_trusted_fact_pattern(
                ContinuityStore(conn),
                user_id=user_id,
                pattern_id=pattern_id,
            )
    except TrustedFactPromotionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/playbooks")
def list_trusted_fact_playbooks_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        ge=1,
        le=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: TrustedFactPlaybookListResponse = list_trusted_fact_playbooks(
            ContinuityStore(conn),
            user_id=user_id,
            request=TrustedFactPlaybookListQueryInput(limit=limit),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/playbooks/{playbook_id}")
def get_trusted_fact_playbook_endpoint(
    playbook_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustedFactPlaybookExplainResponse = get_trusted_fact_playbook(
                ContinuityStore(conn),
                user_id=user_id,
                playbook_id=playbook_id,
            )
    except TrustedFactPromotionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/admin/debug/continuity/artifacts/{artifact_id}")
def get_continuity_artifact_detail_endpoint(
    request: Request,
    artifact_id: UUID,
    user_id: UUID,
    include_raw_content: bool = Query(default=False),
) -> JSONResponse:
    settings = get_settings()
    if include_raw_content and not _allow_raw_evidence_debug_access(settings):
        return JSONResponse(
            status_code=403,
            content={"detail": "raw evidence content access is restricted to development/test"},
        )

    if include_raw_content:
        _audit_raw_evidence_access(
            request=request,
            settings=settings,
            route="/v0/admin/debug/continuity/artifacts/{artifact_id}",
            user_id=user_id,
        )

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityArtifactDetailResponse = get_continuity_artifact_detail(
                ContinuityStore(conn),
                user_id=user_id,
                artifact_id=artifact_id,
                include_raw_content=include_raw_content,
            )
    except ContinuityEvidenceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/review-queue/{continuity_object_id}/corrections")
def apply_continuity_correction_endpoint(
    continuity_object_id: UUID,
    request: ContinuityCorrectionRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = apply_continuity_correction(
                ContinuityStore(conn),
                user_id=request.user_id,
                continuity_object_id=continuity_object_id,
                request=ContinuityCorrectionInput(
                    action=request.action,  # type: ignore[arg-type]
                    reason=request.reason,
                    title=request.title,
                    body=request.body,  # type: ignore[arg-type]
                    provenance=request.provenance,  # type: ignore[arg-type]
                    confidence=request.confidence,
                    replacement_title=request.replacement_title,
                    replacement_body=request.replacement_body,  # type: ignore[arg-type]
                    replacement_provenance=request.replacement_provenance,  # type: ignore[arg-type]
                    replacement_confidence=request.replacement_confidence,
                ),
            )
    except ContinuityReviewValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/open-loops")
def get_continuity_open_loop_dashboard(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityOpenLoopDashboardResponse = compile_continuity_open_loop_dashboard(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityOpenLoopDashboardQueryInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/daily-brief")
def get_continuity_daily_brief(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityDailyBriefResponse = compile_continuity_daily_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityDailyBriefRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/weekly-review")
def get_continuity_weekly_review(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityWeeklyReviewResponse = compile_continuity_weekly_review(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityWeeklyReviewRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/open-loops/{continuity_object_id}/review-action")
def apply_continuity_open_loop_review_action_endpoint(
    continuity_object_id: UUID,
    request: ContinuityOpenLoopReviewActionRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ContinuityOpenLoopReviewActionResponse = apply_continuity_open_loop_review_action(
                ContinuityStore(conn),
                user_id=request.user_id,
                continuity_object_id=continuity_object_id,
                request=ContinuityOpenLoopReviewActionInput(
                    action=request.action,  # type: ignore[arg-type]
                    note=request.note,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityOpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/recall")
def list_continuity_recall(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_RECALL_LIMIT,
    ),
    debug: bool = False,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityRecallResponse = query_continuity_recall(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityRecallQueryInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                    debug=debug,
                ),
            )
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-runs")
def get_continuity_retrieval_runs(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
        ge=1,
        le=MAX_RETRIEVAL_RUN_LIST_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: RetrievalRunListResponse = list_retrieval_runs(
                ContinuityStore(conn),
                user_id=user_id,
                limit=limit,
            )
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-runs/{retrieval_run_id}")
def get_continuity_retrieval_trace(
    retrieval_run_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: RetrievalTraceResponse = get_retrieval_trace(
                ContinuityStore(conn),
                user_id=user_id,
                retrieval_run_id=retrieval_run_id,
            )
    except RetrievalTraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-evaluation")
def get_continuity_retrieval_evaluation(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: RetrievalEvaluationResponse = get_retrieval_evaluation_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/suites")
def get_public_eval_suites(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalSuiteDefinitionListResponse = list_public_eval_suites(
                ContinuityStore(conn),
                user_id=user_id,
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/evals/runs")
def create_public_eval_run(
    request: Request,
    suite_key: list[str] | None = Query(default=None),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunDetailResponse = run_public_evals(
                ContinuityStore(conn),
                user_id=user_id,
                suite_keys=suite_key,
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/runs")
def get_public_eval_runs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunListResponse = list_public_eval_runs(
                ContinuityStore(conn),
                user_id=user_id,
                limit=limit,
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/runs/{eval_run_id}")
def get_public_eval_run_detail(
    eval_run_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunDetailResponse = get_public_eval_run(
                ContinuityStore(conn),
                user_id=user_id,
                eval_run_id=eval_run_id,
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/resumption-brief")
def get_continuity_resumption_brief(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    max_recent_changes: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    ),
    max_open_loops: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    ),
    include_non_promotable_facts: bool = False,
    debug: bool = False,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityResumptionBriefResponse = compile_continuity_resumption_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityResumptionBriefRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    max_recent_changes=max_recent_changes,
                    max_open_loops=max_open_loops,
                    include_non_promotable_facts=include_non_promotable_facts,
                    debug=debug,
                ),
            )
    except ContinuityResumptionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/continuity/brief")
def post_continuity_brief(
    http_request: Request,
    request: ContinuityBriefRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityBriefResponse = compile_continuity_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityBriefRequestInput(
                    brief_type=request.brief_type,  # type: ignore[arg-type]
                    query=request.query,
                    thread_id=request.thread_id,
                    task_id=request.task_id,
                    project=request.project,
                    person=request.person,
                    since=request.since,
                    until=request.until,
                    max_relevant_facts=request.max_relevant_facts,
                    max_recent_changes=request.max_recent_changes,
                    max_open_loops=request.max_open_loops,
                    max_conflicts=request.max_conflicts,
                    max_timeline_highlights=request.max_timeline_highlights,
                    include_non_promotable_facts=request.include_non_promotable_facts,
                ),
            )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except (
        ContinuityBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
        TaskBriefValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-briefs/compile")
def post_v0_task_brief_compile(body: TaskBriefCompileRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, body.user_id) as conn:
            payload: TaskBriefResponse = compile_and_persist_task_brief(
                ContinuityStore(conn),
                user_id=body.user_id,
                request=TaskBriefCompileRequestInput(
                    mode=body.mode,
                    query=body.query,
                    workspace_id=body.workspace_id,
                    pack_id=body.pack_id,
                    pack_version=body.pack_version,
                    thread_id=body.thread_id,
                    task_id=body.task_id,
                    project=body.project,
                    person=body.person,
                    since=body.since,
                    until=body.until,
                    include_non_promotable_facts=body.include_non_promotable_facts,
                    provider_strategy=body.provider_strategy,
                    model_pack_strategy=body.model_pack_strategy,
                    token_budget=body.token_budget,
                ),
            )
    except (
        TaskBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-briefs/{task_brief_id}")
def get_v0_task_brief(task_brief_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_persisted_task_brief(
                ContinuityStore(conn),
                task_brief_id=task_brief_id,
            )
    except TaskBriefNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-briefs/compare")
def post_v0_task_brief_compare(body: TaskBriefCompareRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, body.user_id) as conn:
            payload: TaskBriefComparisonResponse = compare_task_briefs(
                ContinuityStore(conn),
                user_id=body.user_id,
                primary_request=TaskBriefCompileRequestInput(
                    mode=body.primary.mode,
                    query=body.primary.query,
                    workspace_id=body.primary.workspace_id,
                    pack_id=body.primary.pack_id,
                    pack_version=body.primary.pack_version,
                    thread_id=body.primary.thread_id,
                    task_id=body.primary.task_id,
                    project=body.primary.project,
                    person=body.primary.person,
                    since=body.primary.since,
                    until=body.primary.until,
                    include_non_promotable_facts=body.primary.include_non_promotable_facts,
                    provider_strategy=body.primary.provider_strategy,
                    model_pack_strategy=body.primary.model_pack_strategy,
                    token_budget=body.primary.token_budget,
                ),
                secondary_request=TaskBriefCompileRequestInput(
                    mode=body.secondary.mode,
                    query=body.secondary.query,
                    workspace_id=body.secondary.workspace_id,
                    pack_id=body.secondary.pack_id,
                    pack_version=body.secondary.pack_version,
                    thread_id=body.secondary.thread_id,
                    task_id=body.secondary.task_id,
                    project=body.secondary.project,
                    person=body.secondary.person,
                    since=body.secondary.since,
                    until=body.secondary.until,
                    include_non_promotable_facts=body.secondary.include_non_promotable_facts,
                    provider_strategy=body.secondary.provider_strategy,
                    model_pack_strategy=body.secondary.model_pack_strategy,
                    token_budget=body.secondary.token_budget,
                ),
            )
    except (
        TaskBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/chief-of-staff")
def get_chief_of_staff_priority_brief(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
        ge=0,
        le=MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ChiefOfStaffPriorityBriefResponse = compile_chief_of_staff_priority_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ChiefOfStaffPriorityBriefRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ChiefOfStaffValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/chief-of-staff/recommendation-outcomes")
def capture_chief_of_staff_recommendation_outcome_endpoint(
    request: ChiefOfStaffRecommendationOutcomeCaptureRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ChiefOfStaffRecommendationOutcomeCaptureResponse = (
                capture_chief_of_staff_recommendation_outcome(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ChiefOfStaffRecommendationOutcomeCaptureInput(
                        outcome=request.outcome,  # type: ignore[arg-type]
                        recommendation_action_type=request.recommendation_action_type,  # type: ignore[arg-type]
                        recommendation_title=request.recommendation_title,
                        rationale=request.rationale,
                        rewritten_title=request.rewritten_title,
                        target_priority_id=request.target_priority_id,
                        thread_id=request.thread_id,
                        task_id=request.task_id,
                        project=request.project,
                        person=request.person,
                    ),
                )
            )
    except ChiefOfStaffValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/chief-of-staff/handoff-review-actions")
def capture_chief_of_staff_handoff_review_action_endpoint(
    request: ChiefOfStaffHandoffReviewActionCaptureRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ChiefOfStaffHandoffReviewActionCaptureResponse = (
                capture_chief_of_staff_handoff_review_action(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ChiefOfStaffHandoffReviewActionInput(
                        handoff_item_id=request.handoff_item_id,
                        review_action=request.review_action,  # type: ignore[arg-type]
                        note=request.note,
                        thread_id=request.thread_id,
                        task_id=request.task_id,
                        project=request.project,
                        person=request.person,
                    ),
                )
            )
    except ChiefOfStaffValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/chief-of-staff/execution-routing-actions")
def capture_chief_of_staff_execution_routing_action_endpoint(
    request: ChiefOfStaffExecutionRoutingActionCaptureRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ChiefOfStaffExecutionRoutingActionCaptureResponse = (
                capture_chief_of_staff_execution_routing_action(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ChiefOfStaffExecutionRoutingActionInput(
                        handoff_item_id=request.handoff_item_id,
                        route_target=request.route_target,  # type: ignore[arg-type]
                        note=request.note,
                        thread_id=request.thread_id,
                        task_id=request.task_id,
                        project=request.project,
                        person=request.person,
                    ),
                )
            )
    except ChiefOfStaffValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/chief-of-staff/handoff-outcomes")
def capture_chief_of_staff_handoff_outcome_endpoint(
    request: ChiefOfStaffHandoffOutcomeCaptureRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ChiefOfStaffHandoffOutcomeCaptureResponse = (
                capture_chief_of_staff_handoff_outcome(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ChiefOfStaffHandoffOutcomeCaptureInput(
                        handoff_item_id=request.handoff_item_id,
                        outcome_status=request.outcome_status,  # type: ignore[arg-type]
                        note=request.note,
                        thread_id=request.thread_id,
                        task_id=request.task_id,
                        project=request.project,
                        person=request.person,
                    ),
                )
            )
    except ChiefOfStaffValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories")
def list_memories(
    user_id: UUID,
    status: MemoryReviewStatusFilter = Query(default="active"),
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_memory_review_records(
            ContinuityStore(conn),
            user_id=user_id,
            status=status,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/review-queue")
def list_memory_review_queue(
    user_id: UUID,
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
    priority_mode: MemoryReviewQueuePriorityMode = Query(
        default=DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE
    ),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_memory_review_queue_records(
            ContinuityStore(conn),
            user_id=user_id,
            limit=limit,
            priority_mode=priority_mode,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/quality-gate")
def get_memories_quality_gate(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = get_memory_quality_gate_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/trust-dashboard")
def get_memories_trust_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: MemoryTrustDashboardResponse = get_memory_trust_dashboard_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/hygiene-dashboard")
def get_memories_hygiene_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: MemoryHygieneDashboardResponse = get_memory_hygiene_dashboard_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/evaluation-summary")
def get_memories_evaluation_summary(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = get_memory_evaluation_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/semantic-retrieval")
def retrieve_semantic_memories(request: RetrieveSemanticMemoriesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_semantic_memory_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=SemanticMemoryRetrievalRequestInput(
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except SemanticMemoryRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}")
def get_memory(
    memory_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_memory_review_record(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/revisions")
def list_memory_revisions(
    memory_id: UUID,
    user_id: UUID,
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_revision_review_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
                limit=limit,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/{memory_id}/labels")
def create_memory_review_label(
    memory_id: UUID,
    request: CreateMemoryReviewLabelRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_memory_review_label_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                memory_id=memory_id,
                label=request.label,
                note=request.note,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/labels")
def list_memory_review_labels(
    memory_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_review_label_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/embedding-configs")
def create_embedding_config(request: CreateEmbeddingConfigRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_embedding_config_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                config=EmbeddingConfigCreateInput(
                    provider=request.provider,
                    model=request.model,
                    version=request.version,
                    dimensions=request.dimensions,
                    status=request.status,
                    metadata=request.metadata,
                ),
            )
    except EmbeddingConfigValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/embedding-configs")
def list_embedding_configs(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_embedding_config_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memory-embeddings")
def upsert_memory_embedding(request: UpsertMemoryEmbeddingRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_memory_embedding_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=MemoryEmbeddingUpsertInput(
                    memory_id=request.memory_id,
                    embedding_config_id=request.embedding_config_id,
                    vector=tuple(request.vector),
                ),
            )
    except MemoryEmbeddingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifact-chunk-embeddings")
def upsert_task_artifact_chunk_embedding(
    request: UpsertTaskArtifactChunkEmbeddingRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_task_artifact_chunk_embedding_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactChunkEmbeddingUpsertInput(
                    task_artifact_chunk_id=request.task_artifact_chunk_id,
                    embedding_config_id=request.embedding_config_id,
                    vector=tuple(request.vector),
                ),
            )
    except TaskArtifactChunkEmbeddingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/embeddings")
def list_memory_embeddings(memory_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_embedding_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}/chunk-embeddings")
def list_task_artifact_chunk_embeddings_for_artifact(
    task_artifact_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_embedding_records_for_artifact(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings")
def list_task_artifact_chunk_embeddings(
    task_artifact_chunk_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_embedding_records_for_chunk(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_chunk_id=task_artifact_chunk_id,
            )
    except TaskArtifactChunkEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memory-embeddings/{memory_embedding_id}")
def get_memory_embedding(memory_embedding_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_memory_embedding_record(
                ContinuityStore(conn),
                user_id=user_id,
                memory_embedding_id=memory_embedding_id,
            )
    except MemoryEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}")
def get_task_artifact_chunk_embedding(
    task_artifact_chunk_embedding_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_artifact_chunk_embedding_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_chunk_embedding_id=task_artifact_chunk_embedding_id,
            )
    except TaskArtifactChunkEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/entities")
def create_entity(request: CreateEntityRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_entity_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                entity=EntityCreateInput(
                    entity_type=request.entity_type,
                    name=request.name,
                    source_memory_ids=tuple(request.source_memory_ids),
                ),
            )
    except EntityValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/entity-edges")
def create_entity_edge(request: CreateEntityEdgeRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_entity_edge_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                edge=EntityEdgeCreateInput(
                    from_entity_id=request.from_entity_id,
                    to_entity_id=request.to_entity_id,
                    relationship_type=request.relationship_type,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                    source_memory_ids=tuple(request.source_memory_ids),
                ),
            )
    except EntityEdgeValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities")
def list_entities(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_entity_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities/{entity_id}/edges")
def list_entity_edges(entity_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_entity_edge_records(
                ContinuityStore(conn),
                user_id=user_id,
                entity_id=entity_id,
            )
    except EntityNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities/{entity_id}")
def get_entity(entity_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_entity_record(
                ContinuityStore(conn),
                user_id=user_id,
                entity_id=entity_id,
            )
    except EntityNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/auth/magic-link/start")
def start_v1_magic_link(http_request: Request, request: MagicLinkStartRequest) -> JSONResponse:
    settings = get_settings()
    email_fingerprint = hashlib.sha256(request.email.strip().lower().encode("utf-8")).hexdigest()[:20]
    rate_limit_error = _enforce_entrypoint_rate_limit(
        settings=settings,
        key=(
            "auth_magic_link_start:"
            f"{_request_client_identifier(http_request, settings)}:{email_fingerprint}"
        ),
        max_requests=settings.magic_link_start_rate_limit_max_requests,
        window_seconds=settings.magic_link_start_rate_limit_window_seconds,
        detail_code="magic_link_start_rate_limit_exceeded",
        message="magic-link start rate limit exceeded",
    )
    if rate_limit_error is not None:
        return rate_limit_error

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                challenge = start_magic_link_challenge(
                    conn,
                    email=request.email,
                    ttl_seconds=settings.magic_link_ttl_seconds,
                )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    challenge_payload = serialize_magic_link_challenge(challenge)
    delivery_payload = {
        "kind": "simulated_magic_link",
        "posture": "builder_visible_only",
    }
    if settings.app_env not in {"development", "test"}:
        challenge_payload.pop("challenge_token", None)
        delivery_payload = {
            "kind": "magic_link",
            "posture": "out_of_band_delivery_required",
        }

    payload = {
        "challenge": challenge_payload,
        "delivery": delivery_payload,
    }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/auth/magic-link/verify")
def verify_v1_magic_link(http_request: Request, request: MagicLinkVerifyRequest) -> JSONResponse:
    settings = get_settings()
    challenge_fingerprint = hashlib.sha256(request.challenge_token.strip().encode("utf-8")).hexdigest()[:20]
    rate_limit_error = _enforce_entrypoint_rate_limit(
        settings=settings,
        key=(
            "auth_magic_link_verify:"
            f"{_request_client_identifier(http_request, settings)}:{challenge_fingerprint}"
        ),
        max_requests=settings.magic_link_verify_rate_limit_max_requests,
        window_seconds=settings.magic_link_verify_rate_limit_window_seconds,
        detail_code="magic_link_verify_rate_limit_exceeded",
        message="magic-link verify rate limit exceeded",
    )
    if rate_limit_error is not None:
        return rate_limit_error

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                user_account, session, session_token, _device = verify_magic_link_challenge(
                    conn,
                    challenge_token=request.challenge_token,
                    session_ttl_seconds=settings.auth_session_ttl_seconds,
                    device_label=request.device_label,
                    device_key=request.device_key,
                )
                set_current_user_account(conn, user_account["id"])
                ensure_user_preferences_row(conn, user_account_id=user_account["id"])
                preferences = ensure_user_preferences(conn, user_account_id=user_account["id"])
                workspace = None
                if session["workspace_id"] is not None:
                    workspace = get_workspace_for_member(
                        conn,
                        workspace_id=session["workspace_id"],
                        user_account_id=user_account["id"],
                    )
                feature_flags = list_feature_flags_for_user(conn, user_account_id=user_account["id"])
    except MagicLinkTokenExpiredError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except (MagicLinkTokenInvalidError, ValueError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    payload = _serialize_hosted_session_payload(
        session=serialize_auth_session(session),
        user_account=serialize_user_account(user_account),
        workspace=None if workspace is None else serialize_workspace(workspace),
        preferences=serialize_user_preferences(preferences),
        feature_flags=feature_flags,
    )
    payload["session_token"] = session_token
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/auth/logout")
def logout_v1_auth_session(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                logout_auth_session(conn, session_token=session_token)
    except (AuthSessionInvalidError, ValueError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content={"status": "logged_out"})


@app.get("/v1/auth/session")
def get_v1_auth_session(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = get_current_workspace(
                    conn,
                    user_account_id=user_account_id,
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is not None and resolution["session"]["workspace_id"] != workspace["id"]:
                    set_session_workspace(
                        conn,
                        session_id=resolution["session"]["id"],
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                    )
                    resolution["session"]["workspace_id"] = workspace["id"]
                preferences = ensure_user_preferences(conn, user_account_id=user_account_id)
                feature_flags = list_feature_flags_for_user(conn, user_account_id=user_account_id)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    payload = _serialize_hosted_session_payload(
        session=serialize_auth_session(resolution["session"]),
        user_account=serialize_user_account(resolution["user_account"]),
        workspace=None if workspace is None else serialize_workspace(workspace),
        preferences=serialize_user_preferences(preferences),
        feature_flags=feature_flags,
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/workspaces")
def create_v1_workspace(request: Request, body: HostedWorkspaceCreateRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = create_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    name=body.name,
                    slug=body.slug,
                )
                set_session_workspace(
                    conn,
                    session_id=resolution["session"]["id"],
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder({"workspace": serialize_workspace(workspace)}),
    )


@app.get("/v1/workspaces/current")
def get_v1_current_workspace(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                if resolution["session"]["workspace_id"] != workspace["id"]:
                    set_session_workspace(
                        conn,
                        session_id=resolution["session"]["id"],
                        user_account_id=resolution["user_account"]["id"],
                        workspace_id=workspace["id"],
                    )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"workspace": serialize_workspace(workspace)}),
    )


@app.post("/v1/workspaces/bootstrap")
def bootstrap_v1_workspace(
    request: Request,
    body: HostedWorkspaceBootstrapRequest,
) -> JSONResponse:
    settings = get_settings()
    resolved_workspace_id: UUID | None = None
    user_account_id: UUID | None = None

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = None
                if body.workspace_id is not None:
                    workspace = get_workspace_for_member(
                        conn,
                        workspace_id=body.workspace_id,
                        user_account_id=user_account_id,
                    )
                    if workspace is None:
                        raise HostedWorkspaceNotFoundError(f"workspace {body.workspace_id} was not found")
                    resolved_workspace_id = workspace["id"]
                    set_session_workspace(
                        conn,
                        session_id=resolution["session"]["id"],
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                    )
                else:
                    workspace = get_current_workspace(
                        conn,
                        user_account_id=user_account_id,
                        preferred_workspace_id=resolution["session"]["workspace_id"],
                    )
                    if workspace is not None:
                        resolved_workspace_id = workspace["id"]
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                bootstrapped_workspace = complete_workspace_bootstrap(
                    conn,
                    workspace_id=workspace["id"],
                    user_account_id=user_account_id,
                )
                store = ContinuityStore(conn)
                _seed_workspace_provider_configs(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=user_account_id,
                )
                ensure_tier1_model_packs_for_workspace(
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=user_account_id,
                )
                preferences = ensure_user_preferences(conn, user_account_id=user_account_id)
                status_payload = get_bootstrap_status(
                    conn,
                    workspace_id=workspace["id"],
                    user_account_id=user_account_id,
                )
                feature_flags = list_feature_flags_for_user(conn, user_account_id=user_account_id)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        if resolved_workspace_id is not None and user_account_id is not None:
            with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
                with conn.transaction():
                    set_current_user_account(conn, user_account_id)
                    _record_workspace_onboarding_failure(
                        conn,
                        workspace_id=resolved_workspace_id,
                        error_code="workspace_not_found",
                        error_detail=str(exc),
                    )
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except HostedWorkspaceBootstrapConflictError as exc:
        if resolved_workspace_id is not None and user_account_id is not None:
            with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
                with conn.transaction():
                    set_current_user_account(conn, user_account_id)
                    _record_workspace_onboarding_failure(
                        conn,
                        workspace_id=resolved_workspace_id,
                        error_code="bootstrap_conflict",
                        error_detail=str(exc),
                    )
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace": serialize_workspace(bootstrapped_workspace),
                "bootstrap": status_payload,
                "preferences": serialize_user_preferences(preferences),
                "feature_flags": feature_flags,
                "telegram_state": "available_in_p10_s2_transport",
            }
        ),
    )


@app.get("/v1/workspaces/bootstrap/status")
def get_v1_workspace_bootstrap_status(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                status_payload = get_bootstrap_status(
                    conn,
                    workspace_id=workspace["id"],
                    user_account_id=resolution["user_account"]["id"],
                )
                feature_flags = list_feature_flags_for_user(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace": serialize_workspace(workspace),
                "bootstrap": status_payload,
                "feature_flags": feature_flags,
                "telegram_state": "available_in_p10_s2_transport",
            }
        ),
    )


@app.post("/v1/providers")
def register_v1_provider(request: Request, body: RegisterProviderRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider, capability = _register_workspace_provider(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    provider_key=body.provider_key,
                    display_name=body.display_name,
                    base_url=body.base_url,
                    api_key=body.api_key,
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/ollama/register")
def register_v1_ollama_provider(
    request: Request,
    body: RegisterOllamaProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider, capability = _register_workspace_provider(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    provider_key=OLLAMA_ADAPTER_KEY,
                    display_name=body.display_name,
                    base_url=body.base_url,
                    api_key=body.api_key or "",
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/llamacpp/register")
def register_v1_llamacpp_provider(
    request: Request,
    body: RegisterLlamaCppProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider, capability = _register_workspace_provider(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    provider_key=LLAMACPP_ADAPTER_KEY,
                    display_name=body.display_name,
                    base_url=body.base_url,
                    api_key=body.api_key or "",
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/vllm/register")
def register_v1_vllm_provider(
    request: Request,
    body: RegisterVllmProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider, capability = _register_workspace_provider(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    provider_key=VLLM_ADAPTER_KEY,
                    display_name=body.display_name,
                    base_url=body.base_url,
                    api_key=body.api_key or "",
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/azure/register")
def register_v1_azure_provider(
    request: Request,
    body: RegisterAzureProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    if body.auth_mode == AZURE_AUTH_MODE_API_KEY:
        credential = body.api_key
    else:
        credential = body.ad_token
    if credential is None:
        return JSONResponse(status_code=400, content={"detail": "azure credential is required"})

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider, capability = _register_workspace_azure_provider(
                    settings=settings,
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    display_name=body.display_name,
                    base_url=body.base_url,
                    credential=credential,
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    api_version=body.api_version,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.get("/v1/providers")
def list_v1_providers(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                store = ContinuityStore(conn)
                providers = store.list_model_providers_for_workspace(workspace_id=workspace["id"])
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    items = [_serialize_model_provider(provider) for provider in providers]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "order": list(PROVIDER_LIST_ORDER),
                },
            }
        ),
    )


@app.get("/v1/providers/{provider_id}")
def get_v1_provider(provider_id: UUID, request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider = store.get_model_provider_for_workspace_optional(
                    provider_id=provider_id,
                    workspace_id=workspace["id"],
                )
                if provider is None:
                    return JSONResponse(status_code=404, content={"detail": f"provider {provider_id} was not found"})
                capability = store.get_provider_capability_for_provider_optional(
                    provider_id=provider_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": None
                if capability is None
                else _serialize_provider_capability(capability),
            }
        ),
    )


@app.patch("/v1/providers/{provider_id}")
def update_v1_provider(
    provider_id: UUID,
    request: Request,
    body: UpdateProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider = store.get_model_provider_for_workspace_optional(
                    provider_id=provider_id,
                    workspace_id=workspace["id"],
                )
                if provider is None:
                    return JSONResponse(status_code=404, content={"detail": f"provider {provider_id} was not found"})

                provider, capability = _update_workspace_provider(
                    settings=settings,
                    store=store,
                    existing_provider=provider,
                    updated_by_user_account_id=resolution["user_account"]["id"],
                    display_name=body.display_name,
                    base_url=body.base_url,
                    api_key=body.api_key,
                    ad_token=body.ad_token,
                    auth_mode=body.auth_mode,
                    default_model=body.default_model,
                    model_list_path=body.model_list_path,
                    healthcheck_path=body.healthcheck_path,
                    invoke_path=body.invoke_path,
                    api_version=body.api_version,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/test")
def test_v1_provider(request: Request, body: TestProviderRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                provider = store.get_model_provider_for_workspace_optional(
                    provider_id=body.provider_id,
                    workspace_id=workspace["id"],
                )
                if provider is None:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"provider {body.provider_id} was not found"},
                    )

                runtime_provider = resolve_runtime_provider_config_secrets(
                    config=RuntimeProviderConfig.from_row(provider),
                    settings=settings,
                )
                adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
                model_name = (body.model or runtime_provider.default_model).strip()
                if model_name == "":
                    raise ValueError("model is required")

                try:
                    capability_snapshot = adapter.discover_capabilities(
                        config=runtime_provider,
                        settings=settings,
                    )
                except ModelInvocationError as exc:
                    sanitized_discovery_error = sanitize_provider_error_message(str(exc))
                    extra_snapshot_fields = None
                    if runtime_provider.provider_key == AZURE_ADAPTER_KEY:
                        extra_snapshot_fields = {
                            "azure_api_version": runtime_provider.azure_api_version.strip()
                            or DEFAULT_AZURE_API_VERSION,
                            "azure_auth_mode": runtime_provider.auth_mode,
                        }
                    capability = store.upsert_provider_capability(
                        workspace_id=workspace["id"],
                        provider_id=runtime_provider.provider_id,
                        discovered_by_user_account_id=resolution["user_account"]["id"],
                        adapter_key=adapter.adapter_key,
                        discovery_status="failed",
                        capability_snapshot=_fallback_provider_capability_snapshot(
                            adapter_key=adapter.adapter_key,
                            runtime_provider=adapter.runtime_provider,
                            model_list_path=runtime_provider.model_list_path,
                            healthcheck_path=runtime_provider.healthcheck_path,
                            invoke_path=runtime_provider.invoke_path,
                            extra_snapshot_fields=extra_snapshot_fields,
                        ),
                        discovery_error=sanitized_discovery_error,
                    )
                    return JSONResponse(
                        status_code=502,
                        content=jsonable_encoder(
                            {
                                "detail": sanitized_discovery_error,
                                "provider": _serialize_model_provider(provider),
                                "capabilities": _serialize_provider_capability(capability),
                            }
                        ),
                    )
                model_request = build_provider_test_model_request(
                    runtime_provider=runtime_provider.model_provider,
                    model=model_name,
                    prompt_text=body.prompt.strip(),
                )

                try:
                    model_response = _invoke_runtime_provider_model(
                        store=store,
                        workspace_id=workspace["id"],
                        invoked_by_user_account_id=resolution["user_account"]["id"],
                        thread_id=None,
                        invocation_kind="provider_test",
                        adapter=adapter,
                        runtime_provider=runtime_provider,
                        settings=settings,
                        model_request=model_request,
                    )
                except ModelInvocationError as exc:
                    sanitized_invoke_error = sanitize_provider_error_message(str(exc))
                    capability = store.upsert_provider_capability(
                        workspace_id=workspace["id"],
                        provider_id=runtime_provider.provider_id,
                        discovered_by_user_account_id=resolution["user_account"]["id"],
                        adapter_key=adapter.adapter_key,
                        discovery_status="failed",
                        capability_snapshot=capability_snapshot,
                        discovery_error=sanitized_invoke_error,
                    )
                    return JSONResponse(
                        status_code=502,
                        content=jsonable_encoder(
                            {
                                "detail": sanitized_invoke_error,
                                "provider": _serialize_model_provider(provider),
                                "capabilities": _serialize_provider_capability(capability),
                            }
                        ),
                    )

                capability = store.upsert_provider_capability(
                    workspace_id=workspace["id"],
                    provider_id=runtime_provider.provider_id,
                    discovered_by_user_account_id=resolution["user_account"]["id"],
                    adapter_key=adapter.adapter_key,
                    discovery_status="ready",
                    capability_snapshot=capability_snapshot,
                    discovery_error=None,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
                "result": {
                    "provider": model_response.provider,
                    "model": model_response.model,
                    "response_id": model_response.response_id,
                    "finish_reason": model_response.finish_reason,
                    "text": model_response.output_text,
                    "usage": model_response.usage,
                },
            }
        ),
    )


@app.get("/v1/model-packs")
def list_v1_model_packs(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                store = ContinuityStore(conn)
                packs = store.list_model_packs_for_workspace(workspace_id=workspace["id"])
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ModelPackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    items = [_serialize_model_pack(pack) for pack in packs]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "order": list(MODEL_PACK_LIST_ORDER),
                },
            }
        ),
    )


@app.get("/v1/model-packs/{pack_id}")
def get_v1_model_pack(
    pack_id: str,
    request: Request,
    version: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        normalized_pack_id = normalize_pack_id(pack_id)
        normalized_version = None if version is None else normalize_pack_version(version)
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                store = ContinuityStore(conn)
                pack = store.get_model_pack_for_workspace_optional(
                    workspace_id=workspace["id"],
                    pack_id=normalized_pack_id,
                    pack_version=normalized_version,
                )
                if pack is None:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"model pack {normalized_pack_id} was not found"},
                    )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ModelPackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"model_pack": _serialize_model_pack(pack)}),
    )


@app.post("/v1/model-packs")
def create_v1_model_pack(request: Request, body: CreateModelPackRequest) -> JSONResponse:
    settings = get_settings()

    try:
        normalized_pack_id = normalize_pack_id(body.pack_id)
        normalized_pack_version = normalize_pack_version(body.pack_version)
        normalized_family = normalize_pack_family(body.family)
        normalized_briefing_strategy = normalize_briefing_strategy(body.briefing_strategy)
        normalized_briefing_max_tokens = normalize_briefing_max_tokens(body.briefing_max_tokens)
        normalized_contract = normalize_model_pack_contract(body.contract)
        normalized_display_name = body.display_name.strip()
        if normalized_display_name == "":
            raise ModelPackValidationError("display_name is required")

        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                ensure_tier1_model_packs_for_workspace(
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                )
                if is_reserved_tier1_pack_key(
                    pack_id=normalized_pack_id,
                    pack_version=normalized_pack_version,
                ):
                    return JSONResponse(
                        status_code=409,
                        content={
                            "detail": (
                                f"model pack {normalized_pack_id}@{normalized_pack_version} "
                                "is reserved for built-in catalog entries"
                            )
                        },
                    )
                pack = store.create_model_pack(
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                    pack_id=normalized_pack_id,
                    pack_version=normalized_pack_version,
                    display_name=normalized_display_name,
                    family=normalized_family,
                    description=body.description.strip(),
                    status=MODEL_PACK_STATUS_ACTIVE,
                    briefing_strategy=normalized_briefing_strategy,
                    briefing_max_tokens=normalized_briefing_max_tokens,
                    contract=normalized_contract,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "model pack pack_id and pack_version must be unique within the workspace"},
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ModelPackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder({"model_pack": _serialize_model_pack(pack)}),
    )


@app.post("/v1/model-packs/{pack_id}/bind")
def bind_v1_model_pack(pack_id: str, request: Request, body: BindModelPackRequest) -> JSONResponse:
    settings = get_settings()

    try:
        normalized_pack_id = normalize_pack_id(pack_id)
        normalized_pack_version = (
            None if body.pack_version is None else normalize_pack_version(body.pack_version)
        )
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                _ensure_workspace_owner_access(
                    workspace=workspace,
                    user_account_id=resolution["user_account"]["id"],
                )

                store = ContinuityStore(conn)
                ensure_tier1_model_packs_for_workspace(
                    store=store,
                    workspace_id=workspace["id"],
                    created_by_user_account_id=resolution["user_account"]["id"],
                )
                provider = None
                if body.provider_id is not None:
                    provider = store.get_model_provider_for_workspace_optional(
                        provider_id=body.provider_id,
                        workspace_id=workspace["id"],
                    )
                    if provider is None:
                        return JSONResponse(
                            status_code=404,
                            content={"detail": f"provider {body.provider_id} was not found"},
                        )
                pack = store.get_model_pack_for_workspace_optional(
                    workspace_id=workspace["id"],
                    pack_id=normalized_pack_id,
                    pack_version=normalized_pack_version,
                )
                if pack is None:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"model pack {normalized_pack_id} was not found"},
                    )
                if provider is not None:
                    assert_model_pack_runtime_compatibility(
                        pack=pack,
                        provider_key=provider["provider_key"],
                        runtime_provider=provider["model_provider"],
                    )
                store.create_workspace_model_pack_binding(
                    workspace_id=workspace["id"],
                    provider_id=None if provider is None else provider["id"],
                    model_pack_id=pack["id"],
                    bound_by_user_account_id=resolution["user_account"]["id"],
                    binding_source=MODEL_PACK_BINDING_SOURCE_MANUAL,
                    metadata=body.metadata,
                )
                if provider is None:
                    binding = store.get_latest_workspace_model_pack_binding_optional(
                        workspace_id=workspace["id"],
                    )
                else:
                    binding = store.get_resolved_workspace_model_pack_binding_optional(
                        workspace_id=workspace["id"],
                        provider_id=provider["id"],
                    )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ModelPackCompatibilityError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ModelPackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    if binding is None:
        return JSONResponse(status_code=500, content={"detail": "workspace model pack binding could not be resolved"})
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"binding": _serialize_workspace_model_pack_binding(binding)}),
    )


@app.get("/v1/workspaces/{workspace_id}/model-pack-binding")
def get_v1_workspace_model_pack_binding(
    workspace_id: UUID,
    request: Request,
    provider_id: Annotated[UUID | None, Query()] = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_workspace_for_member(
                    conn,
                    workspace_id=workspace_id,
                    user_account_id=resolution["user_account"]["id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": f"workspace {workspace_id} was not found"})

                store = ContinuityStore(conn)
                if provider_id is None:
                    binding = store.get_latest_workspace_model_pack_binding_optional(
                        workspace_id=workspace["id"],
                    )
                else:
                    provider = store.get_model_provider_for_workspace_optional(
                        provider_id=provider_id,
                        workspace_id=workspace["id"],
                    )
                    if provider is None:
                        return JSONResponse(status_code=404, content={"detail": f"provider {provider_id} was not found"})
                    binding = store.get_resolved_workspace_model_pack_binding_optional(
                        workspace_id=workspace["id"],
                        provider_id=provider_id,
                    )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "binding": None
                if binding is None
                else _serialize_workspace_model_pack_binding(binding),
            }
        ),
    )


@app.post("/v1/runtime/invoke")
def invoke_v1_runtime(request: Request, body: RuntimeInvokeRequest) -> JSONResponse:
    settings = get_settings()

    workspace_id: UUID | None = None
    user_account: dict[str, object] | None = None
    runtime_provider: RuntimeProviderConfig | None = None
    model_pack: ModelPackRow | None = None
    model_pack_source: str = "none"

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = get_current_workspace(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                workspace_id = workspace["id"]
                user_account = resolution["user_account"]

                store = ContinuityStore(conn)
                runtime_provider = _runtime_provider_config_or_none(
                    store=store,
                    provider_id=body.provider_id,
                    workspace_id=workspace["id"],
                    settings=settings,
                )
                if runtime_provider is None:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"provider {body.provider_id} was not found"},
                    )
                selected_pack = resolve_workspace_model_pack_selection(
                    store=store,
                    workspace_id=workspace["id"],
                    requested_pack_id=body.pack_id,
                    requested_pack_version=body.pack_version,
                    provider_id=runtime_provider.provider_id,
                )
                model_pack = selected_pack.pack
                model_pack_source = selected_pack.source
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except ModelPackCompatibilityError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ModelPackNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ModelPackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    if workspace_id is None or user_account is None or runtime_provider is None:
        return JSONResponse(status_code=500, content={"detail": "runtime context could not be resolved"})

    selected_model = (body.model or runtime_provider.default_model).strip()
    if selected_model == "":
        return JSONResponse(status_code=400, content={"detail": "model is required"})

    runtime_limits = ContextCompilerLimits(
        max_sessions=body.max_sessions,
        max_events=body.max_events,
        max_memories=body.max_memories,
        max_entities=body.max_entities,
        max_entity_edges=body.max_entity_edges,
    )
    runtime_system_instruction = SYSTEM_INSTRUCTION
    runtime_developer_instruction = DEVELOPER_INSTRUCTION

    try:
        if model_pack is not None:
            assert_model_pack_runtime_compatibility(
                pack=model_pack,
                provider_key=runtime_provider.provider_key,
                runtime_provider=runtime_provider.model_provider,
            )
            runtime_shape = build_model_pack_runtime_shape(model_pack["contract"])
            (
                max_sessions,
                max_events,
                max_memories,
                max_entities,
                max_entity_edges,
            ) = apply_runtime_limit_caps(
                max_sessions=runtime_limits.max_sessions,
                max_events=runtime_limits.max_events,
                max_memories=runtime_limits.max_memories,
                max_entities=runtime_limits.max_entities,
                max_entity_edges=runtime_limits.max_entity_edges,
                shape=runtime_shape,
            )
            runtime_limits = ContextCompilerLimits(
                max_sessions=max_sessions,
                max_events=max_events,
                max_memories=max_memories,
                max_entities=max_entities,
                max_entity_edges=max_entity_edges,
            )
            runtime_system_instruction = append_instruction(
                SYSTEM_INSTRUCTION,
                runtime_shape.system_instruction_append,
            )
            runtime_developer_instruction = append_instruction(
                DEVELOPER_INSTRUCTION,
                runtime_shape.developer_instruction_append,
            )
    except ModelPackCompatibilityError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    user_account_id = user_account["id"]
    if not isinstance(user_account_id, UUID):
        return JSONResponse(status_code=500, content={"detail": "runtime user context is invalid"})

    try:
        adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    try:
        with user_connection(settings.database_url, user_account_id) as conn:
            set_current_user_account(conn, user_account_id)
            store = ContinuityStore(conn)
            result = generate_response(
                store=store,
                settings=settings,
                user_id=user_account_id,
                thread_id=body.thread_id,
                message_text=body.message,
                limits=runtime_limits,
                runtime_override=(runtime_provider.model_provider, selected_model),
                model_invoker=lambda model_request: _invoke_runtime_provider_model(
                    store=store,
                    workspace_id=workspace_id,
                    invoked_by_user_account_id=user_account_id,
                    thread_id=body.thread_id,
                    invocation_kind="runtime_invoke",
                    adapter=adapter,
                    runtime_provider=runtime_provider,
                    settings=settings,
                    model_request=model_request,
                ),
                system_instruction=runtime_system_instruction,
                developer_instruction=runtime_developer_instruction,
            )
            if isinstance(result, ResponseFailure):
                return JSONResponse(
                    status_code=502,
                    content=jsonable_encoder(
                        {
                            "detail": result.detail,
                            "trace": result.trace,
                            "metadata": {
                                "workspace_id": str(workspace_id),
                                "provider_id": str(runtime_provider.provider_id),
                                "provider_key": runtime_provider.provider_key,
                                "model_pack": None
                                if model_pack is None
                                else {
                                    "pack_id": model_pack["pack_id"],
                                    "pack_version": model_pack["pack_version"],
                                    "source": model_pack_source,
                                },
                            },
                        }
                    ),
                )

            assistant_event_id = UUID(result["assistant"]["event_id"])
            assistant_rows = store.list_events_by_ids([assistant_event_id])
            assistant_payload = assistant_rows[0]["payload"] if assistant_rows else {}
            model_payload = assistant_payload.get("model", {})
            usage_payload = (
                model_payload.get("usage")
                if isinstance(model_payload, dict) and isinstance(model_payload.get("usage"), dict)
                else {
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                }
            )
            response_id = (
                model_payload.get("response_id")
                if isinstance(model_payload, dict) and isinstance(model_payload.get("response_id"), str)
                else None
            )
            finish_reason = (
                model_payload.get("finish_reason")
                if isinstance(model_payload, dict) and isinstance(model_payload.get("finish_reason"), str)
                else "incomplete"
            )
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "assistant": {
                    "event_id": result["assistant"]["event_id"],
                    "sequence_no": result["assistant"]["sequence_no"],
                    "provider_id": str(runtime_provider.provider_id),
                    "provider_key": runtime_provider.provider_key,
                    "model_provider": result["assistant"]["model_provider"],
                    "model": result["assistant"]["model"],
                    "response_id": response_id,
                    "finish_reason": finish_reason,
                    "text": result["assistant"]["text"],
                    "usage": usage_payload,
                },
                "trace": result["trace"],
                "metadata": {
                    "workspace_id": str(workspace_id),
                    "model_pack": None
                    if model_pack is None
                    else {
                        "pack_id": model_pack["pack_id"],
                        "pack_version": model_pack["pack_version"],
                        "source": model_pack_source,
                    },
                },
            }
        ),
    )


@app.post("/v1/devices/link/start")
def start_v1_device_link(request: Request, body: DeviceLinkStartRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace_id = body.workspace_id or resolution["session"]["workspace_id"]
                if body.workspace_id is not None:
                    workspace = get_workspace_for_member(
                        conn,
                        workspace_id=body.workspace_id,
                        user_account_id=user_account_id,
                    )
                    if workspace is None:
                        raise HostedWorkspaceNotFoundError(f"workspace {body.workspace_id} was not found")
                    workspace_id = workspace["id"]
                challenge = start_device_link_challenge(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace_id,
                    device_key=body.device_key,
                    device_label=body.device_label,
                    ttl_seconds=settings.device_link_ttl_seconds,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"challenge": serialize_device_link_challenge(challenge)}),
    )


@app.post("/v1/devices/link/confirm")
def confirm_v1_device_link(request: Request, body: DeviceLinkConfirmRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                device = confirm_device_link_challenge(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    challenge_token=body.challenge_token,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except DeviceLinkTokenExpiredError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except DeviceLinkTokenInvalidError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder({"device": serialize_device(device)}),
    )


@app.get("/v1/devices")
def list_v1_devices(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                devices = list_hosted_devices(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=resolution["session"]["workspace_id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    items = [serialize_device(device) for device in devices]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "active_count": sum(1 for item in items if item["status"] == "active"),
                    "revoked_count": sum(1 for item in items if item["status"] == "revoked"),
                    "order": ["created_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.delete("/v1/devices/{device_id}")
def delete_v1_device(device_id: UUID, request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                device = revoke_hosted_device(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    device_id=device_id,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedDeviceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"device": serialize_device(device)}),
    )


@app.get("/v1/preferences")
def get_v1_preferences(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                preferences = ensure_user_preferences(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"preferences": serialize_user_preferences(preferences)}),
    )


@app.patch("/v1/preferences")
def patch_v1_preferences(
    request: Request,
    body: HostedPreferencesPatchRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                preferences = patch_user_preferences(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    timezone=body.timezone,
                    brief_preferences=body.brief_preferences,
                    quiet_hours=body.quiet_hours,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedPreferencesValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"preferences": serialize_user_preferences(preferences)}),
    )


@app.get("/v1/admin/hosted/overview")
def get_v1_admin_hosted_overview(
    request: Request,
    window_hours: int = Query(default=24, ge=1, le=168),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = get_hosted_overview_for_admin(conn, window_hours=window_hours)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/admin/hosted/design-partners/dashboard")
def get_v1_admin_hosted_design_partner_dashboard(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = get_design_partner_dashboard(conn)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/admin/hosted/design-partners")
def get_v1_admin_hosted_design_partners(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = list_design_partners(conn, limit=limit)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/admin/hosted/design-partners")
def post_v1_admin_hosted_design_partner(
    request: Request,
    body: DesignPartnerCreateRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = create_design_partner(
                    conn,
                    created_by_user_account_id=user_account_id,
                    name=body.name,
                    partner_key=body.partner_key,
                    lifecycle_stage=body.lifecycle_stage,
                    onboarding_status=body.onboarding_status,
                    support_status=body.support_status,
                    instrumentation_status=body.instrumentation_status,
                    case_study_status=body.case_study_status,
                    target_outcome=body.target_outcome,
                    launch_notes=body.launch_notes,
                    onboarding_checklist=body.onboarding_checklist,
                    support_checklist=body.support_checklist,
                    success_metrics=body.success_metrics,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v1/admin/hosted/design-partners/{design_partner_id}")
def get_v1_admin_hosted_design_partner_detail(
    design_partner_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = get_design_partner_detail(conn, design_partner_id=design_partner_id)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except DesignPartnerNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.patch("/v1/admin/hosted/design-partners/{design_partner_id}")
def patch_v1_admin_hosted_design_partner(
    design_partner_id: UUID,
    request: Request,
    body: DesignPartnerPatchRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = update_design_partner(
                    conn,
                    design_partner_id=design_partner_id,
                    lifecycle_stage=body.lifecycle_stage,
                    onboarding_status=body.onboarding_status,
                    support_status=body.support_status,
                    instrumentation_status=body.instrumentation_status,
                    case_study_status=body.case_study_status,
                    target_outcome=body.target_outcome,
                    launch_notes=body.launch_notes,
                    onboarding_checklist=body.onboarding_checklist,
                    support_checklist=body.support_checklist,
                    success_metrics=body.success_metrics,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except DesignPartnerNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/admin/hosted/design-partners/{design_partner_id}/workspaces")
def post_v1_admin_hosted_design_partner_workspace(
    design_partner_id: UUID,
    request: Request,
    body: DesignPartnerWorkspaceLinkRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = link_design_partner_workspace(
                    conn,
                    design_partner_id=design_partner_id,
                    workspace_id=body.workspace_id,
                    linked_by_user_account_id=user_account_id,
                    linkage_status=body.linkage_status,
                    environment_label=body.environment_label,
                    instrumentation_ready=body.instrumentation_ready,
                    notes=body.notes,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except DesignPartnerNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except DesignPartnerWorkspaceConflictError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.Error as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.post("/v1/admin/hosted/design-partners/{design_partner_id}/feedback")
def post_v1_admin_hosted_design_partner_feedback(
    design_partner_id: UUID,
    request: Request,
    body: DesignPartnerFeedbackCreateRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = record_design_partner_feedback(
                    conn,
                    design_partner_id=design_partner_id,
                    captured_by_user_account_id=user_account_id,
                    workspace_id=body.workspace_id,
                    source_kind=body.source_kind,
                    category=body.category,
                    sentiment=body.sentiment,
                    urgency=body.urgency,
                    feedback_status=body.feedback_status,
                    case_study_signal=body.case_study_signal,
                    summary=body.summary,
                    detail=body.detail,
                    metadata=body.metadata,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except DesignPartnerNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except DesignPartnerFeedbackValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v1/admin/hosted/workspaces")
def get_v1_admin_hosted_workspaces(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                items = list_hosted_workspaces_for_admin(conn, limit=limit)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "returned_count": len(items),
                    "order": ["updated_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.get("/v1/admin/hosted/delivery-receipts")
def get_v1_admin_hosted_delivery_receipts(
    request: Request,
    limit: int = Query(default=100, ge=1, le=400),
    workspace_id: UUID | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                items = list_hosted_delivery_receipts_for_admin(
                    conn,
                    limit=limit,
                    workspace_id=workspace_id,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "returned_count": len(items),
                    "order": ["recorded_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.get("/v1/admin/hosted/incidents")
def get_v1_admin_hosted_incidents(
    request: Request,
    status: str = Query(default="open", min_length=1, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    workspace_id: UUID | None = None,
) -> JSONResponse:
    settings = get_settings()
    normalized_status = status.strip().casefold()
    if normalized_status not in {"open", "resolved", "all"}:
        return JSONResponse(status_code=400, content={"detail": "status must be one of: open, resolved, all"})

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                items = list_hosted_incidents_for_admin(
                    conn,
                    limit=limit,
                    status_filter=normalized_status,  # type: ignore[arg-type]
                    workspace_id=workspace_id,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "returned_count": len(items),
                    "status_filter": normalized_status,
                    "order": ["occurred_at_desc", "incident_id_desc"],
                },
            }
        ),
    )


@app.get("/v1/admin/hosted/rollout-flags")
def get_v1_admin_hosted_rollout_flags(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                flags = list_rollout_flags_for_admin(conn, user_account_id=user_account_id)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": flags,
                "summary": {
                    "total_count": len(flags),
                    "enabled_count": sum(1 for flag in flags if flag["enabled"]),
                    "disabled_count": sum(1 for flag in flags if not flag["enabled"]),
                    "order": ["flag_key_asc"],
                },
            }
        ),
    )


@app.patch("/v1/admin/hosted/rollout-flags")
def patch_v1_admin_hosted_rollout_flags(
    request: Request,
    body: HostedRolloutFlagsPatchRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                updated_flags = patch_rollout_flags(
                    conn,
                    patches=[
                        {
                            "flag_key": item.flag_key,
                            "enabled": item.enabled,
                            "cohort_key": item.cohort_key,
                            "description": item.description,
                        }
                        for item in body.updates
                    ],
                    allowed_cohort_key=resolution["user_account"]["beta_cohort_key"],
                )
                flags = list_rollout_flags_for_admin(conn, user_account_id=user_account_id)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "updated": updated_flags,
                "items": flags,
                "summary": {
                    "total_count": len(flags),
                    "enabled_count": sum(1 for flag in flags if flag["enabled"]),
                    "disabled_count": sum(1 for flag in flags if not flag["enabled"]),
                },
            }
        ),
    )


@app.get("/v1/admin/hosted/analytics")
def get_v1_admin_hosted_analytics(
    request: Request,
    window_hours: int = Query(default=24, ge=1, le=168),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                telemetry = aggregate_chat_telemetry(conn, window_hours=window_hours)
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder({"analytics": telemetry}))


@app.get("/v1/admin/hosted/rate-limits")
def get_v1_admin_hosted_rate_limits(
    request: Request,
    window_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                _ensure_hosted_admin_access(conn, user_account_id=user_account_id)
                payload = get_hosted_rate_limits_for_admin(
                    conn,
                    window_hours=window_hours,
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/link/start")
def start_v1_telegram_link(request: Request, body: TelegramLinkStartRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=body.workspace_id,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                challenge = start_telegram_link_challenge(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    ttl_seconds=settings.telegram_link_ttl_seconds,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    payload = {
        "workspace_id": str(workspace["id"]),
        "challenge": serialize_channel_link_challenge(challenge, include_token=True),
        "instructions": {
            "bot_username": settings.telegram_bot_username,
            "command": f"/link {challenge['link_code']}",
            "posture": "send the link code to the configured telegram bot, then confirm in hosted settings",
        },
    }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/link/confirm")
def confirm_v1_telegram_link(request: Request, body: TelegramLinkConfirmRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                challenge, identity = confirm_telegram_link_challenge(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    challenge_token=body.challenge_token,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramLinkPendingError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramLinkTokenExpiredError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramLinkTokenInvalidError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "identity": serialize_channel_identity(identity),
                "challenge": serialize_channel_link_challenge(challenge, include_token=False),
            }
        ),
    )


@app.post("/v1/channels/telegram/unlink")
def unlink_v1_telegram(request: Request, body: TelegramUnlinkRequest) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=body.workspace_id,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                identity = unlink_telegram_identity(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder({"identity": serialize_channel_identity(identity)}))


@app.get("/v1/channels/telegram/status")
def get_v1_telegram_status(
    request: Request,
    workspace_id: UUID | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=workspace_id,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                payload = get_telegram_link_status(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/webhook")
async def ingest_v1_telegram_webhook(request: Request) -> JSONResponse:
    settings = get_settings()
    if settings.app_env not in {"development", "test"} and settings.telegram_webhook_secret == "":  # nosec B105
        return JSONResponse(
            status_code=503,
            content={"detail": "telegram webhook ingress is not configured"},
        )

    rate_limit_error = _enforce_entrypoint_rate_limit(
        settings=settings,
        key=f"telegram_webhook:{_request_client_identifier(request, settings)}",
        max_requests=settings.telegram_webhook_rate_limit_max_requests,
        window_seconds=settings.telegram_webhook_rate_limit_window_seconds,
        detail_code="telegram_webhook_rate_limit_exceeded",
        message="telegram webhook rate limit exceeded",
    )
    if rate_limit_error is not None:
        return rate_limit_error

    if settings.telegram_webhook_secret != "":  # nosec B105
        header_secret = request.headers.get("x-telegram-bot-api-secret-token", "").strip()
        if not hmac.compare_digest(header_secret, settings.telegram_webhook_secret):
            return JSONResponse(status_code=401, content={"detail": "telegram webhook secret is invalid"})

    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "telegram webhook payload must be valid json"})

    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"detail": "telegram webhook payload must be an object"})

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                set_hosted_service_bypass(conn, True)
                ingest_result = ingest_telegram_webhook(
                    conn,
                    payload=payload,
                    bot_username=settings.telegram_bot_username,
                )
    except TelegramWebhookValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "status": "accepted",
                "ingest": serialize_webhook_ingest_result(ingest_result),
            }
        ),
    )


@app.get("/v1/channels/telegram/messages")
def list_v1_telegram_messages(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                rows = list_workspace_telegram_messages(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=workspace["id"],
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    items = [serialize_channel_message(row) for row in rows]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "workspace_id": str(workspace["id"]),
                    "total_count": len(items),
                    "order": ["created_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.get("/v1/channels/telegram/threads")
def list_v1_telegram_threads(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                rows = list_workspace_telegram_threads(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=workspace["id"],
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    items = [serialize_channel_thread(row) for row in rows]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "workspace_id": str(workspace["id"]),
                    "total_count": len(items),
                    "order": ["last_message_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.post("/v1/channels/telegram/messages/{message_id}/dispatch")
def dispatch_v1_telegram_message(
    message_id: UUID,
    request: Request,
    body: TelegramDispatchRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                outbound_message, receipt = dispatch_telegram_message(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=workspace["id"],
                    source_message_id=message_id,
                    text=body.text,
                    dispatch_idempotency_key=body.idempotency_key,
                    bot_token=settings.telegram_bot_token,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramMessageNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramRoutingError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "message": serialize_channel_message(outbound_message),
                "receipt": serialize_delivery_receipt(receipt),
            }
        ),
    )


@app.get("/v1/channels/telegram/delivery-receipts")
def list_v1_telegram_delivery_receipts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                rows = list_workspace_telegram_delivery_receipts(
                    conn,
                    user_account_id=resolution["user_account"]["id"],
                    workspace_id=workspace["id"],
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    items = [serialize_delivery_receipt(row) for row in rows]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "workspace_id": str(workspace["id"]),
                    "total_count": len(items),
                    "order": ["recorded_at_desc", "id_desc"],
                },
            }
        ),
    )


@app.get("/v1/channels/telegram/notification-preferences")
def get_v1_telegram_notification_preferences(
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                payload = get_workspace_notification_preferences(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.patch("/v1/channels/telegram/notification-preferences")
def patch_v1_telegram_notification_preferences(
    request: Request,
    body: TelegramNotificationPreferencesPatchRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                patch_payload = body.model_dump(exclude_none=True)
                patch_workspace_notification_subscription(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    patch=patch_payload,
                )
                payload = get_workspace_notification_preferences(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/daily-brief")
def get_v1_telegram_daily_brief(
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                payload = get_workspace_daily_brief_preview(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/daily-brief/deliver")
def post_v1_telegram_daily_brief_deliver(
    request: Request,
    body: TelegramScheduledDeliveryRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                rollout_resolution = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_scheduler_delivery_enabled",
                )
                if not rollout_resolution["enabled"]:
                    record_chat_telemetry(
                        conn,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="scheduler_daily_brief",
                        event_kind="rollout_block",
                        status="blocked_rollout",
                        route_path="/v1/channels/telegram/daily-brief/deliver",
                        rollout_flag_key=rollout_resolution["flag_key"],
                        rollout_flag_state="blocked",
                        evidence={
                            "force": body.force,
                            "idempotency_key": body.idempotency_key,
                        },
                    )
                    return _hosted_rollout_block_error(flag_key=rollout_resolution["flag_key"])

                rate_limit_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_rate_limits_enabled",
                )
                abuse_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_abuse_controls_enabled",
                )
                if rate_limit_rollout["enabled"]:
                    decision = evaluate_hosted_flow_limits(
                        conn,
                        settings=settings,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="scheduler_daily_brief",
                    )
                    if decision["code"] == "hosted_abuse_limit_exceeded" and not abuse_rollout["enabled"]:
                        decision = {
                            **decision,
                            "allowed": True,
                            "code": None,
                            "message": "abuse controls disabled by rollout",
                            "retry_after_seconds": 0,
                            "abuse_signal": None,
                        }

                    if not decision["allowed"]:
                        blocked_status = "abuse_blocked" if decision["code"] == "hosted_abuse_limit_exceeded" else "rate_limited"
                        blocked_event = "abuse_block" if blocked_status == "abuse_blocked" else "rate_limited"
                        record_chat_telemetry(
                            conn,
                            user_account_id=user_account_id,
                            workspace_id=workspace["id"],
                            flow_kind="scheduler_daily_brief",
                            event_kind=blocked_event,  # type: ignore[arg-type]
                            status=blocked_status,  # type: ignore[arg-type]
                            route_path="/v1/channels/telegram/daily-brief/deliver",
                            rollout_flag_key=rate_limit_rollout["flag_key"],
                            rollout_flag_state="enabled",
                            rate_limit_key=decision["rate_limit_key"],
                            rate_limit_window_seconds=decision["window_seconds"],
                            rate_limit_max_requests=decision["max_requests"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            abuse_signal=decision["abuse_signal"],
                            evidence={
                                "force": body.force,
                                "idempotency_key": body.idempotency_key,
                            },
                        )
                        return _hosted_rate_limit_error(
                            detail_code=decision["code"] or "hosted_rate_limit_exceeded",
                            message=decision["message"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            rate_limit_key=decision["rate_limit_key"],
                            window_seconds=decision["window_seconds"],
                            max_requests=decision["max_requests"],
                            observed_requests=decision["observed_requests"],
                            abuse_signal=decision["abuse_signal"],
                        )

                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="scheduler_daily_brief",
                    event_kind="attempt",
                    status="ok",
                    route_path="/v1/channels/telegram/daily-brief/deliver",
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    evidence={
                        "force": body.force,
                        "idempotency_key": body.idempotency_key,
                    },
                )

                payload = deliver_workspace_daily_brief(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    bot_token=settings.telegram_bot_token,
                    force=body.force,
                    idempotency_key=body.idempotency_key,
                )
                delivery_receipt = payload.get("delivery_receipt")
                delivery_receipt_id: UUID | None = None
                if isinstance(delivery_receipt, dict) and isinstance(delivery_receipt.get("id"), str):
                    delivery_receipt_id = UUID(delivery_receipt["id"])

                status_value: str = "ok"
                if isinstance(payload.get("job"), dict):
                    job_status = str(payload["job"].get("status", "ok"))
                    if job_status in {"failed"}:
                        status_value = "failed"
                    elif job_status.startswith("suppressed"):
                        status_value = "suppressed"
                    elif job_status in {"simulated", "delivered"}:
                        status_value = job_status
                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="scheduler_daily_brief",
                    event_kind="result",
                    status=status_value,  # type: ignore[arg-type]
                    route_path="/v1/channels/telegram/daily-brief/deliver",
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    delivery_receipt_id=delivery_receipt_id,
                    evidence={
                        "idempotent_replay": bool(payload.get("idempotent_replay")),
                        "force": body.force,
                    },
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    status_code = 200 if bool(payload.get("idempotent_replay")) else 201
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/open-loop-prompts")
def list_v1_telegram_open_loop_prompts(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                payload = list_workspace_open_loop_prompts(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver")
def post_v1_telegram_open_loop_prompt_deliver(
    prompt_id: str,
    request: Request,
    body: TelegramScheduledDeliveryRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                rollout_resolution = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_scheduler_delivery_enabled",
                )
                if not rollout_resolution["enabled"]:
                    record_chat_telemetry(
                        conn,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="scheduler_open_loop_prompt",
                        event_kind="rollout_block",
                        status="blocked_rollout",
                        route_path=f"/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver",
                        rollout_flag_key=rollout_resolution["flag_key"],
                        rollout_flag_state="blocked",
                        evidence={
                            "prompt_id": prompt_id,
                            "force": body.force,
                            "idempotency_key": body.idempotency_key,
                        },
                    )
                    return _hosted_rollout_block_error(flag_key=rollout_resolution["flag_key"])

                rate_limit_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_rate_limits_enabled",
                )
                abuse_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_abuse_controls_enabled",
                )
                if rate_limit_rollout["enabled"]:
                    decision = evaluate_hosted_flow_limits(
                        conn,
                        settings=settings,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="scheduler_open_loop_prompt",
                    )
                    if decision["code"] == "hosted_abuse_limit_exceeded" and not abuse_rollout["enabled"]:
                        decision = {
                            **decision,
                            "allowed": True,
                            "code": None,
                            "message": "abuse controls disabled by rollout",
                            "retry_after_seconds": 0,
                            "abuse_signal": None,
                        }

                    if not decision["allowed"]:
                        blocked_status = "abuse_blocked" if decision["code"] == "hosted_abuse_limit_exceeded" else "rate_limited"
                        blocked_event = "abuse_block" if blocked_status == "abuse_blocked" else "rate_limited"
                        record_chat_telemetry(
                            conn,
                            user_account_id=user_account_id,
                            workspace_id=workspace["id"],
                            flow_kind="scheduler_open_loop_prompt",
                            event_kind=blocked_event,  # type: ignore[arg-type]
                            status=blocked_status,  # type: ignore[arg-type]
                            route_path=f"/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver",
                            rollout_flag_key=rate_limit_rollout["flag_key"],
                            rollout_flag_state="enabled",
                            rate_limit_key=decision["rate_limit_key"],
                            rate_limit_window_seconds=decision["window_seconds"],
                            rate_limit_max_requests=decision["max_requests"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            abuse_signal=decision["abuse_signal"],
                            evidence={
                                "prompt_id": prompt_id,
                                "force": body.force,
                                "idempotency_key": body.idempotency_key,
                            },
                        )
                        return _hosted_rate_limit_error(
                            detail_code=decision["code"] or "hosted_rate_limit_exceeded",
                            message=decision["message"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            rate_limit_key=decision["rate_limit_key"],
                            window_seconds=decision["window_seconds"],
                            max_requests=decision["max_requests"],
                            observed_requests=decision["observed_requests"],
                            abuse_signal=decision["abuse_signal"],
                        )

                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="scheduler_open_loop_prompt",
                    event_kind="attempt",
                    status="ok",
                    route_path=f"/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver",
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    evidence={
                        "prompt_id": prompt_id,
                        "force": body.force,
                        "idempotency_key": body.idempotency_key,
                    },
                )

                payload = deliver_workspace_open_loop_prompt(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    prompt_id=prompt_id,
                    bot_token=settings.telegram_bot_token,
                    force=body.force,
                    idempotency_key=body.idempotency_key,
                )
                delivery_receipt = payload.get("delivery_receipt")
                delivery_receipt_id: UUID | None = None
                if isinstance(delivery_receipt, dict) and isinstance(delivery_receipt.get("id"), str):
                    delivery_receipt_id = UUID(delivery_receipt["id"])

                status_value: str = "ok"
                if isinstance(payload.get("job"), dict):
                    job_status = str(payload["job"].get("status", "ok"))
                    if job_status in {"failed"}:
                        status_value = "failed"
                    elif job_status.startswith("suppressed"):
                        status_value = "suppressed"
                    elif job_status in {"simulated", "delivered"}:
                        status_value = job_status
                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="scheduler_open_loop_prompt",
                    event_kind="result",
                    status=status_value,  # type: ignore[arg-type]
                    route_path=f"/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver",
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    delivery_receipt_id=delivery_receipt_id,
                    evidence={
                        "idempotent_replay": bool(payload.get("idempotent_replay")),
                        "prompt_id": prompt_id,
                        "force": body.force,
                    },
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramOpenLoopPromptNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    status_code = 200 if bool(payload.get("idempotent_replay")) else 201
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/scheduler/jobs")
def list_v1_telegram_scheduler_jobs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                payload = list_workspace_scheduler_jobs(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    limit=limit,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except TelegramIdentityNotFoundError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TelegramNotificationPreferenceValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/messages/{message_id}/handle")
def handle_v1_telegram_message(
    message_id: UUID,
    request: Request,
    body: TelegramMessageHandleRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                rollout_resolution = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_chat_handle_enabled",
                )
                if not rollout_resolution["enabled"]:
                    record_chat_telemetry(
                        conn,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="chat_handle",
                        event_kind="rollout_block",
                        status="blocked_rollout",
                        route_path="/v1/channels/telegram/messages/{message_id}/handle",
                        channel_message_id=message_id,
                        rollout_flag_key=rollout_resolution["flag_key"],
                        rollout_flag_state="blocked",
                        evidence={"intent_hint": body.intent_hint},
                    )
                    return _hosted_rollout_block_error(flag_key=rollout_resolution["flag_key"])

                rate_limit_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_rate_limits_enabled",
                )
                abuse_rollout = resolve_rollout_flag(
                    conn,
                    user_account_id=user_account_id,
                    flag_key="hosted_abuse_controls_enabled",
                )
                if rate_limit_rollout["enabled"]:
                    decision = evaluate_hosted_flow_limits(
                        conn,
                        settings=settings,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        flow_kind="chat_handle",
                    )
                    if decision["code"] == "hosted_abuse_limit_exceeded" and not abuse_rollout["enabled"]:
                        decision = {
                            **decision,
                            "allowed": True,
                            "code": None,
                            "message": "abuse controls disabled by rollout",
                            "retry_after_seconds": 0,
                            "abuse_signal": None,
                        }

                    if not decision["allowed"]:
                        blocked_status = "abuse_blocked" if decision["code"] == "hosted_abuse_limit_exceeded" else "rate_limited"
                        blocked_event = "abuse_block" if blocked_status == "abuse_blocked" else "rate_limited"
                        record_chat_telemetry(
                            conn,
                            user_account_id=user_account_id,
                            workspace_id=workspace["id"],
                            flow_kind="chat_handle",
                            event_kind=blocked_event,  # type: ignore[arg-type]
                            status=blocked_status,  # type: ignore[arg-type]
                            route_path="/v1/channels/telegram/messages/{message_id}/handle",
                            channel_message_id=message_id,
                            rollout_flag_key=rate_limit_rollout["flag_key"],
                            rollout_flag_state="enabled",
                            rate_limit_key=decision["rate_limit_key"],
                            rate_limit_window_seconds=decision["window_seconds"],
                            rate_limit_max_requests=decision["max_requests"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            abuse_signal=decision["abuse_signal"],
                            evidence={"intent_hint": body.intent_hint},
                        )
                        return _hosted_rate_limit_error(
                            detail_code=decision["code"] or "hosted_rate_limit_exceeded",
                            message=decision["message"],
                            retry_after_seconds=decision["retry_after_seconds"],
                            rate_limit_key=decision["rate_limit_key"],
                            window_seconds=decision["window_seconds"],
                            max_requests=decision["max_requests"],
                            observed_requests=decision["observed_requests"],
                            abuse_signal=decision["abuse_signal"],
                        )

                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="chat_handle",
                    event_kind="attempt",
                    status="ok",
                    route_path="/v1/channels/telegram/messages/{message_id}/handle",
                    channel_message_id=message_id,
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    evidence={"intent_hint": body.intent_hint},
                )

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = handle_telegram_message(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    message_id=message_id,
                    bot_token=settings.telegram_bot_token,
                    intent_hint=body.intent_hint,
                )
                intent_status = str(payload["intent"].get("status", "handled"))
                telemetry_status = "ok" if intent_status == "handled" else "failed"
                delivery_receipt = payload.get("delivery_receipt")
                delivery_receipt_id: UUID | None = None
                if isinstance(delivery_receipt, dict) and isinstance(delivery_receipt.get("id"), str):
                    delivery_receipt_id = UUID(delivery_receipt["id"])
                record_chat_telemetry(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    flow_kind="chat_handle",
                    event_kind="result",
                    status=telemetry_status,  # type: ignore[arg-type]
                    route_path="/v1/channels/telegram/messages/{message_id}/handle",
                    channel_message_id=message_id,
                    delivery_receipt_id=delivery_receipt_id,
                    rollout_flag_key=rollout_resolution["flag_key"],
                    rollout_flag_state="enabled",
                    evidence={
                        "intent_status": intent_status,
                        "intent_kind": payload["intent"].get("intent_kind"),
                    },
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramMessageNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramRoutingError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/messages/{message_id}/result")
def get_v1_telegram_message_result(
    message_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = get_telegram_message_result(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    message_id=message_id,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TelegramMessageResultNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/recall")
def list_v1_telegram_recall(
    request: Request,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_RECALL_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = query_continuity_recall(
                    ContinuityStore(conn),
                    user_id=user_account_id,
                    request=ContinuityRecallQueryInput(
                        query=query_text,
                        thread_id=thread_id,
                        task_id=task_id,
                        project=project,
                        person=person,
                        since=since,
                        until=until,
                        limit=limit,
                    ),
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace_id": str(workspace["id"]),
                "recall": payload,
            }
        ),
    )


@app.get("/v1/channels/telegram/resume")
def get_v1_telegram_resumption_brief(
    request: Request,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    max_recent_changes: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    ),
    max_open_loops: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = compile_continuity_resumption_brief(
                    ContinuityStore(conn),
                    user_id=user_account_id,
                    request=ContinuityResumptionBriefRequestInput(
                        query=query_text,
                        thread_id=thread_id,
                        task_id=task_id,
                        project=project,
                        person=person,
                        since=since,
                        until=until,
                        max_recent_changes=max_recent_changes,
                        max_open_loops=max_open_loops,
                    ),
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityResumptionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace_id": str(workspace["id"]),
                "resume": payload,
            }
        ),
    )


@app.get("/v1/channels/telegram/open-loops")
def get_v1_telegram_open_loops(
    request: Request,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = compile_continuity_open_loop_dashboard(
                    ContinuityStore(conn),
                    user_id=user_account_id,
                    request=ContinuityOpenLoopDashboardQueryInput(
                        query=query_text,
                        thread_id=thread_id,
                        task_id=task_id,
                        project=project,
                        person=person,
                        since=since,
                        until=until,
                        limit=limit,
                    ),
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace_id": str(workspace["id"]),
                "open_loops": payload,
            }
        ),
    )


@app.post("/v1/channels/telegram/open-loops/{open_loop_id}/review-action")
def review_action_v1_telegram_open_loop(
    open_loop_id: UUID,
    request: Request,
    body: TelegramOpenLoopReviewActionBody,
) -> JSONResponse:
    settings = get_settings()

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = apply_telegram_open_loop_review_with_log(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    continuity_object_id=open_loop_id,
                    action=body.action,
                    note=body.note,
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityOpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/channels/telegram/approvals")
def list_v1_telegram_approvals(
    request: Request,
    status: str = Query(default="pending", min_length=1, max_length=20),
) -> JSONResponse:
    settings = get_settings()
    status_filter = status.casefold().strip()
    if status_filter not in {"pending", "all"}:
        return JSONResponse(status_code=400, content={"detail": "status must be one of: pending, all"})

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})

                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                payload = list_telegram_approvals(
                    conn,
                    user_account_id=user_account_id,
                    workspace_id=workspace["id"],
                    status_filter=status_filter,  # type: ignore[arg-type]
                )
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/approvals/{approval_id}/approve")
def approve_v1_telegram_approval(
    approval_id: UUID,
    request: Request,
    body: TelegramApprovalResolveBody | None = None,
) -> JSONResponse:
    del body
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                try:
                    payload = approve_telegram_approval(
                        conn,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        approval_id=approval_id,
                    )
                except (
                    ApprovalResolutionConflictError,
                    TaskStepApprovalLinkageError,
                    TaskStepLifecycleBoundaryError,
                ) as exc:
                    resolution_error = exc
                    payload = None
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/channels/telegram/approvals/{approval_id}/reject")
def reject_v1_telegram_approval(
    approval_id: UUID,
    request: Request,
    body: TelegramApprovalResolveBody | None = None,
) -> JSONResponse:
    del body
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        session_token = _extract_bearer_token(request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                resolution = resolve_auth_session(conn, session_token=session_token)
                user_account_id = resolution["user_account"]["id"]
                workspace = _resolve_workspace_for_hosted_channel_request(
                    conn,
                    user_account_id=user_account_id,
                    session_id=resolution["session"]["id"],
                    preferred_workspace_id=resolution["session"]["workspace_id"],
                    requested_workspace_id=None,
                )
                if workspace is None:
                    return JSONResponse(status_code=404, content={"detail": "no workspace is currently selected"})
                prepare_telegram_continuity_context(conn, user_account_id=user_account_id)
                try:
                    payload = reject_telegram_approval(
                        conn,
                        user_account_id=user_account_id,
                        workspace_id=workspace["id"],
                        approval_id=approval_id,
                    )
                except (
                    ApprovalResolutionConflictError,
                    TaskStepApprovalLinkageError,
                    TaskStepLifecycleBoundaryError,
                ) as exc:
                    resolution_error = exc
                    payload = None
    except (AuthSessionInvalidError, AuthSessionExpiredError, AuthSessionRevokedDeviceError) as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
    except HostedUserAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))
