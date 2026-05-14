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
