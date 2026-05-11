from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping
from uuid import uuid4

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


AGENT_TYPES = (
    "personal_assistant",
    "coding_agent",
    "research_agent",
    "workflow_agent",
    "unknown",
)

PERMISSION_PROFILES = (
    "read_only_agent",
    "project_scoped_agent",
    "trusted_local_agent",
    "memory_proposal_agent",
    "admin_agent",
)

POLICY_DECISIONS = ("allowed", "allowed_with_filtering", "requires_review", "blocked")

RESTRICTED_DOMAINS = frozenset({"family", "health", "spiritual", "legal", "financial"})
RESTRICTED_SENSITIVITY = frozenset({"confidential", "highly_sensitive", "sacred", "regulated"})
ALL_SENSITIVITY = ("public", "internal", "private", "confidential", "highly_sensitive", "sacred", "regulated", "unknown")
DEFAULT_AGENT_SENSITIVITY = ("public", "internal", "private", "unknown")

READ_ACTIONS = {
    "context_pack.request",
    "project.dashboard",
    "open_loop.lookup",
    "recent_decisions.lookup",
    "recent_changes.lookup",
    "connections.find",
    "contradictions.find",
    "review_items.lookup",
    "artifact.lookup",
    "scheduler.status",
}

WRITE_ACTIONS = {
    "source.capture",
    "queue_task.create",
    "artifact.generate",
    "memory.propose",
    "open_loop.create",
    "open_loop.update",
    "artifact.review",
    "scheduler.run_now",
    "scheduler.run_due",
    "scheduler.pause",
    "scheduler.resume",
    "scheduler.configure",
}


class AgentIdentityValidationError(ValueError):
    """Raised when an agent identity payload is malformed."""


class AgentPolicyBlockedError(PermissionError):
    """Raised when a vNext agent policy blocks an operation."""

    def __init__(self, decision: "PolicyDecision") -> None:
        super().__init__("agent policy blocked this action")
        self.decision = decision


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    agent_id: str
    agent_type: str = "unknown"
    agent_run_id: str | None = None
    task_id: str | None = None
    project_scope: tuple[str, ...] = ()
    permission_profile: str = "read_only_agent"

    @property
    def actor_type(self) -> str:
        return "agent"

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AgentIdentity | None":
        nested = payload.get("agent_identity")
        source: Mapping[str, object]
        if isinstance(nested, Mapping):
            source = nested
        else:
            source = payload

        agent_id = _optional_text(source.get("agent_id"))
        if agent_id is None:
            return None

        agent_type = _optional_text(source.get("agent_type")) or _default_agent_type(agent_id)
        if agent_type not in AGENT_TYPES:
            raise AgentIdentityValidationError(f"agent_type must be one of {', '.join(AGENT_TYPES)}")

        permission_profile = _optional_text(source.get("permission_profile")) or _default_permission_profile(agent_id)
        if permission_profile not in PERMISSION_PROFILES:
            raise AgentIdentityValidationError(
                f"permission_profile must be one of {', '.join(PERMISSION_PROFILES)}"
            )

        return cls(
            agent_id=agent_id,
            agent_type=agent_type,
            agent_run_id=_optional_text(source.get("agent_run_id")),
            task_id=_optional_text(source.get("task_id")),
            project_scope=tuple(_string_list(source.get("project_scope"))),
            permission_profile=permission_profile,
        )

    def to_record(self) -> JsonObject:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "agent_run_id": self.agent_run_id,
            "task_id": self.task_id,
            "project_scope": list(self.project_scope),
            "permission_profile": self.permission_profile,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    decision: str
    action: str
    permission_profile: str
    reasons: tuple[str, ...] = ()
    requested_domains: tuple[str, ...] = ()
    effective_domains: tuple[str, ...] = ()
    requested_sensitivity_allowed: tuple[str, ...] = DEFAULT_AGENT_SENSITIVITY
    effective_sensitivity_allowed: tuple[str, ...] = DEFAULT_AGENT_SENSITIVITY
    review_required: bool = False
    trace_id: str = ""
    workflow_type: str | None = None

    def to_record(self) -> JsonObject:
        return {
            "decision": self.decision,
            "action": self.action,
            "permission_profile": self.permission_profile,
            "reasons": list(self.reasons),
            "requested_domains": list(self.requested_domains),
            "effective_domains": list(self.effective_domains),
            "requested_sensitivity_allowed": list(self.requested_sensitivity_allowed),
            "effective_sensitivity_allowed": list(self.effective_sensitivity_allowed),
            "review_required": self.review_required,
            "trace_id": self.trace_id,
            "workflow_type": self.workflow_type,
        }


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AgentIdentityValidationError("agent identity fields must be strings")
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise AgentIdentityValidationError("project_scope must be a list of strings")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise AgentIdentityValidationError("project_scope must be a list of strings")
        normalized = " ".join(item.split()).strip()
        if normalized:
            values.append(normalized)
    return values


