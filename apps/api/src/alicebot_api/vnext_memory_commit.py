from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Mapping
from uuid import UUID, uuid4

from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    PolicyDecision,
    agent_metadata,
    append_policy_events,
    evaluate_agent_policy,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_store import PostgresVNextStore, VNextRow


MEMORY_COMMIT_WRITE_MODES = ("commit", "confirm_inline", "propose_review", "reject")
MEMORY_COMMIT_STATUSES = ("committed", "confirmation_required", "review_required", "rejected")
TRUSTED_COMMIT_PROFILES = {"trusted_local_agent", "admin_agent"}
PROJECT_COMMIT_PROFILES = {"project_scoped_agent"}
REVIEW_ONLY_PROFILES = {"memory_proposal_agent"}
SENSITIVE_DOMAINS = {"family", "health", "spiritual", "legal", "financial"}
SENSITIVE_LEVELS = {"confidential", "highly_sensitive", "sacred", "regulated"}
DIRECT_TRUSTED_SOURCES = {"direct_user_instruction", "trusted_agent", "local_conversation"}
EXTERNAL_REVIEW_SOURCES = {
    "browser_clip",
    "browser_clipper",
    "csv",
    "docx",
    "email",
    "external",
    "generated_artifact",
    "gmail",
    "pdf",
    "research",
    "screenshot_ocr",
    "telegram",
    "telegram_forward",
    "voice_transcript",
    "web_page",
}
EXPLICIT_MEMORY_INTENTS = {
    "explicit_remember",
    "remember_this",
    "save_this",
    "add_to_memory",
    "commit_memory",
}
SECRET_MARKERS = (
    "sk-",
    "ghp_",
    "xoxb-",
    "akia",
    "api_key",
    "access_token",
    "refresh_token",
    "password=",
    "private key",
)


class VNextMemoryCommitValidationError(ValueError):
    """Raised when an agentic memory commit request is invalid."""


@dataclass(frozen=True, slots=True)
class MemoryCommitPolicyDecision:
    write_mode: str
    status: str
    reason: str
    reasons: tuple[str, ...]
    requires_confirmation: bool
    requires_dashboard_review: bool
    policy_decision: PolicyDecision

    def to_record(self) -> JsonObject:
        return {
            "write_mode": self.write_mode,
            "status": self.status,
            "reason": self.reason,
            "reasons": list(self.reasons),
            "requires_confirmation": self.requires_confirmation,
            "requires_dashboard_review": self.requires_dashboard_review,
            "policy_decision": self.policy_decision.to_record(),
            "trace_id": self.policy_decision.trace_id,
        }


@dataclass(frozen=True, slots=True)
class MemoryCommitRequest:
    user_id: str
    title: str
    canonical_text: str
    memory_type: str = "semantic"
    domain: str = "unknown"
    sensitivity: str = "unknown"
    confidence: float = 0.9
    intent: str = "explicit_remember"
    source_type: str = "direct_user_instruction"
    source_refs: tuple[object, ...] = ()
    conversation_excerpt: str | None = None
    rationale: str | None = None
    idempotency_key: str | None = None
    project_scope: tuple[str, ...] = ()
    contradiction_refs: tuple[str, ...] = ()
    trace_id: str | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_iso(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat().replace("+00:00", "Z")


def _normalized_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise VNextMemoryCommitValidationError(f"{field_name} must be a string")
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        raise VNextMemoryCommitValidationError(f"{field_name} must not be empty")
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise VNextMemoryCommitValidationError("optional text fields must be strings")
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        normalized = " ".join(value.split()).strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, (list, tuple)):
        raise VNextMemoryCommitValidationError("list fields must be arrays of strings")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise VNextMemoryCommitValidationError("list fields must be arrays of strings")
        normalized = " ".join(item.split()).strip()
        if normalized:
            output.append(normalized)
    return tuple(output)


def _object_tuple(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise VNextMemoryCommitValidationError("source_refs must be an array")
    return tuple(value)


def _contains_secret_marker(text: str) -> bool:
    folded = text.casefold()
    return any(marker in folded for marker in SECRET_MARKERS)


def _source_ref_values(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, str):
        if value.strip():
            refs.append(value.strip())
    elif isinstance(value, Mapping):
        for key in ("source_id", "id", "ref", "source_ref"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int)):
                refs.append(str(candidate))
        for nested_key in ("source_ids", "source_refs", "sources"):
            refs.extend(_source_ref_values(value.get(nested_key)))
    elif isinstance(value, (list, tuple)):
        for item in value:
            refs.extend(_source_ref_values(item))
    return refs


