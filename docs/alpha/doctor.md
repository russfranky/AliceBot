# Doctor-first Onboarding

Run doctor before dogfooding and before asking an agent to rely on Alice.

```bash
alicebot vnext doctor --fix-safe --ci
```

Doctor checks:

- required vNext migration tables
- connector settings rows
- connector state rows
- Telegram secret reference posture
- scheduler daemon posture
- connector failure posture
- local `/vnext?mode=live` CORS posture when a browser API URL is configured

Expected success:

- `blocking_failure_count` is `0`
- status is `pass` or `warn`
- warnings include a recommended fix
- no secret value appears in output

Common fixes:

```bash
./scripts/migrate.sh
alicebot vnext doctor --fix-safe --ci
alicebot vnext connectors telegram configure --secret-ref env:TELEGRAM_BOT_TOKEN --allowed-chat-id 123456
alicebot vnext scheduler daemon start --foreground --once
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
```

Use the broader alpha gate when doctor is clean:

```bash
alicebot vnext alpha check
```
