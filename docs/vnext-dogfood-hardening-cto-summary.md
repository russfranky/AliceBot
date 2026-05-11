# Alice vNext Dogfood Hardening: CTO Summary

Date: 2026-05-11
Audience: CTO / technical leadership
Sprint artifact: `codex/dogfood-hardening`
Baseline preserved: `v0.5.1` stable public release, `v0.5.1-vnext-preview` public-preview boundary

## Executive Summary

This phase hardened the Alice vNext local dogfooding loop so the system can be used daily without developer babysitting. The work did not expand into new external connectors. It made the existing live capture stack reliable, configurable, secure, observable, and easier to operate.

The core loop now has production-shaped local-alpha support:

```text
capture -> source archive -> candidate memory -> context pack -> scheduled/model-backed artifact -> review/rating -> dogfooding telemetry
```

The product rule remains unchanged: connector content and generated artifacts are review-only until a human explicitly promotes or accepts them.

## What We Built

### 1. Dedicated Connector Settings Storage

We moved connector configuration out of ad hoc event-log-only storage into a real `connector_settings` table. It stores connector name, enabled/configured state, default domain/sensitivity, sync mode, polling interval, validation errors, timestamps, and metadata. Settings changes still create event-log audit records.

This covers Telegram, local folder, browser clipper, and agent output as the core live dogfood connectors, while the UI also shows the broader supported document and media connector defaults.

### 2. Dedicated Connector State And Cursor Storage

We added a `connector_state` table for cursor/checkpoint persistence, sync timestamps, failure timestamps, errors, counters, dedupe counts, and state metadata.

This means Telegram offsets, local folder scan posture, browser clipper recent capture state, and agent output counters survive process restarts and no longer depend on replaying event logs as the primary state source.

### 3. Local Secret Provider Abstraction

We added a vNext secret-provider layer with:

- environment secret references such as `env:TELEGRAM_BOT_TOKEN`
- encrypted local file fallback for alpha use
- in-memory test provider
- redaction helpers for secret-like fields before persistence

Telegram and browser clipper now use `secret_ref` values instead of returning or persisting raw token values. CLI/API/UI/health/event/source paths expose configured/not-configured posture, not secret content.

### 4. Connector Reliability Hardening

We improved the connector service so it can:

- preserve explicit settings across restart
- persist state and counters separately from events
- retry Telegram fetches with bounded backoff
- avoid advancing cursors past failed items
- safely advance past explicitly rejected non-allowlisted Telegram chats
- count duplicates separately from failures
- ignore generated/dependency folders during local folder scans
- preserve raw evidence while redacting secret fields
- enforce browser clipper capture tokens when configured

### 5. Migration And Doctor Readiness Checks

We added:

- `alicebot vnext migrations status`
- `alicebot vnext doctor --fix-safe`
- `alicebot vnext smoke connector-hardening`
- `alicebot vnext smoke secret-redaction`
- `alicebot vnext smoke dogfood-doctor`

The doctor checks required vNext tables, default connector settings/state rows, Telegram secret references, scheduler daemon posture, connector failures, and recommended fixes. The safe fix path can initialize missing default connector rows.

### 6. Live `/vnext` Connector Configuration

The `/vnext` workspace now exposes live connector configuration controls for the current dogfood loop:

- connector enablement
- default domain and sensitivity
- Telegram allowed chat IDs
- Telegram/browser secret references
- local folder paths/extensions/ignore patterns
- manual sync triggers
- browser test clip capture
- health counters, cursor state, failures, secret presence, and sync mode

Fixture mode still works for demos, but live mode can now update real connector settings.

### 7. Browser Clipper Packaging Improvement

The bookmarklet flow now prompts for the local endpoint, user ID, optional token, and note, then captures URL/title/selection/page text into the local API. The payload path supports capture-token enforcement and redacts the token before source/event persistence.

### 8. Dogfooding Telemetry Upgrade

The dogfooding dashboard now includes:

- capture trends by day and week
- candidate memory review rate
- artifact rating trend
- top failure causes
- scheduler freshness
- agent activity summary
- policy block/filter summary
- readiness status and reasons

This turns dogfood health from a raw counter view into an operator signal.

### 9. Documentation And Runbooks

We added the dogfood daily checklist and updated vNext docs, quickstart, local runtime, security/privacy, CLI integration, release notes, release checklist, README, and control reports to reflect the hardened connector settings/state/secret posture.

## Validation Evidence

Current local validation from this phase:

- `./.venv/bin/python -m pytest tests/unit -q`: `1125 passed`
- `./.venv/bin/python -m pytest tests/integration -q`: `370 passed`
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed and built `/vnext`
- `alicebot vnext migrations status`: passed
- `alicebot vnext smoke connector-hardening`: passed
- `alicebot vnext smoke secret-redaction`: passed
- `alicebot vnext smoke dogfood-doctor`: passed with zero blocking failures and zero warnings
- `alicebot vnext smoke live-capture-connectors`: passed
- `alicebot vnext smoke capture-to-brief`: passed
- `alicebot vnext smoke agentic-scheduler`: passed
- `alicebot eval run --suite all`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes

## Technical Leadership Takeaways

- The current connector layer is now production-shaped for local alpha dogfooding.
- Secret handling is materially safer: connector tokens are references, not normal config values.
- Cursor and health posture now survive restart without event-log replay being the primary state mechanism.
- The UI is no longer only showing connector posture; it can configure the core live dogfood connectors.
- The doctor and smoke commands give operators a repeatable go/no-go check before relying on daily capture.

## Remaining Intentional Boundaries

- No managed OAuth yet.
- No hosted connector polling yet.
- No packaged browser extension yet.
- No production hosted scheduler/SLA yet.
- No automatic promotion of connector captures or generated artifacts into trusted memory.
- The encrypted local secret file is an alpha fallback; production deployments should use the same interface with OS keychain or managed secret infrastructure.

## Recommended Next Phase

The next highest-leverage product slice is broader live-backed `/vnext` operation: connect more of the current review, artifact, project, open-loop, and settings flows to real API writes so the local dogfood workspace becomes the primary daily operator console.
