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
