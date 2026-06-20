# Public Alpha Local Runtime

The alpha runtime is local and technical. It runs Postgres, Redis, API, web, and the optional scheduler daemon on the user machine.

## Commands

```bash
make setup
make migrate
make doctor
make runtime
make alpha-check
alicebot vnext alpha check --headless
alicebot vnext smoke headless-ubuntu
```

`make runtime` is the recommended low-CPU local mode. It builds the web app and serves `/vnext` with `next start`. Use `make dev` only for web UI development.

For API-only agent or Hermes sessions, use `make api` and skip the web process entirely.

Equivalent explicit development commands:

```bash
./scripts/dev_up.sh
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

For Ubuntu systemd service setup, use [headless-ubuntu-install.md](headless-ubuntu-install.md). The default headless posture binds API and web services to `127.0.0.1` and expects `/vnext` access through an SSH tunnel.

## Alpha Readiness

```bash
alicebot vnext alpha check
alicebot vnext alpha check --headless
```

The readiness check summarizes migrations, doctor, scheduler posture, connector settings/state storage, core vNext smokes, agent integration smoke, and the eval command expected for release evidence.
