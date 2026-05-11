# Sprint Packet

## Sprint Title
Alice vNext Sprint 1 - Architecture Foundation and Schema

## Activation Note
- This packet is active.
- `v0.5.1` is the current public release boundary.
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- `M-001` Archive Maintenance CI Repair is implemented in this working tree as the maintenance gate before vNext work.
- This sprint starts the Alice vNext / True Second Brain build from `docs/alice_vnext_true_second_brain_tech_spec.md`.

## Sprint Type
feature-foundation

## Sprint Reason
Alice vNext requires a larger memory-kernel foundation than the existing Phase 14 continuity substrate. The first sprint establishes the v2 schema, contracts, repository boundaries, event-log utility, and Brain Charter model without destructively reorganizing existing Phase 14 modules.

## Git Instructions
- Branch Stack: `codex/archive-maintenance-repair` -> `codex/vnext-backend-kernel` -> `codex/vnext-web-workspace` -> `codex/vnext-release-docs`
- Base Branch: `main`
- PR Strategy: stacked draft PRs by system area
- Merge Policy: merge the stack in order after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-14 baseline
- shipped Bridge `B1` through `B4`
- published `v0.5.1` baseline
- shipped one-call continuity surface
- shipped Alice Lite profile
- shipped hygiene/thread-health visibility
- shipped Phase 14 provider contract, local/self-hosted compatibility, model packs, reference integrations, and design-partner launch surface
- shipped `HF-001` logging safety and disk guardrails
- `M-001` archive-maintenance repair behavior
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Establish the Alice vNext memory-kernel foundation: v2 schema/migration support, shared schema contracts, repository interfaces, append-only event-log utility, and ALICE.md / Brain Charter model.

## In Scope
- v2-compatible database migration for sources, source chunks, provenance links, graph edges, projects, people, beliefs, generated artifacts, task queue, event log, and brain charters
- compatibility extensions for existing `memories`, `memory_revisions`, and `open_loops`
- domain/sensitivity enums and constraints
- shared JSON schemas/types for memory, source, artifact, graph edge, context pack, and event records
- repository protocol interfaces for the vNext storage abstraction
- Postgres vNext store facade with CRUD-style methods for the Sprint 1 entities
- event-log helper for deterministic hashable event records
- Brain Charter model and default ALICE.md template
- forward-compatible Sprint 2 seed for vNext text/file/Markdown/ChatGPT source capture, hashing, chunking, candidate-memory extraction, provenance linking, CLI commands, and minimal source API endpoints
- forward-compatible Sprint 3 seed for query classification, keyword retrieval, domain/sensitivity filtering, context-pack generation, trace metadata, and CLI/API/MCP access
- forward-compatible Sprint 4 seed for task queue enqueue/process behavior, deterministic generated artifacts, artifact review/export actions, and CLI/API access
- forward-compatible Sprint 5 seed for deterministic daily brief and weekly synthesis artifacts, provenance sections, sensitivity inheritance, candidate open loops/memories, and CLI/API/MCP manual triggers
- forward-compatible Sprint 6 seed for deterministic connection reports, candidate graph edge creation, edge review status, graph neighborhood lookup, and CLI/API/MCP access
- forward-compatible Sprint 7 seed for deterministic contradiction reports, candidate contradiction edges, belief review state changes, belief state history lookup, and CLI/API/MCP access
- forward-compatible Sprint 8 seed for project update candidates, candidate project-state memories, open-loop extraction/review, project dashboard data, and CLI/API/MCP access
- forward-compatible Sprint 9 UI seed for a fixture-backed vNext second-brain workspace with Home, Inbox, Ask Alice, briefs, generated artifacts, memory review, queue, projects, people, beliefs, open loops, timeline, graph, and settings/privacy surfaces
- forward-compatible Sprint 10 eval/hardening seed for deterministic synthetic benchmark generation, recall/temporal/contradiction/privacy/provenance/open-loop/prompt-injection eval suites, baseline metrics, report writing, and `alicebot eval ...` CLI access
- forward-compatible Sprint 11 connector expansion seed for deterministic Telegram, browser clipper, PDF/DOCX/CSV/screenshot, and voice-transcript payload ingestion with raw evidence preservation, default domain/sensitivity, cursor-based duplicate prevention, API/CLI access, and connector settings UI
- forward-compatible Sprint 12 public release polish seed for README vNext positioning, quickstart, Docker/local install docs, example ALICE.md, synthetic demo dataset, demo video script, contributor guide, security/privacy docs, architecture docs, and release checklist
- targeted migration and contract tests

## Out Of Scope
- full live-backed vNext UI integration beyond the fixture-backed Sprint 9 seed
- live connector OAuth/linking, live external polling, browser extension packaging, OCR/transcription model execution, and cloud/file-system watchers beyond deterministic Sprint 11 payload ingestion
- actual public tag creation, release publishing, demo video recording, or third-party distribution for the Sprint 12 docs seed
- production autonomous queue worker scheduling and external tool execution
- production scheduled daily/weekly automation and model-backed synthesis
- production-grade connection ranking/evaluation and retrieval reranking from accepted graph edges
- full temporal-state integration for belief histories and model-backed contradiction classification
- fully split UI-backed project subpages and full repeat-suggestion suppression for rejected project update candidates
- model-backed or human-rated eval scoring beyond the deterministic Sprint 10 synthetic harness
- broad package reorganization
- destructive replacement of existing memory or continuity tables

