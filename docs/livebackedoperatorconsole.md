
Alice vNext Sprint Prompt: Live-Backed Operator Console Completion
Sprint Objective
Alice vNext now has a hardened local dogfood loop with live capture connectors, dedicated connector settings/state tables, secret references, doctor checks, scheduler runtime, model-backed Brain workflows, quality ratings, and dogfooding telemetry.
This sprint should make /vnext the primary daily operator console for Alice.
The goal is not to add major new connectors or redesign the UI. The goal is to connect the existing backend capabilities to real /vnext workflows so a user can operate Alice day to day from the web workspace instead of relying on CLI/API calls.
By the end of this sprint, /vnext should let the user:
review captured sources
accept/edit/reject candidate memories
review/promote/archive generated artifacts
rate artifact usefulness
manage open loops
review project updates
configure connector settings
inspect connector health
run/schedule Brain workflows
inspect scheduler history
inspect agent activity
inspect policy blocks
run/read doctor checks
trace capture-to-brief provenance
CLI should remain available for power-user/admin operations, but the normal dogfooding workflow should be possible from /vnext.

⸻

Product Principle
Alice is still:
agentic-first
local-first
review-first
provenance-first
no-auto-promotion
The /vnext UI is not the “main memory engine.” It is the operator cockpit for the memory engine.
Agents such as Hermes and OpenClaw may continue using MCP/API/CLI as primary access paths. /vnext should show what agents did, what Alice generated, what policies blocked or filtered, and what needs human review.
No UI action should bypass the existing policy/review model.

⸻

Current State Assumption
Alice already has:
live-backed /vnext foundation
agentic control plane
governed scheduler daemon
model-backed Brain workflows
quality ratings
live Telegram capture
local folder / Obsidian capture
browser clipper MVP
agent output ingestion
dedicated connector settings table
dedicated connector state/cursor table
secret-provider abstraction
doctor checks
dogfooding dashboard
capture-to-brief smoke
privacy and prompt-injection evals
The previous phase specifically hardened connector settings/state, secret references, doctor checks, live connector configuration, and dogfooding telemetry.
This sprint should build on that and make /vnext the daily control surface.

⸻

Core Build Requirements
1. Live Workspace Data Contract
Create or harden a clear live workspace data contract for /vnext.
The workspace payload should include enough real data to render the operator console without fixture dependence:
current user/system status
recent sources
candidate memories
generated artifacts
artifact ratings
open loops
projects
project update candidates
recent events/timeline
agent activity
policy blocks/filters
scheduler status
scheduler run history
connector settings
connector health
dogfooding metrics
doctor/readiness status
Requirements:
live mode should be default when API config exists
demo fixture mode should remain available
fixture/demo data must be clearly separated from live data
UI should not silently mix live and fixture data in ways that confuse operators
workspace payload should be versioned or typed
loading, empty, error, and permission states must be handled
Acceptance criteria:
/vnext loads a live workspace payload by default.
Demo mode still works via explicit mode selection or query parameter.
The UI clearly indicates live vs demo mode.
The workspace payload is typed and tested.
No required daily operator panel depends only on fixtures.

⸻

2. Inbox and Captured Source Review
Make the Inbox a real operator workflow.
The user should be able to:
view recently captured sources
filter by connector
filter by domain/sensitivity
filter by review status
open source detail
view raw evidence preview
view chunks/provenance where available
see candidate memories generated from source
assign source to project
update source domain/sensitivity if allowed
create open loop from source
mark source reviewed
soft-delete or archive source where policy allows
Required source metadata display:
source type
connector name
captured_at
source_created_at
title
domain
sensitivity
content hash/dedupe status
provenance links
candidate memory count
artifact usage count
Acceptance criteria:
Captured Telegram/local folder/browser/agent-output sources appear in live Inbox.
Source detail shows provenance and connector metadata.
Source domain/sensitivity can be updated through policy-checked API.
Source can be assigned to project.
Source can create an open loop.
Source review actions create event-log entries.
No source action auto-promotes trusted memory.

⸻

