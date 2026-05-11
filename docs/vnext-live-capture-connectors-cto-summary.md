# Alice vNext Live Capture Connectors CTO Summary

Date: 2026-05-11

## Executive Summary

This phase moved Alice vNext from a mostly deterministic preview into a dogfoodable live local capture loop. Alice can now ingest real operator-controlled evidence from Telegram, local folders/Obsidian notes, browser clips, and external agent outputs, then carry that evidence through source archive, candidate memory review, context packs, Daily Brief generation, artifact quality feedback, and dogfooding telemetry.

The trust model did not change: connector content is untrusted source material, raw evidence is preserved, domain/sensitivity defaults remain explicit, generated artifacts and agent proposals stay review-only, and no connector path auto-promotes trusted memory.

## What We Built

- Live Telegram capture: configurable token reference, allowlisted chat IDs, `getUpdates` sync, rejected-chat isolation, cursor tracking, failure logging, and CLI/API status surfaces.
- Local folder and Obsidian capture: add/remove path configuration, Markdown/text sync, polling watch mode, generated/export folder ignores, mtime/path cursor semantics, and content-hash dedupe.
- Browser clipper MVP: local API endpoint for page URL/title/selection/page text/user note, CLI capture command, UI bookmarklet guidance, raw clip preservation, and professional/private defaults.
- Agent output ingestion: CLI/API/MCP path for Hermes/OpenClaw-style outputs, policy-checked agent identity, source archive, review-only generated artifact, optional candidate memory proposal, provenance links, and event-log audit.
- Dogfooding dashboard: capture counts by connector, today/week capture metrics, candidate memory counts, artifact quality averages, useful-insight feedback, open-loop/connection/contradiction counters, connector failures, and connector health.
- Capture-to-brief validation: smoke command proving a browser clip enters retrieval, appears in a context pack, generates a reviewable Daily Brief, records a quality rating, and surfaces in dogfooding telemetry.
- UI coverage: `/vnext` now exposes connector health/defaults/cursors/failures, dogfooding capture health, and browser clipper endpoint/bookmarklet guidance.

## Interfaces Added

- CLI:
  - `alicebot vnext connectors telegram configure/test/sync/status`
  - `alicebot vnext connectors local-folder add-path/remove-path/sync/watch/status`
  - `alicebot vnext connectors browser-clipper capture/status`
  - `alicebot vnext connectors status/health`
  - `alicebot vnext agents ingest-output`
  - `alicebot vnext dogfooding dashboard`
  - `alicebot vnext quality insight`
  - `alicebot vnext smoke live-capture-connectors`
  - `alicebot vnext smoke capture-to-brief`
- API:
  - connector config/status/health endpoints
  - Telegram sync endpoint
  - local folder sync endpoint
  - browser clipper capture endpoint
  - agent output ingestion endpoint
  - dogfooding dashboard endpoint
  - artifact insight feedback endpoint
- MCP:
  - `alice_vnext_ingest_agent_output`

## Validation Evidence

- Unit suite: `1108 passed`
- Targeted connector/API/MCP tests passed
- Web API and vNext page tests passed after contract updates
- Live connector smoke passed against Postgres
- Capture-to-brief smoke passed after applying the existing artifact-quality migration
- The local database needed migration `20260511_0069_model_backed_intelligence_quality` before capture-to-brief could record artifact quality ratings

## Remaining Product Decisions

- Move connector config, secrets, and cursors from event-log-backed config into a dedicated settings table and encrypted local secret store when hardening for non-developer use.
- Decide packaging for browser clipper beyond bookmarklet/local endpoint.
- Decide whether Telegram should stay polling-only locally or gain webhook setup automation.
- Add managed OAuth and hosted connector polling only when the hosted product boundary is ready.
- Decide how much of `/vnext` should become live-write UI for connector configuration versus CLI-first operator controls.
