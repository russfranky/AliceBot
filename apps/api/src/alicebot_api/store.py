from __future__ import annotations

import json
from datetime import datetime
from typing import Any, TypedDict, TypeVar, cast
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
RowT = TypeVar("RowT")


class UserRow(TypedDict):
    id: UUID
    email: str
    display_name: str | None
    created_at: datetime


class ThreadRow(TypedDict):
    id: UUID
    user_id: UUID
    title: str
    agent_profile_id: str
    created_at: datetime
    updated_at: datetime


class AgentProfileRow(TypedDict):
    id: str
    name: str
    description: str
    model_provider: str | None
    model_name: str | None


class SessionRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class EventRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    session_id: UUID | None
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime


class TraceEventRow(TypedDict):
    id: UUID
    user_id: UUID
    trace_id: UUID
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceReviewRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime
    trace_event_count: int


class MemoryRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    memory_type: str
    confidence: float | None
    salience: float | None
    confirmation_status: str
    trust_class: str
    promotion_eligibility: str
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    trust_reason: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    last_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MemoryRevisionRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    sequence_no: int
    action: str
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    candidate: JsonObject
    created_at: datetime


class FactPatternRow(TypedDict):
    id: UUID
    user_id: UUID
    pattern_key: str
    title: str
    memory_type: str
    namespace_key: str
    fact_count: int
    source_fact_ids: list[str]
    evidence_chain: JsonValue
    explanation: str
    created_at: datetime
    updated_at: datetime


class FactPlaybookRow(TypedDict):
    id: UUID
    user_id: UUID
    playbook_key: str
    pattern_id: UUID
    pattern_key: str
    title: str
    memory_type: str
    source_fact_ids: list[str]
    source_pattern_ids: list[str]
    steps: JsonValue
    explanation: str
    created_at: datetime
    updated_at: datetime


class MemoryReviewLabelRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    label: str
    note: str | None
    created_at: datetime


class OpenLoopRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID | None
    title: str
    status: str
    opened_at: datetime
    due_at: datetime | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class ContinuityCaptureEventRow(TypedDict):
    id: UUID
    user_id: UUID
    raw_content: str
    explicit_signal: str | None
    admission_posture: str
    admission_reason: str
    created_at: datetime


class ContinuityObjectRow(TypedDict):
    id: UUID
    user_id: UUID
    capture_event_id: UUID
    object_type: str
    status: str
    is_preserved: bool
    is_searchable: bool
    is_promotable: bool
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: datetime | None
    supersedes_object_id: UUID | None
    superseded_by_object_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ContinuityCorrectionEventRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    action: str
    reason: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    payload: JsonObject
    created_at: datetime


class ContradictionCaseRow(TypedDict):
    id: UUID
    user_id: UUID
    canonical_key: str
    continuity_object_id: UUID
    counterpart_object_id: UUID
    kind: str
    status: str
    rationale: str
    detection_payload: JsonObject
    resolution_action: str | None
    resolution_note: str | None
    continuity_object_updated_at: datetime
    counterpart_object_updated_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TrustSignalRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    signal_key: str
    signal_type: str
    signal_state: str
    direction: str
    magnitude: float
    reason: str
    contradiction_case_id: UUID | None
    related_continuity_object_id: UUID | None
    payload: JsonObject
    created_at: datetime
    updated_at: datetime


class MemoryOperationCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    sync_fingerprint: str
    source_kind: str
    source_candidate_id: str
    source_candidate_type: str
    candidate_payload: JsonObject
    source_scope: JsonObject
    operation_type: str
    operation_reason: str
    policy_action: str
    policy_reason: str
    target_continuity_object_id: UUID | None
    target_snapshot: JsonObject
    applied_operation_id: UUID | None
    created_at: datetime
    applied_at: datetime | None


class MemoryOperationRow(TypedDict):
    id: UUID
    user_id: UUID
    candidate_id: UUID
    operation_type: str
    status: str
    sync_fingerprint: str
    target_continuity_object_id: UUID | None
    resulting_continuity_object_id: UUID | None
    correction_event_id: UUID | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    details: JsonObject
    created_at: datetime


class ContinuityRecallCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    capture_event_id: UUID
    object_type: str
    status: str
    is_preserved: bool
    is_searchable: bool
    is_promotable: bool
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: datetime | None
    supersedes_object_id: UUID | None
    superseded_by_object_id: UUID | None
    object_created_at: datetime
    object_updated_at: datetime
    admission_posture: str
    admission_reason: str
    explicit_signal: str | None
    capture_created_at: datetime


class ContinuityArtifactRow(TypedDict):
    id: UUID
    user_id: UUID
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    created_at: datetime


class ContinuityArtifactCopyRow(TypedDict):
    id: UUID
    user_id: UUID
    artifact_id: UUID
    checksum_sha256: str
    content_text: str
    content_length_bytes: int
    content_encoding: str
    created_at: datetime


class ContinuityArtifactSegmentRow(TypedDict):
    id: UUID
    user_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    source_item_id: str
    sequence_no: int
    segment_kind: str
    locator: JsonObject
    raw_content: str
    checksum_sha256: str
    created_at: datetime


class ContinuityObjectEvidenceLinkRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    artifact_segment_id: UUID | None
    relationship: str
    created_at: datetime


class ContinuityObjectEvidenceRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    artifact_segment_id: UUID | None
    relationship: str
    created_at: datetime
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    artifact_created_at: datetime
    artifact_copy_checksum_sha256: str
    artifact_copy_content_text: str
    artifact_copy_content_length_bytes: int
    artifact_copy_content_encoding: str
    artifact_copy_created_at: datetime
    segment_source_item_id: str | None
    segment_sequence_no: int | None
    segment_kind: str | None
    segment_locator: JsonObject | None
    segment_raw_content: str | None
    segment_checksum_sha256: str | None
    segment_created_at: datetime | None


class EmbeddingConfigRow(TypedDict):
    id: UUID
    user_id: UUID
    provider: str
    model: str
    version: str
    dimensions: int
    status: str
    metadata: JsonObject
    created_at: datetime


class ModelProviderRow(TypedDict):
    id: UUID
    workspace_id: UUID
    created_by_user_account_id: UUID
    provider_key: str
    model_provider: str
    display_name: str
    base_url: str
    api_key: str
    auth_mode: str
    default_model: str
    status: str
    model_list_path: str
    healthcheck_path: str
    invoke_path: str
    azure_api_version: str
    azure_auth_secret_ref: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class ProviderCapabilityRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID
    discovered_by_user_account_id: UUID
    adapter_key: str
    discovery_status: str
    capability_snapshot: JsonObject
    discovery_error: str | None
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class ProviderInvocationTelemetryRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID
    thread_id: UUID | None
    invoked_by_user_account_id: UUID
    invocation_kind: str
    adapter_key: str
    runtime_provider: str
    requested_model: str
    response_model: str | None
    response_id: str | None
    status: str
    latency_ms: int
    usage: JsonObject
    error_detail: str | None
    created_at: datetime


class ModelPackRow(TypedDict):
    id: UUID
    workspace_id: UUID
    created_by_user_account_id: UUID
    pack_id: str
    pack_version: str
    display_name: str
    family: str
    description: str
    status: str
    briefing_strategy: str
    briefing_max_tokens: int | None
    contract: JsonObject
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class WorkspaceModelPackBindingRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID | None
    model_pack_id: UUID
    bound_by_user_account_id: UUID
    binding_source: str
    metadata: JsonObject
    created_at: datetime


class WorkspaceModelPackBindingDetailRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID | None
    model_pack_id: UUID
    bound_by_user_account_id: UUID
    binding_source: str
    metadata: JsonObject
    created_at: datetime
    pack_id: str
    pack_version: str
    pack_display_name: str
    pack_family: str
    pack_description: str
    pack_status: str
    pack_briefing_strategy: str
    pack_briefing_max_tokens: int | None
    pack_contract: JsonObject
    pack_metadata: JsonObject
    pack_created_by_user_account_id: UUID
    pack_created_at: datetime
    pack_updated_at: datetime


class MemoryEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class SemanticMemoryRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    memory_type: str
    confidence: float | None
    salience: float | None
    confirmation_status: str
    trust_class: str
    promotion_eligibility: str
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    trust_reason: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    last_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    score: float


class EntityRow(TypedDict):
    id: UUID
    user_id: UUID
    entity_type: str
    name: str
    source_memory_ids: list[str]
    created_at: datetime


class EntityEdgeRow(TypedDict):
    id: UUID
    user_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    source_memory_ids: list[str]
    created_at: datetime


class RetrievalRunRow(TypedDict):
    id: UUID
    user_id: UUID
    source_surface: str
    ranking_strategy: str
    query_text: str | None
    request_scope: JsonObject
    result_ids: list[str]
    exclusion_summary: JsonObject
    candidate_count: int
    selected_count: int
    debug_enabled: bool
    retention_until: datetime
    created_at: datetime


class TaskBriefRow(TypedDict):
    id: UUID
    user_id: UUID
    mode: str
    query_text: str | None
    scope: JsonObject
    provider_strategy: str
    model_pack_strategy: str
    token_budget: int
    estimated_tokens: int
    item_count: int
    deterministic_key: str
    payload: JsonObject
    created_at: datetime


class EvalSuiteRow(TypedDict):
    id: UUID
    user_id: UUID
    suite_key: str
    title: str
    description: str
    evaluator_kind: str
    fixture_schema_version: str
    fixture_source_path: str
    case_count: int
    suite_order: int
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class EvalCaseRow(TypedDict):
    id: UUID
    user_id: UUID
    suite_id: UUID
    case_key: str
    title: str
    evaluator_kind: str
    case_order: int
    fixture: JsonObject
    expectations: JsonObject
    created_at: datetime
    updated_at: datetime


class EvalRunRow(TypedDict):
    id: UUID
    user_id: UUID
    fixture_schema_version: str
    fixture_source_path: str
    requested_suite_keys: list[str]
    status: str
    summary: JsonObject
    report: JsonObject
    report_digest: str
    created_at: datetime


class EvalResultRow(TypedDict):
    id: UUID
    user_id: UUID
    eval_run_id: UUID
    suite_key: str
    case_key: str
    status: str
    score: float
    summary: JsonObject
    details: JsonObject
    created_at: datetime


class RetrievalCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    retrieval_run_id: UUID
    continuity_object_id: UUID
    rank: int | None
    selected: bool
    exclusion_reason: str | None
    lexical_score: float
    semantic_score: float
    entity_edge_score: float
    temporal_score: float
    trust_score: float
    relevance: float
    scope_matches: list[JsonObject]
    stage_details: JsonObject
    ordering: JsonObject
    title: str
    object_type: str
    status: str
    created_at: datetime


class ConsentRow(TypedDict):
    id: UUID
    user_id: UUID
    consent_key: str
    status: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class PolicyRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str | None
    name: str
    action: str
    scope: str
    effect: str
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: list[str]
    created_at: datetime
    updated_at: datetime


class ToolRow(TypedDict):
    id: UUID
    user_id: UUID
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: str
    active: bool
    tags: list[str]
    action_hints: list[str]
    scope_hints: list[str]
    domain_hints: list[str]
    risk_hints: list[str]
    metadata: JsonObject
    created_at: datetime


class ApprovalRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    task_run_id: UUID | None
    task_step_id: UUID | None
    status: str
    request: JsonObject
    tool: JsonObject
    routing: JsonObject
    routing_trace_id: UUID
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None


class TaskRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    status: str
    request: JsonObject
    tool: JsonObject
    latest_approval_id: UUID | None
    latest_execution_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TaskWorkspaceRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    status: str
    local_path: str
    created_at: datetime
    updated_at: datetime


class GmailAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class CalendarAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class ProtectedGmailCredentialRow(TypedDict):
    gmail_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class ProtectedCalendarCredentialRow(TypedDict):
    calendar_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class ChannelIdentityRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID
    channel_type: str
    external_user_id: str
    external_chat_id: str
    external_username: str | None
    status: str
    linked_at: datetime
    unlinked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChannelLinkChallengeRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID
    channel_type: str
    challenge_token_hash: str
    link_code: str
    status: str
    expires_at: datetime
    confirmed_at: datetime | None
    channel_identity_id: UUID | None
    created_at: datetime


class ChannelThreadRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    external_thread_key: str
    channel_identity_id: UUID | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChannelMessageRow(TypedDict):
    id: UUID
    workspace_id: UUID | None
    channel_thread_id: UUID | None
    channel_identity_id: UUID | None
    channel_type: str
    direction: str
    provider_update_id: str | None
    provider_message_id: str | None
    external_chat_id: str | None
    external_user_id: str | None
    message_text: str | None
    normalized_payload: JsonObject
    route_status: str
    idempotency_key: str
    created_at: datetime
    received_at: datetime


class ChatIntentRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_message_id: UUID
    channel_thread_id: UUID | None
    intent_kind: str
    status: str
    intent_payload: JsonObject
    result_payload: JsonObject
    handled_at: datetime | None
    created_at: datetime


class ChannelDeliveryReceiptRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_message_id: UUID
    channel_type: str
    status: str
    provider_receipt_id: str | None
    failure_code: str | None
    failure_detail: str | None
    scheduled_job_id: UUID | None
    scheduler_job_kind: str | None
    scheduled_for: datetime | None
    schedule_slot: str | None
    notification_policy: JsonObject
    rollout_flag_state: str
    support_evidence: JsonObject
    rate_limit_evidence: JsonObject
    incident_evidence: JsonObject
    recorded_at: datetime
    created_at: datetime


class ApprovalChallengeRow(TypedDict):
    id: UUID
    workspace_id: UUID
    approval_id: UUID
    channel_message_id: UUID | None
    status: str
    challenge_prompt: str
    challenge_payload: JsonObject
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OpenLoopReviewRow(TypedDict):
    id: UUID
    workspace_id: UUID
    continuity_object_id: UUID
    channel_message_id: UUID | None
    correction_event_id: UUID | None
    review_action: str
    note: str | None
    created_at: datetime


class NotificationSubscriptionRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    notifications_enabled: bool
    daily_brief_enabled: bool
    daily_brief_window_start: str
    open_loop_prompts_enabled: bool
    waiting_for_prompts_enabled: bool
    stale_prompts_enabled: bool
    timezone: str
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    created_at: datetime
    updated_at: datetime


class ContinuityBriefRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    brief_kind: str
    assembly_version: str
    summary: JsonObject
    brief_payload: JsonObject
    message_text: str
    compiled_at: datetime
    created_at: datetime


class DailyBriefJobRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    job_kind: str
    prompt_kind: str | None
    prompt_id: str | None
    continuity_object_id: UUID | None
    continuity_brief_id: UUID | None
    schedule_slot: str
    idempotency_key: str
    due_at: datetime
    status: str
    suppression_reason: str | None
    attempt_count: int
    delivery_receipt_id: UUID | None
    payload: JsonObject
    result_payload: JsonObject
    rollout_flag_state: str
    support_evidence: JsonObject
    rate_limit_evidence: JsonObject
    incident_evidence: JsonObject
    attempted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChatTelemetryRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID | None
    channel_message_id: UUID | None
    daily_brief_job_id: UUID | None
    delivery_receipt_id: UUID | None
    flow_kind: str
    event_kind: str
    status: str
    route_path: str
    rollout_flag_key: str | None
    rollout_flag_state: str | None
    rate_limit_key: str | None
    rate_limit_window_seconds: int | None
    rate_limit_max_requests: int | None
    retry_after_seconds: int | None
    abuse_signal: str | None
    evidence: JsonObject
    created_at: datetime


class TaskArtifactRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_workspace_id: UUID
    status: str
    ingestion_status: str
    relative_path: str
    media_type_hint: str | None
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    task_artifact_chunk_id: UUID
    task_artifact_chunk_sequence_no: int
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkSemanticRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_artifact_id: UUID
    relative_path: str
    media_type_hint: str | None
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime
    embedding_config_id: UUID
    score: float


class TaskStepRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    sequence_no: int
    parent_step_id: UUID | None
    source_approval_id: UUID | None
    source_execution_id: UUID | None
    kind: str
    status: str
    request: JsonObject
    outcome: JsonObject
    trace_id: UUID
    trace_kind: str
    created_at: datetime
    updated_at: datetime


class TaskRunRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    status: str
    checkpoint: JsonObject
    tick_count: int
    step_count: int
    max_ticks: int
    retry_count: int
    retry_cap: int
    retry_posture: str
    failure_class: str | None
    stop_reason: str | None
    last_transitioned_at: datetime
    created_at: datetime
    updated_at: datetime


class ToolExecutionRow(TypedDict):
    id: UUID
    user_id: UUID
    approval_id: UUID
    task_run_id: UUID | None
    task_step_id: UUID
    thread_id: UUID
    tool_id: UUID
    trace_id: UUID
    request_event_id: UUID | None
    result_event_id: UUID | None
    status: str
    handler_key: str | None
    idempotency_key: str | None
    request: JsonObject
    tool: JsonObject
    result: JsonObject
    executed_at: datetime


class ExecutionBudgetRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str | None
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    status: str
    deactivated_at: datetime | None
    superseded_by_budget_id: UUID | None
    supersedes_budget_id: UUID | None
    created_at: datetime


class CountRow(TypedDict):
    count: int


class LabelCountRow(TypedDict):
    label: str
    count: int


