# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- Phase 13 is shipped.
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- `v0.5.1` is the latest published tag.
- `M-001` Archive Maintenance CI Repair is implemented in this working tree.
- Alice vNext Sprint 1 - Architecture Foundation and Schema is active.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline includes one-call continuity across API, CLI, and MCP.
- The shipped baseline includes the Alice Lite startup/profile path.
- The shipped baseline includes memory hygiene and thread/conversation health visibility.
- The shipped baseline includes the Phase 14 provider contract, workspace-scoped provider registration/update flows, provider capability snapshots, invocation telemetry persistence, and the OpenAI-compatible adapter hardening from `P14-S1`.
- The shipped baseline includes the Phase 14 local/self-hosted compatibility layer from `P14-S2`, including the dedicated `vllm` provider path, aligned health semantics, and pack-compatibility/runtime coverage for the local/self-hosted provider surface.
- The shipped baseline includes provider-aware model-pack bindings, the first-party `llama` / `qwen` / `gemma` / `gpt-oss` catalog, and pack-aware runtime/briefing defaults from `P14-S3`.
- The shipped baseline includes polished Hermes/OpenClaw reference integrations, generic Python/TypeScript examples, and reproducible reference demos from `P14-S4`.
- The shipped baseline includes the design-partner launch/admin surface from `P14-S5`.
- The shipped baseline includes logging safety and disk guardrails from `HF-001`, including stdout-by-default local logging, disabled local/Lite access logs by default, and bounded file logging when explicitly enabled.
- `v0.5.1` is the current public pre-1.0 release boundary for that shipped baseline.
- The working tree includes the `M-001` archive-maintenance repair: absent archive indexes skip checksum verification, maintenance-user bootstrap commits before benchmark imports, and duplicate workflow alert issues are deduped by commenting on an existing open issue.
- The working tree includes Alice vNext Sprint 1 foundation work: vNext schema migration, shared JSON schemas, repository protocols, Postgres vNext store facade, event-log helper, and Brain Charter model.
- The working tree also includes a Sprint 2 capture seed: vNext manual text/file/Markdown/ChatGPT source capture, content-hash dedupe, chunking, candidate-memory creation, provenance links, failure logging, `alicebot vnext sources ...` CLI commands, and minimal source API endpoints for text capture/get/delete.
- The working tree also includes a Sprint 3 retrieval/context-pack seed: deterministic query classification, keyword memory/source/open-loop retrieval, domain/sensitivity filtering, provenance-backed context packs, trace metadata, `alicebot context-pack`, `/v0/vnext/context-packs`, and `alice_vnext_context_pack` MCP access.
- The working tree also includes a Sprint 4 queue/artifact seed: vNext task enqueue/process-next behavior, deterministic generated artifacts, artifact review/export actions, `alicebot vnext queue ...` and `alicebot vnext artifacts ...` CLI commands, and queue/artifact API endpoints.
- The working tree also includes a Sprint 5 brain-workflow seed: deterministic daily brief and weekly synthesis artifacts, source/reference sections, inherited sensitivity, candidate open loops/memories, `alicebot daily-brief`, `alicebot weekly-synthesis`, vNext artifact-generation API endpoints, and MCP tools for daily/weekly generation.
- The working tree also includes a Sprint 6 connection/graph seed: deterministic connection reports, candidate graph edge creation with confidence/explanations, edge review status, graph neighborhood lookup, `alicebot connections generate`, `alicebot vnext graph ...`, vNext graph API endpoints, and MCP tools for connection/graph operations.
- The working tree also includes a Sprint 7 contradiction/belief seed: deterministic contradiction reports, candidate contradiction graph edges, direct-conflict versus nuance classification, explicit belief challenge/supersession review actions, belief state history lookup, `alicebot vnext contradictions ...`, `alicebot vnext beliefs ...`, vNext belief/contradiction API endpoints, and MCP tools for contradiction/belief operations.
- The working tree also includes a Sprint 8 project/open-loop seed: deterministic project update candidate artifacts, candidate project-state memories, accept/edit/reject review actions, open-loop extraction with source/date/owner metadata, close/snooze/edit/reopen open-loop actions, project dashboard data, `alicebot vnext projects ...`, `alicebot vnext open-loops ...`, vNext project/open-loop API endpoints, and MCP tools for project/open-loop operations.
- The working tree also includes a Sprint 9 UI seed: `/vnext` in the existing Next.js web shell with fixture-backed Home, Inbox, Ask Alice, Daily Brief, Weekly Synthesis, Queue, Generated, Memory Review, Projects, People, Beliefs, Open Loops, Timeline, Graph, and Settings/Privacy surfaces; stateful review actions; Ask Alice provenance; generated artifacts; and visible domain/sensitivity labels.
- The working tree also includes a Sprint 10 eval/hardening seed: deterministic synthetic benchmark corpus generation, recall/temporal/contradiction/privacy/provenance/open-loop/prompt-injection eval suites, baseline targets, `alicebot eval seed/run/report`, an `alice` console-script alias, report writing, zero critical privacy leaks, and prompt-injection sources quarantined without tool writes.
- The working tree also includes a Sprint 11 connector expansion seed: deterministic Telegram, browser clipper, PDF/DOCX/CSV/screenshot, and voice-transcript payload ingestion through the vNext capture path, raw evidence preservation, default domain/sensitivity labels, event-log sync cursors, failure isolation, `alicebot vnext connectors ...` CLI commands, connector API endpoints, and fixture-backed connector settings UI.
- The working tree also includes a Sprint 12 public release polish seed: README vNext preview positioning, docs for quickstart/Docker/local install/architecture/security/privacy/contribution, example `ALICE.md`, synthetic demo dataset, demo video script, and vNext public release checklist with no-secrets and verification gates.

