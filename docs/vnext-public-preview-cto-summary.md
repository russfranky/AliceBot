# Alice vNext Public Preview: CTO Summary

Date: 2026-05-11
Audience: CTO / technical leadership
Release artifact: `v0.5.1-vnext-preview`
Stable baseline preserved: `v0.5.1`
GitHub release: https://github.com/samrusani/AliceBot/releases/tag/v0.5.1-vnext-preview

## Executive Summary

This phase delivered the first public preview of Alice vNext: a local-first "true second brain" layer built on top of the stable Alice `v0.5.1` platform. The work moved Alice beyond continuity recall into a broader memory kernel with source evidence, context packs, reviewable generated artifacts, project/open-loop workflows, connector-backed ingestion, a fixture-backed second-brain workspace, and a deterministic eval suite.

The preview is intentionally scoped as a public pre-release, not a hosted launch. It proves the architecture and developer workflow while keeping high-risk production items deferred: live connector OAuth/polling, hosted SLA, automatic memory promotion, production scheduling, model-backed eval scoring, and live-backed UI expansion.

## Strategic Outcome

The phase establishes Alice vNext as three clear layers:

- **Alice Core**: local-first persistence, provenance, policy, event logging, sources, chunks, memories, revisions, graph edges, projects, people, beliefs, open loops, artifacts, evals, and connector evidence.
- **Alice Brain**: user-facing second-brain workflows such as daily briefs, weekly syntheses, context packs, contradiction reports, connection reports, project updates, and reviewable artifacts.
- **Alice Agent Memory**: CLI, API, and MCP surfaces that let external agents capture, retrieve, resume, explain, and generate context without owning the memory database.

This gives us a credible preview boundary for design partners and technical users while preserving the existing `v0.5.1` release line.

## What We Built

### 1. vNext Memory Kernel

- Added the vNext schema foundation for sources, source chunks, provenance links, graph edges, projects, people, beliefs, generated artifacts, task queue, event log, and Brain Charters.
- Added compatibility extensions for existing memories, memory revisions, and open loops.
- Added shared JSON schema contracts for vNext objects.
- Added repository protocol interfaces and a dedicated `PostgresVNextStore` facade.
- Added append-only event-log helpers with deterministic hashing.
- Added the Brain Charter / `ALICE.md` model and public example template.

### 2. Source Capture And Provenance

- Added manual text capture.
- Added local text file and Markdown folder import.
- Added ChatGPT export import.
- Added content-hash dedupe, chunking, candidate-memory creation, provenance links, and failure logging.
- Added CLI commands under `alicebot vnext sources ...`.
- Added minimal source API endpoints for text capture, lookup, and soft delete.

### 3. Retrieval And Context Packs

- Added deterministic query classification.
- Added keyword retrieval across memories, sources, and open loops.
- Added domain and sensitivity filtering.
- Added provenance-backed context packs with trace metadata.
- Exposed context packs through CLI, API, and MCP:
  - `alicebot context-pack`
  - `/v0/vnext/context-packs`
  - `alice_vnext_context_pack`
- Fixed real Postgres JSON serialization issues around UUID and datetime rows.
- Fixed missing domain-scope behavior so generic queries do not become `unknown`-only.

### 4. Queue And Reviewable Artifacts

- Added vNext task enqueue and process-next behavior.
- Added deterministic generated artifacts.
- Added artifact review actions and Markdown export.
- Added CLI and API access for queue and artifact workflows.
- Preserved the key product rule: generated artifacts are reviewable and are not auto-promoted to trusted memory.

### 5. Brain Workflows

- Added daily brief generation.
- Added weekly synthesis generation.
- Added source/reference sections and inherited sensitivity.
- Added candidate open-loop and memory creation.
- Added CLI, API, and MCP manual triggers for daily/weekly workflows.

### 6. Graph, Connections, Contradictions, And Beliefs

- Added deterministic connection reports.
- Added candidate graph edge creation with confidence and explanations.
- Added graph edge accept/reject review state.
- Added graph neighborhood lookup.
- Added contradiction reports that cite both sides and distinguish direct conflict from nuance.
- Added belief challenge and supersession review actions.
- Added belief state history lookup.
- Exposed these workflows through CLI, API, and MCP where relevant.

### 7. Projects And Open Loops

- Added project update candidate artifacts.
- Added candidate project-state memories.
- Added accept/edit/reject review actions for project updates.
- Added open-loop extraction with source, date, and owner metadata.
- Added close, snooze, edit, and reopen actions for open loops.
- Added project dashboard data.
- Exposed project and open-loop workflows through CLI, API, and MCP.
- Fixed open-loop close persistence to use a valid database status.
- Fixed project update revision persistence by including the required `memory_key`.

### 8. `/vnext` Web Workspace

- Added a fixture-backed `/vnext` workspace in the existing Next.js shell.
- Implemented Home, Inbox, Ask Alice, Daily Brief, Weekly Synthesis, Queue, Generated, Memory Review, Projects, People, Beliefs, Open Loops, Timeline, Graph, and Settings/Privacy surfaces.
- Added stateful review actions for accept, edit, reject, promote, project assignment, label updates, and open-loop creation.
- Added Ask Alice output with answer, sources/provenance, memories used, contradictions, why explanation, and save-as-artifact behavior.
- Added visible domain and sensitivity labels across generated artifacts and review rows.
- Aligned fixture enum values with schema-backed vNext contracts.
- Added all supported Sprint 11 connector settings to the workspace: Telegram, browser clipper, PDF, DOCX, CSV, screenshot OCR, and voice transcript.

### 9. Connector Payload Ingestion

