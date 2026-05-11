from __future__ import annotations

import pytest

from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentPolicyBlockedError,
    append_policy_events,
    ensure_policy_allowed,
    evaluate_agent_policy,
)


class EventStore:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event


def test_agent_identity_defaults_known_agents_without_hardcoding_only_them() -> None:
    hermes = AgentIdentity.from_payload({"agent_id": "hermes"})
    openclaw = AgentIdentity.from_payload({"agent_id": "openclaw", "project_scope": ["Alice"]})
    future_agent = AgentIdentity.from_payload({"agent_id": "research-bot", "permission_profile": "memory_proposal_agent"})

    assert hermes is not None
    assert hermes.agent_type == "personal_assistant"
    assert hermes.permission_profile == "trusted_local_agent"
    assert openclaw is not None
    assert openclaw.agent_type == "coding_agent"
    assert openclaw.permission_profile == "project_scoped_agent"
    assert openclaw.project_scope == ("Alice",)
    assert future_agent is not None
    assert future_agent.agent_type == "unknown"
    assert future_agent.permission_profile == "memory_proposal_agent"


def test_policy_filters_or_blocks_restricted_project_scoped_agent_access() -> None:
    openclaw = AgentIdentity.from_payload({"agent_id": "openclaw", "project_scope": ["Alice"]})
    assert openclaw is not None

    filtered = evaluate_agent_policy(
        identity=openclaw,
        action="context_pack.request",
        domains=("project", "health"),
        sensitivity_allowed=("public", "private", "highly_sensitive"),
        project_scope=("Alice",),
    )
    blocked = evaluate_agent_policy(
        identity=openclaw,
        action="context_pack.request",
        domains=("family", "health"),
        sensitivity_allowed=("private",),
        project_scope=("Alice",),
    )

    assert filtered.decision == "allowed_with_filtering"
    assert filtered.effective_domains == ("project",)
    assert filtered.effective_sensitivity_allowed == ("public", "private")
    assert "restricted_domain_filtered" in filtered.reasons
    assert "restricted_sensitivity_filtered" in filtered.reasons
    assert blocked.decision == "blocked"
    assert "all_requested_domains_restricted" in blocked.reasons


def test_policy_requires_review_for_agent_memory_proposals_and_blocks_auto_promotion() -> None:
    agent = AgentIdentity.from_payload(
        {
            "agent_id": "memory-bot",
            "permission_profile": "memory_proposal_agent",
            "project_scope": ["Alice"],
        }
    )
    assert agent is not None

    proposal = evaluate_agent_policy(
        identity=agent,
        action="memory.propose",
        domains=("project",),
        sensitivity_allowed=("private",),
        project_scope=("Alice",),
    )
    auto_promotion = evaluate_agent_policy(
        identity=agent,
        action="memory.propose",
        domains=("project",),
        sensitivity_allowed=("private",),
        project_scope=("Alice",),
        write_policy="trusted_write",
    )

    assert proposal.decision == "requires_review"
    assert proposal.review_required is True
    assert auto_promotion.decision == "blocked"
    assert "no_auto_promotion" in auto_promotion.reasons
    with pytest.raises(AgentPolicyBlockedError):
        ensure_policy_allowed(auto_promotion)


def test_scheduler_policy_distinguishes_project_scoped_trusted_and_admin_agents() -> None:
    openclaw = AgentIdentity.from_payload({"agent_id": "openclaw", "project_scope": ["Alice"]})
    hermes = AgentIdentity.from_payload({"agent_id": "hermes"})
    admin = AgentIdentity.from_payload({"agent_id": "ops", "permission_profile": "admin_agent"})
    assert openclaw is not None and hermes is not None and admin is not None

    project_report = evaluate_agent_policy(
        identity=openclaw,
        action="scheduler.run_now",
        domains=("project",),
        project_scope=("Alice",),
        workflow_type="project_update_scan",
    )
    daily = evaluate_agent_policy(
        identity=openclaw,
        action="scheduler.run_now",
        domains=("project",),
        project_scope=("Alice",),
        workflow_type="daily_brief",
    )
    project_due = evaluate_agent_policy(
        identity=openclaw,
        action="scheduler.run_due",
        domains=("project",),
        project_scope=("Alice",),
    )
    pause = evaluate_agent_policy(identity=hermes, action="scheduler.pause")
    run_due = evaluate_agent_policy(identity=hermes, action="scheduler.run_due")
    configure = evaluate_agent_policy(identity=admin, action="scheduler.configure")

    assert project_report.decision == "allowed"
    assert daily.decision == "blocked"
    assert "project_scoped_agent_cannot_run_global_workflow" in daily.reasons
    assert project_due.decision == "blocked"
    assert "project_scoped_agent_cannot_trigger_global_scheduler" in project_due.reasons
    assert pause.decision == "allowed"
    assert run_due.decision == "allowed"
    assert configure.decision == "allowed"


def test_policy_events_log_decision_and_filtered_or_blocked_outcomes() -> None:
    store = EventStore()
    agent = AgentIdentity.from_payload({"agent_id": "openclaw", "project_scope": ["Alice"]})
    assert agent is not None
    decision = evaluate_agent_policy(
        identity=agent,
        action="context_pack.request",
        domains=("project", "family"),
        project_scope=("Alice",),
    )

    append_policy_events(store, identity=agent, decision=decision, target_type="context_pack", target_id="pack-1")

    event_types = [event["event_type"] for event in store.events]
    assert event_types == ["policy.decision", "agent.policy_filtered"]
    assert store.events[0]["actor_id"] == "openclaw"
    assert store.events[0]["trace_id"] == decision.trace_id
