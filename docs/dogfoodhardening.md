
Alice vNext Sprint Prompt: Dogfood Hardening + Connector Settings/Secrets

Sprint Objective

Alice vNext now has the full local dogfooding loop:

capture → source archive → candidate memory → context pack → scheduled/model-backed artifact → review/rating → dogfooding telemetry

This sprint should harden the current dogfood loop so Alice can be used daily without developer babysitting.

The goal is not to add many new connectors. The goal is to make the existing live capture stack reliable, secure, configurable, observable, and easier to operate.

Focus on:

1. Dedicated connector settings/state tables
2. Encrypted local secret storage
3. Reliable connector cursor/checkpoint persistence
4. Migration/install/runtime health checks
5. Live /vnext connector configuration UI
6. Browser clipper packaging improvement
7. Telegram reliability improvements
8. Capture reliability and feedback-loop prevention
9. Dogfooding runbook and daily-use checklist

Alice should remain local-first, agentic-first, review-first, and no-auto-promotion.

⸻

Product Principle

Alice is not ready for Gmail/Calendar/OAuth expansion until the existing capture loop is boringly reliable.

This sprint should make the current connector layer production-shaped for local alpha usage.

The user should be able to:

configure Telegram safely
configure watched local folders safely
use browser clipping without friction
see connector health in /vnext
understand sync failures
avoid duplicate capture spam
avoid Alice re-ingesting its own generated artifacts
run migrations/health checks confidently
recover from connector errors

No connector content may become trusted memory without review.

⸻

Current State Assumption

Alice already has:

live Telegram capture
local folder / Obsidian capture
browser clipper MVP
agent output ingestion
dogfooding dashboard
capture health telemetry
scheduler daemon
model-backed Brain workflows
agentic control plane
quality ratings
policy routing
privacy/prompt-injection evals

The known hardening gaps are:

connector config/secrets/cursors are not yet cleanly separated into dedicated storage
Telegram bot token handling needs local secret hardening
browser clipper is still bookmarklet/local-endpoint MVP
/vnext connector config is not fully live-write/productized
migration/install readiness needs stronger checks
capture reliability needs deeper testing

⸻

Core Build Requirements

1. Dedicated Connector Settings Table

Move connector configuration out of ad hoc/event-log-backed config into dedicated persistent storage.

Create a connector settings model/table that supports:

connector_id
connector_name
enabled
configured
default_domain
default_sensitivity
sync_mode
poll_interval_seconds
created_at
updated_at
last_configured_at
metadata_json

Connector settings must support at least:

telegram
local_folder
browser_clipper
agent_output

Requirements:

settings can be read/written through API
settings can be read/written through CLI where appropriate
settings are visible in /vnext
settings changes create event-log entries
settings do not expose secrets
settings include validation errors
settings preserve existing connector behavior after migration

Acceptance criteria:

Connector settings persist across restart.
Connector settings survive migrations.
Connector settings are not stored only in event log.
Connector settings can be updated from /vnext for at least Telegram, local folder, and browser clipper.
Connector settings changes appear in Timeline/event log.

⸻

2. Connector State / Cursor Table

Create dedicated connector state/checkpoint storage.

The state model should support:

connector_id
connector_name
cursor_type
cursor_value
last_sync_at
last_success_at
last_failure_at
last_error
items_seen
items_captured
items_deduped
items_failed
average_processing_time_ms
state_json
updated_at

Use this for:

Telegram update offset
local folder scan/checkpoint state
browser clipper recent capture state
agent output ingestion counters

Requirements:

cursor updates must be atomic enough to avoid skipping failed items
failed items must not advance cursor past unprocessed data unless explicitly safe
duplicates should be counted separately from failures
state must be visible through CLI/API//vnext
state changes must not leak secrets

Acceptance criteria:

Telegram sync resumes from correct update offset after restart.
Local folder watcher does not recapture unchanged files after restart.
Failed connector items are logged and isolated.
Connector health shows accurate seen/captured/deduped/failed counts.

