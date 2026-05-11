# vNext Dogfood Daily Checklist

Use this checklist before relying on Alice vNext for daily local-alpha use. The goal is to keep the capture loop boring: source evidence enters Alice, remains review-only, can be retrieved into briefs, and exposes failures quickly.

## Start Of Day

1. Apply migrations and confirm required tables:

   ```bash
   ./scripts/migrate.sh
   alicebot vnext migrations status
   ```

2. Run the local readiness doctor:

   ```bash
   alicebot vnext doctor --fix-safe
   ```

3. Check connector posture:

   ```bash
   alicebot vnext connectors status
   alicebot vnext connectors health
   alicebot vnext dogfooding dashboard
   ```

4. If Telegram is enabled, verify the secret reference resolves without printing the token:

   ```bash
   alicebot vnext connectors telegram test
   ```

5. If the scheduler is enabled locally, verify daemon status:

   ```bash
   alicebot vnext scheduler daemon status
   alicebot vnext scheduler failures
   ```

## Capture Checks

Use the narrowest connector needed for the day:

```bash
alicebot vnext connectors telegram sync --allowed-chat-id 999001 --retries 3
alicebot vnext connectors local-folder sync
alicebot vnext connectors browser-clipper capture \
  --url https://example.test/day-note \
  --selected-text "Fact: daily dogfood capture is review-only." \
  --domain project \
  --sensitivity private
```

After capture, confirm that new evidence appears as source-backed review material rather than trusted memory:

```bash
alicebot context-pack "today dogfood capture" --domain project --sensitivity-allowed private
alicebot daily-brief --generate --domain project --generated-for 2026-05-11
```

## Reliability Smokes

Run these after connector config changes, migration changes, or before a release branch is pushed:

```bash
alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler
```

## Failure Triage

- Missing `connector_settings` or `connector_state`: run `./scripts/migrate.sh`, then `alicebot vnext doctor --fix-safe`.
- Telegram secret unresolved: update `--secret-ref env:TELEGRAM_BOT_TOKEN` or store a local token with `--bot-token`.
- Repeated Telegram rejections: verify `--allowed-chat-id` values before live polling.
- Local folder recapture noise: check ignored generated folders, extensions, and allowed roots.
- Browser clipper unauthorized: pass the configured local capture token or clear the browser clipper `secret_ref`.
- Scheduler stale or failing: inspect `alicebot vnext scheduler failures`, then keep generated artifacts review-only until the root cause is fixed.

## Non-Negotiables

- No connector source becomes trusted memory without review.
- No token value belongs in event logs, source metadata, artifact metadata, CLI output, API responses, or UI state.
- Failed connector items should be isolated and should not advance cursors past unprocessed data unless the item was explicitly safe to skip.
- Alice-generated artifacts and dependency folders should not be re-ingested as new source truth.
