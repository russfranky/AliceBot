#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/alicebot"
CONFIG_DIR="${HOME}/.config/alicebot"
DATA_DIR="${HOME}/.local/share/alicebot"
STATE_DIR="${HOME}/.local/state/alicebot"
REMOVE_REPO=0
REMOVE_CONFIG=0
REMOVE_DATA=0
DROP_DATABASE=0
NON_INTERACTIVE=0
DRY_RUN=0

log() {
  printf '[alice-uninstall] %s\n' "$*"
}

fail() {
  printf '[alice-uninstall] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Safely stop or uninstall headless Alice Ubuntu services.

By default this script only disables/stops services and preserves repo, config,
data, database, and local secret references.

Options:
  --install-dir PATH      Alice repo directory. Defaults to ~/alicebot.
  --config-dir PATH       Config directory. Defaults to ~/.config/alicebot.
  --remove-repo           Delete the Alice repo directory after confirmation.
  --remove-config         Delete config and local secret references after confirmation.
  --remove-data           Delete local Alice data/state directories after confirmation.
  --drop-database         Drop local alicebot database and roles after confirmation.
  --non-interactive       Fail instead of prompting for destructive actions.
  --dry-run               Print planned commands without changing the host.
  -h, --help              Show this help.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --config-dir)
      CONFIG_DIR="${2:-}"
      shift 2
      ;;
    --remove-repo)
      REMOVE_REPO=1
      shift
      ;;
    --remove-config)
      REMOVE_CONFIG=1
      shift
      ;;
    --remove-data)
      REMOVE_DATA=1
      shift
      ;;
    --drop-database)
      DROP_DATABASE=1
      shift
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
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

run() {
  log "+ $*"
  if [ "${DRY_RUN}" -eq 0 ]; then
    "$@"
  fi
}

confirm() {
  local prompt="$1"
  if [ "${NON_INTERACTIVE}" -eq 1 ]; then
    fail "${prompt} Re-run without --non-interactive or omit the destructive flag."
  fi
  read -r -p "${prompt} Type DELETE to continue: " answer
  if [ "${answer}" != "DELETE" ]; then
    fail "Operator cancelled."
  fi
}

stop_services() {
  if command -v systemctl >/dev/null 2>&1; then
    run sudo systemctl disable --now alice-api alice-web alice-scheduler || true
    run sudo rm -f /etc/systemd/system/alice-api.service /etc/systemd/system/alice-web.service /etc/systemd/system/alice-scheduler.service
    run sudo systemctl daemon-reload
  else
    log "systemctl is not available; skip service removal."
  fi
}

reset_demo_data() {
  if [ -x "${INSTALL_DIR}/.venv/bin/alicebot" ]; then
    run "${INSTALL_DIR}/.venv/bin/alicebot" vnext demo reset || true
    run "${INSTALL_DIR}/.venv/bin/alicebot" vnext doctor --fix-safe --ci || true
  else
    log "Alice virtualenv not found; skip demo reset and doctor."
  fi
}

drop_database() {
  if [ "${DROP_DATABASE}" -eq 0 ]; then
    return
  fi
  confirm "Drop local alicebot database and alicebot roles?"
  run sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'alicebot';"
  run sudo -u postgres dropdb --if-exists alicebot
  run sudo -u postgres dropuser --if-exists alicebot_app
  run sudo -u postgres dropuser --if-exists alicebot_admin
}

remove_paths() {
  if [ "${REMOVE_REPO}" -eq 1 ]; then
    confirm "Delete Alice repo directory ${INSTALL_DIR}?"
    run rm -rf "${INSTALL_DIR}"
  fi
  if [ "${REMOVE_CONFIG}" -eq 1 ]; then
    confirm "Delete Alice config and local secret references under ${CONFIG_DIR}?"
    run rm -rf "${CONFIG_DIR}"
  fi
  if [ "${REMOVE_DATA}" -eq 1 ]; then
    confirm "Delete Alice local data/state under ${DATA_DIR} and ${STATE_DIR}?"
    run rm -rf "${DATA_DIR}" "${STATE_DIR}"
  fi
}

stop_services
reset_demo_data
drop_database
remove_paths

cat <<EOF

Alice services are stopped and disabled.
Preserved by default:
  repo: ${INSTALL_DIR}
  config/secrets: ${CONFIG_DIR}
  data: ${DATA_DIR}
  state/logs: ${STATE_DIR}
  database: alicebot

Use explicit --remove-* or --drop-database flags for destructive cleanup.
EOF
