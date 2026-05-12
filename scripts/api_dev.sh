#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-api-dev] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before starting Alice."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  PRESERVE_ENV_KEYS=(
    APP_ENV
    APP_HOST
    APP_PORT
    APP_RELOAD
    APP_LOG_MODE
    APP_LOG_LEVEL
    APP_LOG_PATH
    APP_LOG_MAX_BYTES
    APP_LOG_BACKUP_COUNT
    APP_ACCESS_LOG
    DATABASE_URL
    DATABASE_ADMIN_URL
    REDIS_URL
    S3_ENDPOINT_URL
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_BUCKET
    HEALTHCHECK_TIMEOUT_SECONDS
    TASK_WORKSPACE_ROOT
    ALICEBOT_AUTH_USER_ID
    PUBLIC_SAMPLE_DATA_PATH
    RESPONSE_RATE_LIMIT_WINDOW_SECONDS
    RESPONSE_RATE_LIMIT_MAX_REQUESTS
    ENTRYPOINT_RATE_LIMIT_BACKEND
  )

  for key in "${PRESERVE_ENV_KEYS[@]}"; do
    if [ "${!key+x}" = "x" ]; then
      export "__PRESERVE_${key}=${!key}"
    fi
  done

  set -a
  . "${REPO_ROOT}/.env"
  set +a

  for key in "${PRESERVE_ENV_KEYS[@]}"; do
    preserve_key="__PRESERVE_${key}"
    if [ "${!preserve_key+x}" = "x" ]; then
      export "${key}=${!preserve_key}"
      unset "${preserve_key}"
    fi
  done
fi

cd "${REPO_ROOT}"

export APP_LOG_MODE="${APP_LOG_MODE:-stdout}"
export APP_ACCESS_LOG="${APP_ACCESS_LOG:-false}"
if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="${REPO_ROOT}/apps/api/src:${PYTHONPATH}"
else
  export PYTHONPATH="${REPO_ROOT}/apps/api/src"
fi

exec "${PYTHON_BIN}" -m alicebot_api.local_server
