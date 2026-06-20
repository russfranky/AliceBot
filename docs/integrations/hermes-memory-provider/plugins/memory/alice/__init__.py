"""Alice memory plugin for Hermes MemoryProvider.

This provider connects Hermes's external memory provider interface to Alice's
continuity APIs.

Design goals:
- Keep Hermes built-in MEMORY.md / USER.md active (additive integration).
- Provide deterministic recall and resumption tools.
- Support prefetch for next-turn context without blocking the tool loop.
"""

from __future__ import annotations

import json
import ipaddress
import logging
import os
import hashlib
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = "alice_memory_provider.json"
_DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_DEFAULT_TIMEOUT_SECONDS = 8.0
_DEFAULT_PREFETCH_LIMIT = 5
_DEFAULT_MAX_RECENT_CHANGES = 5
_DEFAULT_MAX_OPEN_LOOPS = 5
_DEFAULT_CAPTURE_CHAR_LIMIT = 3800
_DEFAULT_SESSION_END_FLUSH_TIMEOUT_SECONDS = 5.0
_CAPTURE_DEDUPE_WINDOW_SECONDS = 5.0
_DEFAULT_BRIDGE_MODE = "assist"
_BRIDGE_CAPTURE_MODES = ("manual", "assist", "auto")
_BRIDGE_CONTRACT_VERSION = "bridge_b2"

_RECALL_LIMIT_MIN = 1
_RECALL_LIMIT_MAX = 50

_OPEN_LOOP_LIMIT_MIN = 0
_OPEN_LOOP_LIMIT_MAX = 50

_RECENT_CHANGES_MIN = 0
_RECENT_CHANGES_MAX = 25

_AUTH_USER_HEADER = "X-AliceBot-User-Id"
_BRIDGE_CONFIG_ALIASES: Dict[str, tuple[str, ...]] = {
    "prefetch_recall_limit": ("prefetch_limit",),
    "prefetch_max_recent_changes": ("max_recent_changes",),
    "prefetch_max_open_loops": ("max_open_loops",),
    "prefetch_include_non_promotable_facts": ("include_non_promotable_facts",),
    "sync_turn_capture_enabled": ("auto_capture",),
    "memory_write_capture_enabled": ("mirror_memory_writes",),
    "bridge_mode": ("capture_mode",),
}
_SAFE_TOOL_ERROR_MESSAGES = (
    "internal provider error",
    "provider is not initialized",
    "provider configuration is invalid",
    "Alice API connection failed",
    "Alice API returned an invalid response payload",
)


ALICE_RECALL_TOOL = {
    "name": "alice_recall",
    "description": (
        "Recall continuity records from Alice with deterministic ranking and provenance. "
        "Use for prior decisions, commitments, blockers, and history-backed answers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "limit": {"type": "integer", "description": "Result limit (1-50)."},
        },
        "required": [],
    },
}

ALICE_RESUME_TOOL = {
    "name": "alice_resumption_brief",
    "description": (
        "Build a scoped resumption brief from Alice continuity state with last decision, "
        "open loops, recent changes, and next action."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "max_recent_changes": {
                "type": "integer",
                "description": "Maximum recent changes to include (0-25).",
            },
            "max_open_loops": {
                "type": "integer",
                "description": "Maximum open loops to include (0-25).",
            },
            "include_non_promotable_facts": {
                "type": "boolean",
                "description": "Include non-promotable continuity facts.",
            },
        },
        "required": [],
    },
}

ALICE_OPEN_LOOPS_TOOL = {
    "name": "alice_open_loops",
    "description": (
        "List open loops from Alice continuity grouped and ranked for execution follow-through."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "limit": {"type": "integer", "description": "Result limit (0-50)."},
        },
        "required": [],
    },
}