⸻

3. Encrypted Local Secret Store

Add a local secret storage abstraction for connector secrets.

Secrets include:

Telegram bot token
future OAuth client secrets/tokens
browser clipper local token if implemented
other connector credentials

Do not store secrets in:

event logs
plain JSON config
database rows without encryption
artifact metadata
source metadata
test snapshots
CLI output
web responses

Implement a secret store abstraction that can support:

OS keychain if available
encrypted local file fallback
environment variable reference
test/mock secret provider

For this sprint, it is acceptable to implement:

environment variable reference + encrypted local fallback

as long as the interface is future-proof.

Secret references should look like:

secret_ref: telegram.bot_token.default

The actual secret value should not be returned by API/CLI/UI.

Acceptance criteria:

Telegram connector uses secret_ref, not raw token storage.
Secrets never appear in event logs.
Secrets never appear in connector health.
Secrets never appear in API responses.
Secrets never appear in web UI.
Tests verify redaction.
CLI can set/update/test Telegram token without printing it.

⸻

4. Migration and Install Health Checks

Add stronger local alpha health checks.

Alice should detect and explain:

missing migrations
out-of-date database schema
missing connector settings rows
missing artifact quality migration
missing scheduler tables
missing secret store configuration
invalid connector config
unavailable local API
scheduler daemon not running
Postgres unavailable

Add CLI:

alicebot vnext doctor
alicebot vnext doctor --fix-safe
alicebot vnext migrations status

doctor should output:

database status
migration status
scheduler status
connector settings status
secret store status
model provider status
capture pipeline status
web/API status if available
recommended fixes

--fix-safe may create missing default connector settings/state rows, but must not run destructive operations.

Acceptance criteria:

Doctor detects missing migration state.
Doctor detects missing connector settings/state.
Doctor detects missing/invalid Telegram secret_ref.
Doctor detects scheduler daemon unavailable or unknown.
Doctor provides human-readable remediation.
Doctor exits non-zero for blocking failures.
Doctor can run in CI/smoke mode.

⸻

5. Live /vnext Connector Configuration UI

Upgrade /vnext connector surfaces from mostly status/health to live configuration.

Add or improve UI for:

Telegram settings
Local Folder settings
Browser Clipper settings
Agent Output ingestion status
Connector Health
Dogfooding Dashboard

Telegram UI

Must support:

enabled/disabled
secret_ref status without showing token
allowed chat IDs
default domain
default sensitivity
polling mode
test connection
run sync now
last sync
last error
recent captures

Local Folder UI

Must support:

add watched path
remove watched path
enable/disable path
recursive yes/no
extension allowlist
ignore patterns
default domain
default sensitivity
run sync now
watch status
last captured file
duplicates skipped
errors

Browser Clipper UI

Must support:

endpoint status
copyable bookmarklet
optional local capture token status if implemented
default domain
default sensitivity
recent clips
test clip form

Agent Output UI

Must show:

recent ingested outputs
agent_id
agent_type
project scope
proposal status
artifact/source links
policy decision

Acceptance criteria:

/vnext can configure Telegram without exposing token.
/vnext can configure local folders.
/vnext can show browser clipper setup instructions and recent clips.
Connector health updates after sync.
Errors are visible and understandable.
Loading/empty/error states are handled.
Demo fixture mode still works.

⸻

6. Browser Clipper Packaging Improvement

Improve the browser clipper MVP without turning this into a full extension project.

Choose the lowest-risk useful improvement:

Preferred:

bookmarklet generator with local endpoint URL and optional token

Optional if easy:

minimal unpacked browser extension scaffold

Required behavior:

capture URL
capture title
capture selected text
capture optional user note
send to local Alice endpoint
show success/failure feedback
mark content as untrusted
dedupe repeated clips

Security requirements:

local endpoint must bind to localhost by default
optional capture token supported or clearly planned
CORS locked down as much as practical
no remote-open unauthenticated capture by default
browser content treated as untrusted

