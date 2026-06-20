# Public Alpha Troubleshooting

## `alicebot` Command Not Found

```bash
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/alicebot --help
```

## Database Connection Fails

```bash
docker compose up -d
./scripts/migrate.sh
alicebot vnext migrations status
```

## Doctor Has Blocking Failures

```bash
alicebot vnext doctor --fix-safe --ci
```

Read `recommended_fixes` in the JSON output.

## `/vnext` Loads Empty

Run:

```bash
alicebot vnext demo load --reset
```

Then refresh `http://localhost:3000/vnext`.

## `/vnext` Shows LIVE API But Load Failed

If `/vnext?mode=live` shows `LIVE API` and then `Unable to load live workspace: Load failed`, the API may be healthy but the browser is blocked by CORS.

Check the API directly:

```bash
curl -i "http://127.0.0.1:8000/v0/vnext/workspace?user_id=${NEXT_PUBLIC_ALICEBOT_USER_ID:-local-alpha-user}"
```

Check the browser preflight:

```bash
curl -i -X OPTIONS "http://127.0.0.1:8000/v0/vnext/workspace?user_id=${NEXT_PUBLIC_ALICEBOT_USER_ID:-local-alpha-user}" \
  -H "Origin: http://127.0.0.1:3000" \
  -H "Access-Control-Request-Method: GET"
```

Expected success includes:

```text
Access-Control-Allow-Origin: http://127.0.0.1:3000
```

Local alpha config should include:

```dotenv
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ALICEBOT_USER_ID=00000000-0000-0000-0000-000000000001
```

Use the same user id as `ALICEBOT_AUTH_USER_ID`. If your manual seed really uses `local-alpha-user`, set `NEXT_PUBLIC_ALICEBOT_USER_ID=local-alpha-user`.

After changing `CORS_ALLOWED_ORIGINS`, restart the API. After changing `NEXT_PUBLIC_*`, restart the web dev server or rebuild/restart the web service.

Run:

```bash
alicebot vnext smoke local-cors
alicebot vnext doctor --fix-safe --ci
```

## Next.js Dev Server Uses CPU While Idle

If Activity Monitor shows `next-server` using noticeable CPU while Alice is idle, check whether it was started through `make dev` or `pnpm --dir apps/web dev`. That mode runs the Next.js development watcher and compiler, which can keep native `next-swc` worker activity alive even when no agent work is happening.

If the agent only needs Alice's API/MCP surface and not the web UI, stop the web process and run only:

```bash
make api
```

If you want `/vnext` open for a long-running local agent or Hermes session, stop the dev server and run:

```bash
make runtime
```

This builds the web app and serves `/vnext` with `next start`, which is the low-CPU runtime path. Keep `make dev` for active web UI development where hot reload matters.

## `/vnext` Fails With `Cannot find module './316.js'`

If the web server returns a 500 for `/vnext?mode=live` with an error like `Cannot find module './316.js'` from `.next/server/webpack-runtime.js`, the local Next.js dev cache is stale or mixed across builds.

Check that the API is still healthy:

```bash
curl -i "http://127.0.0.1:8000/healthz"
```

Then restart the web server with a clean generated cache:

```bash
pnpm --dir apps/web dev:clean
```

If a dev server is already running, stop it first with `Ctrl-C`, then run the command again. This removes only `apps/web/.next`, which is generated build output; it does not remove source files, env files, or local data.

## Agent Policy Blocked

Common reasons:

- project-scoped agent requested restricted domains
- read-only agent attempted a write action
- agent requested high sensitivity not allowed by its profile
- agent tried to bypass proposal-only memory writes

Fix by narrowing domain/sensitivity, adding project scope, or using a stronger permission profile only when explicitly allowed.

## Secrets

Never paste secret values into bug reports. Use secret refs:

```bash
alicebot vnext connectors telegram configure --secret-ref env:TELEGRAM_BOT_TOKEN --allowed-chat-id 123456
```
