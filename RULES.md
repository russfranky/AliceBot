# Rules

## State Discipline
- Treat Phases 9-13 and Bridge `B1` through `B4` as shipped baseline truth.
- Treat Phases 14 and `HF-001` as shipped baseline truth.
- Treat `v0.5.1` as released baseline truth.
- Keep shipped baseline, active phase scope, and later roadmap scope separate.
- Keep [CURRENT_STATE.md](CURRENT_STATE.md) factual/current and [ROADMAP.md](ROADMAP.md) future-facing.
- Keep [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md) as the canonical handoff copy when duplicate current-state files exist.

## Phase 14 Baseline Rule
- Phase 14 was a platform-and-adoption phase. Preserve that shipped boundary as baseline truth: provider adapters, model packs, reference integrations, and design partner onboarding are complete baseline surfaces, not open scope.

## Active vNext Preview Rule
- While `v0.5.1-vnext-preview` is the active release gate, prioritize release accuracy, install clarity, preview-safe docs, and verification evidence. Do not add net-new feature scope unless it is required to fix preview readiness, release evidence, or operator safety.

## Provider Rules
- Continuity semantics must not fork by provider.
- A provider may change capability support, latency, token budgets, and model-specific quirks.
- A provider must not change the continuity object model, contradiction handling, provenance contracts, trust semantics, or one-call continuity behavior.
- Provider capability discovery and invocation telemetry should be first-class, persisted, and inspectable.
- Do not reopen provider-foundation work redundantly after `P14-S1`; follow-on provider sprints must be about contract alignment, compatibility proof, or a newly declared provider class.

## Model Pack Rules
- Model packs are declarative, versioned profiles, not forks.
- Packs may shape prompt/context behavior, tool strategy, briefing strategy, and runtime defaults.
- Packs must not invent a second continuity model or bypass trust/provenance rules.
- Ship only first-party packs for major families first; everything else waits.

## Integration Rules
- For Hermes, use provider hooks for automation and MCP for explicit deep actions.
- Keep MCP fallback viable even when provider or bridge integrations are the recommended mode.
- Reference integrations must be runnable and documented, not aspirational.
- Generic Python and TypeScript integration examples are in-scope platform proof, not optional extras.

## Design Partner Rules
- Design partners are tracked product proof, not ad hoc support conversations.
- Capture onboarding, pilot status, usage summaries, and structured feedback explicitly.
- Choose small, opinionated pilot scopes over broad custom engagements.

## Docs And Operations Rules
- Docs are sprint deliverables, not cleanup work.
- Provider docs, model-pack docs, integration docs, and onboarding docs must stay aligned to shipped behavior.
- Keep `.ai/active/SPRINT_PACKET.md` as the only canonical active sprint packet unless a duplicate artifact is explicitly required.
- Runnable docs/examples and demo helpers should use a shared canonical fixture or the real contract surface, not an ad hoc inline mock payload.
- Acceptance dashboards must derive readiness from persisted evidence that matches the acceptance criteria, not from proxy signals such as linkage alone.
- Canonical launch-set and rollout docs may use anonymized partner identifiers, but placeholders/examples must be labeled as such and must not be used as sprint-completion evidence.
- Keep credentials, tokens, and secret references out of logs, docs, and outward-facing errors.
- Any new workspace-scoped hosted table must ship with row-level security enablement, workspace access policies, and a regression test for that access posture.
- Keep local filesystem paths, workstation usernames, and machine-specific identifiers out of committed docs and reports.
- Keep consequential side effects approval-bounded.
- Commit public evidence only from exact commands and stable fixtures, never from inferred pass states.

## Scope Rules
- Do not widen Phase 14 into retrieval research, graph migration, new channels, marketplace work, enterprise governance expansion, major vertical-agent work, or deep browser/action automation unless explicitly re-scoped.
- Post-phase hotfix sprints must remain defect-only: no new product surface, no unrelated refactors, and no disguised feature expansion.
- Do not silently hardcode unresolved Control Tower decisions as permanent runtime behavior without recording the decision.
- Surface underspecified decisions as Control Tower decisions instead of inventing scope.
