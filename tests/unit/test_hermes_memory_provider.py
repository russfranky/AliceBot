from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import urllib.error

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = (
    REPO_ROOT
    / "docs"
    / "integrations"
    / "hermes-memory-provider"
    / "plugins"
    / "memory"
    / "alice"
    / "__init__.py"
)


def _load_provider_module(monkeypatch: pytest.MonkeyPatch):
    agent_pkg = types.ModuleType("agent")
    memory_provider_pkg = types.ModuleType("agent.memory_provider")

    class _MemoryProvider:
        pass

    memory_provider_pkg.MemoryProvider = _MemoryProvider

    tools_pkg = types.ModuleType("tools")
    tools_registry_pkg = types.ModuleType("tools.registry")
    hermes_constants_pkg = types.ModuleType("hermes_constants")

    def _tool_error(message: str) -> str:
        return f"tool_error:{message}"

    def _get_hermes_home() -> str:
        return "/tmp"

    tools_registry_pkg.tool_error = _tool_error
    hermes_constants_pkg.get_hermes_home = _get_hermes_home

    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.memory_provider", memory_provider_pkg)
    monkeypatch.setitem(sys.modules, "tools", tools_pkg)
    monkeypatch.setitem(sys.modules, "tools.registry", tools_registry_pkg)
    monkeypatch.setitem(sys.modules, "hermes_constants", hermes_constants_pkg)

    module_name = "alice_memory_provider_test_module"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, PROVIDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_base_url_enforces_https_for_non_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)

    with pytest.raises(ValueError, match="https://"):
        module._normalize_base_url("http://example.com")

    assert module._normalize_base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert module._normalize_base_url("https://alice.example.com/v0") == "https://alice.example.com"


def test_request_json_sends_user_scope_in_header_not_query(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "base_url": "http://127.0.0.1:8000",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "timeout_seconds": 8.0,
    }

    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    def _fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)

    result = provider._request_json(
        "GET",
        "/v0/continuity/recall",
        params={"query": "release gating"},
    )

    assert result == {"ok": True}
    assert "user_id=" not in str(captured["url"])

    headers = {str(key).lower(): str(value) for key, value in dict(captured["headers"]).items()}
    assert headers["x-alicebot-user-id"] == "00000000-0000-0000-0000-000000000001"


def test_handle_tool_call_sanitizes_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()

    def _raise_unexpected(_args):  # type: ignore[no-untyped-def]
        raise RuntimeError("database password leaked from /private/tmp/creds.txt")

    monkeypatch.setattr(provider, "_tool_recall", _raise_unexpected)

    response = provider.handle_tool_call("alice_recall", {})
    assert "internal provider error" in response
    assert "password" not in response
    assert "/private/tmp" not in response


def test_handle_tool_call_sanitizes_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "base_url": "http://127.0.0.1:8000",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "timeout_seconds": 8.0,
    }

    def _fake_urlopen(_request, timeout=0):  # type: ignore[no-untyped-def]
        del timeout
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8000/v0/continuity/recall",
            code=500,
            msg="internal error",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"db password leaked"}'),
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)
    response = provider.handle_tool_call("alice_recall", {"query": "foo"})

    assert "HTTP status 500" in response
    assert "password leaked" not in response


def test_bridge_status_reports_legacy_config_compatibility(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:8000",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "prefetch_limit": 7,
                "max_recent_changes": 4,
                "max_open_loops": 3,
                "include_non_promotable_facts": True,
                "auto_capture": True,
                "mirror_memory_writes": True,
                "capture_mode": "auto",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    provider.initialize(session_id="bridge-status", hermes_home=str(tmp_path), agent_context="primary")
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is True
    assert status["config"]["prefetch_recall_limit"] == 7
    assert status["config"]["prefetch_max_recent_changes"] == 4
    assert status["config"]["prefetch_max_open_loops"] == 3
    assert status["config"]["prefetch_include_non_promotable_facts"] is True
    assert status["config"]["sync_turn_capture_enabled"] is True
    assert status["config"]["memory_write_capture_enabled"] is True
    assert status["config"]["bridge_mode"] == "auto"
    assert status["legacy_config_keys"] == [
        "auto_capture",
        "capture_mode",
        "include_non_promotable_facts",
        "max_open_loops",
        "max_recent_changes",
        "mirror_memory_writes",
        "prefetch_limit",
    ]


def test_default_bridge_mode_does_not_enable_sync_capture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:8000",
                "user_id": "00000000-0000-0000-0000-000000000001",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    provider.initialize(session_id="bridge-default", hermes_home=str(tmp_path), agent_context="primary")
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is True
    assert status["config"]["bridge_mode"] == "assist"
    assert status["config"]["sync_turn_capture_enabled"] is False
    assert status["lifecycle_hooks"]["sync_turn"] is False


def test_bridge_mode_auto_implies_sync_capture_when_flag_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:8000",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "bridge_mode": "auto",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    provider.initialize(session_id="bridge-auto", hermes_home=str(tmp_path), agent_context="primary")
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is True
    assert status["config"]["bridge_mode"] == "auto"
    assert status["config"]["sync_turn_capture_enabled"] is True
    assert status["lifecycle_hooks"]["sync_turn"] is True


def test_bridge_mode_auto_respects_explicit_sync_capture_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:8000",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "bridge_mode": "auto",
                "sync_turn_capture_enabled": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    provider.initialize(session_id="bridge-auto-disabled", hermes_home=str(tmp_path), agent_context="primary")
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is True
    assert status["config"]["bridge_mode"] == "auto"
    assert status["config"]["sync_turn_capture_enabled"] is False
    assert status["lifecycle_hooks"]["sync_turn"] is False


def test_invalid_bridge_mode_does_not_imply_sync_capture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:8000",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "bridge_mode": "automatic",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is True
    assert status["config"]["bridge_mode"] == "assist"
    assert status["config"]["sync_turn_capture_enabled"] is False
    assert status["lifecycle_hooks"]["sync_turn"] is False


def test_save_config_preserves_bridge_mode_sync_capture_omission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()

    provider.save_config(
        {
            "base_url": "http://127.0.0.1:8000",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "bridge_mode": "auto",
        },
        str(tmp_path),
    )

    saved = json.loads((tmp_path / "alice_memory_provider.json").read_text(encoding="utf-8"))
    assert saved["bridge_mode"] == "auto"
    assert saved["sync_turn_capture_enabled"] is True


def test_bridge_status_reports_invalid_config_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_provider_module(monkeypatch)
    config_path = tmp_path / "alice_memory_provider.json"
    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://example.com",
                "user_id": "not-a-uuid",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = module.AliceMemoryProvider()
    status = provider.get_status(hermes_home=str(tmp_path))

    assert status["ready"] is False
    assert any("base_url:" in message for message in status["errors"])
    assert any("user_id must be a valid UUID" in message for message in status["errors"])


def test_sync_turn_deduplicates_repeated_callbacks_and_flushes_on_session_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "sync_turn_capture_enabled": True,
        "session_end_flush_timeout_seconds": 5.0,
    }

    captured: list[str] = []

    def _fake_post_capture(raw_content: str) -> None:
        captured.append(raw_content)

    monkeypatch.setattr(provider, "_post_capture", _fake_post_capture)

    provider.sync_turn("Need decision", "Decision confirmed")
    provider.sync_turn("Need decision", "Decision confirmed")
    provider.on_session_end(session_id="session-a")
    provider.on_session_end(session_id="session-a")

    assert captured == ["User: Need decision\nAssistant: Decision confirmed"]


def test_memory_write_deduplicates_repeated_callbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "memory_write_capture_enabled": True,
        "session_end_flush_timeout_seconds": 5.0,
    }

    captured: list[str] = []

    def _fake_post_capture(raw_content: str) -> None:
        captured.append(raw_content)

    monkeypatch.setattr(provider, "_post_capture", _fake_post_capture)

    provider.on_memory_write("add", "MEMORY.md", "Use deterministic release checklist.")
    provider.on_memory_write("add", "MEMORY.md", "Use deterministic release checklist.")
    provider.on_session_end(session_id="session-b")

    assert captured == [
        "Hermes built-in memory update (MEMORY.md): Use deterministic release checklist."
    ]


def test_sync_turn_allows_same_content_after_session_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "sync_turn_capture_enabled": True,
        "session_end_flush_timeout_seconds": 5.0,
    }

    captured: list[str] = []

    def _fake_post_capture(raw_content: str) -> None:
        captured.append(raw_content)

    monkeypatch.setattr(provider, "_post_capture", _fake_post_capture)

    provider.sync_turn("Need decision", "Decision confirmed")
    provider.on_session_end(session_id="session-c")

    provider.sync_turn("Need decision", "Decision confirmed")
    provider.on_session_end(session_id="session-c")

    assert captured == [
        "User: Need decision\nAssistant: Decision confirmed",
        "User: Need decision\nAssistant: Decision confirmed",
    ]


def test_sync_turn_skips_capture_in_manual_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "sync_turn_capture_enabled": True,
        "bridge_mode": "manual",
        "session_end_flush_timeout_seconds": 5.0,
    }

    captured: list[str] = []

    def _fake_post_capture(raw_content: str) -> None:
        captured.append(raw_content)

    monkeypatch.setattr(provider, "_post_capture", _fake_post_capture)

    provider.sync_turn("Decision: keep scope tight", "Confirmed")
    provider.on_session_end(session_id="session-manual")

    assert captured == []


def test_post_capture_uses_b2_candidate_commit_pipeline_for_sync_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "bridge_mode": "assist",
    }

    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def _fake_request_json(method: str, path: str, *, params=None, payload=None):  # type: ignore[no-untyped-def]
        del params
        requests.append((method, path, payload))
        if path == "/v0/continuity/captures/candidates":
            return {
                "candidates": [
                    {
                        "candidate_id": "cand-1",
                        "candidate_type": "decision",
                        "object_type": "Decision",
                        "normalized_text": "Keep scope tight",
                        "confidence": 0.98,
                        "trust_class": "deterministic",
                        "evidence_snippet": "Decision",
                        "explicit": True,
                        "source_role": "user",
                        "admission_reason": "explicit_prefix_decision",
                        "proposed_action": "auto_save_candidate",
                    }
                ]
            }
        return {"ok": True}

    monkeypatch.setattr(provider, "_request_json", _fake_request_json)

    provider._post_capture("User: Decision: Keep scope tight\nAssistant: Confirmed")

    assert requests[0][0:2] == ("POST", "/v0/continuity/captures/candidates")
    assert requests[1][0:2] == ("POST", "/v0/continuity/captures/commit")
    assert requests[1][2] is not None
    assert requests[1][2]["mode"] == "assist"
    assert requests[1][2]["source_kind"] == "sync_turn"
    assert isinstance(requests[1][2]["sync_fingerprint"], str)
    assert requests[1][2]["sync_fingerprint"].startswith("sync_turn:")


def test_post_capture_falls_back_to_legacy_endpoint_when_b2_endpoints_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "bridge_mode": "assist",
    }

    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def _fake_request_json(method: str, path: str, *, params=None, payload=None):  # type: ignore[no-untyped-def]
        del params
        requests.append((method, path, payload))
        if path == "/v0/continuity/captures/candidates":
            raise RuntimeError("Alice API request failed with HTTP status 404")
        return {"ok": True}

    monkeypatch.setattr(provider, "_request_json", _fake_request_json)

    provider._post_capture("User: Decision: Keep scope tight\nAssistant: Confirmed")

    assert requests[0][1] == "/v0/continuity/captures/candidates"
    assert requests[1][1] == "/v0/continuity/captures"
