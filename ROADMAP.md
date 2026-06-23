# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
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
- Alice vNext Sprint 1 through Sprint 12 preview scope is implemented.
- Alice vNext live capture connectors are implemented for allowlisted Telegram, local folder/Obsidian notes, browser clips, and agent outputs.
- Alice vNext dogfood hardening is implemented for dedicated connector settings/state, local secret references, readiness doctor checks, live `/vnext` connector configuration, and daily-use runbooks.
- Alice vNext public preview release gate is active for `v0.5.1-vnext-preview`.

## SpacetimeDB Port (Active, Additive)
- An additive port of Alice onto a hosted SpacetimeDB module (maincloud) is in progress alongside
  the Postgres baseline; Postgres remains the system of record.
- Live and verified on maincloud: the continuity core (capture/commit/correct, recall, idempotency,
  per-caller isolation) and the execution pillar (the task worker collapsed into a scheduled
  procedure — approval-gated, tools registry/allowlist with per-run endpoints, idempotent
  `tool_executions`, retry/backoff, stuck-run recovery).
- Next: execution budgets, task lineage/artifacts, secrets for authed tools; Track B re-point of the
  CLI/MCP/API surfaces and Track C Postgres→SpacetimeDB data migration. See `docs/adr/spacetimedb-*.md`.

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

## Active Release Gate

### Alice vNext Public Preview: `v0.5.1-vnext-preview`
- publish the completed Sprint 1-12 plus live capture connector vNext preview as a pre-release without replacing stable `v0.5.1`
- preserve `v0.5.1`/Phase 14 behavior while documenting the vNext preview boundary
- include current release evidence for Postgres-backed CLI/API/MCP smoke, live-capture smoke, capture-to-brief smoke, full unit tests, integration tests, web tests/lint/build, control-doc truth, evals, and security scans
- keep explicit preview limitations: no hosted SLA, no managed connector OAuth, no hosted connector polling, no automatic artifact promotion, no production scheduler, no broad live-write `/vnext` expansion
- include dogfood hardening evidence for connector settings/state persistence, secret redaction, doctor checks, live connector configuration, and repeatable smoke validation

## Next Roadmap Gate
- After the vNext dogfood hardening merge, choose the next product slice: broader live-backed `/vnext` review/workflow UI, managed connector OAuth, production scheduling, or model-backed/live-store evals.
- Preserve the shipped Phase 14 platform plus the `HF-001` logging guardrails as baseline behavior.

## Beyond Phase 14
- Alice vNext follows `docs/alice_vnext_true_second_brain_tech_spec.md`.
- The immediate feature sequence starts with the vNext memory kernel before production queue automation, graph/contradiction intelligence, connectors, and UI expansion.