3. Memory Review Console
Make Memory Review fully live-backed and usable.
The user should be able to:
see pending candidate memories
filter by source, project, connector, domain, sensitivity, agent, confidence
open candidate detail
see source evidence/provenance
accept candidate
edit candidate then accept
reject candidate
mark candidate private
assign candidate to project
merge or supersede where existing backend supports it
see review history
Required candidate detail sections:
candidate memory text
why Alice thinks it matters
source evidence
provenance links
confidence
domain/sensitivity
agent or workflow origin
policy decision
review status
event history
Acceptance criteria:
Candidate memories from live captures appear in Memory Review.
Accept/edit/reject/private/project assignment write to real backend.
Every review action creates event-log entry.
Accepted memory appears in later context packs.
Rejected memory does not keep reappearing unless new evidence changes the proposal.
No generated artifact or candidate memory auto-promotes.

⸻

4. Generated Artifacts Console
Make Generated Artifacts a complete daily review surface.
The user should be able to:
view artifacts by type
filter by generated_by: scheduler, agent, user, system
filter by workflow type
filter by review status
filter by model mode: deterministic/model-backed
open artifact detail
see source references
see provider/model metadata
see scheduler_run_id / agent_run_id / trace_id
review artifact
archive artifact
promote artifact to memory proposal
create open loop from artifact
create project update from artifact
rate artifact quality
mark useful insight: yes/no/not sure
compare deterministic vs model-backed where available
Required artifact detail sections:
content
facts
inferences
recommendations
uncertainties
source references
contradictions considered
open questions
provider/model metadata
policy/routing decision
review history
quality ratings
useful insight feedback
Acceptance criteria:
Daily Brief, Weekly Synthesis, Connection Report, Contradiction Report, Open Loop Review, and Project Update Scan artifacts render from live data.
Artifact review/archive/promote/rate actions persist.
Quality ratings update dogfooding dashboard.
Useful insight feedback persists.
Artifact promotion creates review-only memory proposal, not trusted memory.
Model metadata is visible where available.

⸻

5. Open Loops Console
Make Open Loops fully live-backed.
The user should be able to:
create open loop
edit open loop
close open loop
reopen open loop
snooze open loop
assign project
assign person if supported
set priority
set due date
link to source/artifact/memory
filter by project/status/priority/due date
Acceptance criteria:
Open loops created from source/artifact/manual UI persist.
Close/reopen/snooze/edit actions persist.
Open loops appear in Daily Brief and relevant project dashboards.
Event log records all state changes.
Invalid status transitions are blocked with clear UI errors.

⸻

6. Project Operator View
Make Projects useful for daily work.
Each project page should show live:
current state
recent project sources
project memories
project update candidates
open loops
generated artifacts
recent decisions
recent changes
related agents/activity
policy blocks relevant to project
timeline events
The user should be able to:
create project
edit project basics
review project update candidate
accept/edit/reject project update
create project open loop
generate project-specific context pack
run project update scan
view project-related artifacts
Acceptance criteria:
Project dashboard uses real backend data.
Project update candidates can be accepted/edited/rejected.
Accepted project update creates memory/revision/event log.
Project-specific context pack can be generated from UI.
Project open loops and artifacts are visible.

⸻

7. Scheduler and Brain Workflow Operations
The Schedules view should become an operator-grade control panel.
The user should be able to:
view daemon status
view global pause/resume state
view all workflows
enable/disable workflows
edit schedule where supported
run now
pause/resume scheduler
view next run
view last run
view last success
view last failure
view run history
open generated artifact from run
open trace/event history for run
Workflow types:
daily_brief
weekly_synthesis
connection_report
contradiction_report
open_loop_review
project_update_scan
Acceptance criteria:
Schedule settings are live-backed.
Run-now works from UI.
Pause/resume works from UI where policy allows.
Run history is visible.
Failures are visible and understandable.
Generated artifacts link back to scheduler runs.
Scheduler actions create event-log entries.
No scheduled workflow auto-promotes trusted memory.

⸻

