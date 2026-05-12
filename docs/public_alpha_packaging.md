

Alice vNext Sprint Prompt: Public Alpha Packaging + Agent Integration Pack

Sprint Objective

Alice vNext has now reached a local dogfood alpha state. The latest phase made /vnext a live-backed daily operator console with source review, candidate memory review, artifact review/rating, doctor/readiness checks, capture-to-brief traceability, scheduler visibility, connector health, and event-log-backed review flows. The current product rule remains unchanged: source evidence and generated artifacts stay review-only until a human explicitly accepts, promotes, or archives them.

This sprint should prepare Alice vNext for a small public/design-partner alpha.

The key product assumption is:

Alice is agent-first, not dashboard-first.
Most users will connect Hermes, OpenClaw, or custom agents to Alice.
Agents will request context, submit outputs, propose memories, create open loops, and trigger workflows.
The /vnext console exists for review, governance, audit, configuration, doctor checks, and troubleshooting.

The goal is to make Alice installable, understandable, demoable, and agent-connectable by a technical alpha user without direct hand-holding.

⸻

Product Positioning

Alice should be positioned as:

Local-first memory and continuity infrastructure for humans and agents.

Not:

A notes app
An Obsidian clone
A chatbot with memory
A dashboard-first second brain

The correct user story is:

Install Alice locally.
Connect your agents.
Give them durable, private, provenance-aware, reviewable memory.
Use /vnext to govern, review, audit, and configure.

⸻

Core Scope

This sprint has two major workstreams:

1. Public Alpha Packaging
2. Agent Integration Pack

Do not add major new product features. Package, document, test, and smooth the current system.

⸻

Workstream 1: Public Alpha Packaging

1. One-Command Local Setup

Create or improve a simple local install path for technical users.

Support the current recommended local stack.

At minimum, document and test:

clone repo
install backend dependencies
install frontend dependencies
configure environment
run migrations
run doctor
start API
start /vnext
start scheduler daemon
open /vnext

Preferred:

make setup
make dev
make doctor
make vnext

or equivalent project-native commands.

Acceptance criteria:

Fresh local setup path is documented.
Setup does not require reading internal sprint notes.
Missing dependencies produce clear errors.
Doctor is part of the first-run flow.
User can reach /vnext after setup.
User can run at least one smoke command after setup.

⸻

2. First-Run Alpha Checklist

Add a first-run checklist for users.

This can be in docs first, and optionally visible in /vnext.

Checklist:

1. Install Alice.
2. Run migrations.
3. Run doctor.
4. Start local API.
5. Start scheduler daemon.
6. Open /vnext.
7. Configure Brain Charter / ALICE.md.
8. Configure one capture path:
   - local folder
   - browser clipper
   - Telegram
9. Capture first source.
10. Review captured source.
11. Generate Daily Brief or Connection Report.
12. Review/rate generated artifact.
13. Inspect trace from source to artifact.
14. Connect an agent through MCP/API.

Acceptance criteria:

First-run checklist exists.
Checklist links to commands/docs.
Checklist explains expected success state.
Checklist explains where to go when doctor fails.

⸻

3. Public Alpha README

Rewrite or add a public alpha README section that explains:

What Alice is
What Alice is not
Why agent-first memory matters
Core architecture
Local-first trust model
No-auto-promotion model
MCP/API/CLI/UI surfaces
Supported alpha connectors
Known limitations
Quickstart
Agent integration path
Security/privacy posture

The README should make the product clear within the first 60 seconds.

Recommended opening:

Alice is a local-first memory and continuity layer for humans and agents.
It lets agents like Hermes, OpenClaw, or your own custom agents request scoped context, submit outputs, propose memories, create open loops, and generate reviewable artifacts — without giving them direct write access to trusted memory.
The /vnext workspace is the operator console for review, audit, configuration, and troubleshooting.

Acceptance criteria:

README clearly explains Alice Core, Alice Brain, Alice Agent Memory, and /vnext.
README emphasizes agent-first usage.
README includes quickstart commands.
README includes alpha limitations.
README includes security/privacy expectations.

⸻

4. Alpha Docs Structure

Create or update docs:

docs/
  alpha/
    quickstart.md
    first-run.md
    local-runtime.md
    doctor.md
    agent-integration.md
    hermes-skill.md
    openclaw-skill.md
    custom-agent-guide.md
    mcp-tools.md
    context-pack-recipes.md
    memory-proposal-recipes.md
    dogfooding-guide.md
    troubleshooting.md
    known-limitations.md
    security-and-privacy.md

