from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Callable
from uuid import UUID

from alicebot_api.db import user_connection
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_scheduler import VNextSchedulerService
from alicebot_api.vnext_store import PostgresVNextStore


DEFAULT_RUNTIME_DIR = Path("~/.alicebot/vnext-scheduler").expanduser()
DEFAULT_PID_FILE = DEFAULT_RUNTIME_DIR / "scheduler.pid"
DEFAULT_STATUS_FILE = DEFAULT_RUNTIME_DIR / "scheduler-status.json"
DEFAULT_LOG_FILE = DEFAULT_RUNTIME_DIR / "scheduler.log"


@dataclass(frozen=True, slots=True)
class SchedulerRuntimeConfig:
    database_url: str
    user_id: UUID
    interval_seconds: float = 60.0
    limit: int = 10
    pid_file: Path = DEFAULT_PID_FILE
    status_file: Path = DEFAULT_STATUS_FILE
    log_file: Path = DEFAULT_LOG_FILE
    once: bool = False


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_safe(child) for child in value]
    if isinstance(value, tuple):
        return [_json_safe(child) for child in value]
    if isinstance(value, (datetime, Path, UUID)):
        return str(value)
    return value


def _write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> JsonObject | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def daemon_status(*, pid_file: Path = DEFAULT_PID_FILE, status_file: Path = DEFAULT_STATUS_FILE) -> JsonObject:
    status = _read_json(status_file) or {}
    pid = status.get("pid")
    if not isinstance(pid, int):
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            pid = None
    running = False if status.get("running") is False else _pid_running(pid) if isinstance(pid, int) else False
    return {
        "configured": status != {} or pid is not None,
        "running": running,
        "pid": pid,
        "pid_file": str(pid_file),
        "status_file": str(status_file),
        **status,
        "running": running,
    }


def stop_daemon(*, pid_file: Path = DEFAULT_PID_FILE, status_file: Path = DEFAULT_STATUS_FILE, timeout_seconds: float = 10.0) -> JsonObject:
    status = daemon_status(pid_file=pid_file, status_file=status_file)
    pid = status.get("pid")
    if not isinstance(pid, int):
        return {**status, "stopped": False, "message": "No scheduler daemon pid file found."}
    if not _pid_running(pid):
        return {**status, "stopped": True, "message": "Scheduler daemon was already stopped."}
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_running(pid):
            return {**daemon_status(pid_file=pid_file, status_file=status_file), "stopped": True}
        time.sleep(0.2)
    return {**daemon_status(pid_file=pid_file, status_file=status_file), "stopped": False, "message": "Scheduler daemon did not stop before timeout."}


def start_background_daemon(config: SchedulerRuntimeConfig) -> JsonObject:
    current = daemon_status(pid_file=config.pid_file, status_file=config.status_file)
    if current.get("running") is True:
        return {**current, "started": False, "message": "Scheduler daemon is already running."}
    config.pid_file.parent.mkdir(parents=True, exist_ok=True)
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "alicebot_api",
        "--database-url",
        config.database_url,
        "--user-id",
        str(config.user_id),
        "vnext",
        "scheduler",
        "daemon",
        "start",
        "--foreground",
        "--interval-seconds",
        str(config.interval_seconds),
        "--limit",
        str(config.limit),
        "--pid-file",
        str(config.pid_file),
        "--status-file",
        str(config.status_file),
        "--log-file",
        str(config.log_file),
    ]
    log_handle = config.log_file.open("ab")
    process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True)
    log_handle.close()
    config.pid_file.write_text(str(process.pid), encoding="utf-8")
    _write_json(
        config.status_file,
        {
            "pid": process.pid,
            "running": True,
            "started_at": _now_iso(),
            "last_heartbeat_at": _now_iso(),
            "interval_seconds": config.interval_seconds,
            "limit": config.limit,
            "mode": "background",
            "log_file": str(config.log_file),
        },
    )
    return daemon_status(pid_file=config.pid_file, status_file=config.status_file) | {"started": True}


def run_foreground_daemon(
    config: SchedulerRuntimeConfig,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> JsonObject:
    stop_requested = False

    def _request_stop(_signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True

    previous_sigterm = signal.signal(signal.SIGTERM, _request_stop)
    previous_sigint = signal.signal(signal.SIGINT, _request_stop)
    config.pid_file.parent.mkdir(parents=True, exist_ok=True)
    config.pid_file.write_text(str(os.getpid()), encoding="utf-8")
    started_at = _now_iso()
    last_payload: JsonObject = {
        "pid": os.getpid(),
        "running": True,
        "started_at": started_at,
        "last_heartbeat_at": started_at,
        "interval_seconds": config.interval_seconds,
        "limit": config.limit,
        "mode": "foreground",
        "last_due_scan": None,
        "last_error": None,
    }
    try:
        while not stop_requested:
            try:
                with user_connection(config.database_url, config.user_id) as conn:
                    result = VNextSchedulerService(PostgresVNextStore(conn)).run_due_workflows(limit=config.limit)
                last_payload = {
                    **last_payload,
                    "running": True,
                    "last_heartbeat_at": _now_iso(),
                    "last_due_scan": result,
                    "last_due_scan_at": result.get("checked_at"),
                    "last_due_count": result.get("due_count", 0),
                    "last_error": None,
                }
            except Exception as exc:  # pragma: no cover - exercised through CLI smoke paths
                last_payload = {
                    **last_payload,
                    "running": True,
                    "last_heartbeat_at": _now_iso(),
                    "last_error": str(exc),
                    "last_error_type": type(exc).__name__,
                }
            _write_json(config.status_file, last_payload)
            if config.once:
                break
            sleep_fn(max(config.interval_seconds, 0.1))
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)
        stopped_payload = {**last_payload, "running": False, "stopped_at": _now_iso()}
        _write_json(config.status_file, stopped_payload)
    return daemon_status(pid_file=config.pid_file, status_file=config.status_file)


__all__ = [
    "DEFAULT_LOG_FILE",
    "DEFAULT_PID_FILE",
    "DEFAULT_RUNTIME_DIR",
    "DEFAULT_STATUS_FILE",
    "SchedulerRuntimeConfig",
    "daemon_status",
    "run_foreground_daemon",
    "start_background_daemon",
    "stop_daemon",
]