## Phase Transition Note
- Phase 14 is complete as a feature phase.
- `HF-001` is complete as a defect-only hardening sprint.
- `v0.5.1` closes the shipped Phase 14 platform plus the post-phase logging safety hardening.
- `M-001` is implemented in this working tree and should be validated in GitHub Actions after PR push/merge.
- Alice vNext Sprint 1 is now the active build sprint on top of that repaired baseline.

## Immediate Control Tower Decisions Needed
- Use the separate `PostgresVNextStore` facade as the Sprint 2 persistence boundary unless a concrete integration blocker appears.
- Decide whether old `memories` rows should be backfilled into full v2 canonical text/domain/sensitivity values before Sprint 2.
- Decide whether the vNext capture API should expose local folder import directly or keep folder import CLI-only for local deployments.
- Decide whether vNext context packs should be automatically persisted as generated artifacts or remain ephemeral until a user enqueues a queue task.
- Decide which queue write policies may advance beyond deterministic local artifacts into external tool execution.
- Decide how production daily/weekly scheduling should be configured and whether model-backed synthesis should replace or augment the deterministic Sprint 5 templates.
- Decide how accepted vNext graph edges should influence retrieval ranking beyond trace/neighborhood visibility.
- Decide how vNext belief status history should be unified with the existing temporal-state APIs and whether contradiction classification should use model-backed evidence review.
- Decide how project-update rejection suppression should be persisted beyond event logs and how UI project pages should expose candidate review state.
- Decide which vNext UI surfaces should become live-backed first after the fixture-backed Sprint 9 seed.
- Decide when the deterministic Sprint 10 eval harness should graduate to model-backed, live-store-backed, or human-rated scoring.
- Decide which Sprint 11 connectors should become live-backed first and where connector secrets/cursors should live once event-log cursor seeding is no longer enough.
- Decide whether Sprint 12 docs are enough to tag a vNext preview or whether a fresh-machine install timing run is required first.
- Avoid reopening completed Phase 14 or `HF-001` scope unless a concrete defect or release-readiness issue is identified.
