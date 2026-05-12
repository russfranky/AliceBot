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
cp .env.example .env
cp .env.lite.example .env.lite
make setup
make migrate
make doctor
```

Expected success:

- Python dependencies install into `.venv`
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

## First Smoke

```bash
alicebot vnext smoke operator-console
alicebot vnext smoke agent-integration-pack
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
