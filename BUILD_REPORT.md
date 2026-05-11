# BUILD_REPORT

## sprint objective

Package the completed Alice vNext preview plus live capture connector slice for the `v0.5.1-vnext-preview` public pre-release while preserving `v0.5.1` as the stable pre-1.0 public release line.

## completed work

- added vNext preview release notes
- added the `v0.5.1-vnext-preview` tag plan and rollback path
- completed the vNext public release checklist with current evidence
- updated README and vNext docs to link the release notes and tag plan
- added live local capture for Telegram, local folders/Obsidian notes, browser clips, and Hermes/OpenClaw-style agent output ingestion
- added connector health telemetry, dogfooding capture-health metrics, and capture-to-brief smoke validation
- added a 2026-05-11 changelog entry for the vNext preview release package
- realigned control docs away from stale "Sprint 1 active" wording and into the vNext public-preview release gate
- kept stable release truth explicit: `v0.5.1` remains the stable pre-1.0 public release boundary

## incomplete work

- no implementation work remains for the preview release package or live capture connector slice
- managed connector OAuth, hosted connector polling, packaged browser extensions, hosted SLA, automatic memory promotion, production scheduling, broad live-write `/vnext`, and model-backed evals remain intentionally deferred beyond this preview

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
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `apps/api/src/alicebot_api/vnext_capture.py`
- `apps/api/src/alicebot_api/vnext_connectors.py`
- `apps/api/src/alicebot_api/vnext_dogfooding.py`
- `apps/web/app/vnext/page.test.tsx`
- `apps/web/components/vnext-brain-workspace.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `docs/release/v0.5.1-vnext-preview-release-notes.md`
- `docs/release/v0.5.1-vnext-preview-tag-plan.md`
- `docs/release/vnext-public-release-checklist.md`
- `docs/vnext-live-capture-connectors-cto-summary.md`
- `docs/vnext/README.md`
- `docs/vnext/architecture.md`
- `docs/vnext/local-runtime.md`
- `docs/vnext/security-privacy.md`
- `docs/integrations/cli.md`
- `docs/integrations/mcp.md`
- `docs/livecaptureconnectors.md`
- `tests/unit/test_mcp.py`
- `tests/unit/test_vnext_connectors.py`
- `tests/unit/test_vnext_main.py`

## tests run

- real Postgres vNext smoke covering CLI, API, and MCP paths: passed
- real Postgres live-capture connector smoke: passed
- real Postgres capture-to-brief smoke: passed
- `./.venv/bin/python -m pytest tests/unit -q`: `1108 passed`
- `./.venv/bin/python -m pytest tests/integration -q`: `370 passed`
- `pnpm --dir apps/web test`: `207 passed`
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
