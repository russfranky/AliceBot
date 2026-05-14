from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
from typing import Any, Protocol, cast

from alicebot_api.config import Settings, get_settings
from alicebot_api.vnext_connectors import CORE_SETTINGS_CONNECTORS, VNextConnectorService
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_scheduler_runtime import daemon_status
from alicebot_api.vnext_secrets import SecretProvider, default_secret_provider

LOCAL_VNEXT_FRONTEND_ORIGINS = ("http://127.0.0.1:3000", "http://localhost:3000")
LOCAL_VNEXT_CORS_RECOMMENDED_FIX = (
    "CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000"
)


class VNextDoctorStore(Protocol):
    def connector_storage_status(self) -> JsonObject: ...

    def list_connector_settings(self) -> list[JsonObject]: ...

    def list_connector_states(self) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    severity: str
    message: str
    recommended_fix: str | None = None
    details: JsonObject | None = None

    def to_record(self) -> JsonObject:
        return {
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "recommended_fix": self.recommended_fix,
            "details": self.details or {},
        }


class VNextDoctorService:
    def __init__(
        self,
        store: VNextDoctorStore,
        *,
        secret_provider: SecretProvider | None = None,
        env: Mapping[str, str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        self.store = store
        self.secret_provider = secret_provider or default_secret_provider()
        self.env = os.environ if env is None else env
        self.cwd = cwd or Path.cwd()

    def _check(
        self,
        checks: list[DoctorCheck],
        *,
        name: str,
        ok: bool,
        severity: str,
        message_ok: str,
        message_fail: str,
        recommended_fix: str | None = None,
        details: JsonObject | None = None,
    ) -> None:
        checks.append(
            DoctorCheck(
                name=name,
                status="pass" if ok else "fail",
                severity="info" if ok else severity,
                message=message_ok if ok else message_fail,
                recommended_fix=None if ok else recommended_fix,
                details=details,
            )
        )

    def migration_status(self) -> JsonObject:
        status = self.store.connector_storage_status()
        required_tables = {
            "connector_settings": bool(status.get("connector_settings_exists")),
            "connector_state": bool(status.get("connector_state_exists")),
            "artifact_quality_ratings": bool(status.get("artifact_quality_ratings_exists")),
            "scheduler_workflows": bool(status.get("scheduler_workflows_exists")),
            "scheduler_runs": bool(status.get("scheduler_runs_exists")),
        }
        missing = [name for name, exists in required_tables.items() if not exists]
        return {
            "status": "ok" if not missing else "missing_migrations",
            "migration_revision": status.get("migration_revision"),
            "required_tables": required_tables,
            "missing_tables": missing,
        }

    def local_live_cors_status(self, settings: Settings | None = None) -> JsonObject:
        return local_live_cors_status(settings=settings or get_settings(), env=self.env, cwd=self.cwd)

    def run(self, *, fix_safe: bool = False, ci: bool = False) -> JsonObject:
        if fix_safe:
            VNextConnectorService(cast(Any, self.store), secret_provider=self.secret_provider).ensure_default_settings()

        checks: list[DoctorCheck] = []
        migration_status = self.migration_status()
        self._check(
            checks,
            name="migrations",
            ok=migration_status["status"] == "ok",
            severity="blocking",
            message_ok="Required vNext dogfood hardening tables are present.",
            message_fail="Database schema is missing required vNext dogfood hardening tables.",
            recommended_fix="./scripts/migrate.sh",
            details=cast(JsonObject, migration_status),
        )

        try:
            settings = self.store.list_connector_settings()
            states = self.store.list_connector_states()
        except Exception as exc:
            settings = []
            states = []
            checks.append(
                DoctorCheck(
                    name="connector_storage",
                    status="fail",
                    severity="blocking",
                    message=f"Connector settings/state storage is unavailable: {type(exc).__name__}.",
                    recommended_fix="./scripts/migrate.sh",
                )
            )

        setting_names = {str(row.get("connector_name")) for row in settings}
        state_names = {str(row.get("connector_name")) for row in states}
        missing_settings = [name for name in CORE_SETTINGS_CONNECTORS if name not in setting_names]
        missing_states = [name for name in CORE_SETTINGS_CONNECTORS if name not in state_names]
        self._check(
            checks,
            name="connector_settings",
            ok=not missing_settings,
            severity="blocking",
            message_ok="Core connector settings rows exist.",
            message_fail="Core connector settings rows are missing.",
            recommended_fix="alicebot vnext doctor --fix-safe",
            details={"missing": missing_settings},
        )
        self._check(
            checks,
            name="connector_state",
            ok=not missing_states,
            severity="blocking",
            message_ok="Core connector state rows exist.",
            message_fail="Core connector state rows are missing.",
            recommended_fix="alicebot vnext doctor --fix-safe",
            details={"missing": missing_states},
        )

        telegram = next((row for row in settings if row.get("connector_name") == "telegram"), None)
        telegram_enabled = bool(telegram.get("enabled")) if isinstance(telegram, dict) else False
        telegram_secret_ref = str(telegram.get("secret_ref") or "") if isinstance(telegram, dict) else ""
        telegram_secret_resolved = bool(telegram_secret_ref and self.secret_provider.has_secret(telegram_secret_ref))
        telegram_secret_ok = (not telegram_enabled and (ci or not telegram_secret_ref)) or (
            bool(telegram_secret_ref) and telegram_secret_resolved
        )
        self._check(
            checks,
            name="telegram_secret_ref",
            ok=telegram_secret_ok,
            severity="blocking" if telegram_enabled else "warning",
            message_ok="Telegram secret_ref is configured without exposing the token.",
            message_fail="Telegram secret_ref is missing or unresolved.",
            recommended_fix="alicebot vnext connectors telegram configure --secret-ref telegram.bot_token.default --bot-token <redacted>",
            details={"enabled": telegram_enabled, "secret_ref": telegram_secret_ref or None, "secret_resolved": telegram_secret_resolved},
        )

        scheduler = daemon_status()
        scheduler_known = not bool(scheduler.get("stopped")) or "pid file" not in str(scheduler.get("message", "")).casefold()
        self._check(
            checks,
            name="scheduler_daemon",
            ok=scheduler_known,
            severity="warning",
            message_ok="Scheduler daemon status is available.",
            message_fail="Scheduler daemon is unavailable or has not been started.",
            recommended_fix="alicebot vnext scheduler daemon start --foreground --once",
            details=cast(JsonObject, scheduler),
        )

        health = VNextConnectorService(cast(Any, self.store), secret_provider=self.secret_provider).connector_health_all()
        failing_connectors = [
            item
            for item in cast(list[JsonObject], health.get("items", []))
            if int(item.get("items_failed", 0) or 0) > 0 or item.get("last_error")
        ]
        self._check(
            checks,
            name="capture_pipeline",
            ok=len(failing_connectors) == 0,
            severity="warning",
            message_ok="Connector capture pipeline has no recorded connector failures.",
            message_fail="Connector capture pipeline has recorded failures.",
            recommended_fix="alicebot vnext connectors status",
            details={"failing_connectors": [item.get("connector_name") for item in failing_connectors]},
        )

        local_cors = self.local_live_cors_status()
        local_cors_ok = bool(local_cors["ok"])
        self._check(
            checks,
            name="local_vnext_cors",
            ok=local_cors_ok,
            severity="warning",
            message_ok=str(local_cors["message"]),
            message_fail=str(local_cors["message"]),
            recommended_fix=LOCAL_VNEXT_CORS_RECOMMENDED_FIX,
            details=cast(JsonObject, local_cors),
        )

        blocking = [check for check in checks if check.status == "fail" and check.severity == "blocking"]
        warnings = [check for check in checks if check.status == "fail" and check.severity == "warning"]
        payload = {
            "status": "fail" if blocking else "warn" if warnings else "pass",
            "fix_safe_applied": fix_safe,
            "ci_mode": ci,
            "blocking_failure_count": len(blocking),
            "warning_count": len(warnings),
            "checks": [check.to_record() for check in checks],
            "recommended_fixes": [
                check.recommended_fix for check in checks if check.status == "fail" and check.recommended_fix is not None
            ],
            "migration_status": migration_status,
            "connector_health": health,
        }
        return cast(JsonObject, payload)


def _parse_env_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}

    values: dict[str, str] = {}
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == "" or stripped.startswith("#") or "=" not in stripped:
            continue
        line = stripped.removeprefix("export ").strip()
        key, raw_value = line.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            parsed = shlex.split(raw_value, comments=True, posix=True)
        except ValueError:
            continue
        values[key] = parsed[0] if parsed else ""
    return values


def _csv_tokens(value: str) -> tuple[str, ...]:
    return tuple(token.strip() for token in value.split(",") if token.strip() != "")


def _merged_local_env(env: Mapping[str, str], cwd: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    for relative_path in (".env", "apps/web/.env.local"):
        merged.update(_parse_env_file(cwd / relative_path))
    merged.update(dict(env))
    return merged


def local_live_cors_status(
    *,
    settings: Settings,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> JsonObject:
    merged_env = _merged_local_env(os.environ if env is None else env, cwd or Path.cwd())
    frontend_api_base_url = (
        merged_env.get("NEXT_PUBLIC_ALICEBOT_API_BASE_URL")
        or merged_env.get("ALICEBOT_API_BASE_URL")
        or ""
    ).strip()
    frontend_user_id = (
        merged_env.get("NEXT_PUBLIC_ALICEBOT_USER_ID") or merged_env.get("ALICEBOT_USER_ID") or ""
    ).strip()
    configured_origins = settings.cors_allowed_origins
    if len(configured_origins) == 0:
        configured_origins = _csv_tokens(merged_env.get("CORS_ALLOWED_ORIGINS", ""))

    frontend_live_configured = frontend_api_base_url != ""
    required = set(LOCAL_VNEXT_FRONTEND_ORIGINS)
    configured = set(configured_origins)
    missing = sorted(required - configured)
    wildcard_present = "*" in configured

    if not frontend_live_configured:
        return {
            "ok": True,
            "message": "Local /vnext live browser API URL is not configured; CORS check is not required.",
            "frontend_live_configured": False,
            "frontend_api_base_url": None,
            "frontend_user_id_configured": bool(frontend_user_id),
            "required_origins": list(LOCAL_VNEXT_FRONTEND_ORIGINS),
            "configured_origins": list(configured_origins),
            "missing_origins": [],
            "wildcard_present": wildcard_present,
        }

    if wildcard_present:
        return {
            "ok": False,
            "message": "Local /vnext live mode has wildcard CORS; use explicit localhost origins instead.",
            "frontend_live_configured": True,
            "frontend_api_base_url": frontend_api_base_url,
            "frontend_user_id_configured": bool(frontend_user_id),
            "required_origins": list(LOCAL_VNEXT_FRONTEND_ORIGINS),
            "configured_origins": list(configured_origins),
            "missing_origins": missing,
            "wildcard_present": True,
        }

    if missing:
        return {
            "ok": False,
            "message": "Local /vnext live mode is configured, but CORS is missing one or more localhost frontend origins.",
            "frontend_live_configured": True,
            "frontend_api_base_url": frontend_api_base_url,
            "frontend_user_id_configured": bool(frontend_user_id),
            "required_origins": list(LOCAL_VNEXT_FRONTEND_ORIGINS),
            "configured_origins": list(configured_origins),
            "missing_origins": missing,
            "wildcard_present": False,
        }

    return {
        "ok": True,
        "message": "Local /vnext live CORS allows the localhost frontend origins explicitly.",
        "frontend_live_configured": True,
        "frontend_api_base_url": frontend_api_base_url,
        "frontend_user_id_configured": bool(frontend_user_id),
        "required_origins": list(LOCAL_VNEXT_FRONTEND_ORIGINS),
        "configured_origins": list(configured_origins),
        "missing_origins": [],
        "wildcard_present": False,
    }


__all__ = [
    "DoctorCheck",
    "LOCAL_VNEXT_CORS_RECOMMENDED_FIX",
    "LOCAL_VNEXT_FRONTEND_ORIGINS",
    "VNextDoctorService",
    "VNextDoctorStore",
    "local_live_cors_status",
]
