# Alice vNext Public Preview

Alice vNext is the next public wedge for Alice as an agent-native second brain: a local-first memory kernel, reviewable generated briefs, model-backed source-grounded synthesis, live local connector-backed evidence capture, hardened connector settings/state/secrets, agent-facing context packs, governed agent proposals, and a local scheduler runtime.

This preview is not a hosted launch. It is a repo-local, deterministic public preview built around the vNext memory-kernel schema and the fixture-safe workflows shipped under `v0.5.1-vnext-preview`.

## Product Shape

Alice vNext has three layers:

- **Alice Core**: the local-first persistence, provenance, policy, and event-log substrate. Core owns sources, chunks, memories, revisions, graph edges, projects, open loops, artifacts, evals, and connector evidence.
- **Alice Brain**: the user-facing second-brain workflows on top of Core. Brain generates daily briefs, weekly syntheses, context packs, contradiction reports, connection reports, project updates, open-loop reviews, and reviewable artifacts in deterministic or model-backed mode.
- **Alice Agent Memory**: the agent integration layer. Agent Memory exposes continuity through CLI, API, and MCP so external agents can capture, retrieve, resume, explain, generate context, propose memory, and trigger governed scheduler workflows without owning the memory database.

## Preview Surfaces

- Source capture: manual text, local text/Markdown files, Markdown folders, ChatGPT exports.
- Retrieval: deterministic context packs with domain/sensitivity filters and provenance.
- Brain workflows: daily brief, weekly synthesis, connection report, contradiction report, project update, open-loop review.
- Model-backed intelligence: provider/routing abstraction, local-first model policy, source-grounded sections, prompt hashes, context hashes, model metadata, and deterministic-vs-model comparison mode.
- Quality review: artifact ratings for usefulness, accuracy, source grounding, novel connections, actionability, hallucination risk, verbosity, missed context, and comments.
- Agentic control plane: scoped agent identities, permission profiles, policy decisions, memory proposals, and Agent Activity audit surface.
- Governed scheduler: disabled-by-default workflow controls, a local daemon runner, due scans, run history, trace IDs, failures, duplicate-run locks, and reviewable artifacts.
- Connectors: allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clipper capture endpoint, Hermes/OpenClaw-style agent output ingestion, dedicated settings/state rows, local encrypted secret references, retry/cursor hardening, plus deterministic PDF, DOCX, CSV, screenshot OCR, and voice transcript payload ingestion.
- UI: live/fixture-backed `/vnext` workspace for review, Ask Alice, briefs, queue, projects, Agent Activity, Schedules, beliefs, graph, live connector configuration, connector health/defaults/bookmarklet guidance, dogfooding readiness telemetry, privacy settings, model comparison, and quality ratings.
- Evals: synthetic corpus and baseline metrics for recall, temporal reasoning, contradictions, provenance, privacy, open loops, and prompt injection.

## Start Here

1. Follow [vNext quickstart](quickstart.md).
2. Review [architecture](architecture.md).
3. Review [security and privacy](security-privacy.md).
4. Review [local runtime](local-runtime.md) before running scheduler workflows in the background.
5. Use [example ALICE.md](ALICE.example.md) as the first Brain Charter.
6. Use [demo script](demo-video-script.md) for a short walkthrough.
7. Use [release checklist](../release/vnext-public-release-checklist.md) before publishing or tagging.
8. Review [preview release notes](../release/v0.5.1-vnext-preview-release-notes.md) and [tag plan](../release/v0.5.1-vnext-preview-tag-plan.md).
9. Review the [dogfood daily checklist](../runbooks/vnext-dogfood-daily-checklist.md) before daily local-alpha use.
10. Review the [agentic control plane CTO summary](../vnext-agentic-control-plane-cto-summary.md), [local runtime CTO summary](../vnext-local-runtime-cto-summary.md), [model-backed intelligence CTO summary](../vnext-model-backed-intelligence-cto-summary.md), [live capture connectors CTO summary](../vnext-live-capture-connectors-cto-summary.md), and [dogfood hardening CTO summary](../vnext-dogfood-hardening-cto-summary.md) for sprint closeouts.

## Launch Boundary

The public preview should prove that a technical user can install Alice locally, capture live local evidence, configure local connector defaults safely, run readiness checks, and generate a first daily brief in under 20 minutes. It should not claim managed connector OAuth, packaged browser extensions, hosted connector polling, cloud sync, hosted SLA, or automatic promotion of generated artifacts into trusted memory.
