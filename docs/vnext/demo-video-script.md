# vNext Demo Video Script

Target length: 3 to 5 minutes.

## 1. Opening

Show the repo root and say:

```text
Alice vNext is a local-first second brain for AI agents. It preserves raw evidence, proposes memories for review, generates daily and weekly brain artifacts, and exposes the same continuity through CLI, API, MCP, and the web workspace.
```

## 2. Install and Start

Show:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
```

Then mention Alice Lite as the faster local profile:

```bash
./scripts/alice_lite_up.sh
```

## 3. Capture Evidence

Show:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "sources", "capture-text", "TODO: confirm launch checklist owner", "--domain", "project", "--sensitivity", "private"]))'
```

Call out that raw text is preserved before chunking and candidate memory extraction.

## 4. Generate a Daily Brief

Show:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["daily-brief", "--generate", "--domain", "project", "--generated-for", "2026-05-11"]))'
```

Call out source references, reviewable artifact status, open loops, and sensitivity inheritance.

## 5. Connector Payload

Show:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "connectors", "list"]))'
```

Then show a browser clip JSON payload and explain:

```text
The connector seed ingests already-exported payloads. It does not perform live OAuth or remote polling in this preview.
```

## 6. Web Workspace

Open:

```text
http://localhost:3000/vnext
```

Show:

- Inbox review
- Ask Alice answer with provenance
- Daily Brief and Weekly Synthesis
- Open Loops
- Connection Graph
- Connector Settings

## 7. Evals and Release Gate

Show:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'
./.venv/bin/python -m pytest tests/unit -q
pnpm --dir apps/web test
```

Close with:

```text
Alice vNext is not a generic notes app. It is private, correctable, inspectable continuity for humans and agents.
```
