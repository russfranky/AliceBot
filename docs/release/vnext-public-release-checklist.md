# vNext Public Release Checklist

Use this checklist before cutting a vNext preview tag or public announcement. Do not publish until every required item is checked with current evidence.

## Docs

- [x] README links the vNext preview, quickstart, architecture, security/privacy, demo script, release checklist, release notes, and tag plan.
- [x] Quickstart includes local install, Docker/local stack, first source capture, and first daily brief.
- [x] Docs explain Alice Core vs Alice Brain vs Alice Agent Memory.
- [x] Example `ALICE.md` is included and uses only synthetic content.
- [x] Demo video script is current.
- [x] Contributor guide explains how to work on vNext safely.
- [x] Security/privacy docs describe connector boundaries and secret handling.

## Product Gate

- [x] New user can install locally and generate a first daily brief in under 20 minutes.
- [x] `/vnext` renders the fixture-backed workspace.
- [x] Connector settings are visible in the UI.
- [x] Connector settings can be updated from `/vnext` for Telegram, local folder, and browser clipper defaults.
- [x] Connector settings and state persist in dedicated tables, with event-log audit entries for changes.
- [x] Connector secrets use references and local encrypted/env-backed providers without exposing raw values.
- [x] Connector health and dogfooding capture metrics are visible in the UI.
- [x] Local doctor checks report missing migrations, missing connector rows, secret reference problems, scheduler posture, and capture failures.
- [x] `/vnext` exposes live source review/update/archive, source-backed open-loop creation, doctor/readiness checks, and capture-to-brief traces.
- [x] Live local capture works for allowlisted Telegram, local folder/Obsidian notes, browser clips, and agent outputs.
- [x] Connector payload ingestion preserves raw evidence, default domain/sensitivity, and cursor posture.
- [x] Generated artifacts remain reviewable and are not auto-promoted to trusted memory.
- [x] Model-backed artifacts remain source-grounded, policy-routed, and reviewable.
- [x] Human artifact quality ratings can be created and exported.

## Verification

- [x] `./.venv/bin/python -m pytest tests/unit -q`
- [x] `pnpm --dir apps/web test`
- [x] `pnpm --dir apps/web lint`
- [x] `pnpm --dir apps/web build`
- [x] `python3 scripts/check_control_doc_truth.py`
- [x] `git diff --check`
- [x] `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`
- [x] Real Postgres vNext CLI/API/MCP smoke check.
- [x] Real Postgres scheduled model-backed workflow smoke check.
- [x] Real Postgres connector-hardening smoke check.
- [x] Real Postgres secret-redaction smoke check.
- [x] Real Postgres dogfood-doctor smoke check.
- [x] Real Postgres operator-console smoke check.

## Security and Privacy

- [x] No secrets, private exports, real personal data, or production credentials are committed.
- [x] Demo dataset contains only synthetic people, projects, notes, and connector payloads.
- [x] Prompt-injection evals show zero tool writes.
- [x] Critical privacy leakage evals show zero critical leaks.
- [x] New connector/write paths have security review notes.
- [x] Connector settings/state storage and secret references have security review notes.
- [x] Post-merge GitHub Security Scans passed on `main`.

## Release Operations

- [x] Changelog entry prepared.
- [x] Tag plan prepared: `docs/release/v0.5.1-vnext-preview-tag-plan.md`.
- [x] Rollback path documented.
- [x] Known limitations documented: no managed connector OAuth, no packaged browser extension, no hosted connector polling, no hosted SLA, no automatic memory promotion, no production scheduler.
- [x] Release owner signs off.

## Evidence

Current evidence recorded on 2026-05-11:

- Real Postgres vNext smoke passed for source capture, connector ingest, scoped and unscoped context packs, daily brief generation, project update review, open-loop close, API context packs, API project dashboard, MCP context pack, and MCP project dashboard.
- Real Postgres scheduled model-backed smoke passed for local routing, provider metadata, review status, source refs, and grounded output sections.
- Real Postgres live-capture connector smoke passed for allowlisted Telegram sync, rejected chat isolation, local folder generated-folder ignore behavior, browser clip capture, review-only agent output ingestion, and connector health telemetry.
- Real Postgres capture-to-brief smoke passed for browser clip capture, context-pack inclusion, Daily Brief generation, source references, quality rating recording, and dogfooding telemetry.
- Real Postgres connector-hardening smoke passed for settings rows, cursor persistence, rejected-chat logging, generated-folder ignores, restart dedupe, and health counters.
- Real Postgres secret-redaction smoke passed for Telegram token absence, browser token absence, and redacted capture-token evidence.
- Real Postgres dogfood-doctor smoke passed with zero blocking failures and zero warnings.
- Real Postgres operator-console smoke passed for source review, memory review, artifact review/rating, source-backed open loops, scheduler run-now, connector health, doctor readiness, event logging, and capture-to-brief traceability.
- `./.venv/bin/python -m pytest tests/unit -q`: `1125 passed`.
- `./.venv/bin/python -m pytest tests/integration -q`: `370 passed`.
- `pnpm --dir apps/web test`: `207 passed`.
- `pnpm --dir apps/web lint`: passed.
- `pnpm --dir apps/web build`: passed and built `/vnext`.
- `python3 scripts/check_control_doc_truth.py`: passed.
- `alicebot eval run --suite all`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes.
- `git diff --check`: clean.
- GitHub Security Scans on merged `main` passed for CodeQL JavaScript, CodeQL Python, and Gitleaks.
