# Public Alpha Local Runtime

The alpha runtime is local and technical. It runs Postgres, Redis, API, web, and the optional scheduler daemon on the user machine.

## Commands

```bash
make setup
make migrate
make doctor
make dev
make alpha-check
```

Equivalent explicit commands:

```bash
docker compose up -d
./scripts/migrate.sh
alicebot vnext doctor --fix-safe --ci
APP_RELOAD=false ./scripts/api_dev.sh
pnpm --dir apps/web dev
alicebot vnext scheduler daemon start --foreground
```

## Runtime URLs

- API: `http://localhost:8000`
- vNext operator console: `http://localhost:3000/vnext`
- MCP server: stdio process via `alicebot-mcp`

## Alpha Readiness

```bash
alicebot vnext alpha check
```

The readiness check summarizes migrations, doctor, scheduler posture, connector settings/state storage, core vNext smokes, agent integration smoke, and the eval command expected for release evidence.
