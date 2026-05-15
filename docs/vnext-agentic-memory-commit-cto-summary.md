# Alice vNext Agentic Memory Commit CTO Summary

## Phase Scope

This phase adds a governed path for trusted local agents to write explicit memory instructions through Alice without bypassing policy, provenance, audit, or user repair controls. The feature is designed for Hermes, OpenClaw, and custom MCP/API/CLI agents that hear direct user instructions such as "remember this", "save this", or "add this to memory".

## What We Built

- A shared agentic memory commit service with four write outcomes: `committed`, `confirmation_required`, `review_required`, and `rejected`.
- A policy engine that evaluates agent identity, permission profile, domain, sensitivity, source type, confidence, contradiction refs, project scope, and unsafe secret markers before any write.
- Direct auto-commit only for explicit, high-confidence, direct-source writes from trusted local agents or in-scope project agents.
- Inline confirmation for sensitive domains, restricted sensitivity, contradictions, and medium-confidence writes.
- Dashboard review for external sources, generated/bulk inputs, memory-proposal agents, and low-confidence facts.
- Rejection for read-only agents, out-of-scope project agents, unsafe secret storage, missing explicit intent, and policy-blocked writes.

## Operator Surfaces

- API:
  - `POST /v0/vnext/memories/commit`
  - `POST /v0/vnext/memories/confirm`
  - `POST /v0/vnext/memories/undo`
  - `POST /v0/vnext/memories/correct`
  - `POST /v0/vnext/memories/forget`
  - `GET /v0/vnext/memories/recent-commits`
  - `GET /v0/vnext/memories/{memory_id}/audit`
- MCP:
  - `alice_vnext_commit_memory`
  - `alice_vnext_confirm_memory`
  - `alice_vnext_undo_memory`
  - `alice_vnext_correct_memory`
  - `alice_vnext_forget_memory`
  - `alice_vnext_recent_memory_commits`
  - `alice_vnext_memory_audit`
- CLI:
  - `alicebot vnext memories commit`
  - `alicebot vnext memories confirm`
  - `alicebot vnext memories undo`
  - `alicebot vnext memories correct`
  - `alicebot vnext memories forget`
  - `alicebot vnext memories recent`
  - `alicebot vnext memories audit`

## Memory Lifecycle

- Inline confirmations are persisted as reviewable memory rows with confirmation id, proposed text, domain, sensitivity, policy reason, agent id, creation time, expiry time, and pending/confirmed/rejected/expired status in metadata.
- Undo and forget mark memories as superseded while preserving event and revision history.
- Correct updates the canonical text, appends a correction revision, and keeps the memory active.
- Retrieval now only selects active or accepted vNext memories, so candidate, superseded, forgotten, undone, or review-gated rows do not enter context packs.

## `/vnext` Visibility

The live workspace payload and UI now expose recent trusted memory commits and inline confirmations in Agent Activity. Operators can distinguish auto-committed, inline-confirmed, pending confirmation, corrected, undone, and forgotten memory lifecycle states without mixing them into ordinary pending proposals.

## Agent Pack Updates

Hermes, OpenClaw, custom-agent, MCP, and integration docs now tell agents to use Alice's official commit/confirm/undo/correct/forget tools and never write directly to Postgres. OpenClaw is limited to explicit `project` domain commits inside its project scope; non-project or sensitive personal writes are blocked or review-gated.

## Validation Added

- Unit coverage for the policy matrix: trusted commit, sensitive confirmation, external review, read-only rejection, project-scoped allow/reject, and contradiction confirmation.
- Store coverage that context-pack memory search excludes non-active/non-accepted rows.
- MCP coverage for new tool registration, commit, recent commits, audit, and inline confirmation.
- CLI parser coverage for all new memory commands and the new smoke.
- Postgres-backed API integration coverage for commit, correction, context inclusion, undo, context exclusion, audit, sensitive confirmation, external review, and read-only rejection.
- New smoke: `alicebot vnext smoke agentic-memory-commit`.

## Success Criteria

- Trusted local agents can immediately commit explicit user memory instructions.
- Sensitive or ambiguous facts still require user confirmation.
- External/generated facts stay in dashboard review.
- Read-only and out-of-scope agents cannot write.
- Undo/forget/correct are durable, auditable, and respected by retrieval.
- `/vnext`, API, MCP, and CLI all expose the same lifecycle rather than separate code paths.

## Known Limits

- This is local vNext only; it does not add hosted team permissions, cloud sync, billing, Gmail/Calendar OAuth, voice, or OCR expansion.
- The CTO summary document cannot include the final PR number and squash merge SHA until the GitHub PR is opened and merged; those are reported in the release handoff after merge.