Keep docs practical and command-oriented.

Acceptance criteria:

Docs are navigable from README.
Docs avoid internal-only assumptions.
Docs include copy-paste examples.
Docs clearly distinguish alpha vs future capabilities.

⸻

5. Demo Dataset and Demo Mode

Package a small safe demo dataset.

It should demonstrate:

sources
candidate memories
generated artifacts
open loops
project updates
agent activity
policy block/filter
capture-to-brief trace
quality ratings
scheduler run
connector health

Acceptance criteria:

Demo dataset contains no private data.
Demo dataset can be loaded/reset.
Demo mode clearly indicates it is demo data.
Demo can show a source → memory → artifact → rating → trace loop.

⸻

6. Alpha Readiness Gate

Create a single readiness command or documented command sequence.

Preferred:

alicebot vnext alpha check

or document equivalent commands.

It should run or summarize:

migrations status
doctor
scheduler status
connector settings/state presence
secret redaction smoke
operator console smoke
capture-to-brief smoke
agent integration smoke
eval suite status

Acceptance criteria:

Alpha readiness command or checklist exists.
Blocking failures are obvious.
Warnings are understandable.
Output does not expose secrets.

⸻

Workstream 2: Agent Integration Pack

7. MCP Tool Quickstart

Create a practical MCP integration guide.

It should include:

how to expose Alice MCP server
how an agent should identify itself
how to request context packs
how to ingest agent output
how to propose memory
how to create open loops
how to review artifacts
how permission profiles work
how to avoid sensitive domains

Acceptance criteria:

MCP quickstart includes exact commands/config examples.
MCP quickstart includes at least one end-to-end agent example.
MCP quickstart explains no-auto-promotion.
MCP quickstart explains policy errors.

⸻

8. Hermes Skill Pack

Create a ready-to-use Hermes skill/instruction file.

Path suggestion:

docs/alpha/hermes-skill.md
agent-skills/hermes/alice-memory-skill.md

Hermes should be instructed to use Alice as the user’s durable memory and continuity layer.

The Hermes skill should say:

Before planning, answering, or acting on important user context, request a scoped context pack from Alice.
When the user makes a durable decision, states a stable preference, creates an open loop, or changes project direction, propose memory to Alice.
When Hermes creates summaries, plans, follow-ups, meeting notes, or daily briefings, ingest them into Alice as reviewable agent outputs.
Never directly mutate trusted memory.
Never bypass Alice policy.
Never request sensitive domains unless needed and allowed.
Use /vnext review queues for human approval.

Hermes default permissions:

permission_profile: trusted_local_agent
agent_type: personal_assistant
scope: broad but policy-filtered
allowed domains: professional, project, personal where configured
restricted by default: health, family, spiritual, legal, financial, regulated unless explicitly enabled

Hermes recipes:

Daily planning context
Meeting preparation context
Follow-up/open-loop context
Project briefing context
Personal assistant memory proposal
Artifact submission

Acceptance criteria:

Hermes skill is copy-paste usable.
Hermes skill includes tool usage recipes.
Hermes skill includes permission guidance.
Hermes skill includes examples of good and bad memory proposals.

⸻

9. OpenClaw Skill Pack

Create a ready-to-use OpenClaw skill/instruction file.

Path suggestion:

docs/alpha/openclaw-skill.md
agent-skills/openclaw/alice-project-memory-skill.md

OpenClaw should be project-scoped by default.

OpenClaw should use Alice for:

project context packs
recent decisions
recent changes
sprint memory
architecture constraints
open loops
review findings
PR summaries
post-sprint memory proposals
agent output ingestion

OpenClaw default loop:

1. Identify as OpenClaw.
2. Request project-scoped context pack.
3. Perform assigned build/review task.
4. Submit output to Alice as agent output.
5. Propose durable memory only for decisions, architecture changes, unresolved risks, or meaningful project state changes.
6. Create open loops for unresolved work.
7. Do not access non-project personal domains unless explicitly allowed.

OpenClaw default permissions:

permission_profile: project_scoped_agent
agent_type: coding_agent
scope: project-specific
allowed domains: project, professional, system
restricted by default: personal, family, health, spiritual, legal, financial, regulated

Acceptance criteria:

