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
- [x] Connector payload ingestion preserves raw evidence, default domain/sensitivity, and cursor posture.
- [x] Generated artifacts remain reviewable and are not auto-promoted to trusted memory.

## Verification

- [x] `./.venv/bin/python -m pytest tests/unit -q`
- [x] `pnpm --dir apps/web test`
- [x] `pnpm --dir apps/web lint`
- [x] `pnpm --dir apps/web build`
- [x] `python3 scripts/check_control_doc_truth.py`
- [x] `git diff --check`
- [x] `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`
- [x] Real Postgres vNext CLI/API/MCP smoke check.

## Security and Privacy

- [x] No secrets, private exports, real personal data, or production credentials are committed.
- [x] Demo dataset contains only synthetic people, projects, notes, and connector payloads.
- [x] Prompt-injection evals show zero tool writes.
- [x] Critical privacy leakage evals show zero critical leaks.
- [x] New connector/write paths have security review notes.
- [x] Post-merge GitHub Security Scans passed on `main`.

## Release Operations

- [x] Changelog entry prepared.
- [x] Tag plan prepared: `docs/release/v0.5.1-vnext-preview-tag-plan.md`.
- [x] Rollback path documented.
- [x] Known limitations documented: no live connector OAuth/polling, no hosted SLA, no automatic memory promotion, no production scheduler.
- [x] Release owner signs off.

## Evidence

Current evidence recorded on 2026-05-11:

- Real Postgres vNext smoke passed for source capture, connector ingest, scoped and unscoped context packs, daily brief generation, project update review, open-loop close, API context packs, API project dashboard, MCP context pack, and MCP project dashboard.
- `./.venv/bin/python -m pytest tests/unit -q`: `1057 passed`.
- `pnpm --dir apps/web test`: `205 passed`.
- `pnpm --dir apps/web lint`: passed.
- `pnpm --dir apps/web build`: passed and built `/vnext`.
- `python3 scripts/check_control_doc_truth.py`: passed.
- `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes.
- `git diff --check`: clean.
- GitHub Security Scans on merged `main` passed for CodeQL JavaScript, CodeQL Python, and Gitleaks.
