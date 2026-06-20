#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ALICEBOT_REPO_URL:-https://github.com/samrusani/AliceBot.git}"
TAG=""
BRANCH="main"
INSTALL_DIR="${HOME}/alicebot"
CONFIG_DIR="${HOME}/.config/alicebot"
DATA_DIR="${HOME}/.local/share/alicebot"
STATE_DIR="${HOME}/.local/state/alicebot"
SECRETS_DIR="${HOME}/.config/alicebot/secrets"
ALICE_RUNTIME_DIR="${HOME}/.alicebot"
ENV_FILE=""
SKIP_POSTGRES_INSTALL=0
NON_INTERACTIVE=0
INSTALL_SYSTEMD=0
DRY_RUN=0
RUN_ALPHA_CHECK=1
PNPM_VERSION="${PNPM_VERSION:-10.23.0}"

log() {
  printf '[alice-install] %s\n' "$*"
}

fail() {
  printf '[alice-install] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Install AliceBot on a headless Ubuntu host.

Usage:
  bash install-alice.sh [options]

Options:
  --tag VERSION              Check out a specific tag, for example v0.6.0-alpha-rc.2.
  --branch NAME              Check out a branch. Defaults to main when --tag is omitted.
  --install-dir PATH         Repository install directory. Defaults to ~/alicebot.
  --config-dir PATH          Config directory. Defaults to ~/.config/alicebot.
  --skip-postgres-install    Do not install/configure local Postgres; verify only.
  --install-systemd          Install alice-api, alice-web, and alice-scheduler systemd units.
  --non-interactive          Fail instead of prompting.
  --skip-alpha-check         Skip final alicebot vnext alpha check --headless --skip-smokes.
  --dry-run                  Print planned commands without changing the host.
  -h, --help                 Show this help.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tag)
      TAG="${2:-}"
      BRANCH=""
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      TAG=""
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --config-dir)
      CONFIG_DIR="${2:-}"
      shift 2
      ;;
    --skip-postgres-install)
      SKIP_POSTGRES_INSTALL=1
      shift
      ;;
    --install-systemd)
      INSTALL_SYSTEMD=1
      shift
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
      shift
      ;;
    --skip-alpha-check)
      RUN_ALPHA_CHECK=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

INSTALL_DIR="$(realpath -m "${INSTALL_DIR/#\~/${HOME}}")"
CONFIG_DIR="$(realpath -m "${CONFIG_DIR/#\~/${HOME}}")"
DATA_DIR="$(realpath -m "${DATA_DIR/#\~/${HOME}}")"
STATE_DIR="$(realpath -m "${STATE_DIR/#\~/${HOME}}")"
SECRETS_DIR="$(realpath -m "${SECRETS_DIR/#\~/${HOME}}")"
ALICE_RUNTIME_DIR="$(realpath -m "${ALICE_RUNTIME_DIR/#\~/${HOME}}")"
ENV_FILE="${CONFIG_DIR}/.env"

run() {
  log "+ $*"
  if [ "${DRY_RUN}" -eq 0 ]; then
    "$@"
  fi
}

run_in_install_dir() {
  log "+ (cd ${INSTALL_DIR} && $*)"
  if [ "${DRY_RUN}" -eq 0 ]; then
    (cd "${INSTALL_DIR}" && "$@")
  fi
}

confirm() {
  local prompt="$1"
  if [ "${NON_INTERACTIVE}" -eq 1 ]; then
    fail "${prompt} Re-run without --non-interactive or choose a non-destructive path."
  fi
  read -r -p "${prompt} [y/N] " answer
  case "${answer}" in
    y|Y|yes|YES) return 0 ;;
    *) fail "Operator cancelled." ;;
  esac
}

require_ubuntu() {
  if [ ! -r /etc/os-release ]; then
    fail "This installer expects Ubuntu and could not read /etc/os-release."
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ]; then
    fail "This installer currently supports Ubuntu only; detected ID=${ID:-unknown}."
  fi
  case "${VERSION_ID:-}" in
    22.04|24.04) log "Detected Ubuntu ${VERSION_ID}." ;;
    *) log "Detected Ubuntu ${VERSION_ID:-unknown}; continuing, but 22.04 and 24.04 are the documented assumptions." ;;
  esac
}

install_system_packages() {
  run sudo apt-get update
  run sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git build-essential python3 python3-venv python3-pip \
    openssl pkg-config libpq-dev redis-tools
}

install_pnpm_from_npm() {
  local npm_bin npm_prefix
  npm_bin="$(command -v npm || true)"
  if [ -z "${npm_bin}" ]; then
    fail "npm is required to install pnpm when corepack is unavailable."
  fi

  npm_prefix="$("${npm_bin}" config get prefix 2>/dev/null || true)"
  if [[ "${npm_bin}" == "${HOME}/"* || "${npm_prefix}" == "${HOME}/"* ]]; then
    run "${npm_bin}" install -g "pnpm@${PNPM_VERSION}"
  else
    run sudo "${npm_bin}" install -g "pnpm@${PNPM_VERSION}"
  fi
}

install_node_and_pnpm() {
  local corepack_bin node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || true)"
  if [ -z "${node_major}" ] || [ "${node_major}" -lt 20 ]; then
    log "Installing Node.js 20 through NodeSource."
    run sudo install -d -m 0755 /etc/apt/keyrings
    if [ "${DRY_RUN}" -eq 0 ]; then
      curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
      echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
        | sudo tee /etc/apt/sources.list.d/nodesource.list >/dev/null
    else
      log "+ curl NodeSource key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg"
      log "+ write /etc/apt/sources.list.d/nodesource.list"
    fi
    run sudo apt-get update
    run sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
  fi
  corepack_bin="$(command -v corepack || true)"
  if [ -n "${corepack_bin}" ]; then
    if [[ "${corepack_bin}" == "${HOME}/"* ]]; then
      run "${corepack_bin}" enable
      run "${corepack_bin}" prepare "pnpm@${PNPM_VERSION}" --activate
    else
      run sudo "${corepack_bin}" enable
      run sudo "${corepack_bin}" prepare "pnpm@${PNPM_VERSION}" --activate
    fi
  elif ! command -v pnpm >/dev/null 2>&1; then
    install_pnpm_from_npm
  fi
}