Acceptance criteria:

User can copy bookmarklet from /vnext.
Bookmarklet can submit URL/title/selection/user note to Alice.
Alice stores browser clip as source with provenance.
Repeated identical clips dedupe.
Browser clip appears in Inbox and dogfooding dashboard.
Prompt-injection test for malicious browser clip still passes.

⸻

7. Telegram Reliability Improvements

Harden Telegram capture for daily dogfooding.

Requirements:

allowlisted chat IDs required
clear rejection logging for non-allowlisted chats
cursor/update offset durability
rate-limit/backoff handling
network failure handling
malformed update handling
dedupe repeated updates
safe token redaction
sync summary reporting

CLI/API should clearly report:

updates seen
messages captured
duplicates skipped
rejected chats
failures
next offset
last error

Acceptance criteria:

Telegram sync can be run repeatedly without duplicate memory spam.
Non-allowlisted chat messages are rejected and logged without capture.
Network/API errors do not corrupt cursor state.
Bot token is never logged.
Telegram status is understandable from CLI and /vnext.

⸻

8. Local Folder Watcher Reliability

Harden local folder/Obsidian capture.

Requirements:

ignore Alice-generated/export folders by default
ignore .git/node_modules/.venv/cache folders by default
debounce rapid file changes
dedupe unchanged files by content hash
handle file deletion without crashing
handle rename as new path or stable source update, but document behavior
support initial backfill
support incremental sync

Acceptance criteria:

Watcher does not ingest Alice generated artifacts by default.
Watcher does not loop on Alice exports.
Editing a Markdown file updates/captures once after debounce.
Unchanged files are deduped.
Deleting a watched file does not crash sync/watch.
Local folder status shows ignored/deduped/captured counts.

⸻

9. Dogfooding Dashboard Improvements

Improve the dogfooding dashboard so it is useful for daily review.

Add:

capture trend by day/week
connector health summary
sources captured by connector
candidate memory review rate
artifact rating trend
useful insight yes/no/not sure counts
top failure causes
scheduler freshness
agent activity summary
policy block/filter summary

Add a simple “dogfood readiness” indicator:

Green: capture + scheduler + model/routing + review loop healthy
Yellow: minor connector/scheduler/rating issues
Red: capture or scheduler broken

Acceptance criteria:

Dashboard answers whether Alice is being fed daily.
Dashboard answers whether Alice outputs are being reviewed/rated.
Dashboard answers which connector is failing.
Dashboard shows recent useful insight feedback.
Dashboard links to failed connector events.

⸻

10. Capture Reliability Tests and Smokes

Add/update smoke tests.

Required smoke tests:

alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor

Existing smokes must continue to pass:

alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler

Add prompt-injection regression cases for:

Telegram malicious instruction
browser malicious instruction
Markdown malicious instruction
agent output malicious instruction

Acceptance criteria:

0 prompt-injection tool writes
0 policy bypasses
0 auto-promotions
0 critical privacy leaks
secret redaction tests pass
connector restart/cursor tests pass
generated-folder feedback loop tests pass

⸻

Required End-to-End Flows

Flow 1: Safe Telegram setup and sync

User configures Telegram secret_ref and allowed chat IDs.
User runs Telegram test.
User sends message from allowlisted chat.
Alice captures it.
User sends message from non-allowlisted chat.
Alice rejects it and logs policy/rejection.
Token never appears in logs/API/UI.
Cursor persists after restart.

Flow 2: Safe Obsidian/local folder dogfooding

User adds watched Obsidian folder.
Alice initial backfills Markdown notes.
Alice ignores generated/export folders.
User edits a note.
Watcher captures update after debounce.
Duplicate unchanged files are skipped.
Source appears in Inbox/context packs.

Flow 3: Browser clipper local capture