8. Connector Configuration and Health Console
Make connector configuration fully usable from /vnext for the dogfood connectors.
Supported connectors:
Telegram
Local Folder / Obsidian
Browser Clipper
Agent Output
Telegram
UI should support:
enabled/disabled
secret_ref status
allowed chat IDs
default domain
default sensitivity
polling/sync settings
test connection
run sync now
view last sync
view next offset/cursor posture
view rejected chats
view failures
view recent captures
Local Folder
UI should support:
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
ignored files
errors
Browser Clipper
UI should support:
endpoint status
bookmarklet generator
optional token status
default domain
default sensitivity
test clip form
recent clips
copy setup instructions
Agent Output
UI should show:
recent agent-ingested outputs
agent_id
agent_type
project scope
source/artifact links
proposal status
policy decision
Acceptance criteria:
Connector settings are editable from /vnext.
Connector state/health is visible from /vnext.
Manual sync/test actions work from /vnext.
Secret values are never displayed.
Connector failures link to relevant events/logs.
Live connector changes create event-log entries.

⸻

9. Agent Activity and Policy Console
Make agent observability useful.
The Agent Activity view should show:
agent identities
permission profile
recent context packs requested
artifacts generated
outputs ingested
memory proposals submitted
open loops created
project updates proposed
scheduler actions requested
policy blocks
policy filters
requires-review decisions
restricted-domain requests
The user should be able to:
filter by agent
filter by project
filter by policy decision
open related artifact/source/memory proposal
open event detail
view trace ID/run ID/task ID
Acceptance criteria:
Hermes/OpenClaw-style agent activity is visible.
Policy blocks/filters are visible and explainable.
Agent memory proposals link to Memory Review.
Agent artifacts link to Generated.
Agent output ingestion links to sources/artifacts.

⸻

10. Doctor and Readiness UI
Expose doctor/readiness checks in /vnext.
The user should be able to see:
database/migration status
scheduler daemon status
connector settings status
connector state status
secret provider status
model provider/routing status
capture pipeline status
recent blocking failures
recommended fixes
Optional if safe:
run doctor from UI
run doctor --fix-safe from UI with confirmation
Acceptance criteria:
/vnext shows dogfood readiness status.
Readiness reasons are understandable.
Blocking failures are clear.
Safe fixes require confirmation.
Doctor output does not expose secrets.

⸻

11. Capture-to-Brief Traceability
Add a trace view or detail panel that lets the user follow an item through the loop:
source captured
source chunked
candidate memory created
context pack retrieved it
artifact cited it
artifact rated useful/not useful
memory accepted/rejected
This can be implemented as a timeline panel on source/artifact detail or as a dedicated trace view.
Acceptance criteria:
User can open a captured source and see whether it influenced context packs or artifacts.
User can open an artifact and see which sources influenced it.
Capture-to-brief smoke proves traceability.
Trace view includes source/artifact/memory/event IDs.

⸻

API Requirements
Add or harden API endpoints as needed for the UI.
The API should support:
workspace live payload
source list/detail/review/update
candidate memory list/detail/review
artifact list/detail/review/rate/promote/archive
open loop CRUD
project dashboard/update candidate review
scheduler status/config/run history/run-now/pause/resume
connector settings/state/health/test/sync
agent activity/policy events
doctor/readiness status
capture-to-brief trace
All write endpoints must:
run policy checks
create event-log entries
return clear errors
not expose secrets
not auto-promote memory

⸻

UI Requirements
The UI should prioritize usability over visual redesign.
Required pages or tabs:
Home
Inbox
Memory Review
Generated
Daily Brief
Weekly Synthesis
Projects
Open Loops
Schedules
Connectors
Agent Activity
Dogfooding Dashboard
Timeline
Settings / Brain Charter
Doctor / Readiness
Existing pages can be reused and improved.
Requirements:
consistent loading states
consistent empty states
consistent error states
clear live/demo mode indicator
clear domain/sensitivity labels
clear review status labels
clear generated_by labels
clear policy decision labels
clear source/provenance links

⸻

Security and Privacy Requirements
Preserve all existing guardrails.
Required:
No UI action auto-promotes trusted memory.
No connector content bypasses review.
No generated artifact bypasses review.
No agent proposal bypasses review.
No source content becomes tool/system instruction.
Secret values are never displayed in UI/API/logs.
Domain/sensitivity policies are enforced.
Restricted actions show clear permission errors.
Prompt-injection tests still pass.
Privacy leakage evals still pass.

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
billing
cloud sync
This sprint is about completing the local operator console, not expanding the integration surface.

