⸻

Next Sprint Scope

Objective

Turn the current governed scheduler into a reliable local runtime that can run Alice Brain workflows automatically, complete the remaining scheduled workflow generators, and reduce /vnext fixture dependency.

By the end of the sprint, Alice should be able to run locally in the background, execute due workflows safely, generate reviewable artifacts, show all runs in /vnext, and preserve agent/policy/audit controls.

⸻

Core deliverables

1. Local scheduler daemon / service runner
2. launchd/systemd recipes
3. Full deterministic generators for remaining scheduler workflows
4. Fully live-backed scheduler and agent activity surfaces
5. Reduced /vnext fixture dependency
6. Scheduler failure/recovery hardening
7. Agent policy telemetry summary
8. Updated local alpha docs

⸻

Build requirements

1. Local scheduler daemon

Add a lightweight local runtime around:

alicebot vnext scheduler run-due

Supported modes:

foreground dev mode
background local daemon mode
systemd recipe for Linux
launchd recipe for macOS
Docker/local process option if already compatible

The daemon should:

poll due workflows on a configurable interval
respect pause/resume state
not run disabled workflows
avoid duplicate concurrent runs
log start/success/failure
recover cleanly after restart
persist last run and next run state

No hosted scheduler yet.

⸻

2. Complete remaining scheduled workflow generators

Daily Brief and Weekly Synthesis are already primary runnable workflows.

Now complete deterministic artifact generation for:

connection_report
contradiction_report
open_loop_review
project_update_scan

Each should produce a reviewable generated artifact with:

artifact_type
workflow_type
scheduler_run_id
trace_id
generated_by = scheduler
source refs
domain
sensitivity
policy decision
review status
created_at

No workflow may auto-promote anything into trusted memory.

⸻

3. Live-backed /vnext cleanup

Reduce fixture dependency in the existing workspace.

Prioritize making these fully live-backed:

Agent Activity
Schedules
Timeline/Event Log
Generated Artifacts
Memory Review
Projects
Open Loops

Fixture/demo mode can remain, but live mode should be clearly default when API config exists.

⸻

4. Scheduler observability

Add better operator visibility.

The UI should show:

daemon status if available
last due scan
next due workflow
currently running workflow
recent failures
last successful run per workflow
workflow run history
blocked/filtered policy decisions

CLI should expose:

alicebot vnext scheduler daemon start
alicebot vnext scheduler daemon status
alicebot vnext scheduler daemon stop
alicebot vnext scheduler runs
alicebot vnext scheduler failures

If stop/status are not practical cross-platform yet, document the local process approach clearly.

⸻

5. Agent policy telemetry

Add a simple summary view/report showing:

policy blocks by agent
policy filters by agent
requires-review decisions by agent
most common restricted domains requested
most common workflows triggered by agents
memory proposals by agent
artifact generation by agent

This is important because Alice is agentic-first. We need to see how Hermes/OpenClaw actually interact with the system.

⸻

Acceptance criteria

Local scheduler daemon or service runner exists.
Daemon can run due workflows without manual CLI invocation.
macOS launchd recipe exists.
Linux systemd recipe exists.
Scheduler does not run disabled workflows.
Scheduler respects global pause/resume.
Scheduler prevents duplicate concurrent runs for the same workflow.
Daily Brief scheduled run still works.
Weekly Synthesis scheduled run still works.
Connection Report scheduled run produces a real reviewable artifact.
Contradiction Report scheduled run produces a real reviewable artifact.
Open Loop Review scheduled run produces a real reviewable artifact.
Project Update Scan scheduled run produces a real reviewable artifact.
All scheduled artifacts include generated_by, workflow_type, scheduler_run_id, trace_id, source refs, domain, sensitivity, and review status.
No scheduled workflow auto-promotes artifacts into trusted memory.
Scheduler failures are captured and visible in /vnext.
Timeline/Event Log shows scheduler run lifecycle events.
Agent Activity and Schedules pages are live-backed.
Generated Artifacts, Memory Review, Projects, and Open Loops are live-backed or substantially more live-backed than the previous phase.
Demo fixture mode remains available.
Postgres-backed smoke test covers daemon/due-run behavior.
Policy telemetry summary exists through CLI/API and visible minimally in /vnext.
Existing agent permission rules remain enforced.
Existing no-auto-promotion, privacy, and prompt-injection evals still pass.
Python tests pass.
Integration tests pass.
Web tests pass.
Web lint passes.
Web build passes.
git diff --check passes.

⸻

Explicit deferrals

Still defer:

live Gmail OAuth
live Calendar OAuth
live Telegram polling
browser extension runtime actions
OCR execution
voice transcription execution
hosted scheduler service
cloud deployment
mobile app
automatic memory promotion
human-rated eval scoring
major UI redesign

After this sprint, the system will be ready for either:

Model-Backed Intelligence

or:

Live Connector Auth/Polling

But I would only choose between those after seeing whether the local runtime loop feels useful in dogfooding.

Bottom line

This PR is a major step. Alice now has the right agentic control model.

The next milestone is operational:

Alice should run locally in the background, execute governed workflows on schedule, generate useful reviewable artifacts, and show exactly what happened.

Once that is stable, then we make the intelligence stronger.