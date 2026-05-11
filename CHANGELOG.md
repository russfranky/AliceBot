# Changelog

## 2026-05-11

- Added the Alice vNext live capture connector slice for local dogfooding: allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clipper capture, Hermes/OpenClaw-style agent output ingestion, connector health telemetry, dogfooding dashboard metrics, capture-to-brief smoke validation, and review-only trust preservation.
- Prepared the Alice vNext public-preview release package for `v0.5.1-vnext-preview`.
- Promoted the vNext preview docs from release-candidate posture to tag-ready preview posture while keeping `v0.5.1` as the current stable pre-1.0 public release.
- Added vNext preview release notes and tag plan with rollback instructions.
- Completed the vNext public release checklist with current verification evidence.
- Realigned control docs from stale "Sprint 1 active" wording to the completed Sprint 1-12 preview surface and the active vNext release gate.
- Verified the vNext Postgres-backed CLI/API/MCP smoke path, full unit suite, web test/lint/build gates, control-doc truth check, eval harness, Git diff whitespace check, and post-merge GitHub Security Scans.

## 2026-04-16

- Closed out Phase 14 after shipping all five planned sprints:
  - `P14-S1` provider abstraction cleanup + OpenAI-compatible adapter
  - `P14-S2` Ollama + llama.cpp + vLLM adapters
  - `P14-S3` model packs
  - `P14-S4` reference integrations
  - `P14-S5` design partner launch
- Shipped `HF-001` to eliminate unbounded local log growth by defaulting local/Lite logging to stdout, disabling local/Lite access logs by default, and adding bounded opt-in file logging.
- Promoted the public release boundary from `v0.4.0` to `v0.5.1`.
- Added Phase 14 closeout summary and closeout packet.
- Added `v0.5.1` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.5.1`.
- Realigned canonical quickstart, MCP, and integration docs to the shipped Phase 14 + `HF-001` baseline.

## 2026-04-15

- Closed out Phase 13 after shipping all three planned sprints:
  - `P13-S1` one-call continuity
  - `P13-S2` Alice Lite
  - `P13-S3` memory hygiene and conversation health
- Promoted the public release boundary from `v0.3.2` to `v0.4.0`.
- Added Phase 13 closeout summary and closeout packet.
- Added `v0.4.0` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.4.0`.
- Realigned current quickstart and integration docs to the shipped Phase 13 baseline.

## 2026-04-14

- Closed out Phase 12 after shipping all five planned sprints:
  - `P12-S1` hybrid retrieval + reranking
  - `P12-S2` automated memory operations
  - `P12-S3` contradiction detection + trust calibration
  - `P12-S4` public eval harness
  - `P12-S5` task-adaptive briefing
- Added Phase 12 closeout summary and closeout packet.
- Updated the documented release target from `v0.2.0` to `v0.3.2` for the completed Phase 12 boundary.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.3.2`.
- Added `v0.3.2` release checklist, tag plan, and public release runbook.
- Kept the published release truth explicit: the latest published tag remains `v0.2.0` until `v0.3.2` is cut.

- Prepared `R1` release-readiness package for `v0.2.0` as a pre-1.0 public release boundary.
- Added `v0.2.0` release checklist, tag plan, and public release runbook.
- Realigned launch-facing docs to shipped scope through Phase 11 and Bridge `B1` through `B4`.
- Recorded release-gate evidence in `BUILD_REPORT.md` and `REVIEW_REPORT.md` for `R1`.

## 2026-04-08

- Compacted the live control docs so `README.md`, `ROADMAP.md`, and `RULES.md` carry only current Phase 9 completion truth.
- Archived superseded Phase 9 planning and control material into local-only internal archives.
- Kept the quickstart, integration, release, runbook, and evaluation artifacts as the canonical Phase 9 launch surface.

## 2026-04-07

- Prepared the first public `v0.1.0` launch documentation set for the shipped Phase 9 wedge.
- Added onboarding, integration, release, and repo policy docs without expanding product scope.

## 2026-03-11

- Hardened the local runtime and verification path used by the public release candidate.
- Kept the launch surface aligned with deterministic local startup, migration, sample-data, and health-check flows.
