# Alice vNext Local Runtime

Alice vNext now includes a local scheduler runtime for running governed Alice Brain workflows in the background. This is a local alpha runtime, not a hosted scheduler service.

## What It Runs

The daemon wraps:

```bash
alicebot vnext scheduler daemon start
```

In foreground mode, it polls `alicebot vnext scheduler run-due` behavior on an interval and persists status to `~/.alicebot/vnext-scheduler/scheduler-status.json`. In background mode, it spawns the same foreground worker as a local process and records a pid file, status file, and log file.

## Commands

```bash
alicebot vnext scheduler daemon start
alicebot vnext scheduler daemon start --foreground
alicebot vnext scheduler daemon start --foreground --once
alicebot vnext scheduler daemon status
alicebot vnext scheduler daemon stop
alicebot vnext scheduler runs
alicebot vnext scheduler failures
alicebot vnext agents policy-telemetry
alicebot vnext smoke local-runtime
alicebot vnext smoke model-backed
alicebot vnext connectors status
alicebot vnext connectors health
alicebot vnext dogfooding dashboard
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
```

Useful options:

- `--interval-seconds`: due-scan polling interval. Default: `60`.
- `--limit`: maximum due workflows per scan. Default: `10`.
- `--pid-file`: daemon pid path. Default: `~/.alicebot/vnext-scheduler/scheduler.pid`.
- `--status-file`: daemon status JSON path. Default: `~/.alicebot/vnext-scheduler/scheduler-status.json`.
- `--log-file`: daemon log path. Default: `~/.alicebot/vnext-scheduler/scheduler.log`.

## Scheduler Guarantees

- Workflows remain disabled by default.
- Disabled workflows are not run.
- Paused workflows are not run.
- Due scans use a per-workflow Postgres advisory lock to avoid duplicate concurrent runs for the same workflow.
- Daily Brief and Weekly Synthesis scheduled runs still produce reviewable generated artifacts.
- Connection Report, Contradiction Report, Open Loop Review, and Project Update Scan now produce deterministic reviewable artifacts from scheduled runs.
- Scheduled artifacts include scheduler trace metadata: `generated_by`, `workflow_type`, `scheduler_run_id`, `trace_id`, `source_refs`, `domain`, `sensitivity`, and `review_status`.
- Scheduled workflows can run with `--generation-mode deterministic` or `--generation-mode model_backed`. Model-backed scheduled runs store prompt hashes, input context hashes, provider/model metadata, source-grounded sections, and routing policy.
- Generated artifacts and agent proposals are not auto-promoted into trusted memory.

## Operator Visibility

The `/vnext` Schedules surface shows daemon posture, last due scan, next due workflow, currently running workflow, recent failures, last successful run per workflow, and run history. The Timeline surface remains backed by the append-only event log. Agent Activity includes policy blocks, filters, review-gated decisions, workflow triggers, memory proposals, and artifact generation telemetry.

The `/vnext` Home and Connectors surfaces also show dogfooding and capture health: captures by connector, captures today/week, candidate memory creation, artifact ratings, useful-insight feedback, connector enabled/configured state, cursors, dedupe, failures, and last sync posture.

The API exposes the same local runtime posture through:

- `GET /v0/vnext/scheduler/status`
- `GET /v0/vnext/scheduler/runs`
- `GET /v0/vnext/scheduler/failures`
- `POST /v0/vnext/scheduler/run-due`
- `GET /v0/vnext/agents/policy-telemetry`
- `GET /v0/vnext/connectors/health`
- `GET /v0/vnext/dogfooding`

Scheduler workflow configuration can also carry `model_options` so due scans run model-backed workflows only when policy and routing allow them.

## macOS launchd

Use [docs/runbooks/vnext-local-scheduler.launchd.plist](../runbooks/vnext-local-scheduler.launchd.plist) as the template. Replace the paths, `ALICE_DATABASE_URL`, and `ALICE_USER_ID` values before loading it.

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.alicebot.vnext-scheduler.plist
launchctl kickstart -k gui/$(id -u)/com.alicebot.vnext-scheduler
launchctl bootout gui/$(id -u)/com.alicebot.vnext-scheduler
```

## Linux systemd

Use [docs/runbooks/vnext-local-scheduler.service](../runbooks/vnext-local-scheduler.service) as the template. Replace the working directory, environment variables, user, and venv path before enabling it.

```bash
systemctl --user daemon-reload
systemctl --user enable --now alicebot-vnext-scheduler.service
systemctl --user status alicebot-vnext-scheduler.service
systemctl --user stop alicebot-vnext-scheduler.service
```

## Validation

The local runtime smoke is Postgres-backed:

```bash
alicebot vnext smoke local-runtime
alicebot vnext smoke model-backed
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
```

It seeds a small local-runtime fixture, marks all six scheduler workflows due, runs the foreground daemon once, and checks that each workflow produces a reviewable artifact with scheduler metadata.

The model-backed smoke seeds a scheduled model-backed workflow and verifies that the due scan creates a reviewable artifact with local-only routing, provider metadata, source references, and the required grounded output sections.

The live-capture connector smoke verifies allowlisted Telegram import, rejected Telegram chat isolation, local folder import with generated-folder ignore rules, browser clipper capture, review-only agent output ingestion, and connector health telemetry. The capture-to-brief smoke verifies that a fresh browser clip can enter retrieval, produce a reviewable Daily Brief, record a quality rating, and show up in dogfooding telemetry.
