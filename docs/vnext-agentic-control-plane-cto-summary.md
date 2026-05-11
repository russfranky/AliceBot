# Alice vNext Agentic Control Plane: CTO Summary

Date: 2026-05-11
Audience: CTO / technical leadership
Phase artifact: vNext agentic control plane and governed local scheduler
Branch: `codex/agentic-control-plane-scheduler`
PR: https://github.com/samrusani/AliceBot/pull/199
Merge commit: pending until squash merge

## Executive Summary

This phase turns Alice vNext from a human-operated second-brain preview into an agent-operable control plane. Agents can now identify themselves, request context, propose memory, trigger governed workflows, and inspect scheduler state through CLI, API, and MCP without receiving direct write access to trusted memory.

The important architectural shift is that agent activity is now explicit, policy checked, and auditable. Alice records who acted, what permission profile was used, which filters were applied, which actions were blocked, and which generated artifacts require review. The scheduler is local and governed: workflows are disabled by default, can be enabled/configured by policy, run into reviewable artifacts, and can be triggered either manually or by local due scans when `next_run_at` arrives.

## What We Built

### Agent Control Plane

- Added agent identities with `agent_id`, `agent_type`, `agent_run_id`, `task_id`, `project_scope`, and `permission_profile`.
- Added permission profiles: `read_only_agent`, `project_scoped_agent`, `trusted_local_agent`, `memory_proposal_agent`, and `admin_agent`.
- Added policy decisions: `allowed`, `allowed_with_filtering`, `requires_review`, and `blocked`.
- Added policy event logging for decisions, filtering, and blocked actions.
- Preserved no-auto-promotion: agents can propose memory and generate artifacts, but trusted memory changes still require review.

### Governed Scheduler

- Added persistent scheduler workflow and run state in Postgres.
- Added disabled-by-default workflows for `daily_brief`, `weekly_synthesis`, `connection_report`, `contradiction_report`, `open_loop_review`, and `project_update_scan`.
- Added schedule validation, timezone-aware `next_run_at`, run history, trace IDs, failure capture, and last-result state.
- Added local due scans that run enabled, unpaused workflows when `next_run_at` is due, then advance or clear the next run timestamp.
- Kept scheduler outputs reviewable. Daily and weekly workflows produce generated artifacts; other workflow types have deterministic report scaffolds for this sprint.

### API Surface

- Added agent memory proposal support through `POST /v0/vnext/memory-proposals`.
- Added scheduler status and run history:
  - `GET /v0/vnext/scheduler/status`
  - `GET /v0/vnext/scheduler/runs`
- Added scheduler configuration and execution:
  - `PATCH /v0/vnext/scheduler/workflows/{workflow_type}`
  - `POST /v0/vnext/scheduler/workflows/{workflow_type}/run-now`
  - `POST /v0/vnext/scheduler/run-due`
  - `POST /v0/vnext/scheduler/pause`
  - `POST /v0/vnext/scheduler/resume`
- Updated the vNext workspace payload with agent activity and scheduler state.

### MCP Surface

- Added agent-native vNext tools for capture, queueing, artifact generation, project dashboards, open loops, recent decisions/changes, connection and contradiction discovery, memory proposals, review item lookup, artifact lookup/review, and scheduler control.
- Added scheduler MCP tools:
  - `alice_vnext_scheduler_status`
  - `alice_vnext_scheduler_run_now`
  - `alice_vnext_scheduler_run_due`
  - `alice_vnext_scheduler_pause`
  - `alice_vnext_scheduler_resume`
- Ensured blocked MCP policy decisions are logged before the tool returns a permission error.

### CLI Surface

- Added shared vNext agent arguments: `--agent-id`, `--agent-type`, `--agent-run-id`, `--agent-task-id`, `--project-scope`, and `--permission-profile`.
- Added `alicebot vnext agents propose-memory`.
- Added scheduler commands:
  - `alicebot vnext scheduler status`
  - `alicebot vnext scheduler run-now`
  - `alicebot vnext scheduler run-due`
  - `alicebot vnext scheduler pause`
  - `alicebot vnext scheduler resume`
- Added `alicebot vnext smoke agentic-scheduler`, a Postgres-backed sprint smoke that verifies defaults, proposal-only memory writes, scheduler runs, due scans, policy blocks, pause/resume, and run history.

### Web Workspace

- Added `/vnext` Agent Activity and Schedules views.
- Exposed agent identities, permission posture, recent agent events, policy blocks/filters, generated/proposed work, workflow state, enable/disable controls, pause/resume, run-now, schedule editing, and recent scheduler runs.
- Aligned fixture values with schema-backed vNext enums.
- Completed the Sprint 11 connector fixture list: Telegram, browser, PDF, DOCX, CSV, screenshot OCR, and voice.

### Review Fixes And Hardening

- Normalized UUID and datetime values before JSON serialization and event hashing.
- Fixed explicit CLI sensitivity filters so public-only requests do not accidentally include private/internal rows.
- JSON-encoded vNext CLI/MCP result payloads before dumping.
- Included `memory_key` in project update revisions.
- Persisted closed open loops using the database-valid resolved state.
- Fixed generic retrieval so missing domain scope does not become `unknown`-only.
- Fixed scheduler `next_run_at` clearing so pause/disable/manual workflows do not retain stale due timestamps.
- Fixed legacy memory revision inserts after the vNext revision migration made revision fields required.
- Stabilized integration tests around Telegram rate-limit backend state and Node 20 TypeScript example execution.

## Guardrails Preserved

- No generated artifact or agent proposal is auto-promoted into trusted memory.
- Restricted domains and high-sensitivity classes are filtered or blocked by policy.
- Read-only agents cannot write.
- Project-scoped agents cannot control the global scheduler and can only run limited project workflows.
- Scheduler configuration requires admin permission.
- Pause/resume and due-run control require trusted local or admin permission.
- All agent and scheduler activity is traceable through event logs and run records.

## Validation Evidence

Current local validation performed during this phase:

- Python compile checks for the new scheduler, policy, store, CLI, API, and MCP modules: passed.
- Focused control-plane unit tests: `40 passed`.
- Full unit suite: `1069 passed`.
- Full integration suite: `370 passed`.
- Web tests: `207 passed`.
- Web lint: passed.
- Web build: passed and built `/vnext`.
- `alicebot eval run --suite all`: `170/170` passed, with `0` critical privacy leaks and `0` prompt-injection tool writes.
- `alicebot vnext smoke agentic-scheduler`: passed, including the due-scan execution gate.
- `git diff --check`: passed.

## Known Limitations

- This is still local-governed scheduling, not a hosted production scheduler service.
- Daily Brief and Weekly Synthesis are the primary fully runnable scheduler workflows; other scheduled workflow types currently emit deterministic reviewable report scaffolds.
- The `/vnext` workspace includes fixture-backed preview data in addition to live API-backed scheduler/agent surfaces.
- Connectors remain deterministic payload normalizers; live OAuth, polling, OCR execution, and transcription execution are separate integration work.
- Agent writes remain proposal/review-only by design.

## Recommended Next Phase

- Add a small local scheduler daemon or launchd/systemd recipe around `alicebot vnext scheduler run-due`.
- Convert the remaining scheduler workflow scaffolds into full deterministic report generators.
- Expand `/vnext` from mixed fixture/live data to fully live-backed workspace data.
- Add hosted scheduler readiness checks only after local scheduler behavior is stable.
- Add design-partner telemetry around which agent policies block, filter, or require review most often.
