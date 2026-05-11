# Architecture

## Scope Boundary
- **Shipped baseline:** Phases 9-14, `HF-001`, and Bridge `B1` through `B4`.
- **Current execution posture:** `v0.5.1` remains the stable public release tag; Phase 14 and `HF-001` are shipped; `v0.5.1-vnext-preview` is the vNext public-preview tag target.
- **Release principle:** `v0.5.1` is the current pre-1.0 public release boundary for the shipped Phase 14 platform plus the logging-safety hardening.

## Current System Overview
Alice is a modular continuity platform with shared continuity semantics across local, hosted, provider-runtime, CLI, MCP, Hermes-integrated, and imported-workflow surfaces.

## Technical Stack
- API/runtime: Python + FastAPI in [`apps/api/src/alicebot_api`](apps/api/src/alicebot_api)
- Persistence: Postgres with Alembic migrations in [`apps/api/alembic/versions`](apps/api/alembic/versions)
- Optional cache/runtime support: Redis
- Web/admin: Next.js app in [`apps/web`](apps/web)
- CLI + MCP: Python CLI/MCP plus package shims in [`packages/alice-cli`](packages/alice-cli) and [`packages/alice-core`](packages/alice-core)
- Ops/demo/test scripts: [`scripts`](scripts)

## Shipped Module Boundaries

### Continuity Core
- Capture, review, lifecycle, explainability, recall, resumption, open-loop workflows, and one-call continuity assembly.

### Retrieval And Evidence Foundations
- Hybrid retrieval, embeddings, entity/entity-edge support, reranking, trust-aware evidence shaping, and persisted retrieval traces.

### Mutation, Trust, And Briefing Foundations
- Explicit memory operations, contradiction cases, trust signals, public eval persistence, and task-adaptive briefing.

### Hosted/Product Layer
- Workspace, identity, devices, preferences, telemetry, web/admin, and channel surfaces.

### Provider Runtime Foundation
- Workspace-scoped provider records, capability snapshots, runtime invocation boundaries, model-pack primitives, and secret handling.

### Integration Surfaces
- CLI, MCP, Hermes bridge/provider flows, OpenClaw import/augmentation, deployment profiles such as Alice Lite, and generic external-builder reference examples.

### vNext Preview Surfaces
- local-first vNext memory kernel with sources, source chunks, provenance links, generated artifacts, artifact quality ratings, event log, agent identities, scheduler workflows, and connector evidence
- live local capture connectors for allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clip captures, and Hermes/OpenClaw-style agent output ingestion
- `/vnext` operator workspace with live/fixture-backed review, Ask Alice, generated artifacts, model comparison, scheduler controls, connector health, dogfooding telemetry, and privacy settings

## Current Data Model Summary

### Continuity And Memory
- `memories`, `memory_revisions`, `memory_review_labels`
- `continuity_capture_events`, `continuity_objects`, `continuity_correction_events`
- `open_loops`
- `memory_operation_candidates`, `memory_operations`
- `contradiction_cases`, `trust_signals`

### Retrieval And Evaluation
- `embedding_configs`, `memory_embeddings`
- `entities`, `entity_edges`
- `retrieval_runs`, `retrieval_candidates`
- `eval_suites`, `eval_cases`, `eval_runs`, `eval_results`

### Product / Runtime
- `workspaces`, `workspace_members`, `auth_sessions`, `devices`
- `model_providers`, `provider_capabilities`, `model_packs`, `workspace_model_pack_bindings`
- `provider_invocation_telemetry`
- design-partner launch/admin tables from `P14-S5`
- `task_briefs`
- channel, task, trace, approval, and execution tables

## Key Flows In Force

### Capture And Review
1. Raw content enters continuity capture.
2. Alice creates capture events and candidate continuity objects.
3. Review/correction can confirm, edit, supersede, or delete.
4. Explainability preserves provenance and lifecycle state.

### Recall, Resumption, And Briefing
1. Recall loads continuity candidates.
2. Ranking considers semantic similarity, lexical/entity signals, trust, freshness, provenance, and supersession.
3. Resumption and one-call continuity compose ranked recall into decisions, open loops, recent changes, provenance, trust posture, and next action.