INSERT_USER_SQL = """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, %s, %s)
                RETURNING id, email, display_name, created_at
                """

GET_USER_SQL = """
                SELECT id, email, display_name, created_at
                FROM users
                WHERE id = %s
                """

INSERT_THREAD_SQL = """
                INSERT INTO threads (user_id, title, agent_profile_id)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, title, agent_profile_id, created_at, updated_at
                """

GET_THREAD_SQL = """
                SELECT id, user_id, title, agent_profile_id, created_at, updated_at
                FROM threads
                WHERE id = %s
                """

LIST_THREADS_SQL = """
                SELECT id, user_id, title, agent_profile_id, created_at, updated_at
                FROM threads
                ORDER BY created_at DESC, id DESC
                """

LIST_AGENT_PROFILES_SQL = """
                SELECT id, name, description, model_provider, model_name
                FROM agent_profiles
                ORDER BY id ASC
                """

GET_AGENT_PROFILE_SQL = """
                SELECT id, name, description, model_provider, model_name
                FROM agent_profiles
                WHERE id = %s
                """

INSERT_SESSION_SQL = """
                INSERT INTO sessions (user_id, thread_id, status)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, thread_id, status, started_at, ended_at, created_at
                """

LIST_THREAD_SESSIONS_SQL = """
                SELECT id, user_id, thread_id, status, started_at, ended_at, created_at
                FROM sessions
                WHERE thread_id = %s
                ORDER BY started_at ASC, created_at ASC, id ASC
                """

LOCK_THREAD_EVENTS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))"
LOCK_TASK_STEPS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 2))"
LOCK_TASK_WORKSPACES_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 3))"
LOCK_TASK_ARTIFACTS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 4))"
LOCK_TASK_RUNS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 5))"

INSERT_EVENT_SQL = """
                WITH next_sequence AS (
                  SELECT COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no
                  FROM events
                  WHERE thread_id = %s
                    AND user_id = app.current_user_id()
                )
                INSERT INTO events (user_id, thread_id, session_id, sequence_no, kind, payload)
                SELECT app.current_user_id(), %s, %s, next_sequence.sequence_no, %s, %s
                FROM next_sequence
                RETURNING id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                """

LIST_THREAD_EVENTS_SQL = """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE thread_id = %s
                ORDER BY sequence_no ASC
                """

LIST_EVENTS_BY_IDS_SQL = """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE id = ANY(%s)
                ORDER BY sequence_no ASC
                """

INSERT_TRACE_SQL = """
                INSERT INTO traces (user_id, thread_id, kind, compiler_version, status, limits)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, thread_id, kind, compiler_version, status, limits, created_at
                """

GET_TRACE_SQL = """
                SELECT id, user_id, thread_id, kind, compiler_version, status, limits, created_at
                FROM traces
                WHERE id = %s
                """

LIST_TRACE_REVIEWS_SQL = """
                SELECT
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at,
                  COUNT(trace_events.id) AS trace_event_count
                FROM traces
                LEFT JOIN trace_events
                  ON trace_events.trace_id = traces.id
                 AND trace_events.user_id = traces.user_id
                GROUP BY
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at
                ORDER BY traces.created_at DESC, traces.id DESC
                """

GET_TRACE_REVIEW_SQL = """
                SELECT
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at,
                  COUNT(trace_events.id) AS trace_event_count
                FROM traces
                LEFT JOIN trace_events
                  ON trace_events.trace_id = traces.id
                 AND trace_events.user_id = traces.user_id
                WHERE traces.id = %s
                GROUP BY
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at
                """

INSERT_TRACE_EVENT_SQL = """
                INSERT INTO trace_events (user_id, trace_id, sequence_no, kind, payload)
                VALUES (app.current_user_id(), %s, %s, %s, %s)
                RETURNING id, user_id, trace_id, sequence_no, kind, payload, created_at
                """

LIST_TRACE_EVENTS_SQL = """
                SELECT id, user_id, trace_id, sequence_no, kind, payload, created_at
                FROM trace_events
                WHERE trace_id = %s
                ORDER BY sequence_no ASC, id ASC
                """

INSERT_MEMORY_SQL = """
                INSERT INTO memories (
                  user_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  agent_profile_id,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                """

GET_MEMORY_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = %s
                """

LIST_MEMORIES_BY_IDS_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

GET_MEMORY_BY_KEY_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE memory_key = %s
                """

GET_MEMORY_BY_KEY_AND_PROFILE_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE memory_key = %s
                  AND agent_profile_id = %s
                """

LIST_MEMORIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY created_at ASC, id ASC
                """

COUNT_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                """

COUNT_MEMORIES_BY_STATUS_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = %s
                """

COUNT_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                """

LIST_REVIEW_MEMORIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_REVIEW_MEMORIES_BY_STATUS_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = %s
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """

LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_CONTEXT_MEMORIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """

LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE agent_profile_id = %s
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """

UPDATE_MEMORY_SQL = """
                UPDATE memories
                SET value = %s,
                    status = %s,
                    source_event_ids = %s,
                    memory_type = %s,
                    confidence = %s,
                    salience = %s,
                    confirmation_status = %s,
                    trust_class = %s,
                    promotion_eligibility = %s,
                    evidence_count = %s,
                    independent_source_count = %s,
                    extracted_by_model = %s,
                    trust_reason = %s,
                    valid_from = %s,
                    valid_to = %s,
                    last_confirmed_at = %s,
                    updated_at = clock_timestamp(),
                    deleted_at = CASE
                      WHEN %s = 'deleted' THEN clock_timestamp()
                      ELSE NULL
                    END
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                """

LOCK_MEMORY_REVISIONS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 1))"

INSERT_MEMORY_REVISION_SQL = """
                WITH next_sequence AS (
                  SELECT COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no
                  FROM memory_revisions
                  WHERE memory_id = %s
                    AND user_id = app.current_user_id()
                )
                INSERT INTO memory_revisions (
                  user_id,
                  memory_id,
                  sequence_no,
                  revision_number,
                  revision_type,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate,
                  text_before,
                  text_after
                )
                SELECT
                  app.current_user_id(),
                  %s,
                  next_sequence.sequence_no,
                  next_sequence.sequence_no,
                  CASE %s
                    WHEN 'ADD' THEN 'created'
                    WHEN 'UPDATE' THEN 'edited'
                    WHEN 'DELETE' THEN 'archived'
                    ELSE 'edited'
                  END,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                FROM next_sequence
                RETURNING id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                """

LIST_MEMORY_REVISIONS_SQL = """
                SELECT id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                FROM memory_revisions
                WHERE memory_id = %s
                ORDER BY sequence_no ASC
                """