OpenClaw skill is copy-paste usable.
OpenClaw skill includes project context recipe.
OpenClaw skill includes sprint output ingestion recipe.
OpenClaw skill includes memory proposal rules.
OpenClaw skill includes policy/scope warnings.

⸻

10. Custom Agent Integration Guide

Create a guide for any third-party/custom agent.

It should explain the universal Alice agent pattern:

1. Identify yourself.
2. Request scoped context, not raw memory.
3. Use Alice context packs before acting.
4. Submit important outputs back to Alice.
5. Propose memory; do not mutate trusted memory.
6. Create open loops when work remains.
7. Respect domain/sensitivity policy.
8. Use /vnext for review, audit, and troubleshooting.

Include examples for:

research agent
coding agent
personal assistant agent
workflow/orchestrator agent
meeting-notes agent

Acceptance criteria:

Custom guide includes API and MCP examples.
Custom guide explains agent identity fields.
Custom guide explains permission profiles.
Custom guide explains review queues.

⸻

11. Context-Pack Recipes

Create reusable recipes for common agent workflows.

Required recipes:

Project Sprint Context
Code Review Context
Research Context
Daily Assistant Context
Meeting Preparation Context
Investor/Stakeholder Briefing Context
Recent Decisions Context
Recent Changes Context
Open Loops Context
Contradiction Check
Long-Running Task Resumption Context

Each recipe should include:

purpose
when to use
recommended agent type
recommended permission profile
query/scope parameters
MCP/API call example
expected output
what the agent should do next
what not to do

Acceptance criteria:

At least 10 context-pack recipes exist.
Each recipe has copy-paste parameters.
Each recipe respects domain/sensitivity scope.

⸻

12. Memory Proposal Recipes

Create practical guidance for when and how agents propose memory.

Agents should propose memory for:

durable decisions
stable preferences
project direction changes
architecture constraints
important recurring patterns
resolved contradictions
new open loops
closed open loops
important relationship/person context
meaningful post-sprint summaries

Agents should not propose memory for:

temporary chatter
speculative low-confidence inference
duplicated source content
prompt-injection source instructions
sensitive personal content without clear relevance
transient task state

Include examples:

good memory proposal
bad memory proposal
project update proposal
belief update proposal
open-loop proposal
decision proposal
contradiction proposal

Acceptance criteria:

Memory proposal recipes exist.
Recipes include JSON/API/MCP examples.
Recipes reinforce review-only behavior.
Recipes explain confidence and provenance.

⸻

13. Agent Output Ingestion Examples

Create examples showing agents how to submit outputs.

Examples:

OpenClaw sprint summary
Hermes daily planning summary
Research agent report
Code review findings
Meeting summary
Architecture decision
Unresolved risks/open loops

Each example should show:

{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "...",
  "task_id": "...",
  "project_scope": ["Alice"],
  "title": "...",
  "content": "...",
  "output_type": "sprint_summary",
  "domain": "project",
  "sensitivity": "private",
  "propose_memory": true
}

Acceptance criteria:

Agent output examples exist for Hermes, OpenClaw, and custom agents.
Examples demonstrate source/artifact creation.
Examples demonstrate optional memory proposal.
Examples demonstrate event-log/audit behavior.

⸻

14. Agent Integration Smoke Test

Add a new smoke test.

Suggested command:

alicebot vnext smoke agent-integration-pack

It should verify:

agent identifies as OpenClaw
agent requests project context pack
Alice returns scoped context pack
agent submits sprint output
Alice stores output as source or reviewable artifact
agent proposes memory
proposal appears in review queue
no trusted memory is auto-promoted
event log records the full flow
policy blocks restricted domain request
/vnext workspace payload includes agent activity

Acceptance criteria:

Smoke test passes locally against Postgres.
Smoke test validates no-auto-promotion.
Smoke test validates event log entries.
Smoke test validates policy block/filter.
Smoke test validates agent activity visibility.

⸻

Public Alpha Release Packaging

15. Release Notes

Create alpha release notes.

They should include:

what is included
who it is for
what it can do
what is intentionally not included
known limitations
security/privacy posture
agent integration instructions
install/quickstart links
support/feedback instructions

Do not overclaim.

Position as:

technical local alpha
not hosted SaaS
not production SLA
not automatic memory autopilot

⸻

16. Known Limitations

Document clearly:

