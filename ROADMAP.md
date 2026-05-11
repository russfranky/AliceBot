# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
- Bridge Phase (`B1`-`B4`): shipped
- Phase 12: shipped
- Phase 13: shipped
- Phase 14: shipped
- `HF-001` logging safety hardening: shipped
- `v0.5.1`: released

These remain baseline truth and are not future milestones.

## Current Planning Status
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- `M-001` Archive Maintenance CI Repair is implemented in this working tree.
- Alice vNext Sprint 1 - Architecture Foundation and Schema is active.

## Completed Phase 14 Sequence

### P14-S1: Provider Abstraction Cleanup + OpenAI-Compatible Adapter
Status: shipped

### P14-S2: Ollama + llama.cpp + vLLM Adapters
Status: shipped

### P14-S3: Model Packs
Status: shipped

### P14-S4: Reference Integrations
Status: shipped

### P14-S5: Design Partner Launch
Status: shipped

## Completed Post-Phase Hotfix

### HF-001: Logging Safety And Disk Guardrails
Status: shipped

## Completed Maintenance Gate

### M-001: Archive Maintenance CI Repair
- repair nightly archive-maintenance checksum verification when archive-index state is absent in CI
- repair weekly benchmark regeneration failure caused by maintenance-user foreign-key setup
- keep the fix narrow and operational rather than turning it into a new feature phase

## Active Feature Sprint

### Alice vNext Sprint 1: Architecture Foundation and Schema
- add vNext memory-kernel schema foundations without destructive reorganization
- add shared schema contracts, repository interfaces, and a Postgres vNext store facade
- add append-only event-log helper and Brain Charter model
- cover Sprint 1 entities with CRUD-style store tests and event-log write tests
- seed Sprint 2 capture/archive/normalize with text/file/Markdown/ChatGPT capture, hash dedupe, chunking, candidate memories, provenance links, failure logging, CLI commands, and source API endpoints
- seed Sprint 3 retrieval/context packs with query classification, keyword retrieval, graph/vector/temporal scaffolds, sensitivity filtering, trace metadata, and CLI/API/MCP access
- seed Sprint 4 queue/artifacts with task enqueue/process-next behavior, deterministic generated artifacts, artifact review/export actions, and CLI/API access
- seed Sprint 5 daily/weekly brain workflows with deterministic brief/synthesis artifacts, source sections, inherited sensitivity, candidate review objects, and CLI/API/MCP manual triggers
- seed Sprint 6 connection/graph workflows with deterministic connection reports, candidate graph edges, edge review status, graph neighborhood lookup, and CLI/API/MCP access
- seed Sprint 7 contradiction/belief workflows with deterministic contradiction reports, candidate contradiction edges, belief challenge/supersession review actions, belief state history lookup, and CLI/API/MCP access
- seed Sprint 8 project/open-loop workflows with project update candidate artifacts, candidate project-state memories, open-loop extraction/review actions, project dashboard data, and CLI/API/MCP access
- seed Sprint 9 UI with a fixture-backed `/vnext` workspace covering Home, Inbox, Ask Alice, Daily Brief, Weekly Synthesis, Queue, Generated artifacts, Memory Review, Projects, People, Beliefs, Open Loops, Timeline, Graph, and Settings/Privacy
- seed Sprint 10 evals/hardening with deterministic synthetic benchmark corpus generation, recall/temporal/contradiction/privacy/provenance/open-loop/prompt-injection suites, baseline metrics, report writing, and `alicebot eval seed/run/report`
- seed Sprint 11 connector expansion with deterministic Telegram, browser clipper, PDF/DOCX/CSV/screenshot, and voice-transcript payload ingestion, raw evidence preservation, default domain/sensitivity labels, event-log sync cursors, failure isolation, connector API/CLI access, and connector settings UI
- seed Sprint 12 public release polish with README vNext preview positioning, quickstart/Docker/local install docs, architecture and security/privacy docs, example ALICE.md, contributor guide, synthetic demo dataset, demo video script, and vNext public release checklist
- preserve `v0.5.1`/Phase 14 behavior while vNext is built incrementally

## Next Roadmap Gate
- Validate the vNext migration against live Postgres and run a timed fresh-machine quickstart before deciding whether to tag a vNext preview. Remaining product slices are production scheduling, live connector auth/polling, live-backed UI expansion, and model-backed/live-store evals.
- Preserve the shipped Phase 14 platform plus the `HF-001` logging guardrails as baseline behavior.

## Beyond Phase 14
- Alice vNext follows `docs/alice_vnext_true_second_brain_tech_spec.md`.
- The immediate feature sequence starts with the vNext memory kernel before production queue automation, graph/contradiction intelligence, connectors, and UI expansion.
