from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol
from uuid import uuid4

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_PROJECT_LIMIT = 8
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
PROJECT_UPDATE_ACTIONS = {"accept", "edit", "reject"}
OPEN_LOOP_ACTIONS = {"close", "snooze", "edit", "reopen"}


class VNextProjectValidationError(ValueError):
    """Raised when a vNext project or open-loop operation is invalid."""


class VNextProjectStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_artifact(self, artifact: JsonObject) -> JsonObject: ...

    def get_artifact(self, artifact_id: str) -> JsonObject | None: ...

    def update_artifact_status(self, *, artifact_id: str, status: str) -> JsonObject: ...

    def create_memory(self, memory: JsonObject) -> JsonObject: ...

    def update_memory(self, *, memory_id: str, patch: JsonObject) -> JsonObject: ...

    def append_revision(self, revision: JsonObject) -> JsonObject: ...

    def get_project(self, project_id: str) -> JsonObject | None: ...

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_PROJECT_LIMIT,
    ) -> list[JsonObject]: ...

    def update_project(self, *, project_id: str, patch: JsonObject) -> JsonObject: ...

    def create_open_loop(self, loop: JsonObject) -> JsonObject: ...

    def get_open_loop(self, loop_id: str) -> JsonObject | None: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = DEFAULT_PROJECT_LIMIT,
    ) -> list[JsonObject]: ...

    def update_open_loop(self, *, loop_id: str, patch: JsonObject) -> JsonObject: ...

    def update_open_loop_status(self, *, loop_id: str, status: str, resolution_note: str | None = None) -> JsonObject: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_PROJECT_LIMIT,
    ) -> list[JsonObject]: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_PROJECT_LIMIT,
    ) -> list[JsonObject]: ...

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_PROJECT_LIMIT,
    ) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class ProjectAutomationRequest:
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    project_id: str | None = None
    person_id: str | None = None
    max_items: int = DEFAULT_PROJECT_LIMIT


def _validate_request(request: ProjectAutomationRequest) -> None:
    if request.max_items < 1 or request.max_items > 50:
        raise VNextProjectValidationError("max_items must be between 1 and 50")
    if not request.sensitivity_allowed:
        raise VNextProjectValidationError("sensitivity_allowed must not be empty")


