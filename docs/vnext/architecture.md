# vNext Architecture

Alice vNext is organized around inspectable continuity rather than generic notes or hidden chat summaries.

## Layers

### Alice Core

Core owns durable state and policy boundaries:

- `sources` and `source_chunks` preserve raw evidence and normalized text.
- `memories` store typed candidate or accepted claims with status, confidence, domain, and sensitivity.
- `memory_revisions` preserve correction, promotion, supersession, and rejection history.
- `provenance_links` connect memories, artifacts, graph edges, projects, and open loops back to source chunks.
- `event_log` records append-only system events for mutation, connector sync, artifact generation, and review.
- `brain_charters` store the user-editable operating agreement for a brain.
- `agent_identities`, `scheduler_workflows`, and `scheduler_runs` persist governed agent and schedule state across restarts.

### Alice Brain

Brain workflows generate reviewable outputs from Core:

- context packs for retrieval
- daily briefs
- weekly syntheses
- connection reports
- contradiction reports
- project update candidates
- open-loop extraction and review
- generated artifacts with Markdown export

Generated artifacts are not trusted memory by default. Promotion stays explicit and reviewable.

### Alice Agent Memory

Agent Memory exposes Alice to external tools without letting those tools own Alice state:

- CLI commands for local workflows
- API endpoints for product surfaces
- MCP tools for agent environments
- connector payload ingestion for source evidence
- scoped agent identities and permission profiles
- governed scheduler controls for local proactive workflows

Agents can request context, submit tasks, generate artifacts, propose memory, and run allowed scheduler workflows, but durable mutation still passes through Core policies, review state, provenance, and event logging.

## Data Flow

1. Raw input arrives from manual capture, import, or connector payload.
2. Core stores the raw evidence, content hash, connector metadata, domain, sensitivity, and timestamps.
3. Capture splits text into chunks and proposes candidate memories.
4. Brain workflows retrieve allowed evidence and generate reviewable artifacts.
5. Review actions accept, edit, reject, supersede, close, snooze, or promote.
6. Event log records write paths for audit and replay.
7. Agent and scheduler actions add agent identity, policy decision, run ID, trace ID, target ID, and workflow metadata where applicable.

## Agentic Control Plane

Agent-originated API, CLI, and MCP calls can carry `agent_id`, `agent_type`, `agent_run_id`, `task_id`, `project_scope`, and `permission_profile`.

Initial permission profiles are:

- `read_only_agent`
- `project_scoped_agent`
- `trusted_local_agent`
- `memory_proposal_agent`
- `admin_agent`

The policy layer evaluates the requested action, project scope, domain scope, sensitivity scope, workflow type, and write policy. Decisions are `allowed`, `allowed_with_filtering`, `requires_review`, or `blocked`; filtered and blocked outcomes are logged.

Agent proposals remain candidate/review items. This sprint does not allow agent or scheduler output to auto-promote into trusted memory.

## Governed Scheduler

The local scheduler owns disabled-by-default workflow configuration for:

- `daily_brief`
- `weekly_synthesis`
- `connection_report`
- `contradiction_report`
- `open_loop_review`
- `project_update_scan`

Daily Brief and Weekly Synthesis are the primary runnable workflows. Local due scans run enabled, unpaused workflows whose `next_run_at` has arrived, then advance the next run timestamp. Other workflow types have persistent configuration, policy-checked control paths, run history, and generated report artifacts. Scheduler runs record status, trace ID, triggering actor, policy decision, agent identity when present, output artifact ID, and failure details.

## Connector Boundary

Sprint 11 connectors are deterministic payload normalizers, not live integrations. They support:

- Telegram webhook JSON already received by the local system
- browser clip JSON
- PDF/DOCX extracted text payloads
- CSV text or row payloads
- screenshot OCR text payloads
- voice transcript payloads

Each connector preserves raw evidence in source metadata, applies conservative default domain/sensitivity, and uses event-log cursors to skip already-seen items. Cursor advancement pauses when an item fails so a broken item is not silently skipped on the next sync.

## Security Model

- Local-first by default.
- No cloud model call is required by the deterministic vNext seed.
- Connectors do not execute source instructions.
- Prompt-injection eval cases are quarantined and cannot trigger tool writes.
- Sensitive domains and sensitivities are filtered before context-pack assembly.
- Generated artifacts inherit the highest selected source sensitivity.
- Agents cannot bypass domain/sensitivity filters, review-required workflows, scheduler policy checks, Brain Charter constraints, or the no-auto-promotion rule.

## Current Production Gap

Before a public vNext tag, decide whether connector cursors and secrets move from event-log seeding into a dedicated connector settings table or encrypted local secret store. Live connector polling, OAuth, browser extension packaging, OCR execution, transcription execution, hosted scheduling, and automatic memory promotion remain outside this preview.
