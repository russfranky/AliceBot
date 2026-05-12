#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-dev-up] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before starting or migrating Alice."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  set -a
  . "${REPO_ROOT}/.env"
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

cd "${REPO_ROOT}"

configure_compose_postgres_env
docker compose up -d

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
    "Timed out waiting for Postgres readiness and alicebot_app bootstrap. "
    "If DATABASE_URL or DATABASE_ADMIN_URL changed after the compose volume was created, "
    "run 'docker compose down -v' before retrying, or restore the original credentials."
)
PY

"${PYTHON_BIN}" -m alembic -c "${REPO_ROOT}/apps/api/alembic.ini" upgrade head
