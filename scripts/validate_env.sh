#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: scripts/validate_env.sh ENV_FILE [ENV_FILE...]" >&2
  exit 2
fi

python3 - "$@" <<'PY'
from __future__ import annotations

from pathlib import Path
import re
import shlex
import sys


KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [f"{path}: file does not exist"]

    seen: set[str] = set()
    values: dict[str, str] = {}
    for lineno, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        line = stripped.removeprefix("export ").strip()
        if "=" not in line:
            errors.append(f"{path}:{lineno}: expected KEY=VALUE")
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_RE.fullmatch(key):
            errors.append(f"{path}:{lineno}: invalid environment key {key!r}")
            continue
        seen.add(key)

        try:
            parsed_value = shlex.split(value, comments=True, posix=True)
        except ValueError as exc:
            errors.append(f"{path}:{lineno}: invalid shell quoting for {key}: {exc}")
            continue

        if any(ch.isspace() for ch in value) and not value.startswith(("'", '"')):
            errors.append(f"{path}:{lineno}: quote {key} because its value contains spaces")
        values[key] = parsed_value[0] if parsed_value else ""

    if path.name == ".env":
        required = {"APP_ENV", "DATABASE_URL", "DATABASE_ADMIN_URL"}
        missing = sorted(required - seen)
        for key in missing:
            errors.append(f"{path}: missing required key {key}")

        app_env = values.get("APP_ENV", "development")
        if app_env not in {"development", "test"}:
            if values.get("ALICEBOT_AUTH_USER_ID", "") == "":
                errors.append(f"{path}: ALICEBOT_AUTH_USER_ID is required when APP_ENV={app_env}")
            if values.get("TELEGRAM_WEBHOOK_SECRET", "") == "":
                errors.append(f"{path}: TELEGRAM_WEBHOOK_SECRET is required when APP_ENV={app_env}")
            if values.get("S3_ACCESS_KEY", "alicebot") == "alicebot":
                errors.append(f"{path}: S3_ACCESS_KEY must be overridden when APP_ENV={app_env}")
            if values.get("S3_SECRET_KEY", "alicebot-secret") == "alicebot-secret":
                errors.append(f"{path}: S3_SECRET_KEY must be overridden when APP_ENV={app_env}")

    return errors


all_errors: list[str] = []
for raw_path in sys.argv[1:]:
    all_errors.extend(validate(Path(raw_path)))

if all_errors:
    print("Environment validation failed:", file=sys.stderr)
    for error in all_errors:
        print(f"  - {error}", file=sys.stderr)
    raise SystemExit(1)
PY