⸻

Required End-to-End Flows
Flow 1: Daily review from
/vnext
User opens /vnext.
User sees dogfood readiness.
User reviews new captured sources in Inbox.
User accepts/edits/rejects candidate memories.
User reviews generated Daily Brief.
User rates artifact usefulness.
Dogfooding dashboard updates.
Timeline shows actions.
Flow 2: Connector operation from
/vnext
User opens Connectors.
User configures Telegram/local folder/browser clipper defaults.
User runs sync now.
Connector captures source.
Connector health updates.
Source appears in Inbox.
No secrets are exposed.
Flow 3: Scheduler operation from
/vnext
User opens Schedules.
User runs Connection Report now.
Scheduler run starts and completes.
Generated artifact appears.
Run history links to artifact.
Timeline logs run lifecycle.
No artifact auto-promotes.
Flow 4: Agent activity review
OpenClaw submits agent output or memory proposal.
Agent Activity shows the action.
Memory Review shows pending proposal.
User accepts/rejects proposal.
Event log records full flow.
Flow 5: Capture-to-brief trace
Browser clip is captured.
Daily Brief cites browser clip.
User opens source trace.
Trace shows source → context pack/artifact → rating/review path.

⸻

Acceptance Criteria
The sprint is complete only when all of the following are true:
/vnext live mode is the default when API config exists.

Demo mode remains available and clearly labeled.

Inbox is live-backed and supports source review/update/project/open-loop actions.

Memory Review is live-backed and supports accept/edit/reject/private/project assignment actions.

Generated Artifacts is live-backed and supports review/archive/promote/rate/useful insight actions.

Open Loops are live-backed and support create/edit/close/reopen/snooze.

Projects are live-backed and show project state, open loops, artifacts, update candidates, and recent activity.

Project update candidates can be accepted/edited/rejected from UI.

Schedules are live-backed and support status, run-now, pause/resume, run history, and failure visibility.

Connectors are live-backed and support Telegram/local-folder/browser configuration, health, test/sync where supported.

Agent Activity is live-backed and shows agent events, proposals, artifacts, and policy blocks/filters.

Dogfooding Dashboard is live-backed and reflects captures, ratings, reviews, scheduler freshness, policy events, and connector failures.

Doctor/Readiness status is visible in /vnext.

Capture-to-brief traceability exists for sources and artifacts.

All write actions create event-log entries.

All write actions are policy-checked.

No UI/API path exposes secrets.

No UI/API path auto-promotes trusted memory.

Prompt-injection evals still pass.

Privacy leakage evals still pass.

Existing connector hardening smokes still pass.

Existing capture-to-brief smoke still passes.

Existing agentic scheduler smoke still passes.

Python unit tests pass.

Python integration tests pass.

Web tests pass.

Web lint passes.

Web build passes.

Eval suite passes.

git diff --check passes.

⸻

Validation Commands
Run the standard validation suite:
pytest tests/unit -q
pytest tests/integration -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
alicebot eval run --suite all
git diff --check
Re-run existing vNext smokes:
alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler
Add a new smoke test:
alicebot vnext smoke operator-console
The new smoke should verify:
live workspace loads
source review action persists
memory review action persists
artifact rating/review persists
open-loop update persists
scheduler run-now creates artifact
connector health is visible
agent activity is visible
doctor/readiness status is available
capture-to-brief trace exists
event logs are created

⸻

Final Deliverable
At the end of the sprint, provide a CTO summary with:
what was built
which /vnext pages are now fully live-backed
API additions/changes
UI additions/changes
operator workflows supported
connector configuration behavior
scheduler operation behavior
agent activity behavior
doctor/readiness behavior
capture-to-brief traceability
security/privacy guardrails preserved
tests and validation results
known limitations
recommended next phase
PR number
merge commit

⸻

Recommended Next Phase After This
After this sprint, choose based on dogfooding.
Likely candidates:
1. Public Alpha Packaging
2. Voice Capture + Local Transcription
3. Gmail/Calendar Read-Only Connectors
4. Intelligence Improvement Based on Ratings
Default recommendation after this sprint will likely be Public Alpha Packaging, assuming the operator console is usable enough for daily local dogfooding.
