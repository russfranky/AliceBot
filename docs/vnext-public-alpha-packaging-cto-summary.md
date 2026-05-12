# Alice vNext Public Alpha Packaging: CTO Summary

Date: 2026-05-12
Audience: CTO / technical leadership
Sprint artifact: `codex/public-alpha-packaging`

## Executive Summary

This phase packages Alice vNext for a small technical public alpha. It does not add major product features. It turns the current local dogfood system into an installable, understandable, demoable, and agent-connectable package for design partners.

The product position is explicit: Alice is local-first memory and continuity infrastructure for humans and agents. `/vnext` is the operator console for review, audit, configuration, doctor checks, and troubleshooting.

## What Was Packaged

- project-native `make setup`, `make dev`, `make doctor`, `make vnext`, `make scheduler`, and `make alpha-check` commands
- public alpha docs under `docs/alpha/`
- first-run checklist and doctor-first onboarding
- safe synthetic demo dataset load/reset commands
- `alicebot vnext alpha check`
- `alicebot vnext smoke agent-integration-pack`
- Hermes and OpenClaw copy-paste skill packs
- custom agent integration guide
- MCP tool quickstart with end-to-end agent examples
- context-pack, memory-proposal, and agent-output recipes
- design partner onboarding, troubleshooting, known limitations, and security/privacy docs

## First-run Flow

The intended alpha path is:

```bash
make setup
make migrate
make doctor
make dev
alicebot vnext demo load --reset
alicebot vnext alpha check
```

Then the user opens `/vnext`, reviews sources and memory proposals, generates or reviews artifacts, inspects traceability, and connects an agent through MCP/API/CLI.

## Agent Integration Pack

The agent integration pack standardizes the pattern for Hermes, OpenClaw, and custom agents:

1. identify the agent
2. request scoped context packs
3. submit important outputs back to Alice
4. propose memory for review
5. create open loops when work remains
6. respect domain/sensitivity policy
7. use `/vnext` for review and audit

The new smoke verifies OpenClaw identity, project-scoped context, output ingestion, review-only memory proposal creation, no auto-promotion, event logging, restricted-domain policy blocking, and agent activity visibility.

## Guardrails Preserved

- no auto-promotion into trusted memory
- agent outputs are untrusted source evidence
- generated artifacts stay reviewable
- policy blocks and filters are event logged
- secrets are referenced/redacted
- alpha docs do not claim hosted cloud, production SLA, or automatic memory autopilot

## Validation Evidence

Current local validation for this package:

- `pytest tests/unit -q`: 1127 passed
- `pytest tests/integration -q`: 370 passed
- `pnpm --dir apps/web test`: 63 files passed, 209 tests passed
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed
- `alicebot eval run --suite all`: 170/170 passed, 0 critical privacy leaks, 0 prompt-injection tool writes
- `alicebot vnext alpha check`: passed, including existing vNext smokes and `agent-integration-pack`
- `alicebot vnext demo load --reset`: passed
- `alicebot vnext demo reset`: passed
- `python scripts/check_control_doc_truth.py`: passed
- `git diff --check`: passed

## Recommended Next Phase

Default recommendation: Agent Skills v1 Hardening. The first alpha users will judge Alice by how well Hermes, OpenClaw, and custom agents can use scoped context, submit outputs, and create high-quality review-only memory proposals.
