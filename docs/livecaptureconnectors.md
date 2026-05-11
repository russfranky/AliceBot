
Alice vNext Sprint Prompt: Live Capture Connectors + Dogfooding Loop

Project Scope

Alice vNext now has:

local memory kernel
live-backed /vnext workspace
agentic control plane
governed scheduler daemon
model-backed Brain workflows
quality ratings
policy routing
MCP/API/CLI surfaces
no-auto-promotion guardrails
privacy and prompt-injection evals

This sprint should make Alice usable for real daily dogfooding by adding low-friction live capture paths and a feedback loop that shows whether Alice is becoming more useful over time.

The sprint focus is:

1. Live Telegram capture
2. Local folder / Obsidian watcher
3. Browser clipper MVP
4. Agent output ingestion from Hermes/OpenClaw
5. Dogfooding dashboard and capture health telemetry
6. Capture-to-brief loop validation

Do not build every connector. Build the first practical capture loop.

Alice should become easy to feed with real-life notes, project thoughts, browser research, Obsidian/Markdown changes, and agent outputs.

⸻

Product Principle

Alice is agentic-first and local-first.

The user may interact directly with /vnext, but the primary daily paths are likely:

Hermes / OpenClaw / other agents
Telegram quick capture
browser clipping
local notes / Obsidian folders

The /vnext workspace is the operator console for:

review
audit
source health
capture status
agent activity
generated artifacts
quality ratings
dogfooding metrics

Alice must preserve the existing trust model:

capture raw evidence
normalize source
create provenance
generate candidate memory
route through policy
require review before trusted memory
generate artifacts
collect quality feedback

No connector may auto-promote captured content into trusted memory.

⸻

Core Build Requirements

1. Live Capture Connector Framework Hardening

Before adding connector-specific behavior, make sure the live capture framework supports:

connector identity
connector configuration
secret storage reference
enabled/disabled state
cursor/checkpoint state
last sync state
last error
item-level failure isolation
deduplication by content hash and external ID
domain and sensitivity defaults
source provenance
event logging
capture health metrics

Every connector should produce normalized Alice source records with:

{
  "source_type": "telegram_message | local_file | browser_clip | agent_output",
  "connector_name": "...",
  "external_id": "...",
  "title": "...",
  "raw_content": "...",
  "metadata": {},
  "domain": "professional | personal | project | unknown",
  "sensitivity": "public | internal | private | confidential | unknown",
  "captured_at": "...",
  "source_created_at": "...",
  "source_refs": [],
  "content_hash": "..."
}

All captured sources must flow through the existing pipeline:

source capture
→ source chunks
→ provenance links
→ candidate memory generation
→ review queue
→ context-pack availability
→ scheduled/model-backed Brain workflows

⸻

2. Live Telegram Capture

Add a live Telegram capture connector.

Required behavior

Support local Telegram bot capture with:

bot token configuration through local secrets/config
allowed chat ID allowlist
polling mode for local dogfooding
cursor/update offset persistence
text message capture
link message capture
basic attachment metadata capture if present
message timestamp preservation
sender/chat metadata preservation
deduplication
failure isolation

Do not build advanced Telegram workflow automation yet.

Supported message types for this sprint

Required:

plain text
text with URL
forwarded text metadata where available

Optional if simple:

photo/document metadata without OCR
voice metadata without transcription

Do not implement voice transcription in this sprint.

Telegram source mapping

Telegram messages should create sources like:

source_type: telegram_message
connector_name: telegram
title: Telegram capture - YYYY-MM-DD HH:MM
raw_content: message text
metadata:
  chat_id
  message_id
  sender_id
  sender_username
  message_date
  contains_links
  attachment_metadata
domain: configured default, likely personal or professional
sensitivity: configured default, likely private

CLI/API/UI

Add or extend:

alicebot vnext connectors telegram configure
alicebot vnext connectors telegram test
alicebot vnext connectors telegram sync
alicebot vnext connectors telegram status

API endpoints should support:

get connector config/status
update connector config
run sync now
view recent captures
view recent failures

/vnext should show Telegram under Connector Health with:

