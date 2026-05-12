#!/usr/bin/env bash
set -euo pipefail

PNPM_BIN="${PNPM:-pnpm}"
WEB_DIR="${WEB_DIR:-apps/web}"

if ! "${PNPM_BIN}" --version >/dev/null 2>&1; then
  echo "pnpm is not available. Install pnpm or run through the Ubuntu installer." >&2
  exit 1
fi

echo "[alice-setup] Installing web dependencies in ${WEB_DIR} with pnpm approved-builds allowlist."
exec "${PNPM_BIN}" --dir "${WEB_DIR}" install
