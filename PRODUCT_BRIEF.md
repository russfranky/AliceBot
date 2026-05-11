# Product Brief

## Product Summary
Alice is a pre-1.0 continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, provider/runtime portability, and integration paths for external agent runtimes.

## Shipped Baseline
- Phase 9 shipped the continuity core, CLI, MCP, importers, approvals, and evaluation foundation.
- Phase 10 shipped the hosted/product layer, identity/workspace model, and channel surfaces.
- Phase 11 shipped provider runtime foundations, initial provider adapters, and model-pack primitives.
- Bridge `B1` through `B4` shipped Hermes lifecycle hooks, auto-capture, review flow, explainability, packaging docs, smoke validation, and demo path.
- Phase 12 shipped hybrid retrieval and reranking, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- Phase 13 shipped one-call continuity, Alice Lite, and memory hygiene / conversation health visibility.
- Phase 14 shipped provider adapters, model packs, reference integrations, and design-partner launch/admin surfaces.
- `HF-001` shipped logging safety and disk guardrails for local/Lite runtime behavior.
- `v0.5.1` is the latest stable pre-1.0 release tag.
- `v0.5.1-vnext-preview` is the vNext public-preview pre-release target.

## Current Repo Posture
- Phase 14 is shipped.
- `HF-001` is shipped.
- Alice vNext Sprint 1 through Sprint 12 preview scope is implemented.
- Alice vNext live capture connectors are implemented for allowlisted Telegram, local folders/Obsidian notes, browser clips, and agent outputs while preserving review-only trust boundaries.
- Alice vNext dogfood hardening is implemented for connector settings/state persistence, local secret references, cursor reliability, doctor checks, live `/vnext` connector configuration, and daily local-alpha runbooks.
- Alice vNext public preview release gate is active.

## Latest Completed Phase
### Phase 14: Provider Adapters + Design Partner Launch
Phase 14 turned Alice from a strong continuity system into a practical integration platform for local runtimes, self-hosted inference servers, enterprise-curious teams, and early design partners.

## Latest Hardening Sprint
### HF-001: Logging Safety And Disk Guardrails
`HF-001` removed the local/Lite operational defect where logging could grow without bound and exhaust disk.

## Primary Users
- builders who want to plug Alice into their own agents or workflows
- self-hosters running local or private model stacks through Ollama, llama.cpp, or vLLM
- enterprise-curious teams evaluating Alice with Azure or OpenAI-compatible infrastructure
- design partners using Alice in production-like environments and generating adoption proof

## Shipped Scope Through `v0.5.1`
- stable provider abstraction and workspace-scoped provider management
- first-class adapters for OpenAI-compatible, Ollama, llama.cpp, vLLM, and Azure-backed paths
- declarative, versioned model packs with workspace binding and sensible defaults
- reference integrations for Hermes, OpenClaw, generic Python agents, and generic TypeScript agents
- design-partner onboarding, tracking, instrumentation, and structured feedback capture
- logging safety defaults for local/Lite runtime plus bounded opt-in file logging

## Non-Goals
- `v1.0.0` compatibility or support guarantees
- managed cloud/SLA commitments
- new channels
- marketplace work
- enterprise governance/compliance expansion
- major vertical-agent work
- deep browser/action automation

## Success Criteria Reached In `v0.5.1`
- Alice runs cleanly with OpenAI-compatible providers, Ollama, llama.cpp, vLLM, and Azure-backed paths
- users can bind a model pack and get sensible continuity defaults without hand tuning
- Hermes and OpenClaw have polished, documented, and tested Alice paths
- generic Python and TypeScript examples exist and are reproducible
- design-partner onboarding, usage summaries, and structured feedback are part of the shipped admin surface
- local/Lite logging defaults no longer create unbounded disk growth

## Immediate Product Posture
- `v0.5.1` is the current public release boundary.
- `v0.5.1-vnext-preview` is the vNext public-preview release target on top of the shipped Phase 14 + `HF-001` baseline.
- The next product decision after dogfood hardening is whether to prioritize broader live-backed `/vnext` workflows, managed connector OAuth, production scheduling, or model-backed evaluation.