install_pgvector_package() {
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ install postgresql-\$(server major)-pgvector for local Postgres"
    return
  fi

  local package pg_major pg_version_num
  pg_version_num="$(sudo -u postgres psql -Atqc "SHOW server_version_num")"
  pg_major="${pg_version_num:0:2}"
  package="postgresql-${pg_major}-pgvector"

  if ! apt-cache show "${package}" >/dev/null 2>&1; then
    fail "Required pgvector package ${package} is not available. Install pgvector for PostgreSQL ${pg_major}, or rerun with --skip-postgres-install and provide DATABASE_URL/DATABASE_ADMIN_URL for a Postgres instance with pgvector."
  fi

  run sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${package}"
}

prepare_postgres() {
  if [ "${SKIP_POSTGRES_INSTALL}" -eq 1 ]; then
    log "Skipping local Postgres install. Existing DATABASE_URL settings will be verified by migrations."
    return
  fi
  run sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib
  run sudo systemctl enable --now postgresql
  install_pgvector_package
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ prepare local alicebot Postgres roles/database without printing generated passwords"
    return
  fi
  command -v psql >/dev/null 2>&1 || fail "psql is not available after local Postgres install."
  sudo -u postgres psql -tc "SELECT 1" >/dev/null || fail "Postgres is not reachable as the postgres OS user."
}

sync_repo() {
  if [ -e "${INSTALL_DIR}" ] && [ ! -d "${INSTALL_DIR}/.git" ]; then
    fail "${INSTALL_DIR} exists but is not a git checkout. Choose --install-dir or move it first."
  fi
  if [ -d "${INSTALL_DIR}/.git" ]; then
    run git -C "${INSTALL_DIR}" fetch --tags origin
  else
    run mkdir -p "$(dirname "${INSTALL_DIR}")"
    run git clone "${REPO_URL}" "${INSTALL_DIR}"
  fi
  if [ -n "${TAG}" ]; then
    run git -C "${INSTALL_DIR}" checkout "tags/${TAG}"
  else
    run git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    run git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
  fi
}

random_secret() {
  openssl rand -hex 24
}