## Proposed Files And Modules
- `apps/api/alembic/versions/20260510_0067_vnext_memory_kernel_schema.py`
- `apps/api/src/alicebot_api/vnext_repositories.py`
- `apps/api/src/alicebot_api/vnext_store.py`
- `apps/api/src/alicebot_api/vnext_capture.py`
- `apps/api/src/alicebot_api/vnext_retrieval.py`
- `apps/api/src/alicebot_api/vnext_queue.py`
- `apps/api/src/alicebot_api/vnext_brain.py`
- `apps/api/src/alicebot_api/vnext_connections.py`
- `apps/api/src/alicebot_api/vnext_connectors.py`
- `apps/api/src/alicebot_api/vnext_contradictions.py`
- `apps/api/src/alicebot_api/vnext_evals.py`
- `apps/api/src/alicebot_api/vnext_projects.py`
- `apps/api/src/alicebot_api/vnext_event_log.py`
- `apps/api/src/alicebot_api/brain_charter.py`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `apps/web/app/vnext/page.tsx`
- `apps/web/app/vnext/page.test.tsx`
- `apps/web/components/vnext-brain-workspace.tsx`
- `docs/vnext/*.md`
- `docs/release/vnext-public-release-checklist.md`
- `fixtures/vnext/demo_dataset.json`
- `apps/web/components/app-shell.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/globals.css`
- `pyproject.toml`
- `schemas/*.schema.json`
- `tests/unit/test_20260510_0067_vnext_memory_kernel_schema.py`
- `tests/unit/test_vnext_foundation_contracts.py`
- `tests/unit/test_vnext_store.py`
- `tests/unit/test_vnext_capture.py`
- `tests/unit/test_vnext_retrieval.py`
- `tests/unit/test_vnext_queue.py`
- `tests/unit/test_vnext_brain.py`
- `tests/unit/test_vnext_connections.py`
- `tests/unit/test_vnext_connectors.py`
- `tests/unit/test_vnext_contradictions.py`
- `tests/unit/test_vnext_evals.py`
- `tests/unit/test_vnext_release_polish.py`
- `tests/unit/test_vnext_projects.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_vnext_main.py`
- `tests/unit/test_mcp.py`
- control docs

## Planned Deliverables
- vNext schema migration with reversible downgrade statements
- shared JSON schema contracts
- storage repository interface definitions
- Postgres vNext store facade with create/read/update/soft-delete or append methods across sources, source chunks, memories, revisions, provenance links, graph edges, projects, people, beliefs, open loops, generated artifacts, task queue, event log, and Brain Charter
- append-only event log helper
- Brain Charter model/template
- vNext source capture service and CLI for manual text, local files, Markdown folders, and ChatGPT export files
- minimal vNext source API for text capture, source lookup, and source soft-delete
- vNext context-pack retrieval service with classifier, keyword search integration, graph/vector/temporal scaffolds, policy filters, placeholders, and trace records
- vNext context-pack CLI, API, and MCP access
- vNext task queue/artifact service with enqueue, process-next, review, Markdown export, CLI commands, and API endpoints
- vNext daily brief and weekly synthesis service with deterministic templates, source sections, sensitivity inheritance, candidate open-loop/memory creation, CLI commands, API endpoints, and MCP tools
- vNext connection finder service with connection report artifacts, candidate graph edges, review actions, graph neighborhood lookup, CLI commands, API endpoints, and MCP tools
- vNext contradiction finder and belief-review service with contradiction report artifacts, candidate contradiction graph edges, belief challenge/supersession actions, belief state history lookup, CLI commands, API endpoints, and MCP tools
- vNext project/open-loop service with project update candidate artifacts, candidate project-state memories, explicit review actions, open-loop extraction/edit/close/snooze, project dashboard data, CLI commands, API endpoints, and MCP tools
- vNext web UI seed under `/vnext` with visible Home, Inbox, Ask Alice, Daily Brief, Weekly Synthesis, Queue, Generated, Memory Review, Projects, People, Beliefs, Open Loops, Timeline, Graph, and Settings/Privacy surfaces
- vNext eval harness seed with a synthetic benchmark corpus generator, baseline targets, recall/temporal/contradiction/privacy/provenance/open-loop/prompt-injection suite runners, report writer, and `eval seed/run/report` CLI commands
- vNext connector service seed with connector definitions, deterministic item normalizers, raw-evidence archive through source capture, event-log sync cursors, failure isolation, `vnext connectors list/ingest` CLI commands, connector API endpoints, and fixture-backed connector settings UI
- vNext public-preview docs package with README pointers, quickstart, architecture, security/privacy, example ALICE.md, contributor guide, demo video script, synthetic demo dataset, and release checklist
- targeted tests plus full unit-suite verification