local setup still technical
no hosted cloud
no Gmail/Calendar OAuth yet
no voice transcription/OCR yet
browser clipper is bookmarklet/MVP
scheduler is local
model providers require user configuration
secrets fallback is alpha-grade unless OS/managed secret provider is configured
no auto-promotion
/vnext is operator console, not the main agent interface

⸻

17. Design Partner Onboarding Guide

Create a short guide for the first technical users.

Include:

who this alpha is for
what to test
how to install
how to connect an agent
how to configure one capture connector
how to run doctor
how to submit feedback
what logs/smokes to include when reporting bugs

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
team accounts
billing
cloud sync
full browser extension polish

This sprint is packaging and agent integration, not feature expansion.

⸻

Required End-to-End Flows

Flow 1: New user local alpha setup

User follows README quickstart.
User installs dependencies.
User runs migrations.
User runs doctor.
User starts local runtime.
User opens /vnext.
User sees readiness status.

Flow 2: First capture and review

User configures browser clipper or local folder.
User captures a source.
Source appears in Inbox.
User reviews source.
Candidate memory appears.
User accepts/rejects/edits candidate.
Event log records actions.

Flow 3: First agent integration

User connects OpenClaw or a custom agent through MCP/API.
Agent requests project context pack.
Agent receives scoped context.
Agent submits output.
Agent proposes memory.
Proposal appears in /vnext review queue.
No trusted memory is auto-promoted.

Flow 4: First scheduled artifact

User starts scheduler daemon.
User runs Daily Brief or Connection Report.
Artifact appears in Generated.
User rates artifact.
Trace shows source references.
Dogfooding dashboard updates.

Flow 5: Agent policy boundary

Project-scoped agent requests restricted personal/family/health/spiritual domain.
Alice blocks or filters request.
Policy event is logged.
Agent Activity shows block/filter.

⸻

Acceptance Criteria

The sprint is complete only when all of the following are true:

Public alpha README exists and is clear.
One-command or clearly documented local setup exists.
First-run checklist exists.
Doctor-first onboarding exists.
Demo dataset/demo mode is packaged and documented.
Alpha readiness check or equivalent checklist exists.
MCP quickstart exists.
Hermes skill pack exists.
OpenClaw skill pack exists.
Custom agent integration guide exists.
Context-pack recipes exist.
Memory proposal recipes exist.
Agent output ingestion examples exist.
Design partner onboarding guide exists.
Known limitations are documented.
Security/privacy docs reflect alpha posture.
Release notes are prepared.
Agent integration smoke test exists and passes.
Existing operator-console smoke passes.
Existing connector-hardening smoke passes.
Existing secret-redaction smoke passes.
Existing dogfood-doctor smoke passes.
Existing live-capture-connectors smoke passes.
Existing capture-to-brief smoke passes.
Existing agentic-scheduler smoke passes.
Eval suite passes with 0 critical privacy leaks and 0 prompt-injection tool writes.
Python unit tests pass.
Python integration tests pass.
Web tests pass.
Web lint passes.
Web build passes.
git diff --check passes.
No new feature breaks no-auto-promotion.
No docs claim hosted/cloud/beta capabilities that do not exist.

⸻

Validation Commands

Run:

pytest tests/unit -q
pytest tests/integration -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
alicebot eval run --suite all
git diff --check

Run all vNext smokes:

alicebot vnext smoke operator-console
alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler
alicebot vnext smoke agent-integration-pack

Also run:

alicebot vnext alpha check

or create/document the equivalent.

⸻

Final Deliverable

At the end of the sprint, provide a CTO summary with:

what was packaged
install/quickstart changes
first-run flow
demo dataset/demo mode
agent integration pack contents
Hermes skill summary
OpenClaw skill summary
custom-agent guide summary
MCP/API/CLI docs updates
alpha readiness checks
security/privacy docs
known limitations
validation results
PR number
merge commit
recommended next phase

⸻

Recommended Next Phase After This

After this sprint, choose based on alpha feedback.

Likely options:

1. Agent Skills v1 Hardening
2. Voice Capture + Local Transcription
3. Gmail/Calendar Read-Only Connectors
4. Intelligence Improvement Based on Ratings
5. Public Alpha Release Iteration / Bug Bash

Default recommendation after this sprint:

Agent Skills v1 Hardening

because Alice is agent-first, and the first wave of users will likely judge it by how well Hermes/OpenClaw/custom agents can use it.