def _text(row: JsonObject) -> str:
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        raw_text = metadata.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            return raw_text
    for key in ("title", "canonical_text", "summary", "current_state", "description", "name"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return str(row.get("id", "item"))


def _title(row: JsonObject) -> str:
    for key in ("title", "name", "canonical_text"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return str(row.get("id", "item"))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "project"


def _highest_sensitivity(rows: list[JsonObject]) -> str:
    rank = {
        "public": 1,
        "internal": 2,
        "unknown": 2,
        "private": 3,
        "confidential": 4,
        "highly_sensitive": 5,
        "sacred": 6,
        "regulated": 6,
    }
    sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
    if not sensitivities:
        return "unknown"
    return max(sensitivities, key=lambda value: rank.get(value, rank["unknown"]))


def _source_ids(rows: list[JsonObject]) -> list[str]:
    return [str(row.get("id")) for row in rows if row.get("id") is not None]


def _detect_project_change(project: JsonObject, sources: list[JsonObject], memories: list[JsonObject]) -> str:
    name = _title(project)
    for row in [*sources, *memories]:
        text = _text(row)
        for line in text.splitlines() or [text]:
            normalized = " ".join(line.split())
            if not normalized:
                continue
            lowered = normalized.casefold()
            if name.casefold() in lowered or str(project.get("slug", "")).casefold() in lowered:
                return normalized[:500]
            if lowered.startswith(("decision:", "change:", "project:", "now:")):
                return normalized[:500]
    return f"{name} has new evidence that should be reviewed before updating project state."


def _open_loop_candidates(source: JsonObject) -> list[JsonObject]:
    candidates: list[JsonObject] = []
    patterns = (
        ("task", re.compile(r"^\s*(?:todo|task)\s*:?\s*(.+)$", re.IGNORECASE)),
        ("follow_up", re.compile(r"^\s*follow up\s*:?\s*(.+)$", re.IGNORECASE)),
        ("waiting_on_person", re.compile(r"^\s*waiting (?:on|for)\s*:?\s*(.+)$", re.IGNORECASE)),
        ("question", re.compile(r"^\s*(?:question|ask)\s*:?\s*(.+)$", re.IGNORECASE)),
        ("decision_needed", re.compile(r"^\s*decision(?: needed)?\s*:?\s*(.+)$", re.IGNORECASE)),
        ("research_gap", re.compile(r"^\s*research\s*:?\s*(.+)$", re.IGNORECASE)),
        ("project_blocker", re.compile(r"^\s*block(?:ed|er)?\s*:?\s*(.+)$", re.IGNORECASE)),
    )
    for line in _text(source).splitlines():
        for loop_type, pattern in patterns:
            match = pattern.match(line)
            if match is None:
                continue
            title = " ".join(match.group(1).split())
            if not title:
                continue
            owner_match = re.search(r"(?:owner|by)\s*:\s*([A-Za-z0-9 _.-]+)", title, re.IGNORECASE)
            owner = " ".join(owner_match.group(1).split()) if owner_match else None
            candidates.append(
                {
                    "title": title[:240],
                    "description": f"Candidate {loop_type} discovered from source {_title(source)}.",
                    "priority": "high" if loop_type == "project_blocker" else "normal",
                    "source_id": source.get("id"),
                    "domain": source.get("domain", "unknown"),
                    "sensitivity": source.get("sensitivity", "unknown"),
                    "metadata_json": {
                        "candidate": True,
                        "loop_type": loop_type,
                        "owner": owner,
                        "source_captured_at": source.get("captured_at"),
                        "discovered_by": "vnext_project_automation",
                    },
                }
            )
    return candidates


def _project_update_markdown(
    *,
    project: JsonObject,
    change: str,
    suggested_current_state: str,
    sources: list[JsonObject],
    memories: list[JsonObject],
) -> str:
    source_lines = [f"- source:{source.get('id')} {_title(source)}" for source in sources] or ["- No sources selected."]
    memory_lines = [f"- memory:{memory.get('id')} {_title(memory)}" for memory in memories] or ["- No memories selected."]
    return "\n".join(
        [
            f"# Project Update Candidate - {_title(project)}",
            "",
            f"Project: {_title(project)}",
            f"Change Detected: {change}",
            "Why It Matters: This may update the project's current state, but it requires review before promotion.",
            "Suggested Updates:",
            "- current_state",
            "",
            f"Suggested Current State: {suggested_current_state}",
            "",
            "Sources:",
            *source_lines,
            "Memories:",
            *memory_lines,
            "Confidence: 0.72",
            "Actions: Accept / Edit / Reject",
            "",
        ]
    )


class VNextProjectService:
    def __init__(self, store: VNextProjectStore) -> None:
        self.store = store

    def generate_project_update_candidate(self, request: ProjectAutomationRequest | None = None) -> JsonObject:
        request = request or ProjectAutomationRequest()
        _validate_request(request)
        project = self._resolve_project(request)
        domains = list(request.domains) if request.domains else None
        sensitivity_allowed = list(request.sensitivity_allowed)
        sources = self.store.search_sources(
            query=str(project.get("name", "")),
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=request.max_items,
        )
        memories = self.store.search_memories(
            query=str(project.get("name", "")),
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=request.max_items,
        )
        change = _detect_project_change(project, sources, memories)
        suggested_current_state = change
        candidate_memory = self.store.create_memory(
            {
                "memory_type": "project_state",
                "memory_key": f"project_update.{_slug(str(project.get('name', 'project')))}.{uuid4()}",
                "value": {"project_id": project.get("id"), "suggested_current_state": suggested_current_state},
                "status": "candidate",
                "confidence": 0.72,
                "canonical_text": suggested_current_state,
                "summary": suggested_current_state,
                "domain": project.get("domain", "project"),
                "sensitivity": _highest_sensitivity([project, *sources, *memories]),
                "metadata_json": {
                    "candidate": True,
                    "workflow": "project_auto_update",
                    "project_id": project.get("id"),
                    "source_ids": _source_ids(sources),
                    "memory_ids": _source_ids(memories),
                },
            }
        )
        artifact = self.store.create_artifact(
            {
                "artifact_type": "project_update",
                "title": f"Project Update Candidate - {_title(project)}",
                "content_markdown": _project_update_markdown(
                    project=project,
                    change=change,
                    suggested_current_state=suggested_current_state,
                    sources=sources,
                    memories=memories,
                ),
                "status": "needs_review",
                "domain": project.get("domain", "project"),
                "sensitivity": _highest_sensitivity([project, *sources, *memories]),
                "generated_by": "vnext_project_auto_updater",
                "metadata_json": {
                    "workflow": "project_auto_update",
                    "project_id": project.get("id"),
                    "candidate_memory_id": candidate_memory.get("id"),
                    "suggested_current_state": suggested_current_state,
                    "source_ids": _source_ids(sources),
                    "memory_ids": _source_ids(memories),
                },
            }
        )
        append_event(
            self.store,
            event_type="project.update_candidate_created",
            actor_type="system",
            target_type="artifact",
            target_id=str(artifact["id"]),
            payload={
                "project_id": project.get("id"),
                "candidate_memory_id": candidate_memory.get("id"),
                "source_ids": _source_ids(sources),
            },
        )
        return artifact

    def extract_open_loops(self, request: ProjectAutomationRequest | None = None) -> list[JsonObject]:
        request = request or ProjectAutomationRequest()
        _validate_request(request)
        domains = list(request.domains) if request.domains else None
        sources = self.store.search_sources(
            query="",
            domains=domains,
            sensitivity_allowed=list(request.sensitivity_allowed),
            limit=request.max_items,
        )
        created: list[JsonObject] = []
        for source in sources:
            for candidate in _open_loop_candidates(source):
                if request.project_id is not None:
                    candidate["project_id"] = request.project_id
                if request.person_id is not None:
                    candidate["person_id"] = request.person_id
                created.append(self.store.create_open_loop(candidate))
        append_event(
            self.store,
            event_type="open_loop.extraction_completed",
            actor_type="system",
            target_type="open_loop",
            payload={"created_count": len(created), "source_ids": _source_ids(sources)},
        )
        return created

    def review_project_update(
        self,
        *,
        artifact_id: str,
        action: str,
        edited_current_state: str | None = None,
    ) -> JsonObject:
        if action not in PROJECT_UPDATE_ACTIONS:
            raise VNextProjectValidationError("project update action must be accept, edit, or reject")
        artifact = self.store.get_artifact(artifact_id)
        if artifact is None:
            raise VNextProjectValidationError(f"artifact {artifact_id} was not found")
        metadata = artifact.get("metadata_json")
        if not isinstance(metadata, dict) or metadata.get("workflow") != "project_auto_update":
            raise VNextProjectValidationError(f"artifact {artifact_id} is not a project update candidate")
        if action == "reject":
            updated_artifact = self.store.update_artifact_status(artifact_id=artifact_id, status="rejected")
            append_event(
                self.store,
                event_type="project.update_candidate_rejected",
                actor_type="system",
                target_type="artifact",
                target_id=artifact_id,
                payload={"project_id": metadata.get("project_id"), "source_ids": metadata.get("source_ids", [])},
            )
            return updated_artifact

        if action == "edit" and (edited_current_state is None or edited_current_state.strip() == ""):
            raise VNextProjectValidationError("edited_current_state is required for edit")
        current_state = edited_current_state.strip() if edited_current_state is not None else str(metadata.get("suggested_current_state", ""))
        project_id = str(metadata.get("project_id"))
        candidate_memory_id = str(metadata.get("candidate_memory_id"))
        self.store.update_project(project_id=project_id, patch={"current_state": current_state})
        self.store.update_memory(memory_id=candidate_memory_id, patch={"status": "active", "canonical_text": current_state})
        self.store.append_revision(
            {
                "memory_id": candidate_memory_id,
                "revision_type": "edited" if action == "edit" else "promoted",
                "action": "project_update_review",
                "text_after": current_state,
                "reason": "Project update candidate accepted by review action.",
                "metadata_json": {"artifact_id": artifact_id, "project_id": project_id, "action": action},
            }
        )
        updated_artifact = self.store.update_artifact_status(artifact_id=artifact_id, status="accepted")
        append_event(
            self.store,
            event_type="project.update_candidate_accepted",
            actor_type="system",
            target_type="project",
            target_id=project_id,
            payload={"artifact_id": artifact_id, "candidate_memory_id": candidate_memory_id, "action": action},
        )
        return updated_artifact

    def review_open_loop(
        self,
        *,
        loop_id: str,
        action: str,
        title: str | None = None,
        description: str | None = None,
        due_at: str | None = None,
        priority: str | None = None,
        resolution_note: str | None = None,
    ) -> JsonObject:
        if action not in OPEN_LOOP_ACTIONS:
            raise VNextProjectValidationError("open loop action must be close, snooze, edit, or reopen")
        if self.store.get_open_loop(loop_id) is None:
            raise VNextProjectValidationError(f"open loop {loop_id} was not found")
        if action == "close":
            return self.store.update_open_loop_status(loop_id=loop_id, status="closed", resolution_note=resolution_note)
        if action == "reopen":
            return self.store.update_open_loop_status(loop_id=loop_id, status="open")
        patch: JsonObject = {}
        if title is not None:
            patch["title"] = title
        if description is not None:
            patch["description"] = description
        if due_at is not None:
            patch["due_at"] = due_at
        if priority is not None:
            patch["priority"] = priority
        if action == "snooze" and due_at is None:
            raise VNextProjectValidationError("due_at is required for snooze")
        if not patch:
            raise VNextProjectValidationError("at least one editable field is required")
        return self.store.update_open_loop(loop_id=loop_id, patch=patch)

    def project_dashboard(self, *, project_id: str, sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED) -> JsonObject:
        project = self.store.get_project(project_id)
        if project is None:
            raise VNextProjectValidationError(f"project {project_id} was not found")
        domain = str(project.get("domain", "unknown"))
        memories = self.store.search_memories(
            query=str(project.get("name", "")),
            domains=[domain],
            sensitivity_allowed=list(sensitivity_allowed),
            limit=DEFAULT_PROJECT_LIMIT,
        )
        open_loops = self.store.list_open_loops(
            status="open",
            domains=[domain],
            sensitivity_allowed=list(sensitivity_allowed),
            project_id=project_id,
            limit=DEFAULT_PROJECT_LIMIT,
        )
        artifacts = self.store.list_artifacts(
            artifact_type=None,
            domains=[domain],
            sensitivity_allowed=list(sensitivity_allowed),
            limit=DEFAULT_PROJECT_LIMIT,
        )
        return {
            "project": project,
            "state": project.get("current_state"),
            "memories": memories,
            "open_loops": open_loops,
            "artifacts": artifacts,
            "counts": {"memories": len(memories), "open_loops": len(open_loops), "artifacts": len(artifacts)},
        }

    def _resolve_project(self, request: ProjectAutomationRequest) -> JsonObject:
        if request.project_id is not None:
            project = self.store.get_project(request.project_id)
            if project is None:
                raise VNextProjectValidationError(f"project {request.project_id} was not found")
            return project
        projects = self.store.list_projects(
            status="active",
            domains=list(request.domains) if request.domains else None,
            sensitivity_allowed=list(request.sensitivity_allowed),
            limit=1,
        )
        if not projects:
            raise VNextProjectValidationError("no active project was found for update candidate generation")
        return projects[0]


__all__ = [
    "ProjectAutomationRequest",
    "VNextProjectService",
    "VNextProjectStore",
    "VNextProjectValidationError",
]