def _source_uuid(value: object) -> str | None:
    for ref in _source_ref_values(value):
        normalized = ref.removeprefix("source:")
        try:
            return str(UUID(normalized))
        except ValueError:
            continue
    return None


def _memory_metadata(row: Mapping[str, object] | None) -> dict[str, object]:
    if row is None:
        return {}
    metadata = row.get("metadata_json")
    return dict(metadata) if isinstance(metadata, Mapping) else {}


def _agentic_metadata(row: Mapping[str, object] | None) -> dict[str, object]:
    metadata = _memory_metadata(row)
    agentic = metadata.get("agentic_memory")
    return dict(agentic) if isinstance(agentic, Mapping) else {}


def _append_policy_decision(
    store: PostgresVNextStore,
    *,
    identity: AgentIdentity | None,
    decision: PolicyDecision,
    target_type: str | None = None,
    target_id: str | None = None,
) -> None:
    append_policy_events(store, identity=identity, decision=decision, target_type=target_type, target_id=target_id)


def evaluate_memory_commit_policy(
    *,
    identity: AgentIdentity | None,
    request: MemoryCommitRequest,
    policy_decision: PolicyDecision | None = None,
) -> MemoryCommitPolicyDecision:
    base_decision = policy_decision or evaluate_agent_policy(
        identity=identity,
        action="memory.commit",
        domains=(request.domain,),
        sensitivity_allowed=(request.sensitivity,),
        project_scope=request.project_scope,
    )
    reasons: list[str] = list(base_decision.reasons)
    mode = "commit"
    status = "committed"
    if identity is not None and identity.permission_profile in PROJECT_COMMIT_PROFILES and request.domain != "project":
        reasons.append("project_scoped_agent_domain_out_of_scope")

    if identity is None:
        reasons.append("agent_identity_required")
        mode = "reject"
        status = "rejected"
    elif base_decision.decision == "blocked":
        reasons.append("agent_policy_blocked")
        mode = "reject"
        status = "rejected"
    elif _contains_secret_marker(request.canonical_text):
        reasons.append("unsafe_secret_storage")
        mode = "reject"
        status = "rejected"
    elif request.intent.casefold() not in EXPLICIT_MEMORY_INTENTS:
        reasons.append("explicit_memory_intent_required")
        mode = "propose_review"
        status = "review_required"
    elif request.source_type.casefold() in EXTERNAL_REVIEW_SOURCES:
        reasons.append("external_source_requires_review")
        mode = "propose_review"
        status = "review_required"
    elif len(request.source_refs) > 8:
        reasons.append("bulk_source_refs_require_review")
        mode = "propose_review"
        status = "review_required"
    elif identity.permission_profile in REVIEW_ONLY_PROFILES:
        reasons.append("memory_proposal_agent_review_only")
        mode = "propose_review"
        status = "review_required"
    elif identity.permission_profile in PROJECT_COMMIT_PROFILES:
        if request.domain != "project":
            reasons.append("project_scoped_agent_domain_out_of_scope")
            mode = "reject"
            status = "rejected"
        elif not (request.project_scope or identity.project_scope):
            reasons.append("project_scope_required")
            mode = "reject"
            status = "rejected"
        elif request.confidence < 0.5:
            reasons.append("low_confidence_requires_review")
            mode = "propose_review"
            status = "review_required"
    elif identity.permission_profile not in TRUSTED_COMMIT_PROFILES:
        reasons.append("trusted_or_project_scoped_agent_required")
        mode = "reject"
        status = "rejected"

    if mode == "commit":
        if request.confidence < 0.5:
            reasons.append("low_confidence_requires_review")
            mode = "propose_review"
            status = "review_required"
        elif request.confidence < 0.85:
            reasons.append("medium_confidence_requires_confirmation")
            mode = "confirm_inline"
            status = "confirmation_required"
        elif request.domain in SENSITIVE_DOMAINS or request.sensitivity in SENSITIVE_LEVELS:
            reasons.append("sensitive_memory_requires_confirmation")
            mode = "confirm_inline"
            status = "confirmation_required"
        elif request.contradiction_refs:
            reasons.append("contradiction_requires_confirmation")
            mode = "confirm_inline"
            status = "confirmation_required"
        elif request.source_type.casefold() not in DIRECT_TRUSTED_SOURCES:
            reasons.append("non_direct_source_requires_review")
            mode = "propose_review"
            status = "review_required"

    reason = reasons[-1] if reasons else "explicit_trusted_memory_commit"
    return MemoryCommitPolicyDecision(
        write_mode=mode,
        status=status,
        reason=reason,
        reasons=tuple(dict.fromkeys(reasons)),
        requires_confirmation=mode == "confirm_inline",
        requires_dashboard_review=mode == "propose_review",
        policy_decision=base_decision,
    )


