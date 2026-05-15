# Public Alpha Quickstart

This path is for a fresh technical local setup. It does not require internal sprint notes.

## Requirements

- Python 3.12+
- Node 20+
- pnpm
- Docker Desktop or compatible Docker engine
- Git

## One-command Setup

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
make setup
make migrate
make doctor
```

Expected success:

- Python dependencies install into `.venv`
- `.env`, `.env.lite`, and `apps/web/.env.local` are created from the checked-in examples when missing
- web dependencies install under `apps/web`
- Docker services start
- migrations finish
- doctor returns `pass` or a warning without blocking failures

## Start Alice

Run API and web together:

```bash
make dev
```

Or use separate terminals:

```bash
APP_RELOAD=false ./scripts/api_dev.sh
pnpm --dir apps/web dev
alicebot vnext scheduler daemon start --foreground
```

Open:

```text
http://localhost:3000/vnext
```

Local live `/vnext` uses explicit browser/API settings. Keep both frontend origins in the API CORS allowlist and keep the browser API URL pointed at localhost:

```dotenv
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ALICEBOT_USER_ID=00000000-0000-0000-0000-000000000001
```

Use the same user id as `ALICEBOT_AUTH_USER_ID`. If a manual alpha seed uses `local-alpha-user`, set `NEXT_PUBLIC_ALICEBOT_USER_ID=local-alpha-user` for that environment.

## First Smoke

```bash
alicebot vnext smoke operator-console
alicebot vnext smoke local-cors
alicebot vnext smoke agent-integration-pack
alicebot vnext smoke agentic-memory-commit
alicebot vnext alpha check
```

If `alicebot` is not on your shell path, use:

```bash
./.venv/bin/alicebot vnext alpha check
```

## Load Safe Demo Data

```bash
alicebot vnext demo load --reset
```

Expected success:

- synthetic sources appear in `/vnext` Inbox
- candidate memories appear in Memory Review
- generated artifacts appear in Generated
- Agent Activity shows OpenClaw demo activity and a restricted-domain policy block
- Trace shows source-to-artifact provenance

Reset the demo:

```bash
alicebot vnext demo reset
```
