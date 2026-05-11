# BUILD_REPORT

## sprint objective

Harden the Alice vNext local dogfooding loop so existing live capture connectors are reliable, secure, configurable, observable, and operable without developer babysitting.

## completed work

- added dedicated `connector_settings` and `connector_state` tables with RLS, constraints, default-row seeding, and store methods
- moved connector settings/state reads and writes onto dedicated storage while retaining event-log audit entries
- added vNext secret-provider abstraction with environment references, encrypted local fallback storage, in-memory tests, and redaction helpers
- hardened Telegram sync with secret references, retries, allowlist rejection logging, and safe cursor advancement
- hardened local folder scans with generated/dependency folder ignores and restart dedupe
- hardened browser clipper with optional local capture-token enforcement and token redaction before persistence
- added `alicebot vnext migrations status`, `alicebot vnext doctor --fix-safe`, and dogfood hardening smokes
- expanded dogfooding telemetry with readiness, trends, review rate, scheduler freshness, agent activity, policy blocks, and top failure causes
- added live `/vnext` connector configuration for Telegram, local folder, and browser clipper defaults, sync actions, status, counters, failures, and secret presence
- updated README, vNext docs, CLI docs, release notes, release checklist, CTO summary, and dogfood daily checklist

## incomplete work

- managed OAuth, hosted connector polling, packaged browser extension distribution, hosted SLA, automatic memory promotion, production scheduling, and broader live-backed `/vnext` workflows remain intentionally deferred
- production deployments should wire the new secret-provider interface to OS keychain or managed secret infrastructure instead of relying on the local encrypted-file alpha fallback

## files changed

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `CHANGELOG.md`
- `CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `REVIEW_REPORT.md`
- `ROADMAP.md`
- `apps/api/alembic/versions/20260511_0070_vnext_connector_settings_state.py`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/vnext_connectors.py`
- `apps/api/src/alicebot_api/vnext_doctor.py`
- `apps/api/src/alicebot_api/vnext_dogfooding.py`
- `apps/api/src/alicebot_api/vnext_secrets.py`
- `apps/api/src/alicebot_api/vnext_store.py`
- `apps/web/components/vnext-brain-workspace.tsx`
- `apps/web/lib/api.ts`
- `docs/dogfoodhardening.md`
- `docs/integrations/cli.md`
- `docs/release/v0.5.1-vnext-preview-release-notes.md`
- `docs/release/vnext-public-release-checklist.md`
- `docs/runbooks/vnext-dogfood-daily-checklist.md`
- `docs/vnext-dogfood-hardening-cto-summary.md`
- `docs/vnext/README.md`
- `docs/vnext/architecture.md`
- `docs/vnext/local-runtime.md`
- `docs/vnext/quickstart.md`
- `docs/vnext/security-privacy.md`
- `tests/unit/test_20260511_0070_vnext_connector_settings_state.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_vnext_connectors.py`
- `tests/unit/test_vnext_doctor.py`
- `tests/unit/test_vnext_secrets.py`
- `tests/unit/test_vnext_store.py`

## tests run

- `./.venv/bin/python -m pytest tests/unit -q`: `1125 passed`
- `./.venv/bin/python -m pytest tests/integration -q`: `370 passed`
- `pnpm --dir apps/web test`: `207 passed`
- `pnpm --dir apps/web lint`: passed
- `pnpm --dir apps/web build`: passed and built `/vnext`
- `./.venv/bin/python scripts/check_control_doc_truth.py`: passed
- `alicebot vnext migrations status`: passed
- `alicebot vnext smoke connector-hardening`: passed
- `alicebot vnext smoke secret-redaction`: passed
- `alicebot vnext smoke dogfood-doctor`: passed with zero blocking failures and zero warnings
- `alicebot vnext smoke live-capture-connectors`: passed
- `alicebot vnext smoke capture-to-brief`: passed
- `alicebot vnext smoke agentic-scheduler`: passed
- `alicebot eval run --suite all`: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes
- `git diff --check`: clean

## blockers/issues

- no known dogfood hardening blocker remains

## recommended next step

Squash-merge the dogfood hardening PR after final verification, then choose the next product slice: broader live-backed `/vnext` workflows, managed connector OAuth, production scheduling, or model-backed/live-store evals.
