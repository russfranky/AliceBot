# BUILD_REPORT

## sprint objective

Package the completed Alice vNext preview for the `v0.5.1-vnext-preview` public pre-release while preserving `v0.5.1` as the stable pre-1.0 public release line.

## completed work

- added vNext preview release notes
- added the `v0.5.1-vnext-preview` tag plan and rollback path
- completed the vNext public release checklist with current evidence
- updated README and vNext docs to link the release notes and tag plan
- added a 2026-05-11 changelog entry for the vNext preview release package
- realigned control docs away from stale "Sprint 1 active" wording and into the vNext public-preview release gate
- kept stable release truth explicit: `v0.5.1` remains the stable pre-1.0 public release boundary

## incomplete work

- no implementation work remains for the preview release package
- live connector OAuth/polling, hosted SLA, automatic memory promotion, production scheduling, live-backed `/vnext`, and model-backed evals remain intentionally deferred beyond this preview

## files changed

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `CHANGELOG.md`
- `CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `REVIEW_REPORT.md`
- `ROADMAP.md`
- `docs/release/v0.5.1-vnext-preview-release-notes.md`
- `docs/release/v0.5.1-vnext-preview-tag-plan.md`
- `docs/release/v0.5.1-tag-plan.md`
- `docs/release/vnext-public-release-checklist.md`
- `docs/vnext/README.md`
- `scripts/check_control_doc_truth.py`

## tests run

- real Postgres vNext smoke covering CLI, API, and MCP paths: passed
- `./.venv/bin/python -m pytest tests/unit -q`: `1057 passed`
- `pnpm --dir apps/web test`: `205 passed`
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed
- `python3 scripts/check_control_doc_truth.py`: passed
- `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes
- `git diff --check`: clean
- GitHub Security Scans on merged `main`: CodeQL JavaScript, CodeQL Python, and Gitleaks passed

## blockers/issues

- no release blocker remains for the vNext preview package
- GitHub Actions reports a non-blocking Node.js 20 deprecation notice for existing third-party actions; this is maintenance follow-up, not a preview release blocker

## recommended next step

Merge the release-packaging PR, create the annotated `v0.5.1-vnext-preview` tag from merged `main`, and publish the GitHub release as a pre-release with `--latest=false`.