write_env_if_missing() {
  run mkdir -p "${CONFIG_DIR}" "${DATA_DIR}" "${STATE_DIR}/logs" "${SECRETS_DIR}" "${ALICE_RUNTIME_DIR}/vnext-scheduler"
  if [ -f "${ENV_FILE}" ]; then
    log "Preserving existing ${ENV_FILE}."
  else
    if [ "${DRY_RUN}" -eq 1 ]; then
      log "+ create ${ENV_FILE} from packaging/ubuntu/alicebot.env.example with generated local passwords"
    else
      local admin_password app_password
      admin_password="$(random_secret)"
      app_password="$(random_secret)"
      sed \
        -e "s#__ALICE_INSTALL_DIR__#${INSTALL_DIR}#g" \
        -e "s#__ALICE_CONFIG_DIR__#${CONFIG_DIR}#g" \
        -e "s#__ALICE_DATA_DIR__#${DATA_DIR}#g" \
        -e "s#__ALICE_STATE_DIR__#${STATE_DIR}#g" \
        -e "s#__ALICE_SECRETS_DIR__#${SECRETS_DIR}#g" \
        -e "s#__ALICEBOT_ADMIN_PASSWORD__#${admin_password}#g" \
        -e "s#__ALICEBOT_APP_PASSWORD__#${app_password}#g" \
        "${INSTALL_DIR}/packaging/ubuntu/alicebot.env.example" > "${ENV_FILE}"
      chmod 0600 "${ENV_FILE}"
    fi
  fi
  if [ -e "${INSTALL_DIR}/.env" ] && [ ! -L "${INSTALL_DIR}/.env" ]; then
    log "Preserving existing ${INSTALL_DIR}/.env."
  else
    run ln -sfn "${ENV_FILE}" "${INSTALL_DIR}/.env"
  fi
}

write_lite_env_if_missing() {
  local lite_env="${INSTALL_DIR}/.env.lite"
  if [ -f "${lite_env}" ]; then
    log "Preserving existing ${lite_env}."
  elif [ "${DRY_RUN}" -eq 1 ]; then
    log "+ create ${lite_env} from .env.lite.example"
  else
    cp "${INSTALL_DIR}/.env.lite.example" "${lite_env}"
  fi
}

validate_env_files() {
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ validate ${ENV_FILE} and ${INSTALL_DIR}/.env.lite before sourcing"
    return
  fi
  run "${INSTALL_DIR}/scripts/validate_env.sh" "${ENV_FILE}" "${INSTALL_DIR}/.env.lite"
}

write_web_env_if_missing() {
  local web_env="${INSTALL_DIR}/apps/web/.env.local"
  if [ -f "${web_env}" ]; then
    log "Preserving existing ${web_env}."
  elif [ "${DRY_RUN}" -eq 1 ]; then
    log "+ create ${web_env} with local /vnext public browser settings"
  else
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    {
      printf '# Local alpha browser settings for /vnext?mode=live.\n'
      printf '# This file contains public browser values only.\n'
      printf 'NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://%s:%s\n' "${ALICE_API_HOST:-127.0.0.1}" "${ALICE_API_PORT:-8000}"
      printf 'NEXT_PUBLIC_ALICEBOT_USER_ID=%s\n' "${NEXT_PUBLIC_ALICEBOT_USER_ID:-${ALICEBOT_AUTH_USER_ID:-00000000-0000-0000-0000-000000000001}}"
    } > "${web_env}"
  fi
}

validate_web_env_file() {
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ validate ${INSTALL_DIR}/apps/web/.env.local"
    return
  fi
  run "${INSTALL_DIR}/scripts/validate_env.sh" "${INSTALL_DIR}/apps/web/.env.local"
}

prepare_database_from_env() {
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ create alicebot database and roles from generated local env file"
    return
  fi
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  local admin_pass app_pass
  admin_pass="${DATABASE_ADMIN_URL#*alicebot_admin:}"
  admin_pass="${admin_pass%@*}"
  app_pass="${DATABASE_URL#*alicebot_app:}"
  app_pass="${app_pass%@*}"
  sudo -u postgres psql <<SQL >/dev/null
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alicebot_admin') THEN
    CREATE ROLE alicebot_admin LOGIN PASSWORD '${admin_pass}';
  ELSE
    ALTER ROLE alicebot_admin WITH LOGIN PASSWORD '${admin_pass}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alicebot_app') THEN
    CREATE ROLE alicebot_app LOGIN PASSWORD '${app_pass}';
  ELSE
    ALTER ROLE alicebot_app WITH LOGIN PASSWORD '${app_pass}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE alicebot OWNER alicebot_admin'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'alicebot')\\gexec
GRANT CONNECT ON DATABASE alicebot TO alicebot_app;
SQL
  sudo -u postgres psql -d alicebot -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
}