enabled/disabled
last sync
last captured item
last error
items captured
items skipped as duplicates
items failed
run sync now

⸻

3. Local Folder / Obsidian Watcher

Add a live local folder watcher for Markdown/text files.

This is critical because power users may already live in Obsidian, Markdown folders, or project note folders.

Required behavior

Support:

one or more watched directories
recursive watch option
file extension allowlist
ignore patterns
initial backfill import
incremental file change detection
debounced change handling
content hash dedupe
file rename handling if practical
soft handling for deleted files
cursor/state persistence

Required file types:

.md
.txt

Optional if already supported safely:

.json
.csv as plain source metadata only

Do not build OCR, DOCX parsing, or PDF parsing expansion in this sprint unless already trivial through existing deterministic normalizers.

Important safety rule

Avoid feedback loops.

The watcher must be able to exclude Alice-generated/export folders, for example:

/generated
/.alice
/Alice Export
/07 Generated
/08 Queue

If Alice exports generated artifacts into a watched Obsidian folder, the watcher must not endlessly re-ingest its own generated outputs unless explicitly configured.

Folder source mapping

source_type: local_file
connector_name: local_folder
external_id: absolute path or stable path hash
title: filename
raw_content: file text
metadata:
  path
  relative_path
  file_size
  mtime
  extension
  watched_root
domain: configured default
sensitivity: configured default

CLI/API/UI

Add or extend:

alicebot vnext connectors local-folder add-path
alicebot vnext connectors local-folder remove-path
alicebot vnext connectors local-folder sync
alicebot vnext connectors local-folder watch
alicebot vnext connectors local-folder status

/vnext should show:

watched folders
last scan
last file captured
files captured
duplicates skipped
ignored files
errors
watch mode active/inactive

⸻

4. Browser Clipper MVP

Add a minimal browser capture path.

Do not overbuild a full polished browser extension yet. The MVP can be:

bookmarklet + local HTTP endpoint
or minimal extension if the repo already has extension scaffolding
or copy/paste web clip form in /vnext with URL/title/selection/body

Pick the lowest-risk implementation that gives real dogfooding value.

Required capture fields

{
  "url": "...",
  "title": "...",
  "selected_text": "...",
  "page_text": "...",
  "user_note": "...",
  "captured_at": "...",
  "domain": "professional",
  "sensitivity": "private"
}

At minimum, support:

URL
page title
selected text
user note
capture timestamp

Optional:

readability extraction
full page text
tags
project assignment

Security requirement

All captured web content is untrusted source material.

It must not be allowed to become instructions to Alice, agents, MCP tools, or the scheduler.

Preserve existing prompt-injection hardening.

Browser source mapping

source_type: browser_clip
connector_name: browser_clipper
title: page title or URL
raw_content: selected text + user note + optional page text
metadata:
  url
  title
  selected_text_present
  user_note_present
  captured_from_browser
domain: configured default
sensitivity: configured default

CLI/API/UI

Required API:

POST /v0/vnext/connectors/browser-clipper/capture

Required UI:

Browser Clipper setup instructions
local capture endpoint status
recent clips
copyable bookmarklet or extension instructions

⸻

5. Agent Output Ingestion

Alice is agentic-first. Hermes/OpenClaw outputs must be capturable as first-class sources or artifacts.

Add a path for agents to submit outputs such as:

research summaries
sprint summaries
code review findings
architecture decisions
project updates
meeting summaries
generated plans
final answers

Required behavior

Agents should be able to ingest an output with:

{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "...",
  "task_id": "...",
  "project_scope": ["Alice"],
  "title": "...",
  "content": "...",
  "output_type": "sprint_summary | research_summary | code_review | project_update | decision | general",
  "domain": "project",
  "sensitivity": "private",
  "source_refs": [],
  "rationale": "...",
  "propose_memory": true
}

This should create:

source record or generated artifact
event log entry
optional candidate memory proposal
provenance links
agent activity entry
review item if propose_memory = true

Do not allow agents to bypass review.

API/MCP/CLI

Add or extend:

alice_vnext_ingest_agent_output
alice_vnext_capture
alice_vnext_propose_memory