def _default_agent_type(agent_id: str) -> str:
    if agent_id.casefold() == "hermes":
        return "personal_assistant"
    if agent_id.casefold() == "openclaw":
        return "coding_agent"
    return "unknown"


def _default_permission_profile(agent_id: str) -> str:
    if agent_id.casefold() == "hermes":
        return "trusted_local_agent"
    if agent_id.casefold() == "openclaw":
        return "project_scoped_agent"
    return "read_only_agent"


def _profile_sensitivity(profile: str) -> tuple[str, ...]:
    if profile == "read_only_agent":
        return ("public", "internal", "unknown")
    if profile == "admin_agent":
        return ALL_SENSITIVITY
    return DEFAULT_AGENT_SENSITIVITY


def _filtered_domains(profile: str, domains: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if profile in {"trusted_local_agent", "admin_agent"}:
        return domains, ()
    blocked = tuple(domain for domain in domains if domain in RESTRICTED_DOMAINS)
    allowed = tuple(domain for domain in domains if domain not in RESTRICTED_DOMAINS)
    return allowed, blocked


def _filtered_sensitivity(profile: str, sensitivity_allowed: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    profile_allowed = set(_profile_sensitivity(profile))
    requested = sensitivity_allowed or _profile_sensitivity(profile)
    allowed = tuple(value for value in requested if value in profile_allowed)
    filtered = tuple(value for value in requested if value not in profile_allowed)
    return allowed or tuple(_profile_sensitivity(profile)), filtered


def evaluate_agent_policy(
    *,
    identity: AgentIdentity | None,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = DEFAULT_AGENT_SENSITIVITY,
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
) -> PolicyDecision:
    trace_id = f"policy-{uuid4()}"
    if identity is None:
        return PolicyDecision(
            decision="allowed",
            action=action,
            permission_profile="user_or_system",
            requested_domains=domains,
            effective_domains=domains,
            requested_sensitivity_allowed=sensitivity_allowed,
            effective_sensitivity_allowed=sensitivity_allowed,
            trace_id=trace_id,
            workflow_type=workflow_type,
        )

    profile = identity.permission_profile
    reasons: list[str] = []
    effective_domains, filtered_domains = _filtered_domains(profile, domains)
    effective_sensitivity, filtered_sensitivity = _filtered_sensitivity(profile, sensitivity_allowed)
    decision = "allowed"
    review_required = False

    if filtered_domains:
        reasons.append("restricted_domain_filtered")
        decision = "allowed_with_filtering"
    if filtered_sensitivity:
        reasons.append("restricted_sensitivity_filtered")
        decision = "allowed_with_filtering"
    if domains and not effective_domains and filtered_domains:
        reasons.append("all_requested_domains_restricted")
        decision = "blocked"

    if profile == "read_only_agent" and action in WRITE_ACTIONS:
        reasons.append("read_only_agent_cannot_write")
        decision = "blocked"

    if action == "memory.propose":
        if profile not in {"project_scoped_agent", "trusted_local_agent", "memory_proposal_agent", "admin_agent"}:
            reasons.append("memory_proposal_permission_required")
            decision = "blocked"
        else:
            review_required = True
            if decision == "allowed":
                decision = "requires_review"

    if action in {"artifact.review", "memory.review"} and profile != "admin_agent":
        reasons.append("human_or_admin_review_required")
        decision = "blocked"

    if write_policy and write_policy != "proposal_only" and profile != "admin_agent":
        reasons.append("no_auto_promotion")
        decision = "blocked"

    if profile == "project_scoped_agent":
        requested_scope = project_scope or identity.project_scope
        if not requested_scope and action in {"context_pack.request", "artifact.generate", "memory.propose", "scheduler.run_now"}:
            reasons.append("project_scope_required")
            decision = "blocked"
        if action == "scheduler.run_now" and workflow_type not in {"connection_report", "contradiction_report", "project_update_scan"}:
            reasons.append("project_scoped_agent_cannot_run_global_workflow")
            decision = "blocked"
        if action == "scheduler.run_due":
            reasons.append("project_scoped_agent_cannot_trigger_global_scheduler")
            decision = "blocked"
        if action in {"scheduler.pause", "scheduler.resume", "scheduler.configure"}:
            reasons.append("project_scoped_agent_cannot_control_global_scheduler")
            decision = "blocked"

    if action == "scheduler.configure" and profile != "admin_agent":
        reasons.append("admin_agent_required_for_scheduler_configuration")
        decision = "blocked"
    if action in {"scheduler.pause", "scheduler.resume"} and profile not in {"trusted_local_agent", "admin_agent"}:
        reasons.append("trusted_or_admin_agent_required_for_scheduler_control")
        decision = "blocked"
    if action == "scheduler.run_now" and profile not in {"project_scoped_agent", "trusted_local_agent", "admin_agent"}:
        reasons.append("trusted_agent_required_for_scheduler_run")
        decision = "blocked"
    if action == "scheduler.run_due" and profile not in {"trusted_local_agent", "admin_agent"}:
        reasons.append("trusted_or_admin_agent_required_for_scheduler_due_run")
        decision = "blocked"

    return PolicyDecision(
        decision=decision,
        action=action,
        permission_profile=profile,
        reasons=tuple(dict.fromkeys(reasons)),
        requested_domains=domains,
        effective_domains=effective_domains,
        requested_sensitivity_allowed=sensitivity_allowed,
        effective_sensitivity_allowed=effective_sensitivity,
        review_required=review_required or decision == "requires_review",
        trace_id=trace_id,
        workflow_type=workflow_type,
    )


def _event_payload(event: Mapping[str, object]) -> Mapping[str, object]:
    payload = event.get("payload_json")
    if isinstance(payload, Mapping):
        return payload
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        return payload
    return {}


def _policy_decision_from_event(event: Mapping[str, object]) -> Mapping[str, object] | None:
    payload = _event_payload(event)
    decision = payload.get("policy_decision")
    return decision if isinstance(decision, Mapping) else None


def _agent_id_for_event(event: Mapping[str, object]) -> str:
    actor_id = event.get("actor_id")
    if isinstance(actor_id, str) and actor_id:
        return actor_id
    payload = _event_payload(event)
    identity = payload.get("agent_identity")
    if isinstance(identity, Mapping) and isinstance(identity.get("agent_id"), str):
        return str(identity["agent_id"])
    return "unknown"


def _counter_rows(counter: Counter[str], *, key_name: str) -> list[JsonObject]:
    return [
        {key_name: key, "count": count}
        for key, count in counter.most_common()
    ]


def _nested_counter_rows(counter: Mapping[str, Counter[str]], *, key_name: str, nested_key: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for key in sorted(counter):
        nested = counter[key]
        rows.append(
            {
                key_name: key,
                "count": sum(nested.values()),
                nested_key: dict(nested.most_common()),
            }
        )
    return sorted(rows, key=lambda row: (-int(row["count"]), str(row[key_name])))


def summarize_agent_policy_telemetry(
    *,
    agent_events: Iterable[Mapping[str, object]],
    artifacts: Iterable[Mapping[str, object]] = (),
    memories: Iterable[Mapping[str, object]] = (),
) -> JsonObject:
    """Build a compact operator summary from append-only agent events."""

    blocks_by_agent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    filters_by_agent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    review_by_agent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    restricted_domains = Counter()
    workflows = Counter()
    workflow_agents: defaultdict[str, Counter[str]] = defaultdict(Counter)
    memory_proposals = Counter()
    artifact_generation = Counter()
    total_policy_decisions = 0
    total_agent_events = 0
    seen_policy_traces: set[str] = set()
    memory_proposal_ids: set[str] = set()
    artifact_generation_ids: set[str] = set()

    for event in agent_events:
        total_agent_events += 1
        agent_id = _agent_id_for_event(event)
        event_type = str(event.get("event_type") or "")
        payload = _event_payload(event)
        decision = _policy_decision_from_event(event)
        if decision is not None:
            trace_id = str(decision.get("trace_id") or event.get("trace_id") or "")
            if trace_id and trace_id in seen_policy_traces:
                decision = None
            elif trace_id:
                seen_policy_traces.add(trace_id)
        if decision is not None:
            total_policy_decisions += 1
            action = str(decision.get("action") or "unknown")
            decision_value = str(decision.get("decision") or "")
            if decision_value == "blocked":
                blocks_by_agent[agent_id][action] += 1
            if decision_value == "allowed_with_filtering":
                filters_by_agent[agent_id][action] += 1
            if decision.get("review_required") is True or decision_value == "requires_review":
                review_by_agent[agent_id][action] += 1
            requested_domains = decision.get("requested_domains")
            effective_domains = set(decision.get("effective_domains") or []) if isinstance(decision.get("effective_domains"), list) else set()
            if isinstance(requested_domains, list):
                for domain in requested_domains:
                    if isinstance(domain, str) and domain not in effective_domains:
                        restricted_domains[domain] += 1
            elif "restricted_domain_filtered" in set(decision.get("reasons") or []):
                restricted_domains["restricted_domain_filtered"] += 1
            workflow_type = decision.get("workflow_type")
            if action == "scheduler.run_now" and isinstance(workflow_type, str) and workflow_type:
                workflows[workflow_type] += 1
                workflow_agents[workflow_type][agent_id] += 1

        if event_type == "agent.memory_proposed":
            if isinstance(event.get("target_id"), str):
                memory_proposal_ids.add(str(event["target_id"]))
            memory_proposals[agent_id] += 1
        if event_type in {"agent.artifact_generated", "artifact.generated"}:
            if isinstance(event.get("target_id"), str):
                artifact_generation_ids.add(str(event["target_id"]))
            artifact_generation[agent_id] += 1
        if event_type.startswith("scheduler.") and agent_id != "unknown":
            workflow_type = payload.get("workflow_type")
            if isinstance(workflow_type, str) and workflow_type:
                workflows[workflow_type] += 1
                workflow_agents[workflow_type][agent_id] += 1

    for memory in memories:
        metadata = memory.get("metadata_json")
        memory_id = str(memory.get("id")) if memory.get("id") is not None else ""
        if (
            isinstance(metadata, Mapping)
            and isinstance(metadata.get("agent_id"), str)
            and memory_id not in memory_proposal_ids
        ):
            memory_proposals[str(metadata["agent_id"])] += 1

    for artifact in artifacts:
        metadata = artifact.get("metadata_json")
        artifact_id = str(artifact.get("id")) if artifact.get("id") is not None else ""
        if isinstance(metadata, Mapping) and metadata.get("generated_by") == "agent" and artifact_id not in artifact_generation_ids:
            agent_id = metadata.get("agent_id")
            artifact_generation[str(agent_id) if isinstance(agent_id, str) and agent_id else "unknown"] += 1

    return {
        "total_agent_events": total_agent_events,
        "total_policy_decisions": total_policy_decisions,
        "policy_blocks_by_agent": _nested_counter_rows(blocks_by_agent, key_name="agent_id", nested_key="actions"),
        "policy_filters_by_agent": _nested_counter_rows(filters_by_agent, key_name="agent_id", nested_key="actions"),
        "requires_review_by_agent": _nested_counter_rows(review_by_agent, key_name="agent_id", nested_key="actions"),
        "restricted_domains_requested": _counter_rows(restricted_domains, key_name="domain"),
        "workflows_triggered_by_agents": [
            {
                "workflow_type": workflow_type,
                "count": count,
                "agents": dict(workflow_agents[workflow_type].most_common()),
            }
            for workflow_type, count in workflows.most_common()
        ],
        "memory_proposals_by_agent": _counter_rows(memory_proposals, key_name="agent_id"),
        "artifact_generation_by_agent": _counter_rows(artifact_generation, key_name="agent_id"),
    }


def ensure_policy_allowed(decision: PolicyDecision) -> None:
    if decision.decision == "blocked":
        raise AgentPolicyBlockedError(decision)


def append_policy_events(
    store,
    *,
    identity: AgentIdentity | None,
    decision: PolicyDecision,
    target_type: str | None = None,
    target_id: str | None = None,
) -> None:
    if identity is None:
        return
    payload = {
        "agent_identity": identity.to_record(),
        "policy_decision": decision.to_record(),
    }
    append_event(
        store,
        event_type="policy.decision",
        actor_type=identity.actor_type,
        actor_id=identity.agent_id,
        target_type=target_type,
        target_id=target_id,
        trace_id=decision.trace_id,
        run_id=identity.agent_run_id,
        payload=payload,
    )
    if decision.decision == "blocked":
        append_event(
            store,
            event_type="agent.policy_blocked",
            actor_type=identity.actor_type,
            actor_id=identity.agent_id,
            target_type=target_type,
            target_id=target_id,
            trace_id=decision.trace_id,
            run_id=identity.agent_run_id,
            payload=payload,
        )
    elif decision.decision == "allowed_with_filtering":
        append_event(
            store,
            event_type="agent.policy_filtered",
            actor_type=identity.actor_type,
            actor_id=identity.agent_id,
            target_type=target_type,
            target_id=target_id,
            trace_id=decision.trace_id,
            run_id=identity.agent_run_id,
            payload=payload,
        )


def agent_metadata(identity: AgentIdentity | None, decision: PolicyDecision | None = None) -> JsonObject:
    metadata: JsonObject = {}
    if identity is not None:
        metadata["generated_by"] = "agent"
        metadata["agent_id"] = identity.agent_id
        metadata["agent_run_id"] = identity.agent_run_id
        metadata["agent_identity"] = identity.to_record()
    if decision is not None:
        metadata["policy_decision"] = decision.to_record()
        metadata["review_required"] = decision.review_required
    return metadata


__all__ = [
    "AGENT_TYPES",
    "PERMISSION_PROFILES",
    "POLICY_DECISIONS",
    "AgentIdentity",
    "AgentIdentityValidationError",
    "AgentPolicyBlockedError",
    "PolicyDecision",
    "agent_metadata",
    "append_policy_events",
    "ensure_policy_allowed",
    "evaluate_agent_policy",
    "summarize_agent_policy_telemetry",
]
