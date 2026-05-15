from __future__ import annotations

from alicebot_api.vnext_agent_control import AgentIdentity
from alicebot_api.vnext_memory_commit import MemoryCommitRequest, evaluate_memory_commit_policy


def _identity(permission_profile: str, *, project_scope: tuple[str, ...] = ()) -> AgentIdentity:
    return AgentIdentity(
        agent_id="hermes" if permission_profile != "project_scoped_agent" else "openclaw",
        agent_type="personal_assistant",
        permission_profile=permission_profile,
        project_scope=project_scope,
    )


def _request(**overrides: object) -> MemoryCommitRequest:
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Coffee preference",
        "canonical_text": "Sam prefers coffee before noon.",
        "domain": "personal",
        "sensitivity": "private",
        "confidence": 0.95,
    }
    payload.update(overrides)
    return MemoryCommitRequest(**payload)  # type: ignore[arg-type]


def test_trusted_explicit_direct_memory_auto_commits() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="professional", sensitivity="internal"),
    )

    assert decision.write_mode == "commit"
    assert decision.status == "committed"
    assert decision.requires_confirmation is False
    assert decision.requires_dashboard_review is False


def test_sensitive_memory_requires_inline_confirmation() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="health", sensitivity="confidential"),
    )

    assert decision.write_mode == "confirm_inline"
    assert decision.status == "confirmation_required"
    assert "sensitive_memory_requires_confirmation" in decision.reasons


def test_external_source_requires_dashboard_review() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(source_type="browser_clip"),
    )

    assert decision.write_mode == "propose_review"
    assert decision.status == "review_required"
    assert "external_source_requires_review" in decision.reasons


def test_read_only_agent_is_rejected() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("read_only_agent"),
        request=_request(domain="professional", sensitivity="internal"),
    )

    assert decision.write_mode == "reject"
    assert decision.status == "rejected"
    assert "read_only_agent_cannot_write" in decision.reasons


def test_project_scoped_agent_can_commit_project_memory_in_scope() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("project_scoped_agent", project_scope=("Alice",)),
        request=_request(domain="project", sensitivity="private", project_scope=("Alice",)),
    )

    assert decision.write_mode == "commit"
    assert decision.status == "committed"


def test_project_scoped_agent_rejects_non_project_memory() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("project_scoped_agent", project_scope=("Alice",)),
        request=_request(domain="family", sensitivity="private", project_scope=("Alice",)),
    )

    assert decision.write_mode == "reject"
    assert "project_scoped_agent_domain_out_of_scope" in decision.reasons


def test_contradiction_requires_inline_confirmation() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="professional", sensitivity="internal", contradiction_refs=("memory-old",)),
    )

    assert decision.write_mode == "confirm_inline"
    assert "contradiction_requires_confirmation" in decision.reasons