CLI:

alicebot vnext agents ingest-output \
  --agent-id openclaw \
  --agent-type coding_agent \
  --project-scope Alice \
  --title "Sprint 12 Summary" \
  --file summary.md \
  --propose-memory

/vnext Agent Activity should show ingested outputs.

⸻

6. Dogfooding Dashboard

Add a dogfooding dashboard or section in /vnext.

The goal is to answer:

Is Alice being fed?
Is capture working?
Are generated outputs useful?
Are users reviewing memory?
Are agents using Alice?
Is Alice surfacing useful connections?

Required metrics

Show at minimum:

captures by connector over time
captures today / this week
candidate memories created
candidate memories accepted/rejected/edited
generated artifacts created
artifact quality ratings average
daily brief read/review status
weekly synthesis review status
connections surfaced
contradictions surfaced
open loops created/closed
agent context packs requested
agent memory proposals
policy blocks/filters
connector failures
last successful scheduler run

Dogfooding “aha” metric

Add a simple user feedback flag on generated artifacts:

Useful insight?
[Yes] [No] [Not sure]

Optional but valuable:

“Alice surfaced something I would have missed”
[Yes] [No]

This should be tracked separately from detailed quality ratings.

⸻

7. Capture Health Telemetry

Add capture health telemetry for each connector.

Each connector should expose:

enabled
configured
last_sync_at
last_success_at
last_failure_at
last_error
items_seen
items_captured
items_deduped
items_failed
cursor_state
average_processing_time

This should be available through:

API
CLI
/vnext
event log

CLI:

alicebot vnext connectors status
alicebot vnext connectors health

⸻

8. Capture-to-Brief Dogfooding Loop

Add a specific dogfooding flow that proves captured data reaches Alice Brain outputs.

Required flow:

1. Capture Telegram message or browser clip.
2. Source appears in Inbox.
3. Candidate memory is generated with provenance.
4. User asks Alice about it.
5. Context pack includes the new source.
6. Daily Brief or Connection Report uses the new source.
7. Generated artifact includes source reference.
8. User rates artifact usefulness.
9. Dogfooding dashboard reflects capture, artifact, and rating.

Add an automated smoke test for this.

⸻

9. UI Requirements

Update /vnext to support:

Connector Health page or panel
Telegram connector settings/status
Local Folder watcher settings/status
Browser Clipper setup/status
Agent Output ingestion visibility
Dogfooding dashboard
Recent captures by connector
Capture errors
Capture-to-artifact trace visibility

Existing pages should also reflect connector data:

Inbox: show connector source and status
Generated: show which captured sources informed artifact
Agent Activity: show agent ingested outputs
Timeline: show connector sync and capture events
Settings: connector defaults for domain/sensitivity

⸻

10. Security and Privacy Requirements

Preserve all existing guardrails.

Required

No connector auto-promotes content into trusted memory.
No connector bypasses domain/sensitivity policy.
No source content is treated as system/tool instruction.
Secrets are not stored in plaintext logs or event payloads.
Telegram bot token must be secret-managed.
Telegram chat allowlist required.
Browser clipper local endpoint must not be open to arbitrary remote access by default.
Local folder watcher must not read outside configured paths.
Agent output ingestion must include agent identity and policy checks.
All capture write paths create event-log entries.
All failures are logged without leaking secrets.

Prompt-injection requirement

Add prompt-injection test cases for:

Telegram message containing malicious instructions
browser clip containing malicious instructions
Markdown file containing malicious instructions
agent output containing malicious instructions

All must pass with:

0 tool writes from injected source content
0 policy bypasses
0 auto-promotions

⸻

11. Explicit Deferrals

Do not build these in this sprint:

Gmail OAuth
Calendar OAuth
live email polling
live calendar polling
advanced Telegram workflows
Telegram voice transcription
OCR execution
PDF OCR
voice transcription execution
mobile app
hosted cloud deployment
automatic memory promotion
major UI redesign
full production browser extension polish
social sharing
team accounts

A minimal browser clipper/bookmarklet is acceptable. A large extension project is not.

⸻

Required End-to-End Flows