User copies bookmarklet from /vnext.
User clips selected text from a page.
Alice stores clip as untrusted browser source.
Clip appears in Inbox.
Clip is available to context packs and Daily Brief.
Repeated identical clip dedupes.

Flow 4: Doctor catches dogfood problems

User runs alicebot vnext doctor.
Doctor reports migration status, connector settings, secret store, scheduler status, and capture pipeline health.
If safe defaults are missing, doctor --fix-safe creates them.
Doctor does not expose secrets.

Flow 5: Dogfooding dashboard shows daily health

Alice captures from Telegram/local folder/browser.
Scheduler generates artifacts.
User rates one artifact as useful.
Dashboard shows captures, connector health, scheduler freshness, review/rating status, and useful insight feedback.

⸻

Explicit Deferrals

Do not build these in this sprint:

Gmail OAuth
Calendar OAuth
live email polling
live calendar polling
Telegram webhook automation
Telegram voice transcription
OCR execution
PDF OCR
voice transcription execution
mobile app
hosted cloud deployment
automatic memory promotion
major UI redesign
full production browser extension polish
team accounts
cloud sync
billing

This sprint is hardening, not expansion.

⸻

Acceptance Criteria

The sprint is complete only when all of the following are true:

Dedicated connector settings table exists.
Dedicated connector state/cursor table exists.
Existing connector config migrates or initializes safely.
Telegram uses secret_ref and no raw bot token is stored in logs/API/UI.
Local secret store abstraction exists with test/mock provider and local fallback or env-ref support.
Connector settings are editable through API/CLI and visible in /vnext.
Telegram config/status/test/sync use the new settings/state model.
Local folder config/status/sync/watch use the new settings/state model.
Browser clipper config/status/capture use the new settings/state model.
Agent output ingestion appears in connector/dogfooding health where appropriate.
Connector state persists across restart.
Telegram cursor persists across restart.
Local folder unchanged files dedupe across restart.
Browser clipper bookmarklet or improved local capture flow works.
Browser clipper endpoint is localhost-first and treats content as untrusted.
vNext Doctor exists and detects migration/config/secret/scheduler/capture health issues.
Doctor --fix-safe can initialize missing safe defaults.
Dogfooding dashboard shows capture health, scheduler freshness, artifact review/rating status, useful insight feedback, connector failures, and policy blocks.
Generated/export folder feedback loop prevention is tested.
Secret redaction is tested.
Prompt-injection connector regressions pass.
Capture-to-brief smoke still passes.
Live-capture-connectors smoke still passes.
Agentic scheduler smoke still passes.
Model-backed workflow tests still pass.
Privacy leakage evals still pass.
No connector auto-promotes content into trusted memory.
No generated artifact auto-promotes into trusted memory.
No agent output bypasses review.
Python unit tests pass.
Python integration tests pass.
Web tests pass.
Web lint passes.
Web build passes.
Eval suite passes.
git diff --check passes.

⸻

Validation Commands

Run the existing validation suite plus the new hardening smokes.

At minimum:

pytest tests/unit -q
pytest tests/integration -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
alicebot eval run --suite all
git diff --check

Add and run:

alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor

Also re-run:

alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler

⸻

Final Deliverable

At the end of the sprint, provide a CTO summary with:

what was built
new connector settings/state model
secret storage approach
migration/doctor behavior
/vnext connector configuration changes
browser clipper improvement
Telegram reliability improvements
local folder watcher improvements
dogfooding dashboard improvements
security/privacy guardrails
prompt-injection validation
tests and validation results
known limitations
recommended next phase
PR number
merge commit

⸻

Recommended Next Phase After This

After this sprint, decide based on dogfooding results.

Likely next options:

1. Gmail/Calendar Read-Only Connectors
2. Voice Capture + Local Transcription
3. Public Alpha Packaging
4. Intelligence Quality Improvement Based on Ratings

My default recommendation after this hardening sprint will likely be Public Alpha Packaging or Voice Capture, unless dogfooding shows that Gmail/Calendar are the highest-value missing input streams.