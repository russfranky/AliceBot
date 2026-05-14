from __future__ import annotations

from alicebot_api.config import Settings
from alicebot_api.vnext_doctor import VNextDoctorService
from alicebot_api.vnext_secrets import InMemorySecretProvider


class DoctorStore:
    def __init__(self) -> None:
        self.settings: list[dict[str, object]] = []
        self.states: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []

    def connector_storage_status(self) -> dict[str, object]:
        return {
            "connector_settings_exists": True,
            "connector_state_exists": True,
            "artifact_quality_ratings_exists": True,
            "scheduler_workflows_exists": True,
            "scheduler_runs_exists": True,
            "migration_revision": "20260511_0070",
        }

    def list_connector_settings(self) -> list[dict[str, object]]:
        return self.settings

    def list_connector_states(self) -> list[dict[str, object]]:
        return self.states

    def list_events(self, **_kwargs) -> list[dict[str, object]]:
        return self.events

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def list_sources(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_memories(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_artifacts(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_artifact_quality_ratings(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_open_loops(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_scheduler_runs(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def get_connector_setting(self, connector_name: str) -> dict[str, object] | None:
        return next((row for row in self.settings if row["connector_name"] == connector_name), None)

    def upsert_connector_setting(self, setting: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            "id": f"setting-{setting['connector_name']}",
            "connector_name": setting["connector_name"],
            "enabled": setting.get("enabled", False),
            "configured": setting.get("configured", False),
            "default_domain": setting["default_domain"],
            "default_sensitivity": setting["default_sensitivity"],
            "sync_mode": setting.get("sync_mode", "manual"),
            "poll_interval_seconds": setting.get("poll_interval_seconds"),
            "secret_ref": setting.get("secret_ref"),
            "validation_errors_json": setting.get("validation_errors_json", []),
            "metadata_json": setting.get("metadata_json", {}),
        }
        self.settings = [item for item in self.settings if item["connector_name"] != row["connector_name"]]
        self.settings.append(row)
        return row

    def get_connector_state(self, connector_name: str, cursor_type: str = "sync_cursor") -> dict[str, object] | None:
        return next(
            (
                row
                for row in self.states
                if row["connector_name"] == connector_name and row.get("cursor_type", "sync_cursor") == cursor_type
            ),
            None,
        )

    def upsert_connector_state(self, state: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            "id": f"state-{state['connector_name']}",
            "connector_name": state["connector_name"],
            "cursor_type": state.get("cursor_type", "sync_cursor"),
            "cursor_value": state.get("cursor_value"),
            "items_seen": state.get("items_seen", 0),
            "items_captured": state.get("items_captured", 0),
            "items_deduped": state.get("items_deduped", 0),
            "items_failed": state.get("items_failed", 0),
        }
        self.states = [item for item in self.states if item["connector_name"] != row["connector_name"]]
        self.states.append(row)
        return row


def test_doctor_fix_safe_initializes_missing_connector_defaults() -> None:
    store = DoctorStore()

    payload = VNextDoctorService(store).run(fix_safe=True, ci=True)

    assert payload["blocking_failure_count"] == 0
    assert {row["connector_name"] for row in store.settings} >= {
        "telegram",
        "local_folder",
        "browser_clipper",
        "agent_output",
    }
    assert any(check["name"] == "connector_settings" and check["status"] == "pass" for check in payload["checks"])


def test_doctor_detects_enabled_telegram_missing_secret_as_blocking() -> None:
    store = DoctorStore()
    store.settings.append(
        {
            "id": "setting-telegram",
            "connector_name": "telegram",
            "enabled": True,
            "configured": True,
            "default_domain": "personal",
            "default_sensitivity": "private",
            "sync_mode": "polling",
            "metadata_json": {"config_json": {"allowed_chat_ids": ["999001"]}},
        }
    )
    store.states.append({"id": "state-telegram", "connector_name": "telegram", "cursor_type": "sync_cursor"})
    for connector_name in ("local_folder", "browser_clipper", "agent_output"):
        store.settings.append(
            {
                "id": f"setting-{connector_name}",
                "connector_name": connector_name,
                "enabled": False,
                "configured": False,
                "default_domain": "project",
                "default_sensitivity": "private",
                "sync_mode": "on_demand",
                "metadata_json": {"config_json": {}},
            }
        )
        store.states.append({"id": f"state-{connector_name}", "connector_name": connector_name, "cursor_type": "sync_cursor"})

    payload = VNextDoctorService(store, secret_provider=InMemorySecretProvider()).run(ci=True)

    assert payload["blocking_failure_count"] == 1
    assert any(check["name"] == "telegram_secret_ref" and check["status"] == "fail" for check in payload["checks"])


def test_doctor_warns_when_local_live_cors_is_missing(tmp_path, monkeypatch) -> None:
    web_dir = tmp_path / "apps" / "web"
    web_dir.mkdir(parents=True)
    (tmp_path / ".env").write_text("CORS_ALLOWED_ORIGINS=http://localhost:3000\n", encoding="utf-8")
    (web_dir / ".env.local").write_text(
        "\n".join(
            [
                "NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000",
                "NEXT_PUBLIC_ALICEBOT_USER_ID=00000000-0000-0000-0000-000000000001",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_doctor.get_settings",
        lambda: Settings(app_env="development", database_url="postgresql://db"),
    )
    store = DoctorStore()

    payload = VNextDoctorService(store, env={}, cwd=tmp_path).run(fix_safe=True, ci=True)

    local_cors = next(check for check in payload["checks"] if check["name"] == "local_vnext_cors")
    assert local_cors["status"] == "fail"
    assert local_cors["severity"] == "warning"
    assert local_cors["recommended_fix"] == "CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000"
    assert local_cors["details"]["missing_origins"] == ["http://127.0.0.1:3000"]


def test_doctor_passes_when_local_live_cors_is_explicit(tmp_path, monkeypatch) -> None:
    web_dir = tmp_path / "apps" / "web"
    web_dir.mkdir(parents=True)
    (tmp_path / ".env").write_text(
        "CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000\n",
        encoding="utf-8",
    )
    (web_dir / ".env.local").write_text(
        "\n".join(
            [
                "NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000",
                "NEXT_PUBLIC_ALICEBOT_USER_ID=00000000-0000-0000-0000-000000000001",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_doctor.get_settings",
        lambda: Settings(app_env="development", database_url="postgresql://db"),
    )
    store = DoctorStore()

    payload = VNextDoctorService(store, env={}, cwd=tmp_path).run(fix_safe=True, ci=True)

    local_cors = next(check for check in payload["checks"] if check["name"] == "local_vnext_cors")
    assert local_cors["status"] == "pass"
    assert local_cors["details"]["wildcard_present"] is False