class VNextMemoryCommitService:
    def __init__(self, store: PostgresVNextStore):
        self.store = store

    def evaluate_policy(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
    ) -> MemoryCommitPolicyDecision:
        self._upsert_identity(identity)
        base_decision = evaluate_agent_policy(
            identity=identity,
            action="memory.commit",
            domains=(request.domain,),
            sensitivity_allowed=(request.sensitivity,),
            project_scope=request.project_scope,
        )
        _append_policy_decision(self.store, identity=identity, decision=base_decision)
        return evaluate_memory_commit_policy(identity=identity, request=request, policy_decision=base_decision)

    def commit(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
    ) -> JsonObject:
        existing = self._idempotent_memory(request.idempotency_key)
        if existing is not None:
            agentic = _agentic_metadata(existing)
            decision_record = agentic.get("policy_decision")
            return {
                "status": agentic.get("status") or "committed",
                "write_mode": agentic.get("write_mode") or "commit",
                "memory": existing,
                "idempotent_replay": True,
                "policy_decision": decision_record if isinstance(decision_record, dict) else {},
            }

        decision = self.evaluate_policy(identity=identity, request=request)
        if decision.write_mode == "reject":
            self._append_decision_event(identity=identity, request=request, decision=decision, target_id=None)
            return {
                "status": "rejected",
                "write_mode": "reject",
                "reason": decision.reason,
                "reasons": list(decision.reasons),
                "policy_decision": decision.to_record(),
            }
        if decision.write_mode == "confirm_inline":
            return self._create_confirmation(identity=identity, request=request, decision=decision)
        if decision.write_mode == "propose_review":
            return self._create_review_candidate(identity=identity, request=request, decision=decision)
        return self._create_committed_memory(identity=identity, request=request, decision=decision, confirmed_inline=False)

    def confirm(
        self,
        *,
        identity: AgentIdentity | None,
        confirmation_id: str,
        action: str = "confirm",
        canonical_text: str | None = None,
        rationale: str | None = None,
    ) -> JsonObject:
        normalized_action = action.strip().casefold()
        if normalized_action not in {"confirm", "reject", "edit"}:
            raise VNextMemoryCommitValidationError("confirmation action must be confirm, reject, or edit")
        memory = self._memory_by_confirmation_id(confirmation_id)
        if memory is None:
            raise VNextMemoryCommitValidationError("confirmation was not found")
        metadata = _memory_metadata(memory)
        agentic = _agentic_metadata(memory)
        confirmation = dict(agentic.get("confirmation") if isinstance(agentic.get("confirmation"), Mapping) else {})
        if confirmation.get("status") != "pending":
            raise VNextMemoryCommitValidationError("confirmation is not pending")

        expires_at_raw = confirmation.get("expires_at")
        if isinstance(expires_at_raw, str):
            expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
            if expires_at < _utc_now():
                confirmation["status"] = "expired"
                agentic["confirmation"] = confirmation
                agentic["status"] = "rejected"
                agentic["lifecycle_status"] = "confirmation_expired"
                updated = self.store.update_memory(
                    memory_id=str(memory["id"]),
                    patch={"status": "rejected", "metadata_json": {**metadata, "agentic_memory": agentic}},
                    actor_type="agent" if identity else "user",
                )
                return {"status": "rejected", "write_mode": "reject", "reason": "confirmation_expired", "memory": updated}

        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        previous_text = str(memory.get("canonical_text") or "")
        next_text = _normalized_text(canonical_text, field_name="canonical_text") if canonical_text is not None else previous_text
        now = _utc_iso()
        if normalized_action == "reject":
            confirmation["status"] = "rejected"
            next_status = "rejected"
            response_status = "rejected"
            event_type = "agent.memory_confirmation_rejected"
            revision_type = "rejected"
        else:
            confirmation["status"] = "confirmed"
            next_status = "active"
            response_status = "committed"
            event_type = "agent.memory_confirmed"
            revision_type = "corrected" if normalized_action == "edit" else "promoted"

        agentic["confirmation"] = confirmation
        agentic["status"] = response_status
        agentic["lifecycle_status"] = "inline_confirmed" if next_status == "active" else "confirmation_rejected"
        agentic["confirmed_at"] = now if next_status == "active" else None
        if rationale is not None:
            agentic["confirmation_rationale"] = rationale
        patch: JsonObject = {
            "status": next_status,
            "metadata_json": {**metadata, "agentic_memory": agentic},
            "last_reviewed_at": now,
        }
        if next_status == "active":
            patch.update(
                {
                    "canonical_text": next_text,
                    "summary": next_text[:280],
                    "value": {**(memory.get("value") if isinstance(memory.get("value"), dict) else {}), "text": next_text},
                    "confirmation_status": "confirmed",
                    "last_confirmed_at": now,
                }
            )
        updated = self.store.update_memory(memory_id=str(memory["id"]), patch=patch, actor_type=actor_type)
        self.store.append_revision(
            {
                "memory_id": str(updated["id"]),
                "memory_key": str(updated["memory_key"]),
                "previous_value": memory.get("value"),
                "new_value": updated.get("value"),
                "source_event_ids": updated.get("source_event_ids"),
                "revision_type": revision_type,
                "action": f"agentic_memory_confirm_{normalized_action}",
                "text_before": previous_text,
                "text_after": next_text,
                "reason": rationale or f"Inline memory confirmation {normalized_action}.",
                "actor_type": actor_type,
                "actor_id": actor_id,
                "metadata_json": {"confirmation_id": confirmation_id, "action": normalized_action},
            },
            actor_type=actor_type,
        )
        append_event(
            self.store,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(updated["id"]),
            trace_id=str(agentic.get("trace_id") or ""),
            payload={"confirmation_id": confirmation_id, "action": normalized_action, "status": response_status},
        )
        return {
            "status": response_status,
            "write_mode": "confirm_inline",
            "confirmation_id": confirmation_id,
            "memory": updated,
        }

    def undo(
        self,
        *,
        identity: AgentIdentity | None,
        memory_id: str | None = None,
        reason: str | None = None,
    ) -> JsonObject:
        memory = self.store.get_memory(memory_id) if memory_id else self._latest_agentic_commit(identity)
        if memory is None:
            raise VNextMemoryCommitValidationError("memory was not found")
        return self._transition_memory(
            identity=identity,
            memory=memory,
            lifecycle_status="undone",
            next_status="superseded",
            event_type="agent.memory_undone",
            revision_type="superseded",
            action="agentic_memory_undo",
            reason=reason or "Agentic memory commit undone.",
        )

    def correct(
        self,
        *,
        identity: AgentIdentity | None,
        memory_id: str,
        canonical_text: str,
        reason: str | None = None,
    ) -> JsonObject:
        memory = self.store.get_memory(memory_id)
        if memory is None:
            raise VNextMemoryCommitValidationError("memory was not found")
        next_text = _normalized_text(canonical_text, field_name="canonical_text")
        metadata = _memory_metadata(memory)
        agentic = _agentic_metadata(memory)
        correction = {"corrected_at": _utc_iso(), "reason": reason, "previous_text": memory.get("canonical_text")}
        history = list(agentic.get("corrections") if isinstance(agentic.get("corrections"), list) else [])
        history.append(correction)
        agentic["corrections"] = history
        agentic["lifecycle_status"] = "corrected"
        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        updated = self.store.update_memory(
            memory_id=str(memory["id"]),
            patch={
                "status": "active",
                "canonical_text": next_text,
                "summary": next_text[:280],
                "value": {**(memory.get("value") if isinstance(memory.get("value"), dict) else {}), "text": next_text},
                "metadata_json": {**metadata, "agentic_memory": agentic},
            },
            actor_type=actor_type,
        )
        self.store.append_revision(
            {
                "memory_id": str(updated["id"]),
                "memory_key": str(updated["memory_key"]),
                "previous_value": memory.get("value"),
                "new_value": updated.get("value"),
                "source_event_ids": updated.get("source_event_ids"),
                "revision_type": "corrected",
                "action": "agentic_memory_correct",
                "text_before": str(memory.get("canonical_text") or ""),
                "text_after": next_text,
                "reason": reason or "Agentic memory correction.",
                "actor_type": actor_type,
                "actor_id": actor_id,
                "metadata_json": {"lifecycle_status": "corrected"},
            },
            actor_type=actor_type,
        )
        append_event(
            self.store,
            event_type="agent.memory_corrected",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(updated["id"]),
            payload={"lifecycle_status": "corrected"},
        )
        return {"status": "committed", "write_mode": "commit", "memory": updated}

    def forget(
        self,
        *,
        identity: AgentIdentity | None,
        memory_id: str,
        reason: str | None = None,
    ) -> JsonObject:
        memory = self.store.get_memory(memory_id)
        if memory is None:
            raise VNextMemoryCommitValidationError("memory was not found")
        return self._transition_memory(
            identity=identity,
            memory=memory,
            lifecycle_status="forgotten",
            next_status="superseded",
            event_type="agent.memory_forgotten",
            revision_type="archived",
            action="agentic_memory_forget",
            reason=reason or "Agentic memory forgotten.",
        )

    def recent_commits(self, *, limit: int = 20) -> JsonObject:
        rows = []
        for memory in self.store.list_memories(status=None):
            agentic = _agentic_metadata(memory)
            if agentic.get("kind") == "agentic_memory_commit":
                rows.append(memory)
            if len(rows) >= limit:
                break
        return {"recent_commits": rows, "count": len(rows)}

    def audit(self, *, memory_id: str) -> JsonObject:
        memory = self.store.get_memory(memory_id)
        if memory is None:
            raise VNextMemoryCommitValidationError("memory was not found")
        return {
            "memory": memory,
            "revisions": self.store.list_revisions(memory_id),
            "events": self.store.list_events(target_type="memory", target_id=memory_id),
            "provenance_links": self.store.list_provenance_links(target_type="memory", target_id=memory_id),
        }

    def inline_confirmations(self, *, limit: int = 20) -> list[VNextRow]:
        rows: list[VNextRow] = []
        for memory in self.store.list_memories(status=None):
            agentic = _agentic_metadata(memory)
            confirmation = agentic.get("confirmation")
            if agentic.get("kind") == "agentic_memory_commit" and isinstance(confirmation, Mapping):
                rows.append(memory)
            if len(rows) >= limit:
                break
        return rows

    def _upsert_identity(self, identity: AgentIdentity | None) -> None:
        if identity is None:
            return
        self.store.upsert_agent_identity(
            {
                "agent_id": identity.agent_id,
                "agent_type": identity.agent_type,
                "permission_profile": identity.permission_profile,
                "project_scope_json": list(identity.project_scope),
                "metadata_json": {"last_agent_run_id": identity.agent_run_id, "last_task_id": identity.task_id},
            },
            actor_type="agent",
        )

    def _idempotent_memory(self, idempotency_key: str | None) -> VNextRow | None:
        if idempotency_key is None:
            return None
        for memory in self.store.list_memories(status=None):
            if _agentic_metadata(memory).get("idempotency_key") == idempotency_key:
                return memory
        return None

    def _base_metadata(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
        decision: MemoryCommitPolicyDecision,
        status: str,
        write_mode: str,
        lifecycle_status: str,
        confirmation: JsonObject | None = None,
    ) -> JsonObject:
        agentic: JsonObject = {
            "kind": "agentic_memory_commit",
            "status": status,
            "write_mode": write_mode,
            "lifecycle_status": lifecycle_status,
            "intent": request.intent,
            "source_type": request.source_type,
            "source_refs": json_safe(list(request.source_refs)),
            "conversation_excerpt": request.conversation_excerpt,
            "rationale": request.rationale,
            "idempotency_key": request.idempotency_key,
            "project_scope": list(request.project_scope),
            "contradiction_refs": list(request.contradiction_refs),
            "policy_decision": decision.to_record(),
            "trace_id": request.trace_id or decision.policy_decision.trace_id,
            "agent_identity": identity.to_record() if identity is not None else None,
        }
        if confirmation is not None:
            agentic["confirmation"] = confirmation
        return {
            "agentic_memory": agentic,
            **agent_metadata(identity, decision.policy_decision),
        }

    def _memory_key(self, request: MemoryCommitRequest) -> str:
        suffix = request.idempotency_key or str(uuid4())
        return f"agentic_memory.{request.memory_type}.{suffix}"

    def _create_committed_memory(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
        decision: MemoryCommitPolicyDecision,
        confirmed_inline: bool,
    ) -> JsonObject:
        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        metadata = self._base_metadata(
            identity=identity,
            request=request,
            decision=decision,
            status="committed",
            write_mode="confirm_inline" if confirmed_inline else "commit",
            lifecycle_status="inline_confirmed" if confirmed_inline else "auto_committed",
        )
        now = _utc_iso()
        memory = self.store.create_memory(
            {
                "memory_type": request.memory_type,
                "memory_key": self._memory_key(request),
                "value": {
                    "text": request.canonical_text,
                    "intent": request.intent,
                    "source_refs": json_safe(list(request.source_refs)),
                },
                "status": "active",
                "confirmation_status": "confirmed",
                "confidence": request.confidence,
                "title": request.title,
                "canonical_text": request.canonical_text,
                "summary": request.canonical_text[:280],
                "domain": request.domain,
                "sensitivity": request.sensitivity,
                "last_confirmed_at": now,
                "metadata_json": metadata,
            },
            actor_type=actor_type,
        )
        self._append_revision(
            memory=memory,
            action="agentic_memory_confirmed" if confirmed_inline else "agentic_memory_commit",
            revision_type="promoted" if confirmed_inline else "created",
            reason=request.rationale or "Agentic memory committed from explicit user intent.",
            actor_type=actor_type,
            actor_id=actor_id,
        )
        self._create_provenance_links(memory=memory, request=request, actor_type=actor_type)
        append_event(
            self.store,
            event_type="agent.memory_committed",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory["id"]),
            trace_id=request.trace_id or decision.policy_decision.trace_id,
            run_id=identity.agent_run_id if identity is not None else None,
            payload={
                "write_mode": "confirm_inline" if confirmed_inline else "commit",
                "policy_decision": decision.to_record(),
                "agent_identity": identity.to_record() if identity is not None else None,
            },
        )
        return {
            "status": "committed",
            "write_mode": "confirm_inline" if confirmed_inline else "commit",
            "memory": memory,
            "policy_decision": decision.to_record(),
        }

    def _create_confirmation(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
        decision: MemoryCommitPolicyDecision,
    ) -> JsonObject:
        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        now = _utc_now()
        confirmation_id = f"confirm-{uuid4()}"
        confirmation: JsonObject = {
            "confirmation_id": confirmation_id,
            "proposed_text": request.canonical_text,
            "domain": request.domain,
            "sensitivity": request.sensitivity,
            "policy_reason": decision.reason,
            "agent_id": identity.agent_id if identity is not None else None,
            "created_at": _utc_iso(now),
            "expires_at": _utc_iso(now + timedelta(hours=24)),
            "status": "pending",
        }
        metadata = self._base_metadata(
            identity=identity,
            request=request,
            decision=decision,
            status="confirmation_required",
            write_mode="confirm_inline",
            lifecycle_status="pending_inline_confirmation",
            confirmation=confirmation,
        )
        memory = self.store.create_memory(
            {
                "memory_type": request.memory_type,
                "memory_key": self._memory_key(request),
                "value": {
                    "text": request.canonical_text,
                    "intent": request.intent,
                    "source_refs": json_safe(list(request.source_refs)),
                },
                "status": "needs_review",
                "confirmation_status": "unconfirmed",
                "confidence": request.confidence,
                "title": request.title,
                "canonical_text": request.canonical_text,
                "summary": request.canonical_text[:280],
                "domain": request.domain,
                "sensitivity": request.sensitivity,
                "metadata_json": metadata,
            },
            actor_type=actor_type,
        )
        self._append_revision(
            memory=memory,
            action="agentic_memory_confirmation_required",
            revision_type="created",
            reason=decision.reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        append_event(
            self.store,
            event_type="agent.memory_confirmation_required",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory["id"]),
            trace_id=request.trace_id or decision.policy_decision.trace_id,
            run_id=identity.agent_run_id if identity is not None else None,
            payload={"confirmation": confirmation, "policy_decision": decision.to_record()},
        )
        return {
            "status": "confirmation_required",
            "write_mode": "confirm_inline",
            "confirmation_id": confirmation_id,
            "confirmation": confirmation,
            "memory": memory,
            "policy_decision": decision.to_record(),
        }

    def _create_review_candidate(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
        decision: MemoryCommitPolicyDecision,
    ) -> JsonObject:
        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        metadata = self._base_metadata(
            identity=identity,
            request=request,
            decision=decision,
            status="review_required",
            write_mode="propose_review",
            lifecycle_status="pending_dashboard_review",
        )
        proposal_id = f"agentic-{uuid4()}"
        metadata["proposal_id"] = proposal_id
        metadata["proposal_type"] = "agentic_memory_commit"
        metadata["review_required"] = True
        memory = self.store.create_memory(
            {
                "memory_type": request.memory_type,
                "memory_key": self._memory_key(request),
                "value": {
                    "proposal_type": "agentic_memory_commit",
                    "text": request.canonical_text,
                    "source_refs": json_safe(list(request.source_refs)),
                    "rationale": request.rationale,
                },
                "status": "candidate",
                "confirmation_status": "unconfirmed",
                "confidence": request.confidence,
                "title": request.title,
                "canonical_text": request.canonical_text,
                "summary": request.canonical_text[:280],
                "domain": request.domain,
                "sensitivity": request.sensitivity,
                "metadata_json": metadata,
            },
            actor_type=actor_type,
        )
        self._append_revision(
            memory=memory,
            action="agentic_memory_review_required",
            revision_type="created",
            reason=decision.reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        append_event(
            self.store,
            event_type="agent.memory_review_required",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory["id"]),
            trace_id=request.trace_id or decision.policy_decision.trace_id,
            run_id=identity.agent_run_id if identity is not None else None,
            payload={"proposal_id": proposal_id, "policy_decision": decision.to_record()},
        )
        append_event(
            self.store,
            event_type="review.item_created",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory["id"]),
            trace_id=request.trace_id or decision.policy_decision.trace_id,
            run_id=identity.agent_run_id if identity is not None else None,
            payload={"review_required": True, "proposal_type": "agentic_memory_commit"},
        )
        return {
            "status": "review_required",
            "write_mode": "propose_review",
            "proposal_id": proposal_id,
            "memory": memory,
            "policy_decision": decision.to_record(),
        }

    def _append_decision_event(
        self,
        *,
        identity: AgentIdentity | None,
        request: MemoryCommitRequest,
        decision: MemoryCommitPolicyDecision,
        target_id: str | None,
    ) -> None:
        append_event(
            self.store,
            event_type="agent.memory_commit_rejected",
            actor_type="agent" if identity is not None else "user",
            actor_id=identity.agent_id if identity is not None else None,
            target_type="memory",
            target_id=target_id,
            trace_id=request.trace_id or decision.policy_decision.trace_id,
            run_id=identity.agent_run_id if identity is not None else None,
            payload={"policy_decision": decision.to_record(), "reason": decision.reason},
        )

    def _append_revision(
        self,
        *,
        memory: Mapping[str, object],
        action: str,
        revision_type: str,
        reason: str,
        actor_type: str,
        actor_id: str | None,
    ) -> None:
        self.store.append_revision(
            {
                "memory_id": str(memory["id"]),
                "memory_key": str(memory["memory_key"]),
                "new_value": memory.get("value"),
                "source_event_ids": memory.get("source_event_ids"),
                "revision_type": revision_type,
                "action": action,
                "text_after": str(memory.get("canonical_text") or ""),
                "reason": reason,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "metadata_json": {"agentic_memory": True},
            },
            actor_type=actor_type,
        )

    def _create_provenance_links(self, *, memory: Mapping[str, object], request: MemoryCommitRequest, actor_type: str) -> None:
        seen: set[str] = set()
        for source_ref in request.source_refs:
            source_id = _source_uuid(source_ref)
            if source_id is None or source_id in seen:
                continue
            seen.add(source_id)
            self.store.create_provenance_link(
                {
                    "target_type": "memory",
                    "target_id": str(memory["id"]),
                    "source_id": source_id,
                    "quote": request.conversation_excerpt,
                    "evidence_role": "supports",
                    "confidence": request.confidence,
                },
                actor_type=actor_type,
            )

    def _memory_by_confirmation_id(self, confirmation_id: str) -> VNextRow | None:
        for memory in self.store.list_memories(status=None):
            confirmation = _agentic_metadata(memory).get("confirmation")
            if isinstance(confirmation, Mapping) and confirmation.get("confirmation_id") == confirmation_id:
                return memory
        return None

    def _latest_agentic_commit(self, identity: AgentIdentity | None) -> VNextRow | None:
        for memory in self.store.list_memories(status="active"):
            agentic = _agentic_metadata(memory)
            if agentic.get("kind") != "agentic_memory_commit":
                continue
            if identity is None or agentic.get("agent_id") == identity.agent_id:
                return memory
            nested_identity = agentic.get("agent_identity")
            if isinstance(nested_identity, Mapping) and nested_identity.get("agent_id") == identity.agent_id:
                return memory
        return None

    def _transition_memory(
        self,
        *,
        identity: AgentIdentity | None,
        memory: VNextRow,
        lifecycle_status: str,
        next_status: str,
        event_type: str,
        revision_type: str,
        action: str,
        reason: str,
    ) -> JsonObject:
        metadata = _memory_metadata(memory)
        agentic = _agentic_metadata(memory)
        history = list(agentic.get("lifecycle_history") if isinstance(agentic.get("lifecycle_history"), list) else [])
        history.append({"status": lifecycle_status, "at": _utc_iso(), "reason": reason})
        agentic["lifecycle_status"] = lifecycle_status
        agentic["lifecycle_history"] = history
        actor_type = "agent" if identity is not None else "user"
        actor_id = identity.agent_id if identity is not None else None
        updated = self.store.update_memory(
            memory_id=str(memory["id"]),
            patch={"status": next_status, "metadata_json": {**metadata, "agentic_memory": agentic}},
            actor_type=actor_type,
        )
        self.store.append_revision(
            {
                "memory_id": str(updated["id"]),
                "memory_key": str(updated["memory_key"]),
                "previous_value": memory.get("value"),
                "new_value": updated.get("value"),
                "source_event_ids": updated.get("source_event_ids"),
                "revision_type": revision_type,
                "action": action,
                "text_before": str(memory.get("canonical_text") or ""),
                "text_after": str(updated.get("canonical_text") or ""),
                "reason": reason,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "metadata_json": {"lifecycle_status": lifecycle_status},
            },
            actor_type=actor_type,
        )
        append_event(
            self.store,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(updated["id"]),
            payload={"lifecycle_status": lifecycle_status, "reason": reason},
        )
        return {"status": lifecycle_status, "write_mode": "commit", "memory": updated}