### Provider Runtime
1. Workspace binds provider and optional model-pack configuration.
2. Runtime invokes through provider adapter boundaries.
3. Invocation telemetry and capability snapshots remain inspectable.

### External Builder Runtime
1. External runtimes use one-call continuity, MCP, Hermes provider-plus-MCP, or OpenClaw import/augmentation paths.
2. Provider and model-pack controls remain Alice-side supporting configuration.
3. Generic examples and reproducible demos package the shipped surface rather than defining a second runtime contract.

## Delivered Phase 14 Delta

### P14-S1: Provider Abstraction Cleanup + OpenAI-Compatible Adapter
- Stabilized the provider adapter contract.
- Shipped workspace-scoped provider registration and update flows.
- Shipped capability discovery and capability snapshots.
- Shipped OpenAI-compatible adapter hardening.
- Shipped provider invocation telemetry persistence and hosted RLS posture for the new telemetry table.

### P14-S2: Ollama + llama.cpp + vLLM Adapters
- Hardened the local/self-hosted runtime paths onto the stabilized provider contract.
- Added the dedicated `vllm` provider path with provider-native health semantics and registration/config support.
- Extended provider/runtime and pack-compatibility coverage for the local/self-hosted provider surface.

### P14-S3: Model Packs
- Added provider-aware workspace model-pack bindings on top of the shipped provider surface.
- Shipped the first-party `llama`, `qwen`, `gemma`, and `gpt-oss` pack catalog.
- Added pack-aware runtime and briefing defaults plus declarative compatibility enforcement.

### P14-S4: Reference Integrations
- Packaged the shipped continuity, provider, and pack surface into polished external-builder paths.
- Refreshed Hermes and OpenClaw documentation around the shipped one-call continuity and provider/pack baseline.
- Added generic Python and TypeScript reference agent examples plus reproducible demos.

### P14-S5: Design Partner Launch
- Turned the shipped Phase 14 platform into tracked pilot adoption and launch evidence.
- Added design-partner objects, workspace linkage, onboarding/support flows, usage summaries, and structured feedback paths.

### HF-001: Logging Safety And Disk Guardrails
- Added explicit logging configuration and moved local/Lite defaults to stdout.
- Disabled access logs by default in Lite/local profile.
- Added bounded rotation when file logging is explicitly enabled.
- Documented the recommended `systemd`/`journald` posture for managed environments.
- Added smoke coverage proving no unbounded local log file is created in `/tmp`.

## Security And Reliability Rules
- Keep user/workspace isolation intact for continuity, provider, runtime, and design-partner data.
- Keep provider credentials and secret references out of logs and outward-facing errors.
- Preserve approval-bounded execution for consequential side effects.
- Keep capture, mutation, provider, and Hermes sync paths idempotent.
- Preserve append-only evidence where the system depends on auditability.
- Do not let provider-specific behavior fork continuity semantics.
- Do not let model packs bypass provenance, trust, or contradiction rules already enforced by the baseline.
- Keep local/Lite logging bounded and operationally safe by default.

## Testing Strategy
- unit/integration tests for continuity, provider runtime, and API behavior
- provider smoke tests and provider-capability parity checks
- model-pack smoke tests and compatibility-matrix validation
- integration smoke tests for Hermes, OpenClaw, Python example, and TypeScript example paths
- design-partner onboarding, linkage, usage-summary, and feedback-flow validation
- logging configuration and `/tmp` safety validation
- vNext live-capture connector smoke and capture-to-brief smoke validation
- release gates remain green across Python, web, Alice Lite, Hermes smoke, and public eval harness
- docs verification is part of sprint completion, not cleanup work

## Current Architectural Posture
- `v0.5.1` is the active public release boundary.
- `v0.5.1-vnext-preview` packages the local-first vNext public preview without changing the stable baseline boundary.
- Alice is now a broader continuity platform with provider/runtime portability, model packs, runnable external-builder integrations, design-partner launch/admin support, and safe local logging defaults.
- The continuity substrate remains the same system of record; the delivered work packages that substrate into practical adoption paths without changing the core continuity semantics.
