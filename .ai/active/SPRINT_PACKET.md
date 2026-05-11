# Sprint Packet

## Sprint Title
Alice vNext Public Preview Release Gate

## Activation Note
- This packet records the active release gate.
- `v0.5.1` remains the current stable pre-1.0 public release boundary.
- `v0.5.1-vnext-preview` is the vNext public-preview tag target.
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- Alice vNext Sprint 1 through Sprint 12 preview scope is implemented.

## Sprint Type
release-gate

## Sprint Reason
The vNext preview surface has moved from incremental seed work into release packaging. The release gate preserves the stable `v0.5.1` baseline while publishing the local-first vNext preview as a GitHub pre-release with current verification evidence and explicit limitations.

## Git Instructions
- Branch: `codex/vnext-preview-release-packaging`
- Base Branch: `main`
- PR Strategy: release-paperwork PR, squash merge, then tag merged `main`
- Merge Policy: merge after checks pass and explicit release approval

## Baseline To Preserve
- shipped Phases 9-14 baseline
- shipped Bridge `B1` through `B4`
- stable `v0.5.1` public release line
- shipped one-call continuity surface
- shipped Alice Lite profile
- shipped hygiene/thread-health visibility
- shipped Phase 14 provider contract, local/self-hosted compatibility, model packs, reference integrations, and design-partner launch surface
- shipped `HF-001` logging safety and disk guardrails
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Publish Alice vNext as the `v0.5.1-vnext-preview` public pre-release with release notes, tag plan, completed checklist evidence, and aligned control docs.

## In Scope
- release notes for `v0.5.1-vnext-preview`
- vNext preview tag plan and rollback path
- completed vNext public release checklist with current evidence
- changelog entry for the preview release package
- README and vNext docs pointing to release notes and tag plan
- control docs updated away from stale "Sprint 1 active" wording
- final verification of docs, tests, evals, and GitHub release state

## Out Of Scope
- new vNext features
- live connector OAuth/polling
- hosted SLA or managed cloud launch
- automatic promotion of generated artifacts into trusted memory
- production daily/weekly scheduler
- live-backed expansion of the `/vnext` UI
- model-backed or human-rated eval scoring
- destructive schema rewrites

## Proposed Files And Modules
- `CHANGELOG.md`
- `README.md`
- `CURRENT_STATE.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `ROADMAP.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `scripts/check_control_doc_truth.py`
- `docs/vnext/README.md`
- `docs/release/vnext-public-release-checklist.md`
- `docs/release/v0.5.1-vnext-preview-release-notes.md`
- `docs/release/v0.5.1-vnext-preview-tag-plan.md`

## Acceptance Criteria
- `v0.5.1` remains documented as the stable pre-1.0 public release boundary.
- `v0.5.1-vnext-preview` is documented as a pre-release preview, not a stable replacement.
- README links the vNext overview, quickstart, architecture, security/privacy, demo script, release checklist, release notes, and tag plan.
- The vNext release checklist records current verification evidence.
- Release notes describe included preview scope and limitations.
- The tag plan includes GitHub pre-release publication and rollback commands.
- Control-doc truth reflects the release gate instead of stale Sprint 1 active wording.
- The tag is created from merged `main`.
- The GitHub release is published as a pre-release with `--latest=false`.

## Required Verification
- `./.venv/bin/python -m pytest tests/unit -q`
- `pnpm --dir apps/web test`
- `pnpm --dir apps/web lint`
- `pnpm --dir apps/web build`
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`
- `git diff --check`
- GitHub PR checks for the release-packaging PR
- GitHub release view for `v0.5.1-vnext-preview`

## Exit Condition
This packet is complete when the release-packaging PR is merged, `v0.5.1-vnext-preview` is pushed as an annotated tag, the GitHub pre-release is published with release notes, and the final release state is verified.
