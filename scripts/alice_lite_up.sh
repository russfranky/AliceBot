#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-lite-up] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before starting Alice Lite."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  set -a
  . "${REPO_ROOT}/.env"
  set +a
fi

if [ -f "${REPO_ROOT}/.env.lite" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env.lite"
  set -a
  . "${REPO_ROOT}/.env.lite"
  set +a
fi

configure_compose_postgres_env() {
  eval "$("${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import os
import shlex
from urllib.parse import unquote, urlparse


def parse(url: str, *, default_user: str, default_password: str, default_db: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    user = unquote(parsed.username or default_user)
    password = unquote(parsed.password or default_password)
    db = (parsed.path or "").lstrip("/") or default_db
    return user, password, db


admin_user, admin_password, db_name = parse(
    os.getenv("DATABASE_ADMIN_URL", "postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot"),
    default_user="alicebot_admin",
    default_password="alicebot_admin",
    default_db="alicebot",
)
app_user, app_password, _ = parse(
    os.getenv("DATABASE_URL", "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"),
    default_user="alicebot_app",
    default_password="alicebot_app",
    default_db=db_name,
)
for key, value in {
    "ALICEBOT_COMPOSE_POSTGRES_USER": admin_user,
    "ALICEBOT_COMPOSE_POSTGRES_PASSWORD": admin_password,
    "ALICEBOT_COMPOSE_POSTGRES_DB": db_name,
    "ALICEBOT_COMPOSE_APP_USER": app_user,
    "ALICEBOT_COMPOSE_APP_PASSWORD": app_password,
}.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"
}

export APP_RELOAD="${APP_RELOAD:-false}"
export ENTRYPOINT_RATE_LIMIT_BACKEND="${ENTRYPOINT_RATE_LIMIT_BACKEND:-memory}"
export APP_LOG_MODE="${APP_LOG_MODE:-stdout}"
export APP_ACCESS_LOG="${APP_ACCESS_LOG:-false}"

cd "${REPO_ROOT}"

configure_compose_postgres_env
docker compose -f "${REPO_ROOT}/docker-compose.lite.yml" up -d

"${PYTHON_BIN}" - <<'PY'
import os
import sys
import time

import psycopg

database_url = os.getenv(
    "DATABASE_ADMIN_URL",
    "postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot",
)
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with psycopg.connect(database_url, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("alicebot_app",))
                if cur.fetchone() == (1,):
                    sys.exit(0)
    except psycopg.Error:
        pass
    time.sleep(1)

raise SystemExit(
    "Timed out waiting for Alice Lite Postgres readiness and alicebot_app bootstrap. "
    "If DATABASE_URL or DATABASE_ADMIN_URL changed after the compose volume was created, "
    "run 'docker compose -f docker-compose.lite.yml down -v' before retrying, or restore the original credentials."
)
PY

"${REPO_ROOT}/scripts/migrate.sh"
"${REPO_ROOT}/scripts/load_sample_data.sh"

echo "Alice Lite is ready on http://${APP_HOST:-127.0.0.1}:${APP_PORT:-8000}"
echo "Next terminal:"
echo "  ${PYTHON_BIN} ${REPO_ROOT}/scripts/bootstrap_alice_lite_workspace.py"

exec "${REPO_ROOT}/scripts/api_dev.sh"
