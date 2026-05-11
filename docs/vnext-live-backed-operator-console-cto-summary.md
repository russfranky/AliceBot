# Alice vNext Live-Backed Operator Console: CTO Summary

Date: 2026-05-12
Audience: CTO / technical leadership
Sprint artifact: `codex/live-backed-operator-console`
Baseline preserved: `v0.5.1` stable public release, `v0.5.1-vnext-preview` public-preview boundary

## Executive Summary

This phase turns `/vnext` from a broad preview dashboard into a daily local operator console for Alice vNext. The backend already had the major primitives: source capture, candidate memories, generated artifacts, project updates, open loops, connector settings/state, scheduler runs, dogfood telemetry, and doctor checks. This sprint connected the remaining operational gaps so a user can run the review loop from the web workspace instead of dropping to CLI/API for core actions.

The working loop is now:

```text
capture -> source review -> candidate memory review -> context pack -> generated/scheduled artifact -> artifact review/rating -> open-loop/project follow-up -> doctor/readiness + trace audit
```

The product rule remains unchanged: source evidence and generated artifacts stay review-only until a human explicitly accepts, promotes, or archives them.

## What We Built

### 1. Live Source Review And Archive

`/vnext` now supports source-level operator actions backed by the API:

- mark source reviewed
- update source title/domain/sensitivity
- assign source to a project
- create source-backed open loops
- archive source through the existing soft-delete path
- preserve review metadata in source `metadata_json`
- append event-log records for source review/archive actions

This closes the biggest daily-use gap: users can now operate the Inbox at the raw-evidence level before any memory promotion happens.

### 2. Capture-To-Brief Traceability

The workspace payload now includes traceability records that connect a source to:

- source chunks
- candidate memories
- generated artifacts
- source-backed open loops
- related event-log entries

The UI renders a Trace panel for the selected source, and the API exposes source/artifact trace endpoints. This gives operators a practical audit path from captured evidence through brief generation and review.

### 3. Doctor And Readiness In The Console

Doctor checks are now available through API and UI, not only CLI:

- `GET /v0/vnext/doctor`
- `POST /v0/vnext/doctor/run`
- `/vnext` Doctor panel
- run doctor
- run doctor `--fix-safe` with confirmation

The console shows migration status, connector settings/state posture, scheduler daemon posture, connector health, blocking failures, warnings, and recommended fixes.

### 4. Stronger Workspace Data Contract

The live workspace payload now includes:

- doctor/readiness status
- source traceability records
- source review metadata
- connector health
- scheduler state
- dogfooding telemetry
- agent activity and policy telemetry
- quality ratings and artifact state

The web API client has typed helpers for source review, source trace, artifact trace, and doctor runs.

### 5. Operator Smoke Test

Added `alicebot vnext smoke operator-console` as the broad daily-operation smoke. It verifies:

- source review action persists
- memory review action persists
- artifact review and rating persist
- source-backed open-loop creation persists
- scheduler run-now creates a reviewable artifact
- connector health is visible
- doctor/readiness is available
- capture-to-brief traceability exists
- event-log entries record operator actions

## API And UI Changes

New API surface:

- `POST /v0/vnext/sources/{source_id}/review`
- `GET /v0/vnext/traces/sources/{source_id}`
- `GET /v0/vnext/traces/artifacts/{artifact_id}`
- `GET /v0/vnext/doctor`
- `POST /v0/vnext/doctor/run`

Updated `/vnext` surfaces:

- Inbox source detail/review controls
- Capture-to-brief Trace panel
- Doctor/Readiness panel
- Generated artifact run/trace metadata display
- Fixture contract updated so demo mode exercises the same enum-backed values and supported connector set

## Guardrails Preserved

- No connector content bypasses review.
- Generated artifacts remain reviewable outputs.
- Source review does not auto-promote memory.
- Secrets remain referenced/redacted, not exposed in UI/API payloads.
- Scheduler outputs remain policy-checked and reviewable.
- Doctor `--fix-safe` is explicit and confirmed from the UI.

## Validation Evidence

Current validation from this phase:

- `./.venv/bin/pytest tests/unit -q`: `1126 passed`
- `./.venv/bin/pytest tests/integration -q`: `370 passed`
- `pnpm --dir apps/web test`: `209 passed`
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed and built `/vnext`
- `./.venv/bin/python scripts/check_control_doc_truth.py`: passed
- `./.venv/bin/alicebot vnext migrations status`: passed
- `./.venv/bin/alicebot vnext smoke operator-console`: passed
- `./.venv/bin/alicebot vnext smoke connector-hardening`: passed
- `./.venv/bin/alicebot vnext smoke secret-redaction`: passed
- `./.venv/bin/alicebot vnext smoke dogfood-doctor`: passed
- `./.venv/bin/alicebot vnext smoke live-capture-connectors`: passed
- `./.venv/bin/alicebot vnext smoke capture-to-brief`: passed
- `./.venv/bin/alicebot vnext smoke agentic-scheduler`: passed
- `./.venv/bin/alicebot eval run --suite all`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes
- `git diff --check`: clean

## Intentional Boundaries

This sprint did not add managed Gmail/Calendar OAuth, Telegram webhook hosting, cloud sync, hosted scheduler SLA, packaged browser extension actions, OCR/transcription execution, team/billing surfaces, or automatic memory promotion.

## Recommended Next Phase

The best next phase is Public Alpha Packaging if dogfooding confirms the console is usable day to day. If dogfooding shows missing input coverage is the blocker, prioritize Gmail/Calendar or voice capture next; otherwise package the local alpha around install, first-run, doctor, operator-console smoke, and the `/vnext` daily review loop.