Flow 1: Telegram quick capture

User sends message to Telegram bot.
Alice polls or receives update.
Message is accepted only if chat_id is allowlisted.
Source is created with Telegram metadata.
Source is chunked and deduped.
Candidate memory/provenance is created.
Inbox shows captured source.
Timeline shows connector capture event.

Flow 2: Obsidian/local file update

User edits Markdown file in watched folder.
Watcher detects change after debounce.
Alice captures or updates source.
Dedupe prevents duplicate memory spam.
Generated/export folders are ignored.
Candidate memory/provenance is created.
Source appears in Inbox and context packs.

Flow 3: Browser clip

User clips selected text and URL.
Alice receives browser clip through local endpoint/form.
Source is stored as untrusted browser content.
Candidate memory/provenance is created.
User can ask Alice about the clip.
Daily Brief or Connection Report can cite it.

Flow 4: OpenClaw ingests sprint output

OpenClaw submits agent output with agent identity.
Alice policy-checks the submission.
Output is stored as source/artifact.
Optional memory proposal is created.
Agent Activity shows submission.
Memory Review shows pending proposal.
No trusted memory is mutated without review.

Flow 5: Dogfooding signal

Scheduler generates Daily Brief or Connection Report.
Artifact cites newly captured source.
User rates artifact as useful/not useful.
Dogfooding dashboard updates metrics.
Quality export includes rating and source relationship.

⸻

Acceptance Criteria

The sprint is complete only when all of the following are true:

Live Telegram capture works in local dogfooding mode.
Telegram connector requires allowlisted chat IDs.
Telegram connector persists cursor/update offset.
Telegram connector dedupes repeated messages.
Telegram connector failures do not corrupt memory.
Local folder watcher supports configured directories.
Local folder watcher supports initial backfill and incremental changes.
Local folder watcher ignores Alice generated/export folders by default.
Local folder watcher dedupes unchanged files by hash.
Browser clipper MVP can capture URL, title, selected text, and user note.
Browser clipper content is marked as untrusted source material.
Agent output ingestion works through API/MCP/CLI.
Agent output ingestion creates source/artifact records with agent identity.
Agent output ingestion can optionally create review-only memory proposals.
No captured connector content auto-promotes into trusted memory.
All connector write paths create event-log entries.
Connector health telemetry exists for Telegram, local folder, browser clipper, and agent output ingestion.
Dogfooding dashboard exists in /vnext.
Dogfooding dashboard shows captures, reviews, artifacts, ratings, agent activity, policy blocks, connector failures, and scheduler health.
Capture-to-brief smoke test passes.
Prompt-injection tests for Telegram/browser/Markdown/agent-output sources pass.
Privacy leakage evals still pass.
Existing model-backed workflow tests still pass.
Existing scheduler daemon tests still pass.
Existing agentic control plane tests still pass.
Python unit tests pass.
Python integration tests pass.
Web tests pass.
Web lint passes.
Web build passes.
Eval suite passes.
git diff --check passes.

⸻

Validation Commands

Run the existing validation suite plus new connector/dogfooding smoke tests.

At minimum:

pytest tests/unit -q
pytest tests/integration -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
alicebot eval run --suite all
git diff --check

Add and run new smoke tests:

alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief

If those exact commands do not exist, create equivalent scripts/pytest targets and document them.

⸻

Final Deliverable

At the end of the sprint, provide a CTO summary with:

what was built
connectors implemented
API/MCP/CLI additions
/vnext UI additions
capture health telemetry
dogfooding dashboard behavior
security/privacy guardrails
prompt-injection validation
tests and validation results
known limitations
recommended next phase
PR number
merge commit

⸻

Recommended Next Phase After This

After this sprint, the recommended next phase should be chosen based on dogfooding results.

Likely options:

1. Gmail/Calendar Read-Only Connectors
2. Voice Capture + Local Transcription
3. Public Alpha Packaging
4. Intelligence Quality Improvement Based on Human Ratings

Do not pre-commit to Gmail/Calendar until we see whether Telegram, local folder, browser clips, and agent outputs produce enough useful daily signal.