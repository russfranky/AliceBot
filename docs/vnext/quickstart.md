# vNext Quickstart

This path is designed for a fresh local install and a first daily brief in under 20 minutes.

## Requirements

- macOS or Linux shell
- Python 3.12+
- Node 20+
- pnpm
- Docker Desktop or compatible Docker engine for the full local stack

## Install

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
cp .env.example .env
cp .env.lite.example .env.lite
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
pnpm --dir apps/web install
```

## Fast Local Path

Use Alice Lite when you want the fastest continuity smoke path:

```bash
./scripts/alice_lite_up.sh
./.venv/bin/python scripts/bootstrap_alice_lite_workspace.py
./.venv/bin/python -m alicebot_api brief --brief-type general --query "local-first startup path"
```

## Full Local Stack

Use Docker for Postgres, Redis, and MinIO-backed local development:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
alicebot vnext migrations status
alicebot vnext doctor --fix-safe
```

Run the API and web app in separate terminals:

```bash
APP_RELOAD=false ./scripts/api_dev.sh
pnpm --dir apps/web dev
```

Open:

```text
http://localhost:3000/vnext
```

## First vNext Daily Brief

Capture source evidence:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "sources", "capture-text", "TODO: confirm launch checklist owner", "--domain", "project", "--sensitivity", "private"]))'
```

Generate a daily brief:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["daily-brief", "--generate", "--domain", "project", "--generated-for", "2026-05-11"]))'
```

If your local console scripts are installed, the equivalent commands are:

```bash
alicebot vnext sources capture-text "TODO: confirm launch checklist owner" --domain project --sensitivity private
alicebot daily-brief --generate --domain project --generated-for 2026-05-11
```

## Live Capture Connector Demo

List vNext connectors and health:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "connectors", "list"]))'
alicebot vnext connectors health
alicebot vnext connectors status
```

Configure Telegram with either an environment reference or the local encrypted secret store. Neither command prints the token value:

```bash
alicebot vnext connectors telegram configure \
  --enabled \
  --allowed-chat-id 999001 \
  --secret-ref env:TELEGRAM_BOT_TOKEN

alicebot vnext connectors telegram configure \
  --enabled \
  --allowed-chat-id 999001 \
  --bot-token "$TELEGRAM_BOT_TOKEN"

alicebot vnext connectors telegram test
```

Capture a browser clip directly into the review path:

```bash
alicebot vnext connectors browser-clipper capture \
  --url https://example.test/launch-note \
  --selected-text "Fact: Alice vNext live browser clips preserve raw evidence." \
  --user-note "Review this before promotion." \
  --domain project \
  --sensitivity private
```

Scan a local Markdown/Text folder:

```bash
alicebot vnext connectors local-folder add-path ~/Notes/Alice --extension .md --extension .txt
alicebot vnext connectors local-folder sync
```

Ingest an agent output as review-only source evidence:

```bash
alicebot vnext agents ingest-output \
  --agent-id openclaw \
  --agent-type coding_agent \
  --title "Sprint summary" \
  --content "Decision: agent output should remain review-only." \
  --propose-memory \
  --domain project \
  --sensitivity private
```

Run the live connector smoke:

```bash
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor
```

## Connector Payload Demo

Ingest a deterministic browser clip payload after creating `clip.json`:

```json
{
  "items": [
    {
      "external_id": "clip-demo-1",
      "cursor": "1",
      "title": "Launch note",
      "url": "https://example.test/launch-note",
      "text": "Fact: Alice vNext connector payloads preserve raw evidence."
    }
  ]
}
```

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "connectors", "ingest", "browser_clipper", "clip.json", "--domain", "learning", "--sensitivity", "private"]))'
```

## Baseline Verification

Run the core checks used by the release checklist:

```bash
./.venv/bin/python -m pytest tests/unit -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
python3 scripts/check_control_doc_truth.py
git diff --check
```