def _parse_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _parse_int(value: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _parse_float(value: Any, *, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _parse_bridge_mode(value: Any, *, default: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _BRIDGE_CAPTURE_MODES:
            return normalized
    return default


def _bridge_mode_implies_sync_capture(_bridge_mode: str, raw_bridge_mode: Any) -> bool:
    if not isinstance(raw_bridge_mode, str):
        return False
    return raw_bridge_mode.strip().lower() in {"assist", "auto"}


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.endswith("/v0"):
        normalized = normalized[:-3]
    parsed = urllib.parse.urlsplit(normalized)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").strip().lower()
    if scheme not in {"http", "https"}:
        raise ValueError("base_url must start with http:// or https://")
    if parsed.netloc.strip() == "":
        raise ValueError("base_url must include a host")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not include query parameters or fragments")
    if scheme != "https" and not _is_loopback_host(hostname):
        raise ValueError("base_url must use https:// unless host is loopback")
    return urllib.parse.urlunsplit((scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _is_loopback_host(hostname: str) -> bool:
    if hostname == "":
        return False
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _sanitize_tool_exception_message(error: Exception) -> str:
    message = str(error).strip()
    if message == "":
        return "internal provider error"
    for prefix in _SAFE_TOOL_ERROR_MESSAGES:
        if message.startswith(prefix):
            return message
    if message.startswith("Alice API request failed with HTTP status "):
        return message
    return "internal provider error"


def _config_path(hermes_home: str) -> Path:
    return Path(hermes_home) / _CONFIG_FILENAME


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def _resolve_config_value(values: Dict[str, Any], key: str) -> tuple[Any, str]:
    value = values.get(key)
    if value not in (None, ""):
        return value, key
    for legacy_key in _BRIDGE_CONFIG_ALIASES.get(key, ()):
        legacy_value = values.get(legacy_key)
        if legacy_value not in (None, ""):
            return legacy_value, legacy_key
    return None, key


def _default_config() -> Dict[str, Any]:
    bridge_mode_value = _first_non_empty(
        os.environ.get("ALICE_MEMORY_BRIDGE_MODE"),
        os.environ.get("ALICE_MEMORY_CAPTURE_MODE"),
    )
    sync_turn_capture_value = _first_non_empty(
        os.environ.get("ALICE_MEMORY_SYNC_TURN_CAPTURE_ENABLED"),
        os.environ.get("ALICE_MEMORY_AUTO_CAPTURE"),
    )
    config = {
        "base_url": os.environ.get("ALICE_API_BASE_URL", _DEFAULT_BASE_URL),
        "user_id": os.environ.get("ALICE_MEMORY_USER_ID", os.environ.get("ALICEBOT_AUTH_USER_ID", "")),
        "timeout_seconds": _parse_float(
            os.environ.get("ALICE_MEMORY_TIMEOUT_SECONDS"),
            default=_DEFAULT_TIMEOUT_SECONDS,
            min_value=0.5,
            max_value=30.0,
        ),
        "prefetch_recall_limit": _parse_int(
            _first_non_empty(
                os.environ.get("ALICE_MEMORY_PREFETCH_RECALL_LIMIT"),
                os.environ.get("ALICE_MEMORY_PREFETCH_LIMIT"),
            ),
            default=_DEFAULT_PREFETCH_LIMIT,
            min_value=_RECALL_LIMIT_MIN,
            max_value=_RECALL_LIMIT_MAX,
        ),
        "prefetch_max_recent_changes": _parse_int(
            _first_non_empty(
                os.environ.get("ALICE_MEMORY_PREFETCH_MAX_RECENT_CHANGES"),
                os.environ.get("ALICE_MEMORY_MAX_RECENT_CHANGES"),
            ),
            default=_DEFAULT_MAX_RECENT_CHANGES,
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        ),
        "prefetch_max_open_loops": _parse_int(
            _first_non_empty(
                os.environ.get("ALICE_MEMORY_PREFETCH_MAX_OPEN_LOOPS"),
                os.environ.get("ALICE_MEMORY_MAX_OPEN_LOOPS"),
            ),
            default=_DEFAULT_MAX_OPEN_LOOPS,
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        ),
        "prefetch_include_non_promotable_facts": _parse_bool(
            _first_non_empty(
                os.environ.get("ALICE_MEMORY_PREFETCH_INCLUDE_NON_PROMOTABLE"),
                os.environ.get("ALICE_MEMORY_INCLUDE_NON_PROMOTABLE"),
            ),
            default=False,
        ),
        "memory_write_capture_enabled": _parse_bool(
            _first_non_empty(
                os.environ.get("ALICE_MEMORY_MEMORY_WRITE_CAPTURE_ENABLED"),
                os.environ.get("ALICE_MEMORY_MIRROR_WRITES"),
            ),
            default=False,
        ),
        "session_end_flush_timeout_seconds": _parse_float(
            os.environ.get("ALICE_MEMORY_SESSION_END_FLUSH_TIMEOUT_SECONDS"),
            default=_DEFAULT_SESSION_END_FLUSH_TIMEOUT_SECONDS,
            min_value=0.5,
            max_value=30.0,
        ),
    }
    if sync_turn_capture_value is not None:
        config["sync_turn_capture_enabled"] = _parse_bool(
            sync_turn_capture_value,
            default=False,
        )
    if bridge_mode_value is not None:
        config["bridge_mode"] = bridge_mode_value
    return config


def _load_config_with_status(hermes_home: str) -> Dict[str, Any]:
    config = _default_config()
    errors: List[str] = []
    file_legacy_keys: List[str] = []

    path = _config_path(hermes_home)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if value is not None and value != "":
                        config[key] = value
                for canonical_key, legacy_keys in _BRIDGE_CONFIG_ALIASES.items():
                    if raw.get(canonical_key) not in (None, ""):
                        continue
                    for legacy_key in legacy_keys:
                        legacy_value = raw.get(legacy_key)
                        if legacy_value in (None, ""):
                            continue
                        config[canonical_key] = legacy_value
                        file_legacy_keys.append(legacy_key)
                        break
            else:
                errors.append("provider config must be a JSON object")
        except Exception:
            logger.debug("Failed to parse %s", path, exc_info=True)
            errors.append("provider config could not be parsed")

    normalized, validation_errors, legacy_config_keys = _load_config_dict_from_values(config)
    errors.extend(validation_errors)
    return {
        "config": normalized,
        "errors": errors,
        "legacy_config_keys": sorted(set(legacy_config_keys) | set(file_legacy_keys)),
        "ready": len(errors) == 0,
        "config_path": str(path),
    }


def _load_config(hermes_home: str) -> Dict[str, Any]:
    loaded = _load_config_with_status(hermes_home)
    return dict(loaded["config"])


def _validate_uuid(value: str) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class AliceMemoryProvider(MemoryProvider):
    """Hermes external memory provider backed by Alice continuity APIs."""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._session_id: str = ""
        self._hermes_home: str = ""
        self._agent_context: str = "primary"
        self._config_errors: List[str] = []
        self._legacy_config_keys: List[str] = []

        self._prefetch_cache: Dict[str, str] = {}
        self._prefetch_threads: Dict[str, threading.Thread] = {}
        self._prefetch_lock = threading.Lock()

        self._capture_thread: Optional[threading.Thread] = None
        self._capture_queue: List[tuple[str, str]] = []
        self._capture_pending_fingerprints: set[str] = set()
        self._capture_recent_fingerprints: Dict[str, float] = {}
        self._capture_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "alice"

    def is_available(self) -> bool:
        from hermes_constants import get_hermes_home

        status = _load_config_with_status(str(get_hermes_home()))
        return bool(status.get("ready"))

    def initialize(self, session_id: str, **kwargs) -> None:
        from hermes_constants import get_hermes_home

        self._session_id = session_id or ""
        self._hermes_home = str(kwargs.get("hermes_home") or get_hermes_home())
        self._agent_context = str(kwargs.get("agent_context") or "primary")
        loaded = _load_config_with_status(self._hermes_home)
        self._config = dict(loaded["config"])
        self._config_errors = list(loaded["errors"])
        self._legacy_config_keys = list(loaded["legacy_config_keys"])
        with self._capture_lock:
            self._capture_queue = []
            self._capture_pending_fingerprints.clear()
            self._capture_recent_fingerprints.clear()

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "base_url",
                "description": "Alice API base URL",
                "required": True,
                "default": _DEFAULT_BASE_URL,
            },
            {
                "key": "user_id",
                "description": "Alice user UUID used for continuity scope",
                "required": True,
            },
            {
                "key": "timeout_seconds",
                "description": "HTTP timeout for Alice API calls",
                "default": str(_DEFAULT_TIMEOUT_SECONDS),
            },
            {
                "key": "prefetch_recall_limit",
                "description": "Prefetch recall limit for bridge pre-turn hook",
                "default": str(_DEFAULT_PREFETCH_LIMIT),
            },
            {
                "key": "prefetch_max_recent_changes",
                "description": "Prefetch recent changes cap",
                "default": str(_DEFAULT_MAX_RECENT_CHANGES),
            },
            {
                "key": "prefetch_max_open_loops",
                "description": "Prefetch open-loop cap",
                "default": str(_DEFAULT_MAX_OPEN_LOOPS),
            },
            {
                "key": "prefetch_include_non_promotable_facts",
                "description": "Include non-promotable facts in prefetch resumption brief",
                "choices": ["true", "false"],
                "default": "false",
            },
            {
                "key": "sync_turn_capture_enabled",
                "description": "Capture post-turn transcripts via sync_turn lifecycle hook",
                "choices": ["true", "false"],
                "default": "false",
            },
            {
                "key": "memory_write_capture_enabled",
                "description": "Capture built-in MEMORY.md / USER.md writes via memory-write hook",
                "choices": ["true", "false"],
                "default": "false",
            },
            {
                "key": "bridge_mode",
                "description": "Bridge capture operating mode: manual, assist, or auto",
                "choices": list(_BRIDGE_CAPTURE_MODES),
                "default": _DEFAULT_BRIDGE_MODE,
            },
            {
                "key": "session_end_flush_timeout_seconds",
                "description": "Session-end capture flush timeout in seconds",
                "default": str(_DEFAULT_SESSION_END_FLUSH_TIMEOUT_SECONDS),
            },
        ]

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        cfg = _default_config()
        path = _config_path(hermes_home)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for key, value in raw.items():
                        if value is not None and value != "":
                            cfg[key] = value
            except Exception:
                logger.debug("Failed to parse %s before saving config", path, exc_info=True)
        cfg.update(values)
        cfg, errors, _ = _load_config_dict_from_values(cfg)
        if errors:
            raise ValueError("; ".join(errors))
        path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def system_prompt_block(self) -> str:
        return (
            "# Alice Continuity Memory\n"
            "Active as an external Hermes memory provider.\n"
            "Hermes built-in MEMORY.md and USER.md remain active.\n"
            "Use alice_recall for scoped history lookup and alice_resumption_brief "
            "to recover last decision, open loops, and next action."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        key = self._session_key(session_id)

        with self._prefetch_lock:
            cached = self._prefetch_cache.pop(key, "")
        if cached:
            return cached

        return self._build_prefetch_context(query)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if not query:
            return

        key = self._session_key(session_id)
        with self._prefetch_lock:
            existing = self._prefetch_threads.get(key)
            if existing and existing.is_alive():
                return

        def _run_prefetch() -> None:
            context = ""
            try:
                context = self._build_prefetch_context(query)
            except Exception as exc:
                logger.debug("Alice prefetch failed: %s", exc)
            with self._prefetch_lock:
                self._prefetch_cache[key] = context

        thread = threading.Thread(
            target=_run_prefetch,
            daemon=True,
            name=f"alice-prefetch-{key[:8] if key else 'default'}",
        )
        with self._prefetch_lock:
            self._prefetch_threads[key] = thread
        thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        if not self._config.get("sync_turn_capture_enabled", False):
            return
        if self._agent_context != "primary":
            return
        if self._config.get("bridge_mode", _DEFAULT_BRIDGE_MODE) == "manual":
            return

        raw_content = self._build_turn_capture_payload(user_content, assistant_content)
        if not raw_content:
            return

        self._enqueue_capture(kind="sync_turn", raw_content=raw_content)

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        if not self._config.get("memory_write_capture_enabled", False):
            return
        if action not in {"add", "replace"}:
            return
        if not content.strip():
            return

        raw_content = f"Hermes built-in memory update ({target}): {content.strip()}"
        self._enqueue_capture(kind="memory_write", raw_content=raw_content)

    def on_session_end(self, *, session_id: str = "") -> None:
        key = self._session_key(session_id)
        flush_timeout = float(
            self._config.get("session_end_flush_timeout_seconds", _DEFAULT_SESSION_END_FLUSH_TIMEOUT_SECONDS)
        )

        with self._prefetch_lock:
            thread = self._prefetch_threads.pop(key, None)
            self._prefetch_cache.pop(key, None)
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=flush_timeout)
        if not (self._capture_thread and self._capture_thread.is_alive()):
            self._drain_capture_queue(drop_on_error=True)
            with self._capture_lock:
                self._capture_pending_fingerprints.clear()
        with self._capture_lock:
            self._capture_recent_fingerprints.clear()

    def get_status(self, *, hermes_home: str = "") -> Dict[str, Any]:
        selected_home = hermes_home or self._hermes_home
        if not selected_home:
            from hermes_constants import get_hermes_home

            selected_home = str(get_hermes_home())
        loaded = _load_config_with_status(selected_home)
        config = dict(loaded["config"])
        return {
            "provider": self.name,
            "bridge_contract_version": _BRIDGE_CONTRACT_VERSION,
            "ready": bool(loaded["ready"]),
            "errors": list(loaded["errors"]),
            "legacy_config_keys": list(loaded["legacy_config_keys"]),
            "lifecycle_hooks": {
                "prefetch": True,
                "queue_prefetch": True,
                "sync_turn": bool(config.get("sync_turn_capture_enabled", False)),
                "on_session_end": True,
                "bridge_mode": str(config.get("bridge_mode", _DEFAULT_BRIDGE_MODE)),
            },
            "config": config,
            "config_path": loaded["config_path"],
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [ALICE_RECALL_TOOL, ALICE_RESUME_TOOL, ALICE_OPEN_LOOPS_TOOL]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        try:
            if tool_name == "alice_recall":
                payload = self._tool_recall(args)
            elif tool_name == "alice_resumption_brief":
                payload = self._tool_resumption_brief(args)
            elif tool_name == "alice_open_loops":
                payload = self._tool_open_loops(args)
            else:
                return tool_error(f"unknown tool: {tool_name}")
            return json.dumps(payload)
        except Exception as exc:
            logger.debug("Alice provider tool call failed for %s", tool_name, exc_info=True)
            return tool_error(f"{tool_name} failed: {_sanitize_tool_exception_message(exc)}")

    def shutdown(self) -> None:
        with self._prefetch_lock:
            threads = list(self._prefetch_threads.values())
            self._prefetch_threads.clear()
            self._prefetch_cache.clear()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        self.on_session_end(session_id=self._session_id)

    def _session_key(self, session_id: str) -> str:
        return session_id or self._session_id or "default"

    def _tool_recall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["limit"] = _parse_int(
            args.get("limit"),
            default=self._config.get("prefetch_recall_limit", _DEFAULT_PREFETCH_LIMIT),
            min_value=_RECALL_LIMIT_MIN,
            max_value=_RECALL_LIMIT_MAX,
        )
        return self._request_json("GET", "/v0/continuity/recall", params=params)

    def _tool_resumption_brief(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["max_recent_changes"] = _parse_int(
            args.get("max_recent_changes"),
            default=self._config.get("prefetch_max_recent_changes", _DEFAULT_MAX_RECENT_CHANGES),
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        )
        params["max_open_loops"] = _parse_int(
            args.get("max_open_loops"),
            default=self._config.get("prefetch_max_open_loops", _DEFAULT_MAX_OPEN_LOOPS),
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        )
        params["include_non_promotable_facts"] = _parse_bool(
            args.get("include_non_promotable_facts"),
            default=bool(self._config.get("prefetch_include_non_promotable_facts", False)),
        )
        return self._request_json("GET", "/v0/continuity/resumption-brief", params=params)

    def _tool_open_loops(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["limit"] = _parse_int(
            args.get("limit"),
            default=self._config.get("prefetch_max_open_loops", _DEFAULT_MAX_OPEN_LOOPS),
            min_value=_OPEN_LOOP_LIMIT_MIN,
            max_value=_OPEN_LOOP_LIMIT_MAX,
        )
        return self._request_json("GET", "/v0/continuity/open-loops", params=params)

    def _scope_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        for key in ("query", "thread_id", "task_id", "project", "person", "since", "until"):
            value = args.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value not in (None, ""):
                params[key] = value
        return params

    def _build_prefetch_context(self, query: str) -> str:
        params: Dict[str, Any] = {}
        normalized_query = (query or "").strip()
        if normalized_query:
            params["query"] = normalized_query
        params["max_recent_changes"] = self._config.get("prefetch_max_recent_changes", _DEFAULT_MAX_RECENT_CHANGES)
        params["max_open_loops"] = self._config.get("prefetch_max_open_loops", _DEFAULT_MAX_OPEN_LOOPS)
        params["include_non_promotable_facts"] = bool(
            self._config.get("prefetch_include_non_promotable_facts", False)
        )

        payload = self._request_json("GET", "/v0/continuity/resumption-brief", params=params)
        brief = payload.get("brief")
        if not isinstance(brief, dict):
            return ""

        lines: List[str] = ["## Alice Continuity Prefetch"]

        last_decision = _extract_single_title(brief.get("last_decision"))
        if last_decision:
            lines.append(f"- Last decision: {last_decision}")

        next_action = _extract_single_title(brief.get("next_action"))
        if next_action:
            lines.append(f"- Next action: {next_action}")

        open_loop_lines = _extract_titles(brief.get("open_loops"), limit=self._config.get("prefetch_max_open_loops", 3))
        if open_loop_lines:
            lines.append("- Open loops:")
            lines.extend([f"  - {item}" for item in open_loop_lines])

        recent_change_lines = _extract_titles(
            brief.get("recent_changes"),
            limit=self._config.get("prefetch_max_recent_changes", 3),
        )
        if recent_change_lines:
            lines.append("- Recent changes:")
            lines.extend([f"  - {item}" for item in recent_change_lines])

        if len(lines) == 1:
            return ""
        return "\n".join(lines)

    def _capture_fingerprint(self, *, kind: str, raw_content: str) -> str:
        digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        return f"{kind}:{digest}"

    def _prune_recent_capture_fingerprints(self, *, now: float) -> None:
        stale_before = now - _CAPTURE_DEDUPE_WINDOW_SECONDS
        stale_keys = [fingerprint for fingerprint, posted_at in self._capture_recent_fingerprints.items() if posted_at < stale_before]
        for fingerprint in stale_keys:
            self._capture_recent_fingerprints.pop(fingerprint, None)

    def _new_capture_thread(self) -> threading.Thread:
        return threading.Thread(
            target=self._capture_worker,
            daemon=True,
            name="alice-sync-capture",
        )

    def _enqueue_capture(self, *, kind: str, raw_content: str) -> None:
        fingerprint = self._capture_fingerprint(kind=kind, raw_content=raw_content)
        worker_to_start: Optional[threading.Thread] = None
        now = time.monotonic()
        with self._capture_lock:
            self._prune_recent_capture_fingerprints(now=now)
            if fingerprint in self._capture_pending_fingerprints:
                return
            posted_at = self._capture_recent_fingerprints.get(fingerprint)
            if posted_at is not None and now - posted_at <= _CAPTURE_DEDUPE_WINDOW_SECONDS:
                return
            self._capture_pending_fingerprints.add(fingerprint)
            self._capture_queue.append((fingerprint, raw_content))
            if self._capture_thread is None or not self._capture_thread.is_alive():
                worker_to_start = self._new_capture_thread()
                self._capture_thread = worker_to_start

        if worker_to_start is not None:
            worker_to_start.start()

    def _capture_worker(self) -> None:
        try:
            self._drain_capture_queue(drop_on_error=False)
        finally:
            worker_to_start: Optional[threading.Thread] = None
            with self._capture_lock:
                self._capture_thread = None
                if self._capture_queue:
                    worker_to_start = self._new_capture_thread()
                    self._capture_thread = worker_to_start
            if worker_to_start is not None:
                worker_to_start.start()

    def _drain_capture_queue(self, *, drop_on_error: bool) -> None:
        while True:
            with self._capture_lock:
                if not self._capture_queue:
                    return
                fingerprint, raw_content = self._capture_queue[0]

            try:
                self._post_capture(raw_content)
            except Exception as exc:
                logger.debug("Alice capture sync failed: %s", exc)
                if not drop_on_error:
                    return
                with self._capture_lock:
                    if self._capture_queue and self._capture_queue[0][0] == fingerprint:
                        self._capture_queue.pop(0)
                    self._capture_pending_fingerprints.discard(fingerprint)
                continue

            with self._capture_lock:
                if self._capture_queue and self._capture_queue[0][0] == fingerprint:
                    self._capture_queue.pop(0)
                self._capture_pending_fingerprints.discard(fingerprint)
                self._capture_recent_fingerprints[fingerprint] = time.monotonic()

    def _is_sync_turn_payload(self, raw_content: str) -> bool:
        stripped = raw_content.strip()
        return stripped.startswith("User:") or stripped.startswith("Assistant:")

    def _split_turn_capture_payload(self, raw_content: str) -> tuple[str, str]:
        user_text = ""
        assistant_text = ""
        for line in raw_content.splitlines():
            if line.startswith("User: "):
                user_text = line[len("User: ") :].strip()
                continue
            if line.startswith("Assistant: "):
                assistant_text = line[len("Assistant: ") :].strip()
        return user_text, assistant_text

    def _post_sync_turn_capture(self, raw_content: str) -> None:
        user_text, assistant_text = self._split_turn_capture_payload(raw_content)
        mode = _parse_bridge_mode(
            self._config.get("bridge_mode", _DEFAULT_BRIDGE_MODE),
            default=_DEFAULT_BRIDGE_MODE,
        )
        sync_fingerprint = self._capture_fingerprint(kind="sync_turn", raw_content=raw_content)

        candidates_payload = self._request_json(
            "POST",
            "/v0/continuity/captures/candidates",
            payload={
                "user_content": user_text[:_DEFAULT_CAPTURE_CHAR_LIMIT],
                "assistant_content": assistant_text[:_DEFAULT_CAPTURE_CHAR_LIMIT],
                "source_kind": "sync_turn",
            },
        )
        candidates = candidates_payload.get("candidates")
        if not isinstance(candidates, list):
            raise RuntimeError("Alice API returned an invalid response payload")

        self._request_json(
            "POST",
            "/v0/continuity/captures/commit",
            payload={
                "mode": mode,
                "sync_fingerprint": sync_fingerprint,
                "source_kind": "sync_turn",
                "candidates": candidates,
            },
        )

    def _post_capture(self, raw_content: str) -> None:
        if self._is_sync_turn_payload(raw_content):
            mode = _parse_bridge_mode(
                self._config.get("bridge_mode", _DEFAULT_BRIDGE_MODE),
                default=_DEFAULT_BRIDGE_MODE,
            )
            if mode in {"assist", "auto"}:
                try:
                    self._post_sync_turn_capture(raw_content)
                    return
                except RuntimeError as exc:
                    message = str(exc)
                    if "HTTP status 404" not in message and "HTTP status 400" not in message:
                        raise
                    logger.debug("Alice bridge capture endpoints unavailable, falling back to legacy capture path")

        payload = {
            "raw_content": raw_content[:_DEFAULT_CAPTURE_CHAR_LIMIT],
        }
        self._request_json("POST", "/v0/continuity/captures", payload=payload)

    def _build_turn_capture_payload(self, user_content: str, assistant_content: str) -> str:
        user_text = (user_content or "").strip()
        assistant_text = (assistant_content or "").strip()
        if not user_text and not assistant_text:
            return ""

        segments: List[str] = []
        if user_text:
            segments.append(f"User: {user_text}")
        if assistant_text:
            segments.append(f"Assistant: {assistant_text}")

        payload = "\n".join(segments)
        if len(payload) > _DEFAULT_CAPTURE_CHAR_LIMIT:
            payload = payload[:_DEFAULT_CAPTURE_CHAR_LIMIT]
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._config:
            raise RuntimeError("provider is not initialized")

        query = dict(params or {})
        user_id = str(self._config.get("user_id", "")).strip()
        if not _validate_uuid(user_id):
            raise RuntimeError("provider configuration is invalid")

        try:
            base_url = _normalize_base_url(str(self._config.get("base_url", _DEFAULT_BASE_URL)))
        except ValueError as exc:
            raise RuntimeError("provider configuration is invalid") from exc
        encoded = urllib.parse.urlencode(query, doseq=True)
        url = f"{base_url}{path}"
        if encoded:
            url = f"{url}?{encoded}"

        data = None
        headers = {
            "Accept": "application/json",
            _AUTH_USER_HEADER: user_id,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)

        timeout = float(self._config.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
                body = response.read().decode("utf-8", errors="replace")
                if not body:
                    return {}
                decoded = json.loads(body)
                if isinstance(decoded, dict):
                    return decoded
                raise RuntimeError("Alice API returned an invalid response payload")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Alice API request failed with HTTP status {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Alice API connection failed") from exc


def _load_config_dict_from_values(values: Dict[str, Any]) -> tuple[Dict[str, Any], List[str], List[str]]:
    config: Dict[str, Any] = {}
    errors: List[str] = []
    legacy_config_keys: List[str] = []

    base_url_value = values.get("base_url", _DEFAULT_BASE_URL)
    try:
        config["base_url"] = _normalize_base_url(str(base_url_value))
    except ValueError as exc:
        errors.append(f"base_url: {exc}")
        config["base_url"] = _normalize_base_url(_DEFAULT_BASE_URL)

    user_id_value = values.get("user_id", "")
    config["user_id"] = str(user_id_value).strip()
    if not _validate_uuid(config["user_id"]):
        errors.append("user_id must be a valid UUID")

    config["timeout_seconds"] = _parse_float(
        values.get("timeout_seconds"),
        default=_DEFAULT_TIMEOUT_SECONDS,
        min_value=0.5,
        max_value=30.0,
    )

    prefetch_recall_limit_value, prefetch_recall_limit_source = _resolve_config_value(values, "prefetch_recall_limit")
    if prefetch_recall_limit_source != "prefetch_recall_limit":
        legacy_config_keys.append(prefetch_recall_limit_source)
    config["prefetch_recall_limit"] = _parse_int(
        prefetch_recall_limit_value,
        default=_DEFAULT_PREFETCH_LIMIT,
        min_value=_RECALL_LIMIT_MIN,
        max_value=_RECALL_LIMIT_MAX,
    )

    prefetch_recent_changes_value, prefetch_recent_changes_source = _resolve_config_value(
        values,
        "prefetch_max_recent_changes",
    )
    if prefetch_recent_changes_source != "prefetch_max_recent_changes":
        legacy_config_keys.append(prefetch_recent_changes_source)
    config["prefetch_max_recent_changes"] = _parse_int(
        prefetch_recent_changes_value,
        default=_DEFAULT_MAX_RECENT_CHANGES,
        min_value=_RECENT_CHANGES_MIN,
        max_value=_RECENT_CHANGES_MAX,
    )

    prefetch_open_loops_value, prefetch_open_loops_source = _resolve_config_value(values, "prefetch_max_open_loops")
    if prefetch_open_loops_source != "prefetch_max_open_loops":
        legacy_config_keys.append(prefetch_open_loops_source)
    config["prefetch_max_open_loops"] = _parse_int(
        prefetch_open_loops_value,
        default=_DEFAULT_MAX_OPEN_LOOPS,
        min_value=_RECENT_CHANGES_MIN,
        max_value=_RECENT_CHANGES_MAX,
    )

    prefetch_non_promotable_value, prefetch_non_promotable_source = _resolve_config_value(
        values,
        "prefetch_include_non_promotable_facts",
    )
    if prefetch_non_promotable_source != "prefetch_include_non_promotable_facts":
        legacy_config_keys.append(prefetch_non_promotable_source)
    config["prefetch_include_non_promotable_facts"] = _parse_bool(
        prefetch_non_promotable_value,
        default=False,
    )

    bridge_mode_value, bridge_mode_source = _resolve_config_value(values, "bridge_mode")
    if bridge_mode_source != "bridge_mode":
        legacy_config_keys.append(bridge_mode_source)
    config["bridge_mode"] = _parse_bridge_mode(
        bridge_mode_value,
        default=_DEFAULT_BRIDGE_MODE,
    )

    sync_turn_capture_value, sync_turn_capture_source = _resolve_config_value(values, "sync_turn_capture_enabled")
    if sync_turn_capture_source != "sync_turn_capture_enabled":
        legacy_config_keys.append(sync_turn_capture_source)
    config["sync_turn_capture_enabled"] = _parse_bool(
        sync_turn_capture_value,
        default=_bridge_mode_implies_sync_capture(config["bridge_mode"], bridge_mode_value),
    )

    memory_write_capture_value, memory_write_capture_source = _resolve_config_value(
        values,
        "memory_write_capture_enabled",
    )
    if memory_write_capture_source != "memory_write_capture_enabled":
        legacy_config_keys.append(memory_write_capture_source)
    config["memory_write_capture_enabled"] = _parse_bool(
        memory_write_capture_value,
        default=False,
    )

    config["session_end_flush_timeout_seconds"] = _parse_float(
        values.get("session_end_flush_timeout_seconds"),
        default=_DEFAULT_SESSION_END_FLUSH_TIMEOUT_SECONDS,
        min_value=0.5,
        max_value=30.0,
    )

    return config, errors, sorted(set(legacy_config_keys))


def _extract_single_title(section: Any) -> str:
    if not isinstance(section, dict):
        return ""
    item = section.get("item")
    if not isinstance(item, dict):
        return ""
    title = item.get("title")
    if isinstance(title, str):
        return title.strip()
    return ""


def _extract_titles(section: Any, *, limit: int) -> List[str]:
    if not isinstance(section, dict):
        return []
    items = section.get("items")
    if not isinstance(items, list):
        return []

    titles: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str):
            continue
        normalized = title.strip()
        if not normalized:
            continue
        titles.append(normalized)
        if len(titles) >= limit:
            break
    return titles


# Plugin entry point ---------------------------------------------------------

def register(ctx) -> None:
    """Register Alice as a Hermes external memory provider."""

    ctx.register_memory_provider(AliceMemoryProvider())
