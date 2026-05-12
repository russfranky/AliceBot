<!--
SEO keywords: alice ai memory, ai agent memory, continuity layer, mcp memory server,
durable memory for agents, agent resumption, open loop tracking, local-first ai runtime
-->

# Alice

**The continuity layer for AI agents.**

![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)
![Docker](https://img.shields.io/badge/docker-required-2496ED)
![License](https://img.shields.io/badge/license-MIT-2ea043)

Alice helps agents **remember what matters, resume interrupted work, explain why something is true, and improve when corrected**.

`v0.5.1` is the current **pre-1.0 public release**.

This working tree also contains the Alice vNext public-preview seed described in
[docs/vnext/README.md](docs/vnext/README.md). The vNext preview uses the pre-release tag
`v0.5.1-vnext-preview`; `v0.5.1` remains the current stable pre-1.0 public release.

Most assistants are still good only in the moment. They can answer the current prompt, but they struggle to preserve decisions, track open loops, recover context across sessions, and stay aligned after memory corrections.

Alice fixes that.

It provides a **local-first memory and continuity engine** for capture, recall, resumption, open-loop tracking, and correction-aware, trust-aware memory, so you do not have to rebuild context from scratch every time work resumes.

**Bring your own models, keep one continuity layer.**

**Works across local, self-hosted, enterprise, and external-agent workflows via CLI, MCP, provider runtime, OpenClaw import, and Hermes integration.**

## Alice vNext Preview

Alice vNext is the next release candidate for the true second-brain product. It is organized into three layers:

- **Alice Core**: local-first storage, provenance, policy, event logging, revisions, graph objects, sources, and connector evidence.
- **Alice Brain**: user-facing second-brain workflows such as daily briefs, weekly syntheses, context packs, contradiction reports, project updates, open loops, and reviewable artifacts.
- **Alice Agent Memory**: CLI, API, and MCP surfaces that let agents capture, retrieve, resume, explain, generate context, propose memory, and trigger governed workflows without owning the memory store.

The vNext preview currently includes deterministic source capture, retrieval/context packs, queue/artifact workflows, daily and weekly brain artifacts, connection/contradiction/project/open-loop workflows, model-backed source-grounded synthesis, human artifact quality ratings, deterministic-vs-model comparison controls, synthetic evals, live local capture connectors for Telegram, local folders/Obsidian notes, browser clips, and Hermes/OpenClaw-style agent outputs, dedicated connector settings/state storage, encrypted local secret references, deterministic document connector payload ingestion, agent identity/policy auditing, a governed local scheduler with due scans, a local scheduler daemon, policy telemetry, dogfooding readiness telemetry, doctor/readiness checks, capture-to-brief traceability, and a live/fixture-backed `/vnext` operator workspace with source review, memory review, artifact review, project, open-loop, scheduler, connector, and doctor controls.

## Public Alpha Quickstart

Alice is a local-first memory and continuity layer for humans and agents. It lets agents like Hermes, OpenClaw, or your own custom agents request scoped context, submit outputs, propose memories, create open loops, and generate reviewable artifacts without giving them direct write access to trusted memory. The `/vnext` workspace is the operator console for review, audit, configuration, and troubleshooting.

Alice is not a notes app, an Obsidian clone, a chatbot with memory, hosted SaaS, or automatic memory autopilot. The public alpha is a technical local alpha for design partners and agent builders.

Fast path:

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
make setup
make migrate
make doctor
make dev
```

Then open:

```text
http://localhost:3000/vnext
```

Load safe synthetic demo data and run the public alpha readiness gate:

```bash
alicebot vnext demo load --reset
alicebot vnext smoke agent-integration-pack
alicebot vnext alpha check
```

Agent integration starts with [docs/alpha/agent-integration.md](docs/alpha/agent-integration.md), [docs/alpha/mcp-tools.md](docs/alpha/mcp-tools.md), [docs/alpha/hermes-skill.md](docs/alpha/hermes-skill.md), and [docs/alpha/openclaw-skill.md](docs/alpha/openclaw-skill.md). Security, privacy, and limitations are documented in [docs/alpha/security-and-privacy.md](docs/alpha/security-and-privacy.md) and [docs/alpha/known-limitations.md](docs/alpha/known-limitations.md).

Headless Ubuntu/Hermes dogfood starts with [docs/alpha/headless-ubuntu-install.md](docs/alpha/headless-ubuntu-install.md) and [docs/alpha/hermes-dogfood-ubuntu.md](docs/alpha/hermes-dogfood-ubuntu.md). The secure default is localhost binding plus SSH tunneling:

```bash
ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@server
```

Start with:

- [Public alpha docs](docs/alpha/README.md)
- [Public alpha quickstart](docs/alpha/quickstart.md)
- [First-run checklist](docs/alpha/first-run.md)
- [Headless Ubuntu install](docs/alpha/headless-ubuntu-install.md)
- [Hermes dogfood on Ubuntu](docs/alpha/hermes-dogfood-ubuntu.md)
- [Agent integration pack](docs/alpha/agent-integration.md)
- [vNext overview](docs/vnext/README.md)
- [vNext quickstart](docs/vnext/quickstart.md)
- [vNext architecture](docs/vnext/architecture.md)
- [vNext local runtime](docs/vnext/local-runtime.md)
- [vNext security and privacy](docs/vnext/security-privacy.md)
- [Example ALICE.md](docs/vnext/ALICE.example.md)
- [vNext demo video script](docs/vnext/demo-video-script.md)
- [vNext release checklist](docs/release/vnext-public-release-checklist.md)
- [vNext preview release notes](docs/release/v0.5.1-vnext-preview-release-notes.md)
- [vNext preview tag plan](docs/release/v0.5.1-vnext-preview-tag-plan.md)
- [Agentic control plane CTO summary](docs/vnext-agentic-control-plane-cto-summary.md)
- [Local runtime CTO summary](docs/vnext-local-runtime-cto-summary.md)
- [Model-backed intelligence CTO summary](docs/vnext-model-backed-intelligence-cto-summary.md)
- [Live capture connectors CTO summary](docs/vnext-live-capture-connectors-cto-summary.md)
- [Dogfood hardening CTO summary](docs/vnext-dogfood-hardening-cto-summary.md)
- [Live-backed operator console CTO summary](docs/vnext-live-backed-operator-console-cto-summary.md)
- [Public alpha packaging CTO summary](docs/vnext-public-alpha-packaging-cto-summary.md)
- [Headless Ubuntu packaging CTO summary](docs/vnext-headless-ubuntu-cto-summary.md)
- [Dogfood daily checklist](docs/runbooks/vnext-dogfood-daily-checklist.md)

## Release Boundary (`v0.5.1`)

Completed baseline included in this pre-1.0 public release:

- Phase 9 continuity core and deterministic local CLI/MCP/importer seams
- Phase 10 hosted/product layer
- Phase 11 provider runtime, adapters, and model packs
- Bridge `B1` through `B4` provider contract, auto-capture flow, review/explainability flow, and bridge docs/smoke validation
- Phase 12 retrieval quality stack:
  - hybrid retrieval and reranking
  - explicit memory mutation operations
  - contradiction detection and trust calibration
  - public eval harness and baseline reports
  - task-adaptive briefing
- Phase 13 adoption surfaces:
  - one-call continuity across API, CLI, and MCP
  - Alice Lite one-command local profile
  - memory hygiene visibility
  - conversation/thread health visibility
- Phase 14 platform surfaces:
  - provider/runtime portability across OpenAI-compatible, Ollama, llama.cpp, vLLM, and Azure-backed paths
  - first-party `llama`, `qwen`, `gemma`, and `gpt-oss` model packs with provider-aware bindings
  - Hermes and OpenClaw reference integrations plus generic Python/TypeScript examples
  - design-partner launch/admin surface and launch evidence artifacts
- `HF-001` logging safety hardening:
  - stdout-by-default local/Lite logging
  - access logs disabled by default in local/Lite profile
  - bounded opt-in file logging with rotation

Historical planning/control artifacts remain available in:
[docs/archive/planning/2026-04-08-context-compaction/README.md](docs/archive/planning/2026-04-08-context-compaction/README.md)

## Why Alice exists

AI assistants still fail in the same places:

- important decisions disappear into old chats
- interrupted work is hard to resume
- blockers and waiting-fors get lost
- memory corrections do not reliably improve future behavior
- "memory" often means vague summaries with unclear provenance

Alice is built to solve those problems directly.

## What Alice gives you

Use Alice if you want your agents or workflows to:

- remember decisions, commitments, and context across sessions
- resume work without rereading long threads
- track waiting-fors, blockers, and unresolved follow-ups
- improve deterministically when memory is corrected
- stay portable across CLI, MCP, and imported workflow data

## Why Alice is different

### Built for continuity, not just storage

Alice does not treat memory as a pile of chat history or loose summaries.
It stores **typed continuity objects, revisions, provenance, and open loops** so context can be reused operationally.

### Built for resumption, not just retrieval

Most memory tools help you find something.
Alice is designed to answer the higher-value questions:

- What did we decide?
- What changed?
- What am I waiting on?
- What should happen next?

### Correction-aware by design

Alice supports explicit **review, correction, and supersession** so future answers improve in a traceable way instead of drifting based on hidden summarization.

### Trust-aware by default

Alice does not treat every memory as equally reliable.
Memories carry **trust classification** and **promotion eligibility**, so agents can search broadly without promoting weak, single-source AI-extracted facts into durable truth by default.

### Explainable, not opaque

Recall, resumption, open-loop review, and explain output all expose a shared explanation model with:

- source facts
- trust posture
- evidence segments
- supersession notes
- timestamps

That makes it easier to audit why an answer appeared, how it was derived, and how corrections changed the explanation chain over time.

### Local-first and agent-agnostic

Alice Core runs locally and exposes the same continuity semantics through the CLI and MCP, so you can use it with your own workflows instead of being locked into a closed assistant product.

### Swap providers, not behavior

Alice is now model-flexible.
You can switch or standardize model backends across local, self-hosted, enterprise, and external-agent environments without rewriting Alice's continuity, memory, approval, or provenance behavior.

## Use Alice with your existing agents

Alice is designed to be a **continuity layer**, not a closed assistant silo.

It already supports:

- **MCP-based integrations**
- **OpenClaw import and augmentation**
- **Hermes provider-plus-MCP bridge for always-on continuity**
- **Hermes external memory provider with lifecycle automation and auto-capture**
- **Provider runtime abstraction for workspace-scoped model/provider integration**
- **Local, self-hosted, enterprise, and external-agent deployment paths**
- imported workflow data from Markdown and ChatGPT exports

That means you can use Alice as shared continuity infrastructure across providers and frameworks instead of rebuilding memory behavior per runtime.

## What ships today

The current open-source surface includes:

- Alice Core
- deterministic CLI workflows
- MCP server
- trust-aware memory classification and promotion controls
- shared explainability across recall, resume, open-loop review, and explain surfaces
- scheduled archive maintenance, ops status reporting, and failure alerting
- Hermes bridge with provider lifecycle hooks, always-on continuity prefetch, turn auto-capture, policy-based commit modes (`manual` / `assist` / `auto`), and reviewable explainable candidate memory flows
- provider runtime abstraction with workspace-scoped provider registration, capability snapshots, OpenAI-compatible base adapter, local Ollama/llama.cpp, self-hosted vLLM, enterprise Azure, model packs, and external-agent integration paths
- provider-aware model-pack bindings and first-party `llama` / `qwen` / `gemma` / `gpt-oss` pack defaults
- hybrid retrieval with persisted retrieval traces and debug visibility
- explicit memory mutation operations with auditability and idempotent replay behavior
- contradiction detection, contradiction-aware ranking penalties, and trust-signal inspection
- public eval harness with fixture catalog and checked-in baseline report support
- task-adaptive briefing for user recall, resume, worker subtask, and agent handoff
- one-call continuity through `POST /v1/continuity/brief`, `alice brief`, and `alice_brief`
- Alice Lite one-command local startup profile
- memory hygiene and thread-health dashboards across API, CLI, and web
- importers for OpenClaw, Markdown, and ChatGPT exports
- OpenClaw adapter and demo path
- generic Python and TypeScript reference agent examples and reproducible demos
- design-partner launch/admin surface and anonymized launch evidence
- stdout-by-default local/Lite logging with bounded opt-in file logging
- evaluation harness and integration docs

## Quickstart

Alice Lite is the lighter local/dev deployment profile. It uses the same continuity semantics and the same one-call continuity surface as the full baseline. It is a deployment profile, not a separate product.

Clone the repo and install the local runtime:

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
make setup
```

Start Alice Lite with one command:

```bash
./scripts/alice_lite_up.sh
```

### First useful result in 5 minutes

In another terminal, bootstrap the sample workspace flow and request the default one-call continuity result:

```bash
./.venv/bin/python scripts/bootstrap_alice_lite_workspace.py
```

Or stay on the direct local CLI path and use the shipped one-call continuity entrypoint:

```bash
./.venv/bin/python -m alicebot_api brief --brief-type general --query "local-first startup path"
```

Inspect runtime status:

```bash
./.venv/bin/python -m alicebot_api status
```

Capture something new:

```bash
./.venv/bin/python -m alicebot_api capture "Remember that the Q3 board pack is due on Thursday."
```

Inspect why something is in memory:

```bash
./.venv/bin/python -m alicebot_api explain <continuity_object_id>
```

Run the Lite smoke check:

```bash
./.venv/bin/python scripts/run_alice_lite_smoke.py
```

For the full local/dev stack with Redis and MinIO, keep using `./scripts/dev_up.sh` plus the existing `./scripts/load_sample_data.sh` and `APP_RELOAD=false ./scripts/api_dev.sh` flow. `dev_up.sh` validates `.env`, derives compose Postgres credentials from the active env, and then runs migrations.

See the full local setup walkthrough in [docs/quickstart/local-setup-and-first-result.md](docs/quickstart/local-setup-and-first-result.md).

## MCP surface

Alice exposes a narrow MCP surface for continuity workflows:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

This makes it straightforward to plug Alice into MCP-capable assistants and development environments without changing the underlying continuity model.

See:

- [docs/integrations/hermes-bridge-operator-guide.md](docs/integrations/hermes-bridge-operator-guide.md)
- [docs/integrations/hermes-provider-plus-mcp-why.md](docs/integrations/hermes-provider-plus-mcp-why.md)
- [docs/integrations/mcp.md](docs/integrations/mcp.md)
- [docs/integrations/hermes.md](docs/integrations/hermes.md)
- [docs/integrations/hermes-memory-provider.md](docs/integrations/hermes-memory-provider.md)
- [docs/integrations/hermes-skill-pack.md](docs/integrations/hermes-skill-pack.md)
- [docs/integrations/phase11-local-provider-adapters.md](docs/integrations/phase11-local-provider-adapters.md)
- [docs/integrations/phase11-azure-autogen.md](docs/integrations/phase11-azure-autogen.md)

Recommended Hermes architecture is provider plus MCP, with MCP-only as a fallback.

One-command Hermes bridge demo:

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

Hermes runtime smoke tests:

```bash
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
```

If you use Hermes, run provider plus MCP as the recommended mode, add the skill pack for policy guidance, and keep MCP-only available as fallback.

## OpenClaw and imported workflows

Alice includes importer paths for existing memory and conversation data so you can upgrade an existing workflow instead of starting from zero.

With the current integration surface, you can:

- import OpenClaw memory into Alice
- normalize imported data into Alice continuity objects
- run recall and resumption against imported work
- add Alice MCP workflows on top of an existing setup

OpenClaw demo:

```bash
./scripts/use_alice_with_openclaw.sh
```

See:

- [docs/integrations/importers.md](docs/integrations/importers.md)
- [docs/integrations/openclaw.md](docs/integrations/openclaw.md)

## Why not just use ChatGPT memory?

ChatGPT memory is convenient.
Alice is structured, explainable, correctable, and portable across agent stacks, with explicit provenance, trust, resumption, and open-loop workflows.

## Example outcomes

### Founder and operator continuity

- keep strategic decisions from disappearing into old chats
- resume fundraising, hiring, or product threads quickly
- stay on top of commitments and follow-ups

### Consulting and client work

- preserve client-specific decisions and context
- restart project work without reconstructing the last week
- maintain open loops without building a manual CRM ritual

### Agent memory upgrades

- add durable continuity to an existing agent stack
- improve recall and resumption without rebuilding your runtime
- keep correction and provenance explicit

## Architecture at a glance

Alice is built around a shared continuity core with:

- structured memory revisions
- provenance- and trust-aware recall
- shared explanation chains across recall-derived workflows
- deterministic archive maintenance with ops-visible health summaries
- deterministic resumption briefs
- open-loop objects
- CLI and MCP surfaces on the same semantics

That means the system behaves consistently across local workflows, MCP-connected agents, and imported data sources.

## Scope Notes

Included in the `v0.5.1` release:

- local-first continuity core
- CLI and MCP surfaces
- importer paths (OpenClaw, Markdown, ChatGPT exports)
- provider runtime and model-pack support from Phase 11
- Hermes provider-plus-MCP bridge path with MCP-only fallback
- Phase 12 retrieval, mutation, contradiction/trust, public eval, and task-adaptive briefing surfaces
- Phase 13 one-call continuity, Alice Lite, and hygiene/thread-health visibility surfaces
- Phase 14 provider/runtime portability, first-party model packs, reference integrations, and design-partner launch/admin surfaces
- `HF-001` logging safety and disk-guardrail defaults

Deferred beyond `v0.5.1`:

- `v1.0.0` compatibility/support guarantees
- managed cloud/SLA commitments
- new integrations/channels beyond already shipped baseline

## Docs

- [vNext Preview](docs/vnext/README.md)
- [Public Alpha](docs/alpha/README.md)
- [Public Alpha Quickstart](docs/alpha/quickstart.md)
- [Public Alpha Agent Integration](docs/alpha/agent-integration.md)
- [Headless Ubuntu Install](docs/alpha/headless-ubuntu-install.md)
- [Hermes Dogfood On Ubuntu](docs/alpha/hermes-dogfood-ubuntu.md)
- [Public Alpha Known Limitations](docs/alpha/known-limitations.md)
- [vNext Quickstart](docs/vnext/quickstart.md)
- [vNext Architecture](docs/vnext/architecture.md)
- [vNext Local Runtime](docs/vnext/local-runtime.md)
- [vNext Security and Privacy](docs/vnext/security-privacy.md)
- [Agentic Control Plane CTO Summary](docs/vnext-agentic-control-plane-cto-summary.md)
- [Local Runtime CTO Summary](docs/vnext-local-runtime-cto-summary.md)
- [Model-Backed Intelligence CTO Summary](docs/vnext-model-backed-intelligence-cto-summary.md)
- [Live-Backed Operator Console CTO Summary](docs/vnext-live-backed-operator-console-cto-summary.md)
- [Quickstart](docs/quickstart/local-setup-and-first-result.md)
- [Architecture](ARCHITECTURE.md)
- [MCP](docs/integrations/mcp.md)
- [Hermes Guide](docs/integrations/hermes.md)
- [Hermes Memory Provider](docs/integrations/hermes-memory-provider.md)
- [Hermes Skill Pack](docs/integrations/hermes-skill-pack.md)
- [Importers](docs/integrations/importers.md)
- [OpenClaw Guide](docs/integrations/openclaw.md)
- [Examples](docs/examples/phase9-command-walkthrough.md)

## Contributing

Issues, adapters, importers, eval contributions, and integration examples are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

If you discover a security issue, follow the process in [SECURITY.md](SECURITY.md).

## License

See [LICENSE](LICENSE).
