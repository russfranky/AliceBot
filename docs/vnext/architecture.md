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

Agents can request context and propose writes, but durable mutation still passes through Core policies, review state, provenance, and event logging.

## Data Flow

1. Raw input arrives from manual capture, import, or connector payload.
2. Core stores the raw evidence, content hash, connector metadata, domain, sensitivity, and timestamps.
3. Capture splits text into chunks and proposes candidate memories.
4. Brain workflows retrieve allowed evidence and generate reviewable artifacts.
5. Review actions accept, edit, reject, supersede, close, snooze, or promote.
6. Event log records write paths for audit and replay.

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

## Current Production Gap

Before a public vNext tag, decide whether connector cursors and secrets move from event-log seeding into a dedicated connector settings table or encrypted local secret store. Live connector polling, OAuth, browser extension packaging, OCR execution, and transcription execution remain outside this preview.