COUNT_MEMORY_REVISIONS_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_revisions
                WHERE memory_id = %s
                """

LIST_LIMITED_MEMORY_REVISIONS_SQL = """
                SELECT id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                FROM memory_revisions
                WHERE memory_id = %s
                ORDER BY sequence_no ASC
                LIMIT %s
                """

UPSERT_FACT_PATTERN_SQL = """
                INSERT INTO fact_patterns (
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT (user_id, pattern_key)
                DO UPDATE SET
                  id = EXCLUDED.id,
                  title = EXCLUDED.title,
                  memory_type = EXCLUDED.memory_type,
                  namespace_key = EXCLUDED.namespace_key,
                  fact_count = EXCLUDED.fact_count,
                  source_fact_ids = EXCLUDED.source_fact_ids,
                  evidence_chain = EXCLUDED.evidence_chain,
                  explanation = EXCLUDED.explanation,
                  updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                """

LIST_FACT_PATTERNS_SQL = """
                SELECT
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_patterns
                ORDER BY memory_type ASC, namespace_key ASC, title ASC, id ASC
                LIMIT %s
                """

COUNT_FACT_PATTERNS_SQL = """
                SELECT COUNT(*) AS count
                FROM fact_patterns
                """

GET_FACT_PATTERN_SQL = """
                SELECT
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_patterns
                WHERE id = %s
                """

DELETE_FACT_PATTERNS_NOT_IN_SQL = """
                DELETE FROM fact_patterns
                WHERE user_id = app.current_user_id()
                  AND NOT (id = ANY(%s))
                """

DELETE_ALL_FACT_PATTERNS_SQL = """
                DELETE FROM fact_patterns
                WHERE user_id = app.current_user_id()
                """

UPSERT_FACT_PLAYBOOK_SQL = """
                INSERT INTO fact_playbooks (
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT (user_id, playbook_key)
                DO UPDATE SET
                  id = EXCLUDED.id,
                  pattern_id = EXCLUDED.pattern_id,
                  pattern_key = EXCLUDED.pattern_key,
                  title = EXCLUDED.title,
                  memory_type = EXCLUDED.memory_type,
                  source_fact_ids = EXCLUDED.source_fact_ids,
                  source_pattern_ids = EXCLUDED.source_pattern_ids,
                  steps = EXCLUDED.steps,
                  explanation = EXCLUDED.explanation,
                  updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                """

LIST_FACT_PLAYBOOKS_SQL = """
                SELECT
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_playbooks
                ORDER BY memory_type ASC, pattern_key ASC, title ASC, id ASC
                LIMIT %s
                """

COUNT_FACT_PLAYBOOKS_SQL = """
                SELECT COUNT(*) AS count
                FROM fact_playbooks
                """

GET_FACT_PLAYBOOK_SQL = """
                SELECT
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_playbooks
                WHERE id = %s
                """

DELETE_FACT_PLAYBOOKS_NOT_IN_SQL = """
                DELETE FROM fact_playbooks
                WHERE user_id = app.current_user_id()
                  AND NOT (id = ANY(%s))
                """

DELETE_ALL_FACT_PLAYBOOKS_SQL = """
                DELETE FROM fact_playbooks
                WHERE user_id = app.current_user_id()
                """

INSERT_MEMORY_REVIEW_LABEL_SQL = """
                INSERT INTO memory_review_labels (user_id, memory_id, label, note)
                VALUES (app.current_user_id(), %s, %s, %s)
                RETURNING id, user_id, memory_id, label, note, created_at
                """

LIST_MEMORY_REVIEW_LABELS_SQL = """
                SELECT id, user_id, memory_id, label, note, created_at
                FROM memory_review_labels
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT label, COUNT(*) AS count
                FROM memory_review_labels
                WHERE memory_id = %s
                GROUP BY label
                ORDER BY label ASC
                """

COUNT_LABELED_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE EXISTS (
                  SELECT 1
                  FROM memory_review_labels
                  WHERE memory_review_labels.memory_id = memories.id
                )
                """

COUNT_UNLABELED_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM memory_review_labels
                  WHERE memory_review_labels.memory_id = memories.id
                )
                """

LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT label, COUNT(*) AS count
                FROM memory_review_labels
                GROUP BY label
                ORDER BY label ASC
                """

LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT memory_review_labels.label, COUNT(*) AS count
                FROM memory_review_labels
                INNER JOIN memories ON memories.id = memory_review_labels.memory_id
                WHERE memories.status = 'active'
                GROUP BY memory_review_labels.label
                ORDER BY memory_review_labels.label ASC
                """

INSERT_OPEN_LOOP_SQL = """
                INSERT INTO open_loops (
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                """

GET_OPEN_LOOP_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                WHERE id = %s
                """

LIST_OPEN_LOOPS_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                ORDER BY opened_at DESC, created_at DESC, id DESC
                """

LIST_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                WHERE status = %s
                ORDER BY opened_at DESC, created_at DESC, id DESC
                """

LIST_LIMITED_OPEN_LOOPS_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                FROM open_loops
                WHERE status = %s
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_OPEN_LOOPS_SQL = """
                SELECT COUNT(*) AS count
                FROM open_loops
                """

COUNT_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT COUNT(*) AS count
                FROM open_loops
                WHERE status = %s
                """

UPDATE_OPEN_LOOP_STATUS_SQL = """
                UPDATE open_loops
                SET status = %s,
                    resolved_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE COALESCE(%s, clock_timestamp())
                    END,
                    resolution_note = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE %s
                    END,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                """

INSERT_MODEL_PROVIDER_SQL = """
                INSERT INTO model_providers (
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  created_at,
                  updated_at
                """

GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  created_at,
                  updated_at
                FROM model_providers
                WHERE id = %s
                  AND workspace_id = %s
                """

LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  created_at,
                  updated_at
                FROM model_providers
                WHERE workspace_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_MODEL_PROVIDER_SQL = """
                UPDATE model_providers
                SET provider_key = %s,
                    model_provider = %s,
                    display_name = %s,
                    base_url = %s,
                    api_key = %s,
                    auth_mode = %s,
                    default_model = %s,
                    status = %s,
                    model_list_path = %s,
                    healthcheck_path = %s,
                    invoke_path = %s,
                    azure_api_version = %s,
                    azure_auth_secret_ref = %s,
                    metadata = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND workspace_id = %s
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  created_at,
                  updated_at
                """

UPSERT_PROVIDER_CAPABILITY_SQL = """
                INSERT INTO provider_capabilities (
                  workspace_id,
                  provider_id,
                  discovered_by_user_account_id,
                  adapter_key,
                  discovery_status,
                  capability_snapshot,
                  discovery_error,
                  discovered_at,
                  created_at,
                  updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp(), clock_timestamp())
                ON CONFLICT (provider_id) DO UPDATE
                SET workspace_id = EXCLUDED.workspace_id,
                    discovered_by_user_account_id = EXCLUDED.discovered_by_user_account_id,
                    adapter_key = EXCLUDED.adapter_key,
                    discovery_status = EXCLUDED.discovery_status,
                    capability_snapshot = EXCLUDED.capability_snapshot,
                    discovery_error = EXCLUDED.discovery_error,
                    discovered_at = EXCLUDED.discovered_at,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  workspace_id,
                  provider_id,
                  discovered_by_user_account_id,
                  adapter_key,
                  discovery_status,
                  capability_snapshot,
                  discovery_error,
                  discovered_at,
                  created_at,
                  updated_at
                """

GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL = """
                SELECT
                  id,
                  workspace_id,
                  provider_id,
                  discovered_by_user_account_id,
                  adapter_key,
                  discovery_status,
                  capability_snapshot,
                  discovery_error,
                  discovered_at,
                  created_at,
                  updated_at
                FROM provider_capabilities
                WHERE provider_id = %s
                  AND workspace_id = %s
                """

INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL = """
                INSERT INTO provider_invocation_telemetry (
                  workspace_id,
                  provider_id,
                  thread_id,
                  invoked_by_user_account_id,
                  invocation_kind,
                  adapter_key,
                  runtime_provider,
                  requested_model,
                  response_model,
                  response_id,
                  status,
                  latency_ms,
                  usage,
                  error_detail,
                  created_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  workspace_id,
                  provider_id,
                  thread_id,
                  invoked_by_user_account_id,
                  invocation_kind,
                  adapter_key,
                  runtime_provider,
                  requested_model,
                  response_model,
                  response_id,
                  status,
                  latency_ms,
                  usage,
                  error_detail,
                  created_at
                """

INSERT_MODEL_PACK_SQL = """
                INSERT INTO model_packs (
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                """

INSERT_MODEL_PACK_IF_ABSENT_SQL = """
                INSERT INTO model_packs (
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT (workspace_id, pack_id, pack_version) DO NOTHING
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                """

GET_MODEL_PACK_FOR_WORKSPACE_BY_ID_AND_VERSION_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                FROM model_packs
                WHERE workspace_id = %s
                  AND pack_id = %s
                  AND pack_version = %s
                """

GET_LATEST_MODEL_PACK_FOR_WORKSPACE_BY_ID_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                FROM model_packs
                WHERE workspace_id = %s
                  AND pack_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """

GET_MODEL_PACK_FOR_WORKSPACE_BY_ROW_ID_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                FROM model_packs
                WHERE workspace_id = %s
                  AND id = %s
                """

LIST_MODEL_PACKS_FOR_WORKSPACE_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  pack_id,
                  pack_version,
                  display_name,
                  family,
                  description,
                  status,
                  briefing_strategy,
                  briefing_max_tokens,
                  contract,
                  metadata,
                  created_at,
                  updated_at
                FROM model_packs
                WHERE workspace_id = %s
                ORDER BY pack_id ASC, created_at DESC, id DESC
                """

INSERT_WORKSPACE_MODEL_PACK_BINDING_SQL = """
                INSERT INTO workspace_model_pack_bindings (
                  workspace_id,
                  provider_id,
                  model_pack_id,
                  bound_by_user_account_id,
                  binding_source,
                  metadata,
                  created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING
                  id,
                  workspace_id,
                  provider_id,
                  model_pack_id,
                  bound_by_user_account_id,
                  binding_source,
                  metadata,
                  created_at
                """

GET_LATEST_WORKSPACE_MODEL_PACK_BINDING_SQL = """
                SELECT
                  b.id,
                  b.workspace_id,
                  b.provider_id,
                  b.model_pack_id,
                  b.bound_by_user_account_id,
                  b.binding_source,
                  b.metadata,
                  b.created_at,
                  p.pack_id,
                  p.pack_version,
                  p.display_name AS pack_display_name,
                  p.family AS pack_family,
                  p.description AS pack_description,
                  p.status AS pack_status,
                  p.briefing_strategy AS pack_briefing_strategy,
                  p.briefing_max_tokens AS pack_briefing_max_tokens,
                  p.contract AS pack_contract,
                  p.metadata AS pack_metadata,
                  p.created_by_user_account_id AS pack_created_by_user_account_id,
                  p.created_at AS pack_created_at,
                  p.updated_at AS pack_updated_at
                FROM workspace_model_pack_bindings AS b
                INNER JOIN model_packs AS p
                  ON p.id = b.model_pack_id
                WHERE b.workspace_id = %s
                  AND b.provider_id IS NULL
                ORDER BY b.created_at DESC, b.id DESC
                LIMIT 1
                """

GET_RESOLVED_WORKSPACE_MODEL_PACK_BINDING_SQL = """
                SELECT
                  b.id,
                  b.workspace_id,
                  b.provider_id,
                  b.model_pack_id,
                  b.bound_by_user_account_id,
                  b.binding_source,
                  b.metadata,
                  b.created_at,
                  p.pack_id,
                  p.pack_version,
                  p.display_name AS pack_display_name,
                  p.family AS pack_family,
                  p.description AS pack_description,
                  p.status AS pack_status,
                  p.briefing_strategy AS pack_briefing_strategy,
                  p.briefing_max_tokens AS pack_briefing_max_tokens,
                  p.contract AS pack_contract,
                  p.metadata AS pack_metadata,
                  p.created_by_user_account_id AS pack_created_by_user_account_id,
                  p.created_at AS pack_created_at,
                  p.updated_at AS pack_updated_at
                FROM workspace_model_pack_bindings AS b
                INNER JOIN model_packs AS p
                  ON p.id = b.model_pack_id
                WHERE b.workspace_id = %s
                  AND (b.provider_id = %s OR b.provider_id IS NULL)
                ORDER BY
                  CASE WHEN b.provider_id = %s THEN 0 ELSE 1 END,
                  b.created_at DESC,
                  b.id DESC
                LIMIT 1
                """

WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL = """
                SELECT 1
                FROM workspace_members
                WHERE workspace_id = %s
                  AND user_account_id = %s
                LIMIT 1
                """

INSERT_TASK_BRIEF_SQL = """
                INSERT INTO task_briefs (
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                """

GET_TASK_BRIEF_BY_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                FROM task_briefs
                WHERE id = %s
                """

INSERT_EMBEDDING_CONFIG_SQL = """
                INSERT INTO embedding_configs (
                  user_id,
                  provider,
                  model,
                  version,
                  dimensions,
                  status,
                  metadata,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, provider, model, version, dimensions, status, metadata, created_at
                """

GET_EMBEDDING_CONFIG_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE id = %s
                """

GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE provider = %s
                  AND model = %s
                  AND version = %s
                """

LIST_EMBEDDING_CONFIGS_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                ORDER BY created_at ASC, id ASC
                """

INSERT_MEMORY_EMBEDDING_SQL = """
                INSERT INTO memory_embeddings (
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

GET_MEMORY_EMBEDDING_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE id = %s
                """

GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                  AND embedding_config_id = %s
                """

LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE embedding_config_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_MEMORY_EMBEDDING_SQL = """
                UPDATE memory_embeddings
                SET dimensions = %s,
                    vector = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL = """
                SELECT
                  memories.id,
                  memories.user_id,
                  memories.agent_profile_id,
                  memories.memory_key,
                  memories.value,
                  memories.status,
                  memories.source_event_ids,
                  memories.memory_type,
                  memories.confidence,
                  memories.salience,
                  memories.confirmation_status,
                  memories.trust_class,
                  memories.promotion_eligibility,
                  memories.evidence_count,
                  memories.independent_source_count,
                  memories.extracted_by_model,
                  memories.trust_reason,
                  memories.valid_from,
                  memories.valid_to,
                  memories.last_confirmed_at,
                  memories.created_at,
                  memories.updated_at,
                  memories.deleted_at,
                  1 - (
                    replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM memory_embeddings
                JOIN memories
                  ON memories.id = memory_embeddings.memory_id
                 AND memories.user_id = memory_embeddings.user_id
                WHERE memory_embeddings.embedding_config_id = %s
                  AND memory_embeddings.dimensions = %s
                  AND memories.status = 'active'
                ORDER BY score DESC, memories.created_at ASC, memories.id ASC
                LIMIT %s
                """

RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL = """
                SELECT
                  memories.id,
                  memories.user_id,
                  memories.agent_profile_id,
                  memories.memory_key,
                  memories.value,
                  memories.status,
                  memories.source_event_ids,
                  memories.memory_type,
                  memories.confidence,
                  memories.salience,
                  memories.confirmation_status,
                  memories.trust_class,
                  memories.promotion_eligibility,
                  memories.evidence_count,
                  memories.independent_source_count,
                  memories.extracted_by_model,
                  memories.trust_reason,
                  memories.valid_from,
                  memories.valid_to,
                  memories.last_confirmed_at,
                  memories.created_at,
                  memories.updated_at,
                  memories.deleted_at,
                  1 - (
                    replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM memory_embeddings
                JOIN memories
                  ON memories.id = memory_embeddings.memory_id
                 AND memories.user_id = memory_embeddings.user_id
                WHERE memory_embeddings.embedding_config_id = %s
                  AND memory_embeddings.dimensions = %s
                  AND memories.status = 'active'
                  AND memories.agent_profile_id = %s
                ORDER BY score DESC, memories.created_at ASC, memories.id ASC
                LIMIT %s
                """

RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.task_id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

INSERT_ENTITY_SQL = """
                INSERT INTO entities (user_id, entity_type, name, source_memory_ids, created_at)
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, entity_type, name, source_memory_ids, created_at
                """

GET_ENTITY_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                WHERE id = %s
                """

LIST_ENTITIES_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                ORDER BY created_at ASC, id ASC
                """

INSERT_ENTITY_EDGE_SQL = """
                INSERT INTO entity_edges (
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                """

LIST_ENTITY_EDGES_FOR_ENTITY_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = %s OR to_entity_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_ENTITY_EDGES_FOR_ENTITIES_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = ANY(%s) OR to_entity_id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

INSERT_CONSENT_SQL = """
                INSERT INTO consents (
                  user_id,
                  consent_key,
                  status,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

GET_CONSENT_BY_KEY_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                WHERE consent_key = %s
                """

LIST_CONSENTS_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                ORDER BY consent_key ASC, created_at ASC, id ASC
                """

UPDATE_CONSENT_SQL = """
                UPDATE consents
                SET status = %s,
                    metadata = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

INSERT_POLICY_SQL = """
                INSERT INTO policies (
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                """

GET_POLICY_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE id = %s
                """

LIST_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                ORDER BY priority ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE active = TRUE
                ORDER BY priority ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE active = TRUE
                  AND (agent_profile_id IS NULL OR agent_profile_id = %s)
                ORDER BY priority ASC, created_at ASC, id ASC
                """

INSERT_TOOL_SQL = """
                INSERT INTO tools (
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                """

GET_TOOL_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE id = %s
                """

LIST_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE active = TRUE
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

INSERT_APPROVAL_SQL = """
                INSERT INTO approvals (
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

GET_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                WHERE id = %s
                """

LIST_APPROVALS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                ORDER BY created_at ASC, id ASC
                """

UPDATE_APPROVAL_RESOLUTION_SQL = """
                UPDATE approvals
                SET status = %s,
                    resolved_at = clock_timestamp(),
                    resolved_by_user_id = app.current_user_id()
                WHERE id = %s
                  AND status = 'pending'
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

UPDATE_APPROVAL_TASK_STEP_SQL = """
                UPDATE approvals
                SET task_step_id = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

UPDATE_APPROVAL_TASK_RUN_SQL = """
                UPDATE approvals
                SET task_run_id = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

INSERT_TASK_SQL = """
                INSERT INTO tasks (
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

GET_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE id = %s
                """

GET_TASK_BY_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE latest_approval_id = %s
                """

LIST_TASKS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                ORDER BY created_at ASC, id ASC
                """

UPDATE_TASK_STATUS_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_STATUS_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_approval_id = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_SQL = """
                INSERT INTO gmail_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO gmail_account_credentials (
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_GMAIL_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE id = %s
                """

GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """

UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                UPDATE gmail_account_credentials
                SET
                  auth_kind = %s,
                  credential_kind = %s,
                  secret_manager_kind = %s,
                  secret_ref = %s,
                  credential_blob = %s,
                  updated_at = clock_timestamp()
                WHERE gmail_account_id = %s
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

LIST_GMAIL_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                ORDER BY created_at ASC, id ASC
                """

INSERT_CALENDAR_ACCOUNT_SQL = """
                INSERT INTO calendar_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO calendar_account_credentials (
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_CALENDAR_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE id = %s
                """

GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM calendar_account_credentials
                WHERE calendar_account_id = %s
                """

LIST_CALENDAR_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                ORDER BY created_at ASC, id ASC
                """

INSERT_TASK_WORKSPACE_SQL = """
                INSERT INTO task_workspaces (
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                """

GET_TASK_WORKSPACE_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE id = %s
                """

GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE task_id = %s
                  AND status = 'active'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

LIST_TASK_WORKSPACES_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                ORDER BY created_at ASC, id ASC
                """

INSERT_TASK_ARTIFACT_SQL = """
                INSERT INTO task_artifacts (
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                """

GET_TASK_ARTIFACT_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE id = %s
                """

GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE task_workspace_id = %s
                  AND relative_path = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

LIST_TASK_ARTIFACTS_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                ORDER BY created_at ASC, id ASC
                """

LIST_TASK_ARTIFACTS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE task_id = %s
                ORDER BY created_at ASC, id ASC
                """

LOCK_TASK_ARTIFACT_INGESTION_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 5))"

INSERT_TASK_ARTIFACT_CHUNK_SQL = """
                INSERT INTO task_artifact_chunks (
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                """

LIST_TASK_ARTIFACT_CHUNKS_SQL = """
                SELECT
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                FROM task_artifact_chunks
                WHERE task_artifact_id = %s
                ORDER BY sequence_no ASC, id ASC
                """

GET_TASK_ARTIFACT_CHUNK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                FROM task_artifact_chunks
                WHERE id = %s
                """

INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                WITH inserted AS (
                  INSERT INTO task_artifact_chunk_embeddings (
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                  )
                  VALUES (
                    app.current_user_id(),
                    %s,
                    %s,
                    %s,
                    %s,
                    clock_timestamp(),
                    clock_timestamp()
                  )
                  RETURNING
                    id,
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                )
                SELECT
                  inserted.id,
                  inserted.user_id,
                  chunks.task_artifact_id,
                  inserted.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  inserted.embedding_config_id,
                  inserted.dimensions,
                  inserted.vector,
                  inserted.created_at,
                  inserted.updated_at
                FROM inserted
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = inserted.task_artifact_chunk_id
                 AND chunks.user_id = inserted.user_id
                """

GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.id = %s
                """

GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.task_artifact_chunk_id = %s
                  AND embeddings.embedding_config_id = %s
                """

LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.task_artifact_chunk_id = %s
                ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC
                """

LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE chunks.task_artifact_id = %s
                ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC
                """

UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                WITH updated AS (
                  UPDATE task_artifact_chunk_embeddings
                  SET dimensions = %s,
                      vector = %s,
                      updated_at = clock_timestamp()
                  WHERE id = %s
                  RETURNING
                    id,
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                )
                SELECT
                  updated.id,
                  updated.user_id,
                  chunks.task_artifact_id,
                  updated.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  updated.embedding_config_id,
                  updated.dimensions,
                  updated.vector,
                  updated.created_at,
                  updated.updated_at
                FROM updated
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = updated.task_artifact_chunk_id
                 AND chunks.user_id = updated.user_id
                """

UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL = """
                UPDATE task_artifacts
                SET ingestion_status = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                """

INSERT_TASK_STEP_SQL = """
                INSERT INTO task_steps (
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

GET_TASK_STEP_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE id = %s
                """

GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE task_id = %s
                  AND sequence_no = %s
                """

LIST_TASK_STEPS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE task_id = %s
                ORDER BY sequence_no ASC, created_at ASC, id ASC
                """

UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL = """
                UPDATE task_steps
                SET status = %s,
                    outcome = %s,
                    trace_id = %s,
                    trace_kind = %s,
                    updated_at = clock_timestamp()
                WHERE task_id = %s
                  AND sequence_no = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

UPDATE_TASK_STEP_SQL = """
                UPDATE task_steps
                SET status = %s,
                    outcome = %s,
                    trace_id = %s,
                    trace_kind = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

INSERT_TASK_RUN_SQL = """
                INSERT INTO task_runs (
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

GET_TASK_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                FROM task_runs
                WHERE id = %s
                """

LIST_TASK_RUNS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                FROM task_runs
                WHERE task_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_TASK_RUN_SQL = """
                UPDATE task_runs
                SET status = %s,
                    checkpoint = %s,
                    tick_count = %s,
                    step_count = %s,
                    retry_count = %s,
                    retry_cap = %s,
                    retry_posture = %s,
                    failure_class = %s,
                    stop_reason = %s,
                    last_transitioned_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

ACQUIRE_NEXT_TASK_RUN_SQL = """
                WITH candidate AS (
                  SELECT id
                  FROM task_runs
                  WHERE status IN ('queued', 'running')
                  ORDER BY updated_at ASC, created_at ASC, id ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE task_runs
                SET status = 'running',
                    retry_posture = 'none',
                    failure_class = NULL,
                    stop_reason = NULL,
                    last_transitioned_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = (SELECT id FROM candidate)
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

INSERT_TOOL_EXECUTION_SQL = """
                INSERT INTO tool_executions (
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                """

GET_TOOL_EXECUTION_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                WHERE id = %s
                """

LIST_TOOL_EXECUTIONS_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                ORDER BY executed_at ASC, id ASC
                """

GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                WHERE task_run_id = %s
                  AND approval_id = %s
                  AND idempotency_key = %s
                ORDER BY executed_at ASC, id ASC
                LIMIT 1
                """

INSERT_EXECUTION_BUDGET_SQL = """
                INSERT INTO execution_budgets (
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  supersedes_budget_id
                )
                VALUES (
                  COALESCE(%s, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

GET_EXECUTION_BUDGET_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                FROM execution_budgets
                WHERE id = %s
                """

LIST_EXECUTION_BUDGETS_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                FROM execution_budgets
                ORDER BY created_at ASC, id ASC
                """

DEACTIVATE_EXECUTION_BUDGET_SQL = """
                UPDATE execution_budgets
                SET status = 'inactive',
                    deactivated_at = now()
                WHERE id = %s
                  AND status = 'active'
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

SUPERSEDE_EXECUTION_BUDGET_SQL = """
                UPDATE execution_budgets
                SET status = 'superseded',
                    deactivated_at = now(),
                    superseded_by_budget_id = %s
                WHERE id = %s
                  AND status = 'active'
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

INSERT_CONTINUITY_CAPTURE_EVENT_SQL = """
                INSERT INTO continuity_capture_events (
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                """

GET_CONTINUITY_CAPTURE_EVENT_SQL = """
                SELECT
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                FROM continuity_capture_events
                WHERE id = %s
                """

LIST_CONTINUITY_CAPTURE_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                FROM continuity_capture_events
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTINUITY_CAPTURE_EVENTS_SQL = """
                SELECT COUNT(*) AS count
                FROM continuity_capture_events
                """

INSERT_CONTINUITY_OBJECT_SQL = """
                INSERT INTO continuity_objects (
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                """

GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE capture_event_id = %s
                """

GET_CONTINUITY_OBJECT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE id = %s
                """

GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE provenance ->> 'sync_fingerprint' = %s
                  AND provenance ->> 'candidate_id' = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """

LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE capture_event_id = ANY(%s)
                ORDER BY created_at DESC, id DESC
                """

LIST_CONTINUITY_REVIEW_QUEUE_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE status = ANY(%s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTINUITY_REVIEW_QUEUE_SQL = """
                SELECT COUNT(*) AS count
                FROM continuity_objects
                WHERE status = ANY(%s)
                """

LIST_CONTINUITY_RECALL_CANDIDATES_SQL = """
                SELECT
                  continuity_objects.id,
                  continuity_objects.user_id,
                  continuity_objects.capture_event_id,
                  continuity_objects.object_type,
                  continuity_objects.status,
                  continuity_objects.is_preserved,
                  continuity_objects.is_searchable,
                  continuity_objects.is_promotable,
                  continuity_objects.title,
                  continuity_objects.body,
                  continuity_objects.provenance,
                  continuity_objects.confidence,
                  continuity_objects.last_confirmed_at,
                  continuity_objects.supersedes_object_id,
                  continuity_objects.superseded_by_object_id,
                  continuity_objects.created_at AS object_created_at,
                  continuity_objects.updated_at AS object_updated_at,
                  continuity_capture_events.admission_posture,
                  continuity_capture_events.admission_reason,
                  continuity_capture_events.explicit_signal,
                  continuity_capture_events.created_at AS capture_created_at
                FROM continuity_objects
                JOIN continuity_capture_events
                  ON continuity_capture_events.id = continuity_objects.capture_event_id
                 AND continuity_capture_events.user_id = continuity_objects.user_id
                ORDER BY continuity_objects.created_at DESC, continuity_objects.id DESC
                """

INSERT_RETRIEVAL_RUN_SQL = """
                INSERT INTO retrieval_runs (
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                """

LIST_RETRIEVAL_RUNS_SQL = """
                SELECT
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                FROM retrieval_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

GET_RETRIEVAL_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                FROM retrieval_runs
                WHERE id = %s
                """

UPSERT_EVAL_SUITE_SQL = """
                INSERT INTO eval_suites (
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, suite_key)
                DO UPDATE
                SET title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    evaluator_kind = EXCLUDED.evaluator_kind,
                    fixture_schema_version = EXCLUDED.fixture_schema_version,
                    fixture_source_path = EXCLUDED.fixture_source_path,
                    case_count = EXCLUDED.case_count,
                    suite_order = EXCLUDED.suite_order,
                    metadata = EXCLUDED.metadata,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata,
                  created_at,
                  updated_at
                """

LIST_EVAL_SUITES_SQL = """
                SELECT
                  id,
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata,
                  created_at,
                  updated_at
                FROM eval_suites
                ORDER BY suite_order ASC, suite_key ASC
                """

DELETE_EVAL_SUITES_NOT_IN_SQL = """
                DELETE FROM eval_suites
                WHERE user_id = app.current_user_id()
                  AND NOT (suite_key = ANY(%s))
                """

UPSERT_EVAL_CASE_SQL = """
                INSERT INTO eval_cases (
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, suite_id, case_key)
                DO UPDATE
                SET title = EXCLUDED.title,
                    evaluator_kind = EXCLUDED.evaluator_kind,
                    case_order = EXCLUDED.case_order,
                    fixture = EXCLUDED.fixture,
                    expectations = EXCLUDED.expectations,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations,
                  created_at,
                  updated_at
                """

LIST_EVAL_CASES_FOR_SUITE_SQL = """
                SELECT
                  id,
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations,
                  created_at,
                  updated_at
                FROM eval_cases
                WHERE suite_id = %s
                ORDER BY case_order ASC, case_key ASC
                """

DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL = """
                DELETE FROM eval_cases
                WHERE user_id = app.current_user_id()
                  AND suite_id = %s
                  AND NOT (case_key = ANY(%s))
                """

INSERT_EVAL_RUN_SQL = """
                INSERT INTO eval_runs (
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                """

LIST_EVAL_RUNS_SQL = """
                SELECT
                  id,
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                FROM eval_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

GET_EVAL_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                FROM eval_runs
                WHERE id = %s
                """

INSERT_EVAL_RESULT_SQL = """
                INSERT INTO eval_results (
                  user_id,
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details,
                  created_at
                """

LIST_EVAL_RESULTS_FOR_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details,
                  created_at
                FROM eval_results
                WHERE eval_run_id = %s
                ORDER BY suite_key ASC, case_key ASC, created_at ASC, id ASC
                """

INSERT_RETRIEVAL_CANDIDATE_SQL = """
                INSERT INTO retrieval_candidates (
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status,
                  created_at
                """

LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status,
                  created_at
                FROM retrieval_candidates
                WHERE retrieval_run_id = %s
                ORDER BY selected DESC, rank ASC NULLS LAST, relevance DESC, id ASC
                """

UPSERT_CONTINUITY_ARTIFACT_SQL = """
                INSERT INTO continuity_artifacts (
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, source_kind, import_source_path, relative_path)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_SQL = """
                SELECT
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                FROM continuity_artifacts
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL = """
                SELECT
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                FROM continuity_artifacts
                WHERE source_kind = %s
                  AND import_source_path = %s
                  AND relative_path = %s
                """

UPSERT_CONTINUITY_ARTIFACT_COPY_SQL = """
                INSERT INTO continuity_artifact_copies (
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, artifact_id, checksum_sha256)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_COPY_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE artifact_id = %s
                  AND checksum_sha256 = %s
                """

LIST_CONTINUITY_ARTIFACT_COPIES_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE artifact_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL = """
                INSERT INTO continuity_artifact_segments (
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, artifact_copy_id, source_item_id)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_SEGMENT_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE artifact_copy_id = %s
                  AND source_item_id = %s
                """

LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE artifact_id = %s
                ORDER BY sequence_no ASC, created_at ASC, id ASC
                """

INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL = """
                INSERT INTO continuity_object_evidence_links (
                  user_id,
                  continuity_object_id,
                  artifact_id,
                  artifact_copy_id,
                  artifact_segment_id,
                  relationship
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  continuity_object_id,
                  artifact_id,
                  artifact_copy_id,
                  artifact_segment_id,
                  relationship,
                  created_at
                """

LIST_CONTINUITY_OBJECT_EVIDENCE_SQL = """
                SELECT
                  links.id,
                  links.user_id,
                  links.continuity_object_id,
                  links.artifact_id,
                  links.artifact_copy_id,
                  links.artifact_segment_id,
                  links.relationship,
                  links.created_at,
                  artifacts.source_kind,
                  artifacts.import_source_path,
                  artifacts.relative_path,
                  artifacts.display_name,
                  artifacts.media_type,
                  artifacts.created_at AS artifact_created_at,
                  copies.checksum_sha256 AS artifact_copy_checksum_sha256,
                  copies.content_text AS artifact_copy_content_text,
                  copies.content_length_bytes AS artifact_copy_content_length_bytes,
                  copies.content_encoding AS artifact_copy_content_encoding,
                  copies.created_at AS artifact_copy_created_at,
                  segments.source_item_id AS segment_source_item_id,
                  segments.sequence_no AS segment_sequence_no,
                  segments.segment_kind,
                  segments.locator AS segment_locator,
                  segments.raw_content AS segment_raw_content,
                  segments.checksum_sha256 AS segment_checksum_sha256,
                  segments.created_at AS segment_created_at
                FROM continuity_object_evidence_links AS links
                JOIN continuity_artifacts AS artifacts
                  ON artifacts.id = links.artifact_id
                 AND artifacts.user_id = links.user_id
                JOIN continuity_artifact_copies AS copies
                  ON copies.id = links.artifact_copy_id
                 AND copies.user_id = links.user_id
                LEFT JOIN continuity_artifact_segments AS segments
                  ON segments.id = links.artifact_segment_id
                 AND segments.user_id = links.user_id
                WHERE links.continuity_object_id = %s
                ORDER BY links.created_at ASC, links.id ASC
                """

UPDATE_CONTINUITY_OBJECT_SQL = """
                UPDATE continuity_objects
                SET status = %s,
                    is_preserved = %s,
                    is_searchable = %s,
                    is_promotable = %s,
                    title = %s,
                    body = %s,
                    provenance = %s,
                    confidence = %s,
                    last_confirmed_at = %s,
                    supersedes_object_id = %s,
                    superseded_by_object_id = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                """

INSERT_CONTINUITY_CORRECTION_EVENT_SQL = """
                INSERT INTO continuity_correction_events (
                  user_id,
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload,
                  created_at
                """

LIST_CONTINUITY_CORRECTION_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload,
                  created_at
                FROM continuity_correction_events
                WHERE continuity_object_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

INSERT_CONTRADICTION_CASE_SQL = """
                INSERT INTO contradiction_cases (
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                """

UPDATE_CONTRADICTION_CASE_SQL = """
                UPDATE contradiction_cases
                SET continuity_object_id = %s,
                    counterpart_object_id = %s,
                    kind = %s,
                    status = %s,
                    rationale = %s,
                    detection_payload = %s,
                    resolution_action = %s,
                    resolution_note = %s,
                    continuity_object_updated_at = %s,
                    counterpart_object_updated_at = %s,
                    resolved_at = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                """

GET_CONTRADICTION_CASE_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE id = %s
                """

GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE canonical_key = %s
                """

LIST_CONTRADICTION_CASES_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (%s::uuid IS NULL OR continuity_object_id = %s OR counterpart_object_id = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTRADICTION_CASES_SQL = """
                SELECT COUNT(*) AS count
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (%s::uuid IS NULL OR continuity_object_id = %s OR counterpart_object_id = %s)
                """

LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (
                    continuity_object_id = ANY(%s)
                    OR counterpart_object_id = ANY(%s)
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """

UPSERT_TRUST_SIGNAL_SQL = """
                INSERT INTO trust_signals (
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, signal_key)
                DO UPDATE
                SET continuity_object_id = EXCLUDED.continuity_object_id,
                    signal_type = EXCLUDED.signal_type,
                    signal_state = EXCLUDED.signal_state,
                    direction = EXCLUDED.direction,
                    magnitude = EXCLUDED.magnitude,
                    reason = EXCLUDED.reason,
                    contradiction_case_id = EXCLUDED.contradiction_case_id,
                    related_continuity_object_id = EXCLUDED.related_continuity_object_id,
                    payload = EXCLUDED.payload,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload,
                  created_at,
                  updated_at
                """

LIST_TRUST_SIGNALS_SQL = """
                SELECT
                  id,
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload,
                  created_at,
                  updated_at
                FROM trust_signals
                WHERE (%s::uuid IS NULL OR continuity_object_id = %s)
                  AND (%s::text IS NULL OR signal_state = %s)
                  AND (%s::text IS NULL OR signal_type = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_TRUST_SIGNALS_SQL = """
                SELECT COUNT(*) AS count
                FROM trust_signals
                WHERE (%s::uuid IS NULL OR continuity_object_id = %s)
                  AND (%s::text IS NULL OR signal_state = %s)
                  AND (%s::text IS NULL OR signal_type = %s)
                """

INSERT_MEMORY_OPERATION_CANDIDATE_SQL = """
                INSERT INTO memory_operation_candidates (
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                """

GET_MEMORY_OPERATION_CANDIDATE_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE id = %s
                """

GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE sync_fingerprint = %s
                  AND source_candidate_id = %s
                """

LIST_MEMORY_OPERATION_CANDIDATES_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE (%s::text IS NULL OR policy_action = %s::text)
                  AND (%s::text IS NULL OR operation_type = %s::text)
                  AND (%s::text IS NULL OR sync_fingerprint = %s::text)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_MEMORY_OPERATION_CANDIDATES_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_operation_candidates
                WHERE (%s::text IS NULL OR policy_action = %s::text)
                  AND (%s::text IS NULL OR operation_type = %s::text)
                  AND (%s::text IS NULL OR sync_fingerprint = %s::text)
                """

UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL = """
                UPDATE memory_operation_candidates
                SET applied_operation_id = %s,
                    applied_at = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                """

INSERT_MEMORY_OPERATION_SQL = """
                INSERT INTO memory_operations (
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                """

GET_MEMORY_OPERATION_SQL = """
                SELECT
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                FROM memory_operations
                WHERE id = %s
                """

LIST_MEMORY_OPERATIONS_SQL = """
                SELECT
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                FROM memory_operations
                WHERE (%s::text IS NULL OR sync_fingerprint = %s::text)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_MEMORY_OPERATIONS_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_operations
                WHERE (%s::text IS NULL OR sync_fingerprint = %s::text)
                """

UPDATE_EVENT_ERROR = "events are append-only and must be superseded by new records"
DELETE_EVENT_ERROR = "events are append-only and must not be deleted in place"
UPDATE_TRACE_EVENT_ERROR = "trace events are append-only and must be superseded by new records"
DELETE_TRACE_EVENT_ERROR = "trace events are append-only and must not be deleted in place"


class AppendOnlyViolation(RuntimeError):
    """Raised when a caller attempts to mutate an immutable event."""


class ContinuityStoreInvariantError(RuntimeError):
    """Raised when a write query does not return the row its contract promises."""


class ContinuityStore:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    @staticmethod
    def _default_continuity_searchable(object_type: str) -> bool:
        return object_type != "Note"

    @staticmethod
    def _default_continuity_promotable(object_type: str) -> bool:
        return object_type in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"}

    def _acquire_advisory_lock(self, lock_query: str, lock_key: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(lock_query, (str(lock_key),))

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> RowT:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return cast(RowT, row)

    def _fetch_one_with_lock(
        self,
        *,
        operation_name: str,
        lock_query: str,
        lock_key: UUID,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> RowT:
        with self.conn.cursor() as cur:
            cur.execute(lock_query, (str(lock_key),))
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return cast(RowT, row)

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[RowT]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cast(list[RowT], list(cur.fetchall()))

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> RowT | None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return cast(RowT | None, row)

    def _fetch_count(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "count query did not return a row from the database",
            )

        return cast(CountRow, row)["count"]

    def _execute(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> None:
        del operation_name
        with self.conn.cursor() as cur:
            cur.execute(query, params)

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(repr(value) for value in vector) + "]"

    def create_user(self, user_id: UUID, email: str, display_name: str | None = None) -> UserRow:
        return self._fetch_one(
            "create_user",
            INSERT_USER_SQL,
            (user_id, email, display_name),
        )

    def get_user(self, user_id: UUID) -> UserRow:
        return self._fetch_one("get_user", GET_USER_SQL, (user_id,))

    def create_thread(self, title: str, agent_profile_id: str = "assistant_default") -> ThreadRow:
        return self._fetch_one("create_thread", INSERT_THREAD_SQL, (title, agent_profile_id))

    def get_thread(self, thread_id: UUID) -> ThreadRow:
        return self._fetch_one("get_thread", GET_THREAD_SQL, (thread_id,))

    def get_thread_optional(self, thread_id: UUID) -> ThreadRow | None:
        return self._fetch_optional_one(GET_THREAD_SQL, (thread_id,))

    def list_threads(self) -> list[ThreadRow]:
        return self._fetch_all(LIST_THREADS_SQL)

    def list_agent_profiles(self) -> list[AgentProfileRow]:
        return self._fetch_all(LIST_AGENT_PROFILES_SQL)

    def get_agent_profile_optional(self, profile_id: str) -> AgentProfileRow | None:
        return self._fetch_optional_one(GET_AGENT_PROFILE_SQL, (profile_id,))

    def create_session(self, thread_id: UUID, status: str = "active") -> SessionRow:
        return self._fetch_one("create_session", INSERT_SESSION_SQL, (thread_id, status))

    def list_thread_sessions(self, thread_id: UUID) -> list[SessionRow]:
        return self._fetch_all(LIST_THREAD_SESSIONS_SQL, (thread_id,))

    def append_event(
        self,
        thread_id: UUID,
        session_id: UUID | None,
        kind: str,
        payload: JsonObject,
    ) -> EventRow:
        return self._fetch_one_with_lock(
            operation_name="append_event",
            lock_query=LOCK_THREAD_EVENTS_SQL,
            lock_key=thread_id,
            query=INSERT_EVENT_SQL,
            params=(thread_id, thread_id, session_id, kind, Jsonb(payload)),
        )

    def list_thread_events(self, thread_id: UUID) -> list[EventRow]:
        return self._fetch_all(LIST_THREAD_EVENTS_SQL, (thread_id,))

    def list_events_by_ids(self, event_ids: list[UUID]) -> list[EventRow]:
        if not event_ids:
            return []
        return self._fetch_all(LIST_EVENTS_BY_IDS_SQL, (event_ids,))

    def create_trace(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        kind: str,
        compiler_version: str,
        status: str,
        limits: JsonObject,
    ) -> TraceRow:
        return self._fetch_one(
            "create_trace",
            INSERT_TRACE_SQL,
            (user_id, thread_id, kind, compiler_version, status, Jsonb(limits)),
        )

    def get_trace(self, trace_id: UUID) -> TraceRow:
        return self._fetch_one("get_trace", GET_TRACE_SQL, (trace_id,))

    def get_trace_review_optional(self, trace_id: UUID) -> TraceReviewRow | None:
        return self._fetch_optional_one(GET_TRACE_REVIEW_SQL, (trace_id,))

    def list_trace_reviews(self) -> list[TraceReviewRow]:
        return self._fetch_all(LIST_TRACE_REVIEWS_SQL)

    def append_trace_event(
        self,
        *,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: JsonObject,
    ) -> TraceEventRow:
        return self._fetch_one(
            "append_trace_event",
            INSERT_TRACE_EVENT_SQL,
            (trace_id, sequence_no, kind, Jsonb(payload)),
        )

    def list_trace_events(self, trace_id: UUID) -> list[TraceEventRow]:
        return self._fetch_all(LIST_TRACE_EVENTS_SQL, (trace_id,))

    def create_memory(
        self,
        *,
        memory_key: str,
        value: JsonValue,
        status: str,
        source_event_ids: list[str],
        memory_type: str = "preference",
        confidence: float | None = None,
        salience: float | None = None,
        confirmation_status: str = "unconfirmed",
        trust_class: str = "deterministic",
        promotion_eligibility: str = "promotable",
        evidence_count: int | None = None,
        independent_source_count: int | None = None,
        extracted_by_model: str | None = None,
        trust_reason: str | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        last_confirmed_at: datetime | None = None,
        agent_profile_id: str = "assistant_default",
    ) -> MemoryRow:
        return self._fetch_one(
            "create_memory",
            INSERT_MEMORY_SQL,
            (
                memory_key,
                Jsonb(value),
                status,
                Jsonb(source_event_ids),
                memory_type,
                confidence,
                salience,
                confirmation_status,
                trust_class,
                promotion_eligibility,
                evidence_count,
                independent_source_count,
                extracted_by_model,
                trust_reason,
                valid_from,
                valid_to,
                last_confirmed_at,
                agent_profile_id,
            ),
        )

    def get_memory(self, memory_id: UUID) -> MemoryRow:
        return self._fetch_one("get_memory", GET_MEMORY_SQL, (memory_id,))

    def get_memory_optional(self, memory_id: UUID) -> MemoryRow | None:
        return self._fetch_optional_one(GET_MEMORY_SQL, (memory_id,))

    def list_memories_by_ids(self, memory_ids: list[UUID]) -> list[MemoryRow]:
        if not memory_ids:
            return []
        return self._fetch_all(LIST_MEMORIES_BY_IDS_SQL, (memory_ids,))

    def get_memory_by_key(self, memory_key: str) -> MemoryRow | None:
        return self._fetch_optional_one(GET_MEMORY_BY_KEY_SQL, (memory_key,))

    def get_memory_by_key_and_profile(
        self,
        *,
        memory_key: str,
        agent_profile_id: str,
    ) -> MemoryRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_BY_KEY_AND_PROFILE_SQL,
            (memory_key, agent_profile_id),
        )

    def list_memories(self) -> list[MemoryRow]:
        return self._fetch_all(LIST_MEMORIES_SQL)

    def count_memories(self, *, status: str | None = None) -> int:
        if status is None:
            return self._fetch_count(COUNT_MEMORIES_SQL)
        return self._fetch_count(COUNT_MEMORIES_BY_STATUS_SQL, (status,))

    def count_unlabeled_review_memories(self) -> int:
        return self._fetch_count(COUNT_UNLABELED_REVIEW_MEMORIES_SQL)

    def list_review_memories(self, *, status: str | None = None, limit: int) -> list[MemoryRow]:
        if status is None:
            return self._fetch_all(LIST_REVIEW_MEMORIES_SQL, (limit,))
        return self._fetch_all(LIST_REVIEW_MEMORIES_BY_STATUS_SQL, (status, limit))

    def list_unlabeled_review_memories(self, *, limit: int | None = None) -> list[MemoryRow]:
        if limit is None:
            return self._fetch_all(LIST_UNLABELED_REVIEW_MEMORIES_SQL)
        return self._fetch_all(LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL, (limit,))

    def list_context_memories(self) -> list[MemoryRow]:
        return self._fetch_all(LIST_CONTEXT_MEMORIES_SQL)

    def list_context_memories_for_profile(self, *, agent_profile_id: str) -> list[MemoryRow]:
        return self._fetch_all(LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL, (agent_profile_id,))

    def update_memory(
        self,
        *,
        memory_id: UUID,
        value: JsonValue,
        status: str,
        source_event_ids: list[str],
        memory_type: str = "preference",
        confidence: float | None = None,
        salience: float | None = None,
        confirmation_status: str = "unconfirmed",
        trust_class: str = "deterministic",
        promotion_eligibility: str = "promotable",
        evidence_count: int | None = None,
        independent_source_count: int | None = None,
        extracted_by_model: str | None = None,
        trust_reason: str | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        last_confirmed_at: datetime | None = None,
    ) -> MemoryRow:
        return self._fetch_one(
            "update_memory",
            UPDATE_MEMORY_SQL,
            (
                Jsonb(value),
                status,
                Jsonb(source_event_ids),
                memory_type,
                confidence,
                salience,
                confirmation_status,
                trust_class,
                promotion_eligibility,
                evidence_count,
                independent_source_count,
                extracted_by_model,
                trust_reason,
                valid_from,
                valid_to,
                last_confirmed_at,
                status,
                memory_id,
            ),
        )

    def append_memory_revision(
        self,
        *,
        memory_id: UUID,
        action: str,
        memory_key: str,
        previous_value: JsonValue | None,
        new_value: JsonValue | None,
        source_event_ids: list[str],
        candidate: JsonObject,
    ) -> MemoryRevisionRow:
        return self._fetch_one_with_lock(
            operation_name="append_memory_revision",
            lock_query=LOCK_MEMORY_REVISIONS_SQL,
            lock_key=memory_id,
            query=INSERT_MEMORY_REVISION_SQL,
            params=(
                memory_id,
                memory_id,
                action,
                action,
                memory_key,
                Jsonb(previous_value),
                Jsonb(new_value),
                Jsonb(source_event_ids),
                Jsonb(candidate),
                None if previous_value is None else json.dumps(previous_value, sort_keys=True),
                "{}" if new_value is None else json.dumps(new_value, sort_keys=True),
            ),
        )

    def count_memory_revisions(self, memory_id: UUID) -> int:
        return self._fetch_count(COUNT_MEMORY_REVISIONS_SQL, (memory_id,))

    def list_memory_revisions(
        self,
        memory_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[MemoryRevisionRow]:
        if limit is None:
            return self._fetch_all(LIST_MEMORY_REVISIONS_SQL, (memory_id,))
        return self._fetch_all(LIST_LIMITED_MEMORY_REVISIONS_SQL, (memory_id, limit))

    def upsert_fact_pattern(
        self,
        *,
        pattern_id: UUID,
        pattern_key: str,
        title: str,
        memory_type: str,
        namespace_key: str,
        fact_count: int,
        source_fact_ids: list[str],
        evidence_chain: JsonValue,
        explanation: str,
    ) -> FactPatternRow:
        return self._fetch_one(
            "upsert_fact_pattern",
            UPSERT_FACT_PATTERN_SQL,
            (
                pattern_id,
                pattern_key,
                title,
                memory_type,
                namespace_key,
                fact_count,
                Jsonb(source_fact_ids),
                Jsonb(evidence_chain),
                explanation,
            ),
        )

    def list_fact_patterns(self, *, limit: int) -> list[FactPatternRow]:
        return self._fetch_all(LIST_FACT_PATTERNS_SQL, (limit,))

    def count_fact_patterns(self) -> int:
        return self._fetch_count(COUNT_FACT_PATTERNS_SQL)

    def get_fact_pattern_optional(self, pattern_id: UUID) -> FactPatternRow | None:
        return self._fetch_optional_one(GET_FACT_PATTERN_SQL, (pattern_id,))

    def delete_fact_patterns_not_in(self, pattern_ids: list[UUID]) -> None:
        if not pattern_ids:
            self._execute("delete_all_fact_patterns", DELETE_ALL_FACT_PATTERNS_SQL)
            return
        self._execute("delete_fact_patterns_not_in", DELETE_FACT_PATTERNS_NOT_IN_SQL, (pattern_ids,))

    def upsert_fact_playbook(
        self,
        *,
        playbook_id: UUID,
        playbook_key: str,
        pattern_id: UUID,
        pattern_key: str,
        title: str,
        memory_type: str,
        source_fact_ids: list[str],
        source_pattern_ids: list[str],
        steps: JsonValue,
        explanation: str,
    ) -> FactPlaybookRow:
        return self._fetch_one(
            "upsert_fact_playbook",
            UPSERT_FACT_PLAYBOOK_SQL,
            (
                playbook_id,
                playbook_key,
                pattern_id,
                pattern_key,
                title,
                memory_type,
                Jsonb(source_fact_ids),
                Jsonb(source_pattern_ids),
                Jsonb(steps),
                explanation,
            ),
        )

    def list_fact_playbooks(self, *, limit: int) -> list[FactPlaybookRow]:
        return self._fetch_all(LIST_FACT_PLAYBOOKS_SQL, (limit,))

    def count_fact_playbooks(self) -> int:
        return self._fetch_count(COUNT_FACT_PLAYBOOKS_SQL)

    def get_fact_playbook_optional(self, playbook_id: UUID) -> FactPlaybookRow | None:
        return self._fetch_optional_one(GET_FACT_PLAYBOOK_SQL, (playbook_id,))

    def delete_fact_playbooks_not_in(self, playbook_ids: list[UUID]) -> None:
        if not playbook_ids:
            self._execute("delete_all_fact_playbooks", DELETE_ALL_FACT_PLAYBOOKS_SQL)
            return
        self._execute("delete_fact_playbooks_not_in", DELETE_FACT_PLAYBOOKS_NOT_IN_SQL, (playbook_ids,))

    def create_memory_review_label(
        self,
        *,
        memory_id: UUID,
        label: str,
        note: str | None,
    ) -> MemoryReviewLabelRow:
        return self._fetch_one(
            "create_memory_review_label",
            INSERT_MEMORY_REVIEW_LABEL_SQL,
            (memory_id, label, note),
        )

    def list_memory_review_labels(self, memory_id: UUID) -> list[MemoryReviewLabelRow]:
        return self._fetch_all(LIST_MEMORY_REVIEW_LABELS_SQL, (memory_id,))

    def list_memory_review_label_counts(self, memory_id: UUID) -> list[LabelCountRow]:
        return self._fetch_all(LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL, (memory_id,))

    def count_labeled_memories(self) -> int:
        return self._fetch_count(COUNT_LABELED_MEMORIES_SQL)

    def count_unlabeled_memories(self) -> int:
        return self._fetch_count(COUNT_UNLABELED_MEMORIES_SQL)

    def list_all_memory_review_label_counts(self) -> list[LabelCountRow]:
        return self._fetch_all(LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL)

    def list_active_memory_review_label_counts(self) -> list[LabelCountRow]:
        return self._fetch_all(LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL)

    def create_open_loop(
        self,
        *,
        memory_id: UUID | None,
        title: str,
        status: str,
        opened_at: datetime | None,
        due_at: datetime | None,
        resolved_at: datetime | None,
        resolution_note: str | None,
    ) -> OpenLoopRow:
        return self._fetch_one(
            "create_open_loop",
            INSERT_OPEN_LOOP_SQL,
            (
                memory_id,
                title,
                status,
                opened_at,
                due_at,
                resolved_at,
                resolution_note,
            ),
        )

    def get_open_loop(self, open_loop_id: UUID) -> OpenLoopRow:
        return self._fetch_one("get_open_loop", GET_OPEN_LOOP_SQL, (open_loop_id,))

    def get_open_loop_optional(self, open_loop_id: UUID) -> OpenLoopRow | None:
        return self._fetch_optional_one(GET_OPEN_LOOP_SQL, (open_loop_id,))

    def list_open_loops(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[OpenLoopRow]:
        if status is None and limit is None:
            return self._fetch_all(LIST_OPEN_LOOPS_SQL)
        if status is None:
            return self._fetch_all(LIST_LIMITED_OPEN_LOOPS_SQL, (limit,))
        if limit is None:
            return self._fetch_all(LIST_OPEN_LOOPS_BY_STATUS_SQL, (status,))
        return self._fetch_all(LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL, (status, limit))

    def count_open_loops(self, *, status: str | None = None) -> int:
        if status is None:
            return self._fetch_count(COUNT_OPEN_LOOPS_SQL)
        return self._fetch_count(COUNT_OPEN_LOOPS_BY_STATUS_SQL, (status,))

    def update_open_loop_status_optional(
        self,
        *,
        open_loop_id: UUID,
        status: str,
        resolved_at: datetime | None,
        resolution_note: str | None,
    ) -> OpenLoopRow | None:
        return self._fetch_optional_one(
            UPDATE_OPEN_LOOP_STATUS_SQL,
            (
                status,
                status,
                resolved_at,
                status,
                resolution_note,
                open_loop_id,
            ),
        )

    def create_continuity_capture_event(
        self,
        *,
        raw_content: str,
        explicit_signal: str | None,
        admission_posture: str,
        admission_reason: str,
    ) -> ContinuityCaptureEventRow:
        return self._fetch_one(
            "create_continuity_capture_event",
            INSERT_CONTINUITY_CAPTURE_EVENT_SQL,
            (
                raw_content,
                explicit_signal,
                admission_posture,
                admission_reason,
            ),
        )

    def get_continuity_capture_event_optional(
        self,
        capture_event_id: UUID,
    ) -> ContinuityCaptureEventRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_CAPTURE_EVENT_SQL,
            (capture_event_id,),
        )

    def list_continuity_capture_events(self, *, limit: int) -> list[ContinuityCaptureEventRow]:
        return self._fetch_all(LIST_CONTINUITY_CAPTURE_EVENTS_SQL, (limit,))

    def count_continuity_capture_events(self) -> int:
        return self._fetch_count(COUNT_CONTINUITY_CAPTURE_EVENTS_SQL)

    def create_continuity_object(
        self,
        *,
        capture_event_id: UUID,
        object_type: str,
        status: str,
        title: str,
        body: JsonObject,
        provenance: JsonObject,
        confidence: float,
        is_preserved: bool | None = None,
        is_searchable: bool | None = None,
        is_promotable: bool | None = None,
        last_confirmed_at: datetime | None = None,
        supersedes_object_id: UUID | None = None,
        superseded_by_object_id: UUID | None = None,
    ) -> ContinuityObjectRow:
        resolved_is_preserved = True if is_preserved is None else is_preserved
        resolved_is_searchable = (
            self._default_continuity_searchable(object_type)
            if is_searchable is None
            else is_searchable
        )
        resolved_is_promotable = (
            self._default_continuity_promotable(object_type)
            if is_promotable is None
            else is_promotable
        )
        return self._fetch_one(
            "create_continuity_object",
            INSERT_CONTINUITY_OBJECT_SQL,
            (
                capture_event_id,
                object_type,
                status,
                resolved_is_preserved,
                resolved_is_searchable,
                resolved_is_promotable,
                title,
                Jsonb(body),
                Jsonb(provenance),
                confidence,
                last_confirmed_at,
                supersedes_object_id,
                superseded_by_object_id,
            ),
        )

    def get_continuity_object_by_capture_event_optional(
        self,
        capture_event_id: UUID,
    ) -> ContinuityObjectRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL,
            (capture_event_id,),
        )

    def list_continuity_objects_for_capture_events(
        self,
        capture_event_ids: list[UUID],
    ) -> list[ContinuityObjectRow]:
        if not capture_event_ids:
            return []
        return self._fetch_all(
            LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL,
            (capture_event_ids,),
        )

    def get_continuity_object_optional(
        self,
        continuity_object_id: UUID,
    ) -> ContinuityObjectRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_OBJECT_SQL,
            (continuity_object_id,),
        )

    def get_continuity_object_by_commit_fingerprint_optional(
        self,
        *,
        sync_fingerprint: str,
        candidate_id: str,
    ) -> ContinuityObjectRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL,
            (sync_fingerprint, candidate_id),
        )

    def list_continuity_review_queue(
        self,
        *,
        statuses: list[str],
        limit: int,
    ) -> list[ContinuityObjectRow]:
        return self._fetch_all(
            LIST_CONTINUITY_REVIEW_QUEUE_SQL,
            (statuses, limit),
        )

    def count_continuity_review_queue(
        self,
        *,
        statuses: list[str],
    ) -> int:
        return self._fetch_count(
            COUNT_CONTINUITY_REVIEW_QUEUE_SQL,
            (statuses,),
        )

    def list_continuity_recall_candidates(self) -> list[ContinuityRecallCandidateRow]:
        return self._fetch_all(LIST_CONTINUITY_RECALL_CANDIDATES_SQL)

    def upsert_eval_suite(
        self,
        *,
        suite_key: str,
        title: str,
        description: str,
        evaluator_kind: str,
        fixture_schema_version: str,
        fixture_source_path: str,
        case_count: int,
        suite_order: int,
        metadata: JsonObject,
    ) -> EvalSuiteRow:
        return self._fetch_one(
            "upsert_eval_suite",
            UPSERT_EVAL_SUITE_SQL,
            (
                suite_key,
                title,
                description,
                evaluator_kind,
                fixture_schema_version,
                fixture_source_path,
                case_count,
                suite_order,
                Jsonb(metadata),
            ),
        )

    def list_eval_suites(self) -> list[EvalSuiteRow]:
        return self._fetch_all(LIST_EVAL_SUITES_SQL)

    def delete_eval_suites_not_in(self, suite_keys: list[str]) -> None:
        self._execute("delete_eval_suites_not_in", DELETE_EVAL_SUITES_NOT_IN_SQL, (suite_keys,))

    def upsert_eval_case(
        self,
        *,
        suite_id: UUID,
        case_key: str,
        title: str,
        evaluator_kind: str,
        case_order: int,
        fixture: JsonObject,
        expectations: JsonObject,
    ) -> EvalCaseRow:
        return self._fetch_one(
            "upsert_eval_case",
            UPSERT_EVAL_CASE_SQL,
            (
                suite_id,
                case_key,
                title,
                evaluator_kind,
                case_order,
                Jsonb(fixture),
                Jsonb(expectations),
            ),
        )

    def list_eval_cases_for_suite(self, suite_id: UUID) -> list[EvalCaseRow]:
        return self._fetch_all(LIST_EVAL_CASES_FOR_SUITE_SQL, (suite_id,))

    def delete_eval_cases_for_suite_not_in(self, *, suite_id: UUID, case_keys: list[str]) -> None:
        self._execute(
            "delete_eval_cases_for_suite_not_in",
            DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL,
            (suite_id, case_keys),
        )

    def create_eval_run(
        self,
        *,
        fixture_schema_version: str,
        fixture_source_path: str,
        requested_suite_keys: list[str],
        status: str,
        summary: JsonObject,
        report: JsonObject,
        report_digest: str,
    ) -> EvalRunRow:
        return self._fetch_one(
            "create_eval_run",
            INSERT_EVAL_RUN_SQL,
            (
                fixture_schema_version,
                fixture_source_path,
                Jsonb(requested_suite_keys),
                status,
                Jsonb(summary),
                Jsonb(report),
                report_digest,
            ),
        )

    def list_eval_runs(self, *, limit: int) -> list[EvalRunRow]:
        return self._fetch_all(LIST_EVAL_RUNS_SQL, (limit,))

    def get_eval_run_optional(self, eval_run_id: UUID) -> EvalRunRow | None:
        return self._fetch_optional_one(GET_EVAL_RUN_SQL, (eval_run_id,))

    def create_eval_result(
        self,
        *,
        eval_run_id: UUID,
        suite_key: str,
        case_key: str,
        status: str,
        score: float,
        summary: JsonObject,
        details: JsonObject,
    ) -> EvalResultRow:
        return self._fetch_one(
            "create_eval_result",
            INSERT_EVAL_RESULT_SQL,
            (
                eval_run_id,
                suite_key,
                case_key,
                status,
                score,
                Jsonb(summary),
                Jsonb(details),
            ),
        )

    def list_eval_results_for_run(self, eval_run_id: UUID) -> list[EvalResultRow]:
        return self._fetch_all(LIST_EVAL_RESULTS_FOR_RUN_SQL, (eval_run_id,))

    def create_retrieval_run(
        self,
        *,
        source_surface: str,
        ranking_strategy: str,
        query_text: str | None,
        request_scope: JsonObject,
        result_ids: list[str],
        exclusion_summary: JsonObject,
        candidate_count: int,
        selected_count: int,
        debug_enabled: bool,
        retention_until: datetime,
    ) -> RetrievalRunRow:
        return self._fetch_one(
            "create_retrieval_run",
            INSERT_RETRIEVAL_RUN_SQL,
            (
                source_surface,
                ranking_strategy,
                query_text,
                Jsonb(request_scope),
                Jsonb(result_ids),
                Jsonb(exclusion_summary),
                candidate_count,
                selected_count,
                debug_enabled,
                retention_until,
            ),
        )

    def list_retrieval_runs(self, *, limit: int) -> list[RetrievalRunRow]:
        return self._fetch_all(LIST_RETRIEVAL_RUNS_SQL, (limit,))

    def get_retrieval_run_optional(self, retrieval_run_id: UUID) -> RetrievalRunRow | None:
        return self._fetch_optional_one(GET_RETRIEVAL_RUN_SQL, (retrieval_run_id,))

    def create_retrieval_candidate(
        self,
        *,
        retrieval_run_id: UUID,
        continuity_object_id: UUID,
        rank: int | None,
        selected: bool,
        exclusion_reason: str | None,
        lexical_score: float,
        semantic_score: float,
        entity_edge_score: float,
        temporal_score: float,
        trust_score: float,
        relevance: float,
        scope_matches: list[JsonObject],
        stage_details: JsonObject,
        ordering: JsonObject,
        title: str,
        object_type: str,
        status: str,
    ) -> RetrievalCandidateRow:
        return self._fetch_one(
            "create_retrieval_candidate",
            INSERT_RETRIEVAL_CANDIDATE_SQL,
            (
                retrieval_run_id,
                continuity_object_id,
                rank,
                selected,
                exclusion_reason,
                lexical_score,
                semantic_score,
                entity_edge_score,
                temporal_score,
                trust_score,
                relevance,
                Jsonb(scope_matches),
                Jsonb(stage_details),
                Jsonb(ordering),
                title,
                object_type,
                status,
            ),
        )

    def list_retrieval_candidates_for_run(
        self,
        retrieval_run_id: UUID,
    ) -> list[RetrievalCandidateRow]:
        return self._fetch_all(LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL, (retrieval_run_id,))

    def upsert_continuity_artifact(
        self,
        *,
        source_kind: str,
        import_source_path: str,
        relative_path: str,
        display_name: str,
        media_type: str,
    ) -> ContinuityArtifactRow:
        created = self._fetch_optional_one(
            UPSERT_CONTINUITY_ARTIFACT_SQL,
            (
                source_kind,
                import_source_path,
                relative_path,
                display_name,
                media_type,
            ),
        )
        if created is not None:
            return created
        existing = self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL,
            (source_kind, import_source_path, relative_path),
        )
        if existing is None:
            raise ContinuityStoreInvariantError(
                "upsert_continuity_artifact did not return or reveal an artifact row",
            )
        return existing

    def get_continuity_artifact_optional(
        self,
        artifact_id: UUID,
    ) -> ContinuityArtifactRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_SQL,
            (artifact_id,),
        )

    def upsert_continuity_artifact_copy(
        self,
        *,
        artifact_id: UUID,
        checksum_sha256: str,
        content_text: str,
        content_length_bytes: int,
        content_encoding: str,
    ) -> ContinuityArtifactCopyRow:
        created = self._fetch_optional_one(
            UPSERT_CONTINUITY_ARTIFACT_COPY_SQL,
            (
                artifact_id,
                checksum_sha256,
                content_text,
                content_length_bytes,
                content_encoding,
            ),
        )
        if created is not None:
            return created
        existing = self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL,
            (artifact_id, checksum_sha256),
        )
        if existing is None:
            raise ContinuityStoreInvariantError(
                "upsert_continuity_artifact_copy did not return or reveal an artifact copy row",
            )
        return existing

    def get_continuity_artifact_copy_optional(
        self,
        artifact_copy_id: UUID,
    ) -> ContinuityArtifactCopyRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_COPY_SQL,
            (artifact_copy_id,),
        )

    def list_continuity_artifact_copies(
        self,
        artifact_id: UUID,
    ) -> list[ContinuityArtifactCopyRow]:
        return self._fetch_all(
            LIST_CONTINUITY_ARTIFACT_COPIES_SQL,
            (artifact_id,),
        )

    def upsert_continuity_artifact_segment(
        self,
        *,
        artifact_id: UUID,
        artifact_copy_id: UUID,
        source_item_id: str,
        sequence_no: int,
        segment_kind: str,
        locator: JsonObject,
        raw_content: str,
        checksum_sha256: str,
    ) -> ContinuityArtifactSegmentRow:
        created = self._fetch_optional_one(
            UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL,
            (
                artifact_id,
                artifact_copy_id,
                source_item_id,
                sequence_no,
                segment_kind,
                Jsonb(locator),
                raw_content,
                checksum_sha256,
            ),
        )
        if created is not None:
            return created
        existing = self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL,
            (artifact_copy_id, source_item_id),
        )
        if existing is None:
            raise ContinuityStoreInvariantError(
                "upsert_continuity_artifact_segment did not return or reveal a segment row",
            )
        return existing

    def get_continuity_artifact_segment_optional(
        self,
        artifact_segment_id: UUID,
    ) -> ContinuityArtifactSegmentRow | None:
        return self._fetch_optional_one(
            GET_CONTINUITY_ARTIFACT_SEGMENT_SQL,
            (artifact_segment_id,),
        )

    def list_continuity_artifact_segments(
        self,
        artifact_id: UUID,
    ) -> list[ContinuityArtifactSegmentRow]:
        return self._fetch_all(
            LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL,
            (artifact_id,),
        )

    def create_continuity_object_evidence_link(
        self,
        *,
        continuity_object_id: UUID,
        artifact_id: UUID,
        artifact_copy_id: UUID,
        artifact_segment_id: UUID | None,
        relationship: str,
    ) -> ContinuityObjectEvidenceLinkRow:
        return self._fetch_one(
            "create_continuity_object_evidence_link",
            INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL,
            (
                continuity_object_id,
                artifact_id,
                artifact_copy_id,
                artifact_segment_id,
                relationship,
            ),
        )

    def list_continuity_object_evidence(
        self,
        continuity_object_id: UUID,
    ) -> list[ContinuityObjectEvidenceRow]:
        return self._fetch_all(
            LIST_CONTINUITY_OBJECT_EVIDENCE_SQL,
            (continuity_object_id,),
        )

    def update_continuity_object_optional(
        self,
        *,
        continuity_object_id: UUID,
        status: str,
        is_preserved: bool,
        is_searchable: bool,
        is_promotable: bool,
        title: str,
        body: JsonObject,
        provenance: JsonObject,
        confidence: float,
        last_confirmed_at: datetime | None,
        supersedes_object_id: UUID | None,
        superseded_by_object_id: UUID | None,
    ) -> ContinuityObjectRow | None:
        return self._fetch_optional_one(
            UPDATE_CONTINUITY_OBJECT_SQL,
            (
                status,
                is_preserved,
                is_searchable,
                is_promotable,
                title,
                Jsonb(body),
                Jsonb(provenance),
                confidence,
                last_confirmed_at,
                supersedes_object_id,
                superseded_by_object_id,
                continuity_object_id,
            ),
        )

    def create_continuity_correction_event(
        self,
        *,
        continuity_object_id: UUID,
        action: str,
        reason: str | None,
        before_snapshot: JsonObject,
        after_snapshot: JsonObject,
        payload: JsonObject,
    ) -> ContinuityCorrectionEventRow:
        return self._fetch_one(
            "create_continuity_correction_event",
            INSERT_CONTINUITY_CORRECTION_EVENT_SQL,
            (
                continuity_object_id,
                action,
                reason,
                Jsonb(before_snapshot),
                Jsonb(after_snapshot),
                Jsonb(payload),
            ),
        )

    def list_continuity_correction_events(
        self,
        *,
        continuity_object_id: UUID,
        limit: int,
    ) -> list[ContinuityCorrectionEventRow]:
        return self._fetch_all(
            LIST_CONTINUITY_CORRECTION_EVENTS_SQL,
            (continuity_object_id, limit),
        )

    def create_contradiction_case(
        self,
        *,
        canonical_key: str,
        continuity_object_id: UUID,
        counterpart_object_id: UUID,
        kind: str,
        status: str,
        rationale: str,
        detection_payload: JsonObject,
        resolution_action: str | None,
        resolution_note: str | None,
        continuity_object_updated_at: datetime,
        counterpart_object_updated_at: datetime,
        resolved_at: datetime | None,
    ) -> ContradictionCaseRow:
        return self._fetch_one(
            "create_contradiction_case",
            INSERT_CONTRADICTION_CASE_SQL,
            (
                canonical_key,
                continuity_object_id,
                counterpart_object_id,
                kind,
                status,
                rationale,
                Jsonb(detection_payload),
                resolution_action,
                resolution_note,
                continuity_object_updated_at,
                counterpart_object_updated_at,
                resolved_at,
            ),
        )

    def update_contradiction_case_optional(
        self,
        *,
        contradiction_case_id: UUID,
        continuity_object_id: UUID,
        counterpart_object_id: UUID,
        kind: str,
        status: str,
        rationale: str,
        detection_payload: JsonObject,
        resolution_action: str | None,
        resolution_note: str | None,
        continuity_object_updated_at: datetime,
        counterpart_object_updated_at: datetime,
        resolved_at: datetime | None,
    ) -> ContradictionCaseRow | None:
        return self._fetch_optional_one(
            UPDATE_CONTRADICTION_CASE_SQL,
            (
                continuity_object_id,
                counterpart_object_id,
                kind,
                status,
                rationale,
                Jsonb(detection_payload),
                resolution_action,
                resolution_note,
                continuity_object_updated_at,
                counterpart_object_updated_at,
                resolved_at,
                contradiction_case_id,
            ),
        )

    def get_contradiction_case_optional(
        self,
        contradiction_case_id: UUID,
    ) -> ContradictionCaseRow | None:
        return self._fetch_optional_one(
            GET_CONTRADICTION_CASE_SQL,
            (contradiction_case_id,),
        )

    def get_contradiction_case_by_canonical_key_optional(
        self,
        *,
        canonical_key: str,
    ) -> ContradictionCaseRow | None:
        return self._fetch_optional_one(
            GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL,
            (canonical_key,),
        )

    def list_contradiction_cases(
        self,
        *,
        statuses: list[str],
        limit: int,
        continuity_object_id: UUID | None = None,
    ) -> list[ContradictionCaseRow]:
        return self._fetch_all(
            LIST_CONTRADICTION_CASES_SQL,
            (
                statuses,
                continuity_object_id,
                continuity_object_id,
                continuity_object_id,
                limit,
            ),
        )

    def count_contradiction_cases(
        self,
        *,
        statuses: list[str],
        continuity_object_id: UUID | None = None,
    ) -> int:
        return self._fetch_count(
            COUNT_CONTRADICTION_CASES_SQL,
            (
                statuses,
                continuity_object_id,
                continuity_object_id,
                continuity_object_id,
            ),
        )

    def list_contradiction_cases_for_objects(
        self,
        *,
        continuity_object_ids: list[UUID],
        statuses: list[str],
    ) -> list[ContradictionCaseRow]:
        if not continuity_object_ids:
            return []
        return self._fetch_all(
            LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL,
            (
                statuses,
                continuity_object_ids,
                continuity_object_ids,
            ),
        )

    def upsert_trust_signal(
        self,
        *,
        continuity_object_id: UUID,
        signal_key: str,
        signal_type: str,
        signal_state: str,
        direction: str,
        magnitude: float,
        reason: str,
        contradiction_case_id: UUID | None,
        related_continuity_object_id: UUID | None,
        payload: JsonObject,
    ) -> TrustSignalRow:
        return self._fetch_one(
            "upsert_trust_signal",
            UPSERT_TRUST_SIGNAL_SQL,
            (
                continuity_object_id,
                signal_key,
                signal_type,
                signal_state,
                direction,
                magnitude,
                reason,
                contradiction_case_id,
                related_continuity_object_id,
                Jsonb(payload),
            ),
        )

    def list_trust_signals(
        self,
        *,
        limit: int,
        continuity_object_id: UUID | None = None,
        signal_state: str | None = None,
        signal_type: str | None = None,
    ) -> list[TrustSignalRow]:
        return self._fetch_all(
            LIST_TRUST_SIGNALS_SQL,
            (
                continuity_object_id,
                continuity_object_id,
                signal_state,
                signal_state,
                signal_type,
                signal_type,
                limit,
            ),
        )

    def count_trust_signals(
        self,
        *,
        continuity_object_id: UUID | None = None,
        signal_state: str | None = None,
        signal_type: str | None = None,
    ) -> int:
        return self._fetch_count(
            COUNT_TRUST_SIGNALS_SQL,
            (
                continuity_object_id,
                continuity_object_id,
                signal_state,
                signal_state,
                signal_type,
                signal_type,
            ),
        )

    def create_memory_operation_candidate(
        self,
        *,
        sync_fingerprint: str,
        source_kind: str,
        source_candidate_id: str,
        source_candidate_type: str,
        candidate_payload: JsonObject,
        source_scope: JsonObject,
        operation_type: str,
        operation_reason: str,
        policy_action: str,
        policy_reason: str,
        target_continuity_object_id: UUID | None,
        target_snapshot: JsonObject,
    ) -> MemoryOperationCandidateRow:
        return self._fetch_one(
            "create_memory_operation_candidate",
            INSERT_MEMORY_OPERATION_CANDIDATE_SQL,
            (
                sync_fingerprint,
                source_kind,
                source_candidate_id,
                source_candidate_type,
                Jsonb(candidate_payload),
                Jsonb(source_scope),
                operation_type,
                operation_reason,
                policy_action,
                policy_reason,
                target_continuity_object_id,
                Jsonb(target_snapshot),
            ),
        )

    def get_memory_operation_candidate_optional(
        self,
        candidate_id: UUID,
    ) -> MemoryOperationCandidateRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_OPERATION_CANDIDATE_SQL,
            (candidate_id,),
        )

    def get_memory_operation_candidate_by_sync_source_optional(
        self,
        *,
        sync_fingerprint: str,
        source_candidate_id: str,
    ) -> MemoryOperationCandidateRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL,
            (sync_fingerprint, source_candidate_id),
        )

    def list_memory_operation_candidates(
        self,
        *,
        limit: int,
        policy_action: str | None = None,
        operation_type: str | None = None,
        sync_fingerprint: str | None = None,
    ) -> list[MemoryOperationCandidateRow]:
        return self._fetch_all(
            LIST_MEMORY_OPERATION_CANDIDATES_SQL,
            (
                policy_action,
                policy_action,
                operation_type,
                operation_type,
                sync_fingerprint,
                sync_fingerprint,
                limit,
            ),
        )

    def count_memory_operation_candidates(
        self,
        *,
        policy_action: str | None = None,
        operation_type: str | None = None,
        sync_fingerprint: str | None = None,
    ) -> int:
        return self._fetch_count(
            COUNT_MEMORY_OPERATION_CANDIDATES_SQL,
            (
                policy_action,
                policy_action,
                operation_type,
                operation_type,
                sync_fingerprint,
                sync_fingerprint,
            ),
        )

    def update_memory_operation_candidate_application(
        self,
        *,
        candidate_id: UUID,
        applied_operation_id: UUID,
        applied_at: datetime,
    ) -> MemoryOperationCandidateRow | None:
        return self._fetch_optional_one(
            UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL,
            (
                applied_operation_id,
                applied_at,
                candidate_id,
            ),
        )

    def create_memory_operation(
        self,
        *,
        operation_id: UUID,
        candidate_id: UUID,
        operation_type: str,
        status: str,
        sync_fingerprint: str,
        target_continuity_object_id: UUID | None,
        resulting_continuity_object_id: UUID | None,
        correction_event_id: UUID | None,
        before_snapshot: JsonObject,
        after_snapshot: JsonObject,
        details: JsonObject,
    ) -> MemoryOperationRow:
        return self._fetch_one(
            "create_memory_operation",
            INSERT_MEMORY_OPERATION_SQL,
            (
                operation_id,
                candidate_id,
                operation_type,
                status,
                sync_fingerprint,
                target_continuity_object_id,
                resulting_continuity_object_id,
                correction_event_id,
                Jsonb(before_snapshot),
                Jsonb(after_snapshot),
                Jsonb(details),
            ),
        )

    def get_memory_operation_optional(
        self,
        operation_id: UUID,
    ) -> MemoryOperationRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_OPERATION_SQL,
            (operation_id,),
        )

    def list_memory_operations(
        self,
        *,
        limit: int,
        sync_fingerprint: str | None = None,
    ) -> list[MemoryOperationRow]:
        return self._fetch_all(
            LIST_MEMORY_OPERATIONS_SQL,
            (
                sync_fingerprint,
                sync_fingerprint,
                limit,
            ),
        )

    def count_memory_operations(
        self,
        *,
        sync_fingerprint: str | None = None,
    ) -> int:
        return self._fetch_count(
            COUNT_MEMORY_OPERATIONS_SQL,
            (
                sync_fingerprint,
                sync_fingerprint,
            ),
        )

    def create_model_provider(
        self,
        *,
        workspace_id: UUID,
        created_by_user_account_id: UUID,
        provider_key: str,
        model_provider: str,
        display_name: str,
        base_url: str,
        api_key: str,
        default_model: str,
        status: str,
        metadata: JsonObject,
        auth_mode: str = "bearer",
        model_list_path: str = "",
        healthcheck_path: str = "",
        invoke_path: str = "",
        azure_api_version: str = "",
        azure_auth_secret_ref: str = "",
    ) -> ModelProviderRow:
        return self._fetch_one(
            "create_model_provider",
            INSERT_MODEL_PROVIDER_SQL,
            (
                workspace_id,
                created_by_user_account_id,
                provider_key,
                model_provider,
                display_name,
                base_url,
                api_key,
                auth_mode,
                default_model,
                status,
                model_list_path,
                healthcheck_path,
                invoke_path,
                azure_api_version,
                azure_auth_secret_ref,
                Jsonb(metadata),
            ),
        )

    def get_model_provider_for_workspace_optional(
        self,
        *,
        provider_id: UUID,
        workspace_id: UUID,
    ) -> ModelProviderRow | None:
        return self._fetch_optional_one(
            GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL,
            (provider_id, workspace_id),
        )

    def list_model_providers_for_workspace(self, *, workspace_id: UUID) -> list[ModelProviderRow]:
        return self._fetch_all(
            LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL,
            (workspace_id,),
        )

    def update_model_provider(
        self,
        *,
        provider_id: UUID,
        workspace_id: UUID,
        provider_key: str,
        model_provider: str,
        display_name: str,
        base_url: str,
        api_key: str,
        auth_mode: str,
        default_model: str,
        status: str,
        model_list_path: str,
        healthcheck_path: str,
        invoke_path: str,
        azure_api_version: str,
        azure_auth_secret_ref: str,
        metadata: JsonObject,
    ) -> ModelProviderRow:
        return self._fetch_one(
            "update_model_provider",
            UPDATE_MODEL_PROVIDER_SQL,
            (
                provider_key,
                model_provider,
                display_name,
                base_url,
                api_key,
                auth_mode,
                default_model,
                status,
                model_list_path,
                healthcheck_path,
                invoke_path,
                azure_api_version,
                azure_auth_secret_ref,
                Jsonb(metadata),
                provider_id,
                workspace_id,
            ),
        )

    def upsert_provider_capability(
        self,
        *,
        workspace_id: UUID,
        provider_id: UUID,
        discovered_by_user_account_id: UUID,
        adapter_key: str,
        discovery_status: str,
        capability_snapshot: JsonObject,
        discovery_error: str | None,
    ) -> ProviderCapabilityRow:
        return self._fetch_one(
            "upsert_provider_capability",
            UPSERT_PROVIDER_CAPABILITY_SQL,
            (
                workspace_id,
                provider_id,
                discovered_by_user_account_id,
                adapter_key,
                discovery_status,
                Jsonb(capability_snapshot),
                discovery_error,
            ),
        )

    def get_provider_capability_for_provider_optional(
        self,
        *,
        provider_id: UUID,
        workspace_id: UUID,
    ) -> ProviderCapabilityRow | None:
        return self._fetch_optional_one(
            GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL,
            (provider_id, workspace_id),
        )

    def record_provider_invocation_telemetry(
        self,
        *,
        workspace_id: UUID,
        provider_id: UUID,
        thread_id: UUID | None,
        invoked_by_user_account_id: UUID,
        invocation_kind: str,
        adapter_key: str,
        runtime_provider: str,
        requested_model: str,
        response_model: str | None,
        response_id: str | None,
        status: str,
        latency_ms: int,
        usage: JsonObject,
        error_detail: str | None,
    ) -> ProviderInvocationTelemetryRow:
        return self._fetch_one(
            "record_provider_invocation_telemetry",
            INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL,
            (
                workspace_id,
                provider_id,
                thread_id,
                invoked_by_user_account_id,
                invocation_kind,
                adapter_key,
                runtime_provider,
                requested_model,
                response_model,
                response_id,
                status,
                latency_ms,
                Jsonb(usage),
                error_detail,
            ),
        )

    def create_model_pack(
        self,
        *,
        workspace_id: UUID,
        created_by_user_account_id: UUID,
        pack_id: str,
        pack_version: str,
        display_name: str,
        family: str,
        description: str,
        status: str,
        briefing_strategy: str,
        briefing_max_tokens: int | None,
        contract: JsonObject,
        metadata: JsonObject,
    ) -> ModelPackRow:
        return self._fetch_one(
            "create_model_pack",
            INSERT_MODEL_PACK_SQL,
            (
                workspace_id,
                created_by_user_account_id,
                pack_id,
                pack_version,
                display_name,
                family,
                description,
                status,
                briefing_strategy,
                briefing_max_tokens,
                Jsonb(contract),
                Jsonb(metadata),
            ),
        )

    def create_model_pack_if_absent_optional(
        self,
        *,
        workspace_id: UUID,
        created_by_user_account_id: UUID,
        pack_id: str,
        pack_version: str,
        display_name: str,
        family: str,
        description: str,
        status: str,
        briefing_strategy: str,
        briefing_max_tokens: int | None,
        contract: JsonObject,
        metadata: JsonObject,
    ) -> ModelPackRow | None:
        return self._fetch_optional_one(
            INSERT_MODEL_PACK_IF_ABSENT_SQL,
            (
                workspace_id,
                created_by_user_account_id,
                pack_id,
                pack_version,
                display_name,
                family,
                description,
                status,
                briefing_strategy,
                briefing_max_tokens,
                Jsonb(contract),
                Jsonb(metadata),
            ),
        )

    def get_model_pack_for_workspace_optional(
        self,
        *,
        workspace_id: UUID,
        pack_id: str,
        pack_version: str | None = None,
    ) -> ModelPackRow | None:
        if pack_version is None:
            return self._fetch_optional_one(
                GET_LATEST_MODEL_PACK_FOR_WORKSPACE_BY_ID_SQL,
                (workspace_id, pack_id),
            )
        return self._fetch_optional_one(
            GET_MODEL_PACK_FOR_WORKSPACE_BY_ID_AND_VERSION_SQL,
            (workspace_id, pack_id, pack_version),
        )

    def get_model_pack_for_workspace_by_row_id_optional(
        self,
        *,
        workspace_id: UUID,
        model_pack_id: UUID,
    ) -> ModelPackRow | None:
        return self._fetch_optional_one(
            GET_MODEL_PACK_FOR_WORKSPACE_BY_ROW_ID_SQL,
            (workspace_id, model_pack_id),
        )

    def list_model_packs_for_workspace(self, *, workspace_id: UUID) -> list[ModelPackRow]:
        return self._fetch_all(
            LIST_MODEL_PACKS_FOR_WORKSPACE_SQL,
            (workspace_id,),
        )

    def create_workspace_model_pack_binding(
        self,
        *,
        workspace_id: UUID,
        provider_id: UUID | None,
        model_pack_id: UUID,
        bound_by_user_account_id: UUID,
        binding_source: str,
        metadata: JsonObject,
    ) -> WorkspaceModelPackBindingRow:
        return self._fetch_one(
            "create_workspace_model_pack_binding",
            INSERT_WORKSPACE_MODEL_PACK_BINDING_SQL,
            (
                workspace_id,
                provider_id,
                model_pack_id,
                bound_by_user_account_id,
                binding_source,
                Jsonb(metadata),
            ),
        )

    def get_latest_workspace_model_pack_binding_optional(
        self,
        *,
        workspace_id: UUID,
    ) -> WorkspaceModelPackBindingDetailRow | None:
        return self._fetch_optional_one(
            GET_LATEST_WORKSPACE_MODEL_PACK_BINDING_SQL,
            (workspace_id,),
        )

    def get_resolved_workspace_model_pack_binding_optional(
        self,
        *,
        workspace_id: UUID,
        provider_id: UUID,
    ) -> WorkspaceModelPackBindingDetailRow | None:
        return self._fetch_optional_one(
            GET_RESOLVED_WORKSPACE_MODEL_PACK_BINDING_SQL,
            (workspace_id, provider_id, provider_id),
        )

    def workspace_visible_to_user_account(
        self,
        *,
        workspace_id: UUID,
        user_account_id: UUID,
    ) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL,
                (workspace_id, user_account_id),
            )
            return cur.fetchone() is not None

    def create_task_brief(
        self,
        *,
        mode: str,
        query_text: str | None,
        scope: JsonObject,
        provider_strategy: str,
        model_pack_strategy: str,
        token_budget: int,
        estimated_tokens: int,
        item_count: int,
        deterministic_key: str,
        payload: JsonObject,
    ) -> TaskBriefRow:
        return self._fetch_one(
            "create_task_brief",
            INSERT_TASK_BRIEF_SQL,
            (
                mode,
                query_text,
                Jsonb(scope),
                provider_strategy,
                model_pack_strategy,
                token_budget,
                estimated_tokens,
                item_count,
                deterministic_key,
                Jsonb(payload),
            ),
        )

    def get_task_brief_optional(self, *, task_brief_id: UUID) -> TaskBriefRow | None:
        return self._fetch_optional_one(
            GET_TASK_BRIEF_BY_ID_SQL,
            (task_brief_id,),
        )

    def create_embedding_config(
        self,
        *,
        provider: str,
        model: str,
        version: str,
        dimensions: int,
        status: str,
        metadata: JsonObject,
    ) -> EmbeddingConfigRow:
        return self._fetch_one(
            "create_embedding_config",
            INSERT_EMBEDDING_CONFIG_SQL,
            (provider, model, version, dimensions, status, Jsonb(metadata)),
        )

    def get_embedding_config_optional(self, embedding_config_id: UUID) -> EmbeddingConfigRow | None:
        return self._fetch_optional_one(GET_EMBEDDING_CONFIG_SQL, (embedding_config_id,))

    def get_embedding_config_by_identity_optional(
        self,
        *,
        provider: str,
        model: str,
        version: str,
    ) -> EmbeddingConfigRow | None:
        return self._fetch_optional_one(
            GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL,
            (provider, model, version),
        )

    def list_embedding_configs(self) -> list[EmbeddingConfigRow]:
        return self._fetch_all(LIST_EMBEDDING_CONFIGS_SQL)

    def create_memory_embedding(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> MemoryEmbeddingRow:
        return self._fetch_one(
            "create_memory_embedding",
            INSERT_MEMORY_EMBEDDING_SQL,
            (memory_id, embedding_config_id, dimensions, Jsonb(vector)),
        )

    def get_memory_embedding_optional(self, memory_embedding_id: UUID) -> MemoryEmbeddingRow | None:
        return self._fetch_optional_one(GET_MEMORY_EMBEDDING_SQL, (memory_embedding_id,))

    def get_memory_embedding_by_memory_and_config_optional(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
    ) -> MemoryEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL,
            (memory_id, embedding_config_id),
        )

    def list_memory_embeddings_for_memory(self, memory_id: UUID) -> list[MemoryEmbeddingRow]:
        return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL, (memory_id,))

    def list_memory_embeddings_for_config(
        self,
        embedding_config_id: UUID,
    ) -> list[MemoryEmbeddingRow]:
        return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL, (embedding_config_id,))

    def update_memory_embedding(
        self,
        *,
        memory_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> MemoryEmbeddingRow:
        return self._fetch_one(
            "update_memory_embedding",
            UPDATE_MEMORY_EMBEDDING_SQL,
            (dimensions, Jsonb(vector), memory_embedding_id),
        )

    def retrieve_semantic_memory_matches(
        self,
        *,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[SemanticMemoryRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                limit,
            ),
        )

    def retrieve_semantic_memory_matches_for_profile(
        self,
        *,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
        agent_profile_id: str,
    ) -> list[SemanticMemoryRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                agent_profile_id,
                limit,
            ),
        )

    def retrieve_task_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[TaskArtifactChunkSemanticRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                task_id,
                limit,
            ),
        )

    def retrieve_artifact_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_artifact_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[TaskArtifactChunkSemanticRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                task_artifact_id,
                limit,
            ),
        )

    def create_entity(
        self,
        *,
        entity_type: str,
        name: str,
        source_memory_ids: list[str],
    ) -> EntityRow:
        return self._fetch_one(
            "create_entity",
            INSERT_ENTITY_SQL,
            (entity_type, name, Jsonb(source_memory_ids)),
        )

    def get_entity_optional(self, entity_id: UUID) -> EntityRow | None:
        return self._fetch_optional_one(GET_ENTITY_SQL, (entity_id,))

    def list_entities(self) -> list[EntityRow]:
        return self._fetch_all(LIST_ENTITIES_SQL)

    def create_entity_edge(
        self,
        *,
        from_entity_id: UUID,
        to_entity_id: UUID,
        relationship_type: str,
        valid_from: datetime | None,
        valid_to: datetime | None,
        source_memory_ids: list[str],
    ) -> EntityEdgeRow:
        return self._fetch_one(
            "create_entity_edge",
            INSERT_ENTITY_EDGE_SQL,
            (
                from_entity_id,
                to_entity_id,
                relationship_type,
                valid_from,
                valid_to,
                Jsonb(source_memory_ids),
            ),
        )

    def list_entity_edges_for_entity(self, entity_id: UUID) -> list[EntityEdgeRow]:
        return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITY_SQL, (entity_id, entity_id))

    def list_entity_edges_for_entities(self, entity_ids: list[UUID]) -> list[EntityEdgeRow]:
        if not entity_ids:
            return []
        return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITIES_SQL, (entity_ids, entity_ids))

    def create_consent(
        self,
        *,
        consent_key: str,
        status: str,
        metadata: JsonObject,
    ) -> ConsentRow:
        return self._fetch_one(
            "create_consent",
            INSERT_CONSENT_SQL,
            (consent_key, status, Jsonb(metadata)),
        )

    def get_consent_by_key_optional(self, consent_key: str) -> ConsentRow | None:
        return self._fetch_optional_one(GET_CONSENT_BY_KEY_SQL, (consent_key,))

    def list_consents(self) -> list[ConsentRow]:
        return self._fetch_all(LIST_CONSENTS_SQL)

    def update_consent(
        self,
        *,
        consent_id: UUID,
        status: str,
        metadata: JsonObject,
    ) -> ConsentRow:
        return self._fetch_one(
            "update_consent",
            UPDATE_CONSENT_SQL,
            (status, Jsonb(metadata), consent_id),
        )

    def create_policy(
        self,
        *,
        agent_profile_id: str | None = None,
        name: str,
        action: str,
        scope: str,
        effect: str,
        priority: int,
        active: bool,
        conditions: JsonObject,
        required_consents: list[str],
    ) -> PolicyRow:
        return self._fetch_one(
            "create_policy",
            INSERT_POLICY_SQL,
            (
                agent_profile_id,
                name,
                action,
                scope,
                effect,
                priority,
                active,
                Jsonb(conditions),
                Jsonb(required_consents),
            ),
        )

    def get_policy_optional(self, policy_id: UUID) -> PolicyRow | None:
        return self._fetch_optional_one(GET_POLICY_SQL, (policy_id,))

    def list_policies(self) -> list[PolicyRow]:
        return self._fetch_all(LIST_POLICIES_SQL)

    def list_active_policies(self, *, agent_profile_id: str | None = None) -> list[PolicyRow]:
        if agent_profile_id is None:
            return self._fetch_all(LIST_ACTIVE_POLICIES_SQL)
        return self._fetch_all(LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL, (agent_profile_id,))

    def create_tool(
        self,
        *,
        tool_key: str,
        name: str,
        description: str,
        version: str,
        metadata_version: str,
        active: bool,
        tags: list[str],
        action_hints: list[str],
        scope_hints: list[str],
        domain_hints: list[str],
        risk_hints: list[str],
        metadata: JsonObject,
    ) -> ToolRow:
        return self._fetch_one(
            "create_tool",
            INSERT_TOOL_SQL,
            (
                tool_key,
                name,
                description,
                version,
                metadata_version,
                active,
                Jsonb(tags),
                Jsonb(action_hints),
                Jsonb(scope_hints),
                Jsonb(domain_hints),
                Jsonb(risk_hints),
                Jsonb(metadata),
            ),
        )

    def get_tool_optional(self, tool_id: UUID) -> ToolRow | None:
        return self._fetch_optional_one(GET_TOOL_SQL, (tool_id,))

    def list_tools(self) -> list[ToolRow]:
        return self._fetch_all(LIST_TOOLS_SQL)

    def list_active_tools(self) -> list[ToolRow]:
        return self._fetch_all(LIST_ACTIVE_TOOLS_SQL)

    def create_approval(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        task_run_id: UUID | None = None,
        task_step_id: UUID | None = None,
        status: str,
        request: JsonObject,
        tool: JsonObject,
        routing: JsonObject,
        routing_trace_id: UUID,
    ) -> ApprovalRow:
        return self._fetch_one(
            "create_approval",
            INSERT_APPROVAL_SQL,
            (
                thread_id,
                tool_id,
                task_run_id,
                task_step_id,
                status,
                Jsonb(request),
                Jsonb(tool),
                Jsonb(routing),
                routing_trace_id,
            ),
        )

    def get_approval_optional(self, approval_id: UUID) -> ApprovalRow | None:
        return self._fetch_optional_one(GET_APPROVAL_SQL, (approval_id,))

    def list_approvals(self) -> list[ApprovalRow]:
        return self._fetch_all(LIST_APPROVALS_SQL)

    def resolve_approval_optional(
        self,
        *,
        approval_id: UUID,
        status: str,
    ) -> ApprovalRow | None:
        return self._fetch_optional_one(
            UPDATE_APPROVAL_RESOLUTION_SQL,
            (status, approval_id),
        )

    def update_approval_task_step_optional(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
    ) -> ApprovalRow | None:
        return self._fetch_optional_one(
            UPDATE_APPROVAL_TASK_STEP_SQL,
            (task_step_id, approval_id),
        )

    def update_approval_task_run_optional(
        self,
        *,
        approval_id: UUID,
        task_run_id: UUID | None,
    ) -> ApprovalRow | None:
        return self._fetch_optional_one(
            UPDATE_APPROVAL_TASK_RUN_SQL,
            (task_run_id, approval_id),
        )

    def create_task(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        status: str,
        request: JsonObject,
        tool: JsonObject,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> TaskRow:
        return self._fetch_one(
            "create_task",
            INSERT_TASK_SQL,
            (
                thread_id,
                tool_id,
                status,
                Jsonb(request),
                Jsonb(tool),
                latest_approval_id,
                latest_execution_id,
            ),
        )

    def get_task_optional(self, task_id: UUID) -> TaskRow | None:
        return self._fetch_optional_one(GET_TASK_SQL, (task_id,))

    def get_task_by_approval_optional(self, approval_id: UUID) -> TaskRow | None:
        return self._fetch_optional_one(GET_TASK_BY_APPROVAL_SQL, (approval_id,))

    def list_tasks(self) -> list[TaskRow]:
        return self._fetch_all(LIST_TASKS_SQL)

    def update_task_status_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        status: str,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STATUS_BY_APPROVAL_SQL,
            (status, approval_id),
        )

    def update_task_execution_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        latest_execution_id: UUID,
        status: str,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL,
            (status, latest_execution_id, approval_id),
        )

    def update_task_status_optional(
        self,
        *,
        task_id: UUID,
        status: str,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STATUS_SQL,
            (status, latest_approval_id, latest_execution_id, task_id),
        )

    def create_gmail_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
    ) -> GmailAccountRow:
        return self._fetch_one(
            "create_gmail_account",
            INSERT_GMAIL_ACCOUNT_SQL,
            (provider_account_id, email_address, display_name, scope),
        )

    def create_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedGmailCredentialRow:
        return self._fetch_one(
            "create_gmail_account_credential",
            INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL,
            (
                gmail_account_id,
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
            ),
        )

    def get_gmail_account_optional(self, gmail_account_id: UUID) -> GmailAccountRow | None:
        return self._fetch_optional_one(GET_GMAIL_ACCOUNT_SQL, (gmail_account_id,))

    def get_gmail_account_credential_optional(
        self,
        gmail_account_id: UUID,
    ) -> ProtectedGmailCredentialRow | None:
        return self._fetch_optional_one(GET_GMAIL_ACCOUNT_CREDENTIAL_SQL, (gmail_account_id,))

    def update_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedGmailCredentialRow:
        return self._fetch_one(
            "update_gmail_account_credential",
            UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL,
            (
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
                gmail_account_id,
            ),
        )

    def get_gmail_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> GmailAccountRow | None:
        return self._fetch_optional_one(
            GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
            (provider_account_id,),
        )

    def list_gmail_accounts(self) -> list[GmailAccountRow]:
        return self._fetch_all(LIST_GMAIL_ACCOUNTS_SQL)

    def create_calendar_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
    ) -> CalendarAccountRow:
        return self._fetch_one(
            "create_calendar_account",
            INSERT_CALENDAR_ACCOUNT_SQL,
            (provider_account_id, email_address, display_name, scope),
        )

    def create_calendar_account_credential(
        self,
        *,
        calendar_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedCalendarCredentialRow:
        return self._fetch_one(
            "create_calendar_account_credential",
            INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
            (
                calendar_account_id,
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
            ),
        )

    def get_calendar_account_optional(self, calendar_account_id: UUID) -> CalendarAccountRow | None:
        return self._fetch_optional_one(GET_CALENDAR_ACCOUNT_SQL, (calendar_account_id,))

    def get_calendar_account_credential_optional(
        self,
        calendar_account_id: UUID,
    ) -> ProtectedCalendarCredentialRow | None:
        return self._fetch_optional_one(
            GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
            (calendar_account_id,),
        )

    def get_calendar_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> CalendarAccountRow | None:
        return self._fetch_optional_one(
            GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
            (provider_account_id,),
        )

    def list_calendar_accounts(self) -> list[CalendarAccountRow]:
        return self._fetch_all(LIST_CALENDAR_ACCOUNTS_SQL)

    def lock_task_workspaces(self, task_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_WORKSPACES_SQL, (str(task_id),))

    def create_task_workspace(
        self,
        *,
        task_id: UUID,
        status: str,
        local_path: str,
    ) -> TaskWorkspaceRow:
        return self._fetch_one(
            "create_task_workspace",
            INSERT_TASK_WORKSPACE_SQL,
            (task_id, status, local_path),
        )

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> TaskWorkspaceRow | None:
        return self._fetch_optional_one(GET_TASK_WORKSPACE_SQL, (task_workspace_id,))

    def get_active_task_workspace_for_task_optional(self, task_id: UUID) -> TaskWorkspaceRow | None:
        return self._fetch_optional_one(GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL, (task_id,))

    def list_task_workspaces(self) -> list[TaskWorkspaceRow]:
        return self._fetch_all(LIST_TASK_WORKSPACES_SQL)

    def lock_task_artifacts(self, task_workspace_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_ARTIFACTS_SQL, (str(task_workspace_id),))

    def create_task_artifact(
        self,
        *,
        task_id: UUID,
        task_workspace_id: UUID,
        status: str,
        ingestion_status: str,
        relative_path: str,
        media_type_hint: str | None,
    ) -> TaskArtifactRow:
        return self._fetch_one(
            "create_task_artifact",
            INSERT_TASK_ARTIFACT_SQL,
            (
                task_id,
                task_workspace_id,
                status,
                ingestion_status,
                relative_path,
                media_type_hint,
            ),
        )

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> TaskArtifactRow | None:
        return self._fetch_optional_one(GET_TASK_ARTIFACT_SQL, (task_artifact_id,))

    def get_task_artifact_by_workspace_relative_path_optional(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> TaskArtifactRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL,
            (task_workspace_id, relative_path),
        )

    def list_task_artifacts(self) -> list[TaskArtifactRow]:
        return self._fetch_all(LIST_TASK_ARTIFACTS_SQL)

    def list_task_artifacts_for_task(self, task_id: UUID) -> list[TaskArtifactRow]:
        return self._fetch_all(LIST_TASK_ARTIFACTS_FOR_TASK_SQL, (task_id,))

    def lock_task_artifact_ingestion(self, task_artifact_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_ARTIFACT_INGESTION_SQL, (str(task_artifact_id),))

    def create_task_artifact_chunk(
        self,
        *,
        task_artifact_id: UUID,
        sequence_no: int,
        char_start: int,
        char_end_exclusive: int,
        text: str,
    ) -> TaskArtifactChunkRow:
        return self._fetch_one(
            "create_task_artifact_chunk",
            INSERT_TASK_ARTIFACT_CHUNK_SQL,
            (task_artifact_id, sequence_no, char_start, char_end_exclusive, text),
        )

    def get_task_artifact_chunk_optional(self, task_artifact_chunk_id: UUID) -> TaskArtifactChunkRow | None:
        return self._fetch_optional_one(GET_TASK_ARTIFACT_CHUNK_SQL, (task_artifact_chunk_id,))

    def list_task_artifact_chunks(self, task_artifact_id: UUID) -> list[TaskArtifactChunkRow]:
        return self._fetch_all(LIST_TASK_ARTIFACT_CHUNKS_SQL, (task_artifact_id,))

    def create_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> TaskArtifactChunkEmbeddingRow:
        return self._fetch_one(
            "create_task_artifact_chunk_embedding",
            INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (task_artifact_chunk_id, embedding_config_id, dimensions, Jsonb(vector)),
        )

    def get_task_artifact_chunk_embedding_optional(
        self,
        task_artifact_chunk_embedding_id: UUID,
    ) -> TaskArtifactChunkEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (task_artifact_chunk_embedding_id,),
        )

    def get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
    ) -> TaskArtifactChunkEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL,
            (task_artifact_chunk_id, embedding_config_id),
        )

    def list_task_artifact_chunk_embeddings_for_chunk(
        self,
        task_artifact_chunk_id: UUID,
    ) -> list[TaskArtifactChunkEmbeddingRow]:
        return self._fetch_all(
            LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL,
            (task_artifact_chunk_id,),
        )

    def list_task_artifact_chunk_embeddings_for_artifact(
        self,
        task_artifact_id: UUID,
    ) -> list[TaskArtifactChunkEmbeddingRow]:
        return self._fetch_all(
            LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL,
            (task_artifact_id,),
        )

    def update_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> TaskArtifactChunkEmbeddingRow:
        return self._fetch_one(
            "update_task_artifact_chunk_embedding",
            UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (dimensions, Jsonb(vector), task_artifact_chunk_embedding_id),
        )

    def update_task_artifact_ingestion_status(
        self,
        *,
        task_artifact_id: UUID,
        ingestion_status: str,
    ) -> TaskArtifactRow:
        return self._fetch_one(
            "update_task_artifact_ingestion_status",
            UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL,
            (ingestion_status, task_artifact_id),
        )

    def lock_task_steps(self, task_id: UUID) -> None:
        self._acquire_advisory_lock(LOCK_TASK_STEPS_SQL, task_id)

    def create_task_step(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        parent_step_id: UUID | None = None,
        source_approval_id: UUID | None = None,
        source_execution_id: UUID | None = None,
        kind: str,
        status: str,
        request: JsonObject,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow:
        return self._fetch_one_with_lock(
            operation_name="create_task_step",
            lock_query=LOCK_TASK_STEPS_SQL,
            lock_key=task_id,
            query=INSERT_TASK_STEP_SQL,
            params=(
                task_id,
                sequence_no,
                parent_step_id,
                source_approval_id,
                source_execution_id,
                kind,
                status,
                Jsonb(request),
                Jsonb(outcome),
                trace_id,
                trace_kind,
            ),
        )

    def get_task_step_optional(self, task_step_id: UUID) -> TaskStepRow | None:
        return self._fetch_optional_one(GET_TASK_STEP_SQL, (task_step_id,))

    def get_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
            (task_id, sequence_no),
        )

    def list_task_steps_for_task(self, task_id: UUID) -> list[TaskStepRow]:
        return self._fetch_all(LIST_TASK_STEPS_FOR_TASK_SQL, (task_id,))

    def update_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        status: str,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
            (
                status,
                Jsonb(outcome),
                trace_id,
                trace_kind,
                task_id,
                sequence_no,
            ),
        )

    def update_task_step_optional(
        self,
        *,
        task_step_id: UUID,
        status: str,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STEP_SQL,
            (
                status,
                Jsonb(outcome),
                trace_id,
                trace_kind,
                task_step_id,
            ),
        )

    def lock_task_runs(self, task_id: UUID) -> None:
        self._acquire_advisory_lock(LOCK_TASK_RUNS_SQL, task_id)

    def create_task_run(
        self,
        *,
        task_id: UUID,
        status: str,
        checkpoint: JsonObject,
        tick_count: int,
        step_count: int,
        max_ticks: int,
        retry_count: int,
        retry_cap: int,
        retry_posture: str,
        failure_class: str | None,
        stop_reason: str | None,
    ) -> TaskRunRow:
        return self._fetch_one(
            "create_task_run",
            INSERT_TASK_RUN_SQL,
            (
                task_id,
                status,
                Jsonb(checkpoint),
                tick_count,
                step_count,
                max_ticks,
                retry_count,
                retry_cap,
                retry_posture,
                failure_class,
                stop_reason,
            ),
        )

    def get_task_run_optional(self, task_run_id: UUID) -> TaskRunRow | None:
        return self._fetch_optional_one(GET_TASK_RUN_SQL, (task_run_id,))

    def list_task_runs_for_task(self, task_id: UUID) -> list[TaskRunRow]:
        return self._fetch_all(LIST_TASK_RUNS_FOR_TASK_SQL, (task_id,))

    def update_task_run_optional(
        self,
        *,
        task_run_id: UUID,
        status: str,
        checkpoint: JsonObject,
        tick_count: int,
        step_count: int,
        retry_count: int,
        retry_cap: int,
        retry_posture: str,
        failure_class: str | None,
        stop_reason: str | None,
    ) -> TaskRunRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_RUN_SQL,
            (
                status,
                Jsonb(checkpoint),
                tick_count,
                step_count,
                retry_count,
                retry_cap,
                retry_posture,
                failure_class,
                stop_reason,
                task_run_id,
            ),
        )

    def acquire_next_task_run_optional(self) -> TaskRunRow | None:
        return self._fetch_optional_one(ACQUIRE_NEXT_TASK_RUN_SQL)

    def create_tool_execution(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
        thread_id: UUID,
        tool_id: UUID,
        trace_id: UUID,
        request_event_id: UUID | None,
        result_event_id: UUID | None,
        status: str,
        handler_key: str | None,
        request: JsonObject,
        tool: JsonObject,
        result: JsonObject,
        task_run_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ToolExecutionRow:
        return self._fetch_one(
            "create_tool_execution",
            INSERT_TOOL_EXECUTION_SQL,
            (
                approval_id,
                task_run_id,
                task_step_id,
                thread_id,
                tool_id,
                trace_id,
                request_event_id,
                result_event_id,
                status,
                handler_key,
                idempotency_key,
                Jsonb(request),
                Jsonb(tool),
                Jsonb(result),
            ),
        )

    def get_tool_execution_optional(self, execution_id: UUID) -> ToolExecutionRow | None:
        return self._fetch_optional_one(GET_TOOL_EXECUTION_SQL, (execution_id,))

    def list_tool_executions(self) -> list[ToolExecutionRow]:
        return self._fetch_all(LIST_TOOL_EXECUTIONS_SQL)

    def get_tool_execution_by_idempotency_optional(
        self,
        *,
        task_run_id: UUID,
        approval_id: UUID,
        idempotency_key: str,
    ) -> ToolExecutionRow | None:
        return self._fetch_optional_one(
            GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL,
            (task_run_id, approval_id, idempotency_key),
        )

    def create_execution_budget(
        self,
        *,
        budget_id: UUID | None = None,
        agent_profile_id: str | None = None,
        tool_key: str | None,
        domain_hint: str | None,
        max_completed_executions: int,
        rolling_window_seconds: int | None = None,
        supersedes_budget_id: UUID | None = None,
    ) -> ExecutionBudgetRow:
        return self._fetch_one(
            "create_execution_budget",
            INSERT_EXECUTION_BUDGET_SQL,
            (
                budget_id,
                agent_profile_id,
                tool_key,
                domain_hint,
                max_completed_executions,
                rolling_window_seconds,
                supersedes_budget_id,
            ),
        )

    def get_execution_budget_optional(self, execution_budget_id: UUID) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(GET_EXECUTION_BUDGET_SQL, (execution_budget_id,))

    def list_execution_budgets(self) -> list[ExecutionBudgetRow]:
        return self._fetch_all(LIST_EXECUTION_BUDGETS_SQL)

    def deactivate_execution_budget_optional(
        self,
        execution_budget_id: UUID,
    ) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(DEACTIVATE_EXECUTION_BUDGET_SQL, (execution_budget_id,))

    def supersede_execution_budget_optional(
        self,
        *,
        execution_budget_id: UUID,
        superseded_by_budget_id: UUID,
    ) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(
            SUPERSEDE_EXECUTION_BUDGET_SQL,
            (
                superseded_by_budget_id,
                execution_budget_id,
            ),
        )

    def update_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(UPDATE_EVENT_ERROR)

    def delete_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(DELETE_EVENT_ERROR)

    def update_trace_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(UPDATE_TRACE_EVENT_ERROR)

    def delete_trace_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(DELETE_TRACE_EVENT_ERROR)