def memory_commit_request_from_payload(payload: Mapping[str, object], *, user_id: object) -> MemoryCommitRequest:
    confidence = payload.get("confidence", 0.9)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise VNextMemoryCommitValidationError("confidence must be a number")
    if confidence < 0.0 or confidence > 1.0:
        raise VNextMemoryCommitValidationError("confidence must be between 0.0 and 1.0")
    return MemoryCommitRequest(
        user_id=str(user_id),
        title=_normalized_text(payload.get("title"), field_name="title"),
        canonical_text=_normalized_text(payload.get("canonical_text"), field_name="canonical_text"),
        memory_type=_normalized_text(payload.get("memory_type", "semantic"), field_name="memory_type"),
        domain=_normalized_text(payload.get("domain", "unknown"), field_name="domain"),
        sensitivity=_normalized_text(payload.get("sensitivity", "unknown"), field_name="sensitivity"),
        confidence=float(confidence),
        intent=_normalized_text(payload.get("intent", "explicit_remember"), field_name="intent"),
        source_type=_normalized_text(payload.get("source_type", "direct_user_instruction"), field_name="source_type"),
        source_refs=_object_tuple(payload.get("source_refs")),
        conversation_excerpt=_optional_text(payload.get("conversation_excerpt")),
        rationale=_optional_text(payload.get("rationale")),
        idempotency_key=_optional_text(payload.get("idempotency_key")),
        project_scope=_string_tuple(payload.get("project_scope")),
        contradiction_refs=_string_tuple(payload.get("contradiction_refs")),
        trace_id=_optional_text(payload.get("trace_id")),
    )


__all__ = [
    "MEMORY_COMMIT_STATUSES",
    "MEMORY_COMMIT_WRITE_MODES",
    "MemoryCommitPolicyDecision",
    "MemoryCommitRequest",
    "VNextMemoryCommitService",
    "VNextMemoryCommitValidationError",
    "evaluate_memory_commit_policy",
    "memory_commit_request_from_payload",
]
