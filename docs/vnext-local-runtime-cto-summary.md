# Alice vNext Local Runtime: CTO Summary

Date: 2026-05-11
Audience: CTO / technical leadership
Phase artifact: vNext local runtime scheduler
Branch: `codex/local-runtime-scheduler`

## Executive Summary

This phase turns the governed vNext scheduler into an operational local runtime. Alice can now run in the background, poll for due Brain workflows, avoid duplicate concurrent runs, produce reviewable artifacts for all scheduled workflow types, and expose scheduler and agent-policy telemetry in the `/vnext` operator workspace.

The important product shift is that Alice vNext is no longer only a manually triggered preview. It now has the local process model needed for dogfooding: the scheduler can run due work on its own, recover across restarts through persisted workflow/run state, show failures and run history, and preserve the no-auto-promotion and policy-audit controls from the agentic control plane.

## What We Built

### Local Scheduler Runtime

- Added a local daemon module for foreground, one-shot, and background scheduler operation.
- Added pid, status, heartbeat, due-scan, error, and log-file handling under `~/.alicebot/vnext-scheduler` by default.
- Added CLI controls:
  - `alicebot vnext scheduler daemon start`
  - `alicebot vnext scheduler daemon start --foreground`
  - `alicebot vnext scheduler daemon start --foreground --once`
  - `alicebot vnext scheduler daemon status`
  - `alicebot vnext scheduler daemon stop`
- Added `alicebot vnext scheduler runs` and `alicebot vnext scheduler failures`.
- Added macOS launchd and Linux systemd templates for local service installation.

### Scheduler Hardening

- Added a per-workflow Postgres advisory lock so concurrent due scans skip a workflow already being run.
- Preserved disabled-by-default behavior.
- Preserved pause/resume behavior.
- Preserved disabled workflow exclusion.
- Added richer scheduler status: last due scan, next due workflow, currently running workflow, recent failures, last successful run per workflow, and expanded recent run history.
- Added failure capture that records failed run state and workflow `last_error` without crashing the scheduler loop.

### Full Scheduled Workflow Coverage

Daily Brief and Weekly Synthesis remained scheduled, reviewable workflows.

This phase completed deterministic scheduled artifacts for the remaining workflow types:

- `connection_report`
- `contradiction_report`
- `open_loop_review`
- `project_update_scan`

Every scheduled artifact is review-only and carries scheduler metadata: `generated_by`, `workflow_type`, `scheduler_run_id`, `trace_id`, `source_refs`, `domain`, `sensitivity`, and `review_status`.

### Agent Policy Telemetry

- Added policy decision records that retain requested domains and sensitivity filters as well as effective filters.
- Added a telemetry summary for:
  - policy blocks by agent
  - policy filters by agent
  - requires-review decisions by agent
  - restricted domains requested
  - workflows triggered by agents
  - memory proposals by agent
  - artifact generation by agent
- Exposed telemetry through:
  - `alicebot vnext agents policy-telemetry`
  - `GET /v0/vnext/agents/policy-telemetry`
  - the `/vnext` Agent Activity surface

### Live Operator Workspace

- Extended `/vnext` Schedules with daemon state, last due scan, last due count, next due workflow, current run, recent failures, last successful run per workflow, run-due control, and run history.
- Extended `/vnext` Agent Activity with aggregated policy telemetry.
- Kept demo/fixture mode available while making live workspace payloads the source for scheduler, agent activity, timeline, generated artifacts, memory review, projects, and open loops when API configuration exists.

### Local Runtime Smoke

- Added `alicebot vnext smoke local-runtime`.
- The smoke seeds a small Postgres-backed local-runtime fixture, marks all six workflows due, runs the foreground daemon once, and verifies that every scheduled workflow produces a reviewable artifact with scheduler metadata.

## Guardrails Preserved

- No scheduled workflow auto-promotes artifacts into trusted memory.
- Agent memory writes remain proposal/review-only.
- Existing agent permission rules remain enforced.
- Restricted domains and high-sensitivity scopes remain filtered or blocked by policy.
- Scheduler configuration and global controls remain policy checked.
- The local daemon is explicitly not a hosted scheduler service.

## Operator Takeaways

- Alice can now run locally in the background and execute governed work without manual CLI invocation.
- The scheduler has enough visibility for dogfooding: status, history, failure state, daemon heartbeat, and event-log traces.
- All proactive Brain workflows now produce concrete reviewable outputs instead of placeholder scheduler scaffolding.
- Agent telemetry gives us the first useful view into how Hermes/OpenClaw-style callers interact with policy gates.
- The next product decision should be based on dogfooding signal: either deepen model-backed intelligence or move into live connector auth/polling.

## Validation Evidence

Current local validation performed during this phase:

- Python compile checks for scheduler runtime, scheduler service, CLI, API, store, Brain workflows, and project/connection/contradiction services: passed.
- Focused local-runtime unit tests: `37 passed`.
- Full Python unit suite: `1077 passed`.
- Full Python integration suite: `370 passed`.
- Web test suite: `207 passed`.
- Web lint: passed.
- Web production build: passed and built `/vnext`.
- `alicebot vnext smoke agentic-scheduler`: passed.
- `alicebot vnext smoke local-runtime`: passed, including all six scheduled workflows and daemon one-shot due scan.
- Background daemon start/status/stop probe: passed with temporary pid/status/log paths and a long polling interval.
- Live Postgres advisory-lock probe: passed, confirming duplicate same-workflow due runs are skipped while another transaction holds the workflow lock.
- `alicebot eval run --suite all`: `170/170` passed, with `0` critical privacy leaks and `0` prompt-injection tool writes.
- `git diff --check`: passed.
