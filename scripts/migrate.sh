#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-migrate] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before migrating Alice."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  set -a
  . "${REPO_ROOT}/.env"
  set +a
fi

cd "${REPO_ROOT}"

"${PYTHON_BIN}" -m alembic -c "${REPO_ROOT}/apps/api/alembic.ini" upgrade "${1:-head}"