seed_default_user_from_env() {
  if [ "${DRY_RUN}" -eq 1 ]; then
    log "+ seed configured local Alice user row if missing"
    return
  fi
  "${INSTALL_DIR}/.venv/bin/python" - <<'PY'
import os
from uuid import UUID

import psycopg


user_id_raw = os.environ.get("ALICEBOT_AUTH_USER_ID", "").strip()
if not user_id_raw:
    raise SystemExit("ALICEBOT_AUTH_USER_ID is required before seeding the local Alice user")

try:
    user_id = UUID(user_id_raw)
except ValueError as exc:
    raise SystemExit("ALICEBOT_AUTH_USER_ID must be a valid UUID") from exc

conninfo = os.environ.get("DATABASE_ADMIN_URL") or os.environ.get("DATABASE_URL")
if not conninfo:
    raise SystemExit("DATABASE_ADMIN_URL or DATABASE_URL is required before seeding the local Alice user")

email = f"local-alpha-{user_id}@alicebot.local"
display_name = "Local Alpha User"

with psycopg.connect(conninfo) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET email = EXCLUDED.email,
                display_name = EXCLUDED.display_name
            """,
            (user_id, email, display_name),
        )
PY
}

install_project_dependencies() {
  run python3 -m venv "${INSTALL_DIR}/.venv"
  run "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
  run "${INSTALL_DIR}/.venv/bin/python" -m pip install -e "${INSTALL_DIR}[dev]"
  run env PNPM=pnpm WEB_DIR="${INSTALL_DIR}/apps/web" "${INSTALL_DIR}/scripts/pnpm_web_install.sh"
  run pnpm --dir "${INSTALL_DIR}/apps/web" build
}

run_migrations_and_checks() {
  if [ "${DRY_RUN}" -eq 0 ]; then
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
  fi
  run_in_install_dir "${INSTALL_DIR}/.venv/bin/python" -m alembic -c apps/api/alembic.ini upgrade head
  seed_default_user_from_env
  run "${INSTALL_DIR}/.venv/bin/alicebot" vnext doctor --fix-safe --ci
  if [ "${RUN_ALPHA_CHECK}" -eq 1 ]; then
    run "${INSTALL_DIR}/.venv/bin/alicebot" vnext alpha check --headless --skip-smokes
  fi
}

install_systemd_units() {
  if [ "${INSTALL_SYSTEMD}" -eq 0 ]; then
    return
  fi
  local user group service
  user="$(id -un)"
  group="$(id -gn)"
  for service in alice-api alice-web alice-scheduler; do
    if [ "${DRY_RUN}" -eq 1 ]; then
      log "+ install /etc/systemd/system/${service}.service from packaging/systemd/${service}.service"
    else
      sed \
        -e "s#__ALICE_USER__#${user}#g" \
        -e "s#__ALICE_GROUP__#${group}#g" \
        -e "s#__ALICE_INSTALL_DIR__#${INSTALL_DIR}#g" \
        -e "s#__ALICE_ENV_FILE__#${ENV_FILE}#g" \
        -e "s#__ALICE_STATE_DIR__#${STATE_DIR}#g" \
        -e "s#__ALICE_RUNTIME_DIR__#${ALICE_RUNTIME_DIR}#g" \
        "${INSTALL_DIR}/packaging/systemd/${service}.service" \
        | sudo tee "/etc/systemd/system/${service}.service" >/dev/null
    fi
  done
  run sudo systemctl daemon-reload
  log "Systemd units installed. Start them with: sudo systemctl enable --now alice-api alice-web alice-scheduler"
}

print_next_steps() {
  cat <<EOF

Alice headless Ubuntu install prepared.

Next steps:
  1. Review config: ${ENV_FILE}
  2. Start services:
       sudo systemctl enable --now alice-api alice-web alice-scheduler
  3. Check services:
       systemctl status alice-api alice-web alice-scheduler
       journalctl -u alice-api -f
  4. Tunnel from your laptop:
       ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@server
  5. Open:
       http://127.0.0.1:3000/vnext
  6. Run:
       ${INSTALL_DIR}/.venv/bin/alicebot vnext alpha check --headless --api-url http://127.0.0.1:8000/healthz --web-url http://127.0.0.1:3000/vnext
       ${INSTALL_DIR}/.venv/bin/alicebot vnext smoke agent-integration-pack

Security default: Alice services bind to 127.0.0.1. Use SSH tunneling first; do not expose /vnext publicly without adding your own authenticated reverse proxy.
EOF
}

require_ubuntu
install_system_packages
install_node_and_pnpm
prepare_postgres
sync_repo
write_env_if_missing
write_lite_env_if_missing
validate_env_files
write_web_env_if_missing
validate_web_env_file
if [ "${SKIP_POSTGRES_INSTALL}" -eq 0 ]; then
  prepare_database_from_env
fi
install_project_dependencies
run_migrations_and_checks
install_systemd_units
print_next_steps