- Added deterministic connector definitions and payload normalizers for:
  - Telegram
  - browser clipper
  - PDF
  - DOCX
  - CSV
  - screenshot OCR
  - voice transcript
- Preserved raw payload/extracted evidence in source metadata.
- Stored default domain and sensitivity labels with sources.
- Added cursor handling to skip duplicate items and avoid advancing past failed items.
- Added failure isolation so broken connector items do not become broken memories.
- Added connector list/ingest CLI commands and connector API endpoints.

### 10. Synthetic Eval And Hardening Harness

- Added deterministic synthetic benchmark corpus generation.
- Covered people, projects, notes, decisions, beliefs, contradictions, superseded beliefs, open loops, personal reflections, future reminders, hidden cross-domain connections, and prompt-injection sources.
- Added eval suites for:
  - exact recall
  - temporal reasoning
  - contradiction precision
  - provenance precision
  - privacy leakage
  - open-loop recall
  - prompt-injection write safety
- Added `alicebot eval seed/run/report`.
- Added an `alice` console-script alias.
- Confirmed zero critical privacy leaks and zero prompt-injection tool writes in the preview gate.

### 11. Public Preview Documentation And Release Packaging

- Added public vNext overview, quickstart, architecture, security/privacy, contributor guide, synthetic demo dataset, example `ALICE.md`, demo video script, release checklist, release notes, and tag plan.
- Completed the vNext release checklist with current evidence.
- Added rollback instructions for the preview tag.
- Published the GitHub pre-release `v0.5.1-vnext-preview`.
- Kept `v0.5.1` marked as the stable public "Latest" release.

### 12. Release-Blocking Fixes From Review

Before release, we fixed multiple issues that would have affected real Postgres-backed usage:

- Normalized UUID/datetime values before JSON serialization and event hashing.
- Preserved explicit CLI sensitivity filters so `--sensitivity-allowed public` actually narrows results.
- JSON-encoded vNext CLI/MCP command results before dumping.
- Included `memory_key` in project update revisions.
- Persisted closed open loops as the valid `resolved` state.
- Removed the accidental `unknown`-only domain filter for generic no-scope queries.
- Cast optional SQL placeholders so psycopg/Postgres can infer types correctly.
- Fixed generated artifact promoted timestamp casting.
- Verified these fixes with a real Postgres vNext smoke test, not only string-based fakes.

### 13. CI And Release Infrastructure Hardening

After the preview release, we cleaned up the GitHub Actions runtime warnings:

- Upgraded pinned GitHub Actions to Node 24 compatible versions.
- Upgraded CodeQL from v3 to v4.
- Replaced the Node 20 Gitleaks action with the official Gitleaks CLI release plus checksum verification.
- Kept NPM package publishing on Node 20 for now to avoid mixing package runtime changes with action-runtime maintenance.
- Verified the post-merge Security Scans run on `main`.
- Confirmed final check-run annotations no longer include Node 20 deprecation warnings.

## Validation Evidence

The preview release gate included:

- Real Postgres vNext smoke for:
  - source capture
  - connector ingest
  - scoped and unscoped context packs
  - daily brief generation
  - project update review
  - open-loop close
  - API context packs
  - API project dashboard
  - MCP context pack
  - MCP project dashboard
- `./.venv/bin/python -m pytest tests/unit -q`: `1057 passed`
- `pnpm --dir apps/web test`: `205 passed`
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed and built `/vnext`
- `python3 scripts/check_control_doc_truth.py`: passed
- `alicebot eval run --suite all`: `170/170` cases passed
- Critical privacy leak count: `0`
- Prompt-injection tool write count: `0`
- `git diff --check`: clean
- GitHub Security Scans on merged `main`: CodeQL JavaScript, CodeQL Python, and Gitleaks passed

## Current Limitations

These are intentional preview boundaries:

- No hosted SLA or managed cloud launch.
- No live connector OAuth, external polling, browser extension actions, OCR model execution, or transcription model execution.
- No automatic promotion of generated artifacts into trusted memory.
- No production daily/weekly scheduler.
- `/vnext` is fixture-backed; live-backed UI expansion remains future work.
- Eval scoring is deterministic and synthetic; model-backed or human-rated scoring is future work.
- Package publishing remains on Node 20 even though GitHub Actions runtime warnings were resolved.

## Technical Leadership Takeaways

- The phase delivered a coherent vNext product slice, not just isolated backend primitives.
- The memory kernel, provenance model, CLI/API/MCP access, and reviewable artifacts now align around a second-brain architecture.
- The preview is safer than a typical prototype because it includes security/privacy evals, prompt-injection write-safety checks, connector failure isolation, and explicit no-auto-promotion rules.
- The UI is intentionally fixture-backed but broad enough to demonstrate the target workspace and review model.
- The real Postgres smoke found and fixed issues that unit fakes did not catch, which materially improved release confidence.
- The release is cleanly packaged as a pre-release, so it does not disturb the stable `v0.5.1` line.

## Recommended Next Phase

The next phase should choose one primary product slice instead of expanding all fronts at once:

1. **Live-backed `/vnext` UI**: connect the current workspace to real API data and review actions.
2. **Connector auth and polling**: turn deterministic payload ingestion into real connector flows with secret/cursor storage.
3. **Production scheduling**: add governed daily/weekly generation schedules and operational controls.
4. **Model-backed intelligence**: add model-backed synthesis, contradiction review, and human-rated eval scoring.

The strongest next step is likely live-backed `/vnext` UI, because it converts the already-built backend and review workflows into an inspectable product experience without immediately taking on live connector or scheduler risk.