## Acceptance Criteria
- migrations define all Sprint 1 vNext entities or compatibility columns
- all new vNext entities have domain/sensitivity where applicable
- memory type compatibility preserves legacy memory types while adding vNext types
- event log is append-only and RLS-scoped
- shared schema files exist for memory/source/artifact/graph/context/event
- repository interfaces match the spec-required storage abstraction names
- vNext store methods cover CRUD-style access for major Sprint 1 entities
- create/update store operations append event-log records
- vNext capture imports preserve raw source text before chunking
- vNext capture deduplicates by content hash and links candidate memories to source chunks
- vNext Markdown folder import can process 100 unique markdown files and skip duplicates
- vNext import failures are logged and do not prevent later files in the same folder from importing
- `alicebot context-pack "query"` returns a structured vNext context pack
- context pack includes memories, sources, contradictions placeholder, open loops placeholder, and trace metadata
- sensitive memories are filtered according to the allowed sensitivity policy
- vNext context packs are available through API and MCP
- vNext queue tasks can be enqueued and processed into deterministic generated artifacts
- vNext artifacts can be reviewed and exported through CLI and API paths
- vNext daily briefs and weekly syntheses create reviewable generated artifacts with source references and `artifact.generated` events
- vNext weekly syntheses create candidate insight memories without auto-promotion
- vNext connection reports create candidate graph edges with confidence/explanations and log each candidate edge
- vNext graph edges can be accepted/rejected and queried by graph neighborhood
- vNext contradiction reports cite both sides, distinguish direct conflict from nuance, recommend a review action, and do not mutate beliefs automatically
- vNext beliefs can be challenged/superseded through explicit review actions and queried for current/history state
- vNext project notes create reviewable project update candidates and accepting them updates project state plus memory revisions
- vNext open loops preserve source/date metadata, owner where detected, and support close/snooze/edit/reopen review actions with project filtering
- `/vnext` exposes the Sprint 9 UI surfaces without requiring a live API connection
- vNext UI review actions update visible fixture-backed state for accept, edit, reject, promote, project assignment, label updates, and open-loop creation
- vNext UI Ask Alice output shows an answer, sources/provenance, memories used, contradictions, why explanation, and save-as-artifact behavior
- vNext UI generated artifacts and review rows show domain/sensitivity labels plus source/provenance context
- vNext synthetic benchmark generation includes the spec counts for people, projects, notes, decisions, beliefs, contradictions, superseded beliefs, open loops, personal reflections, future reminders, hidden cross-domain connections, and prompt-injection sources
- `alicebot eval run --suite all` completes and reports baseline metrics for exact recall, temporal accuracy, contradiction precision, provenance precision, privacy leakage, open-loop recall, and prompt-injection write safety
- critical privacy leakage evals pass with zero critical leaks
- prompt-injection corpus sources are quarantined and do not trigger tool writes
- vNext connector definitions cover Telegram, browser clipper, PDF, DOCX, CSV, screenshot OCR, and voice transcription payloads
- each vNext connector archive preserves raw payload/extracted evidence in source metadata
- each vNext connector supports default domain and sensitivity labels
- connector sync cursors skip already-seen items and avoid advancing past failed items
- connector sync failures log failure events without importing broken items into memory
- `/vnext` exposes connector settings defaults and allows fixture-backed default label edits
- README and vNext docs clearly explain Alice Core vs Alice Brain vs Alice Agent Memory
- quickstart documents local install, Docker/local stack, first source capture, and first daily brief
- demo dataset is synthetic and contains no obvious secret markers or private account data
- release checklist captures tests/lint/evals, no-secrets review, connector security review, and known limitations
- no existing Alice functionality is broken by the foundation changes

## Required Verification
- `pnpm test app/vnext/page.test.tsx` from `apps/web`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_connectors.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_release_polish.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_evals.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_20260510_0067_vnext_memory_kernel_schema.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_foundation_contracts.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_store.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_capture.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_retrieval.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_queue.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_brain.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_connections.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_contradictions.py -q`
- `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all", "--report-path", "/tmp/alice-vnext-eval-report.json"]))'`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_projects.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_cli.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_vnext_main.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_mcp.py -q`
- `./.venv/bin/python -m pytest tests/unit -q`
- `python3 scripts/check_control_doc_truth.py`
- `git diff --check`

## Control Tower Decisions Needed
- decide whether the public default should remain Postgres-first for vNext development while SQLite support is designed
- decide whether old `memories` rows should be backfilled into full v2 canonical text/domain/sensitivity values before Sprint 2
- decide which Sprint 11 connectors should become live-backed first and where connector secrets/cursors should live once event-log cursor seeding is no longer enough

## Exit Condition
This sprint is complete when the vNext schema foundation, shared contracts, repository interfaces, event-log utility, Brain Charter model, and targeted tests are implemented without regressing the existing unit suite.
