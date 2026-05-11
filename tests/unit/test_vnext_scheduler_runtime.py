from __future__ import annotations

import json
import os
from pathlib import Path

from alicebot_api.vnext_scheduler_runtime import _sleep_interruptibly, daemon_status


def test_daemon_status_preserves_explicit_stopped_state_for_foreground_once(tmp_path: Path) -> None:
    pid_file = tmp_path / "scheduler.pid"
    status_file = tmp_path / "scheduler-status.json"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    status_file.write_text(
        json.dumps({"pid": os.getpid(), "running": False, "mode": "foreground"}),
        encoding="utf-8",
    )

    status = daemon_status(pid_file=pid_file, status_file=status_file)

    assert status["pid"] == os.getpid()
    assert status["running"] is False


def test_sleep_interruptibly_uses_short_slices_and_stops_early() -> None:
    calls: list[float] = []

    def sleep_fn(seconds: float) -> None:
        calls.append(seconds)

    _sleep_interruptibly(60, should_stop=lambda: len(calls) >= 2, sleep_fn=sleep_fn)

    assert calls == [0.5, 0.5]
