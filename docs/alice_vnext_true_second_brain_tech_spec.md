# Alice vNext Technical Specification

**Version:** v2.0 Draft 1  
**Product Codename:** Alice Brain / True Second Brain  
**Primary Goal:** Expand Alice from a local-first agent memory layer into a multi-layer memory infrastructure platform for humans and agents.

---

## 1. Executive Summary

Alice vNext turns Alice into a **local-first memory operating system** with several product layers:

1. **Alice Core** — deterministic memory kernel, provenance, corrections, temporal state, retrieval, context packs, graph, MCP/API.
2. **Alice Brain** — user-facing true second brain: daily briefs, weekly synthesis, connection discovery, contradiction detection, thesis tracking, open loops, and knowledge distillation.
3. **Alice Agent Memory** — memory and continuity layer for autonomous agents, exposed via MCP/API/CLI.
4. **Alice Connectors** — capture/import ecosystem: files, Obsidian, Markdown, ChatGPT exports, Telegram, browser, Readwise, Gmail, Calendar, voice, PDFs, screenshots, and future integrations.
5. **Alice UI** — local desktop/web interface for inbox, memory review, daily brief, graph, projects, people, timeline, queue, and generated artifacts.

Alice must not become a generic notes app, Obsidian clone, or chatbot with memory. The core product is **private, correctable, inspectable continuity**.

Alice’s central promise:

> Alice remembers your life and work with provenance, connects the dots across time, challenges contradictions, and gives humans and agents the right context at the right moment.

---

## 2. Product Thesis

Most second brain systems fail because they are optimized for input, not output. Users capture articles, notes, voice memos, messages, and ideas, but the system rarely returns useful synthesis unprompted.

Alice vNext solves this by making memory active:

- It captures raw evidence.
- It preserves provenance.
- It extracts claims, people, projects, concepts, beliefs, decisions, and open loops.
- It builds a memory graph and memory trees.
- It generates daily/weekly/monthly artifacts.
- It detects contradictions and recurring patterns.
- It tracks how the user’s beliefs evolve over time.
- It lets the user correct, approve, reject, or supersede memories.
- It exposes compact context packs to agents.

Alice does **not** silently rewrite the user’s memory. Alice proposes, explains, logs, and asks for review when appropriate.

---

## 3. Goals and Non-Goals

## 3.1 Goals

### Core Goals

- Build a deterministic memory kernel with append-only event logging.
- Preserve raw evidence before summarization or transformation.
- Support provenance-aware memory retrieval.
- Support correction, supersession, and temporal validity.
- Support memory review and user approval workflows.
- Support generated artifacts: briefs, reports, updates, connection maps, distillations.
- Support human memory and agent memory from the same core primitives.
- Support local-first operation.
- Support exportable, open formats.
- Support evaluation harnesses to prove memory quality.

### Product Goals

- Give the user a daily morning brief.
- Give the user a weekly synthesis.
- Surface non-obvious connections between new and old information.
- Detect contradictions between current notes and older beliefs/theses.
- Track project state automatically.
- Track open loops and unresolved commitments.
- Track people and relationship context, with strict privacy controls.
- Track beliefs/theses and how they evolve over time.
- Provide an asynchronous queue where the user can ask Alice to research, synthesize, analyze, compare, or draft outputs.
- Provide a generated-artifacts area where Alice outputs reviewable work.

### Developer / Agent Goals

- Provide clear API, CLI, and MCP surfaces.
- Provide modular workers that agents can implement independently.
- Provide strict acceptance criteria and test coverage.
- Keep architecture clean enough for open-source contributors.

## 3.2 Non-Goals

Alice vNext is not:

- A generic chat app.
- A Notion clone.
- An Obsidian clone.
- A cloud-only personal assistant.
- A fully autonomous agent allowed to rewrite user memory without review.
- A trading system.
- A financial/legal/medical advisor.
- A black-box recommendation engine.
- A social network.

---

## 4. Guiding Principles

1. **Raw evidence first.** Never summarize before preserving the original.
2. **Provenance always.** Every memory must answer: where did this come from?
3. **Append-only by default.** Do not mutate history; add revisions and supersessions.
4. **User sovereignty.** The user can inspect, correct, reject, delete, export, and explain memories.
5. **Generated is not truth.** Generated artifacts are outputs, not automatically durable memory.
6. **Local-first.** Private memory should work without cloud dependency.
7. **Permissioned domains.** Work, family, health, spiritual, legal, financial, and confidential contexts must be separable.
8. **Temporal reasoning.** Alice must know what was true, believed, active, stale, or superseded at a given time.
9. **Agent-readable context.** Agents should receive compact context packs, not raw memory dumps.
10. **Eval-driven.** Memory claims must be tested with benchmarks, not just demos.

---

## 5. Product Layers

```text
Alice
├── Alice Core
│   ├── Event log
│   ├── Raw archive
│   ├── Memory objects
│   ├── Memory revisions
│   ├── Provenance
│   ├── Temporal state
│   ├── Graph edges
│   ├── Retrieval router
│   ├── Context compiler
│   ├── Correction/supersession engine
│   ├── Policy engine
│   └── Eval harness
│
├── Alice Brain
│   ├── Daily briefs
│   ├── Weekly synthesis
│   ├── Monthly distillation
│   ├── Connection finder
│   ├── Contradiction finder
│   ├── Thesis tracker
│   ├── Open loop tracker
│   ├── Project auto-updater
│   ├── People memory
│   ├── Life domains
│   └── Generated artifacts
│
├── Alice Agent Memory
│   ├── MCP server
│   ├── CLI
│   ├── Agent context packs
│   ├── Agent run memory
│   ├── Resumption briefs
│   └── Tool-call memory
│
├── Alice Connectors
│   ├── Files / folders
│   ├── Obsidian / Markdown
│   ├── ChatGPT export
│   ├── Telegram
│   ├── Browser extension
│   ├── Readwise / Kindle
│   ├── Gmail
│   ├── Calendar
│   ├── Voice / Whisper-compatible transcription
│   ├── PDFs / DOCX / CSV / screenshots
│   └── Future connectors
│
└── Alice UI
    ├── Inbox
    ├── Ask Alice
    ├── Daily brief
    ├── Weekly synthesis
    ├── Memory review
    ├── Queue
    ├── Generated artifacts
    ├── Projects
    ├── People
    ├── Beliefs / theses
    ├── Timeline
    ├── Graph
    ├── Open loops
    └── Settings / privacy
```

---

## 6. High-Level System Architecture

```text
Capture Sources
  ├── Manual notes
  ├── Files
  ├── Obsidian / Markdown
  ├── ChatGPT exports
  ├── Telegram
  ├── Browser clips
  ├── Email / calendar
  ├── Voice notes
  └── Readwise / highlights
        ↓
Connector Layer
        ↓
Raw Archive + Event Log
        ↓
Normalizer Workers
  ├── Parse
  ├── Clean
  ├── Chunk
  ├── Extract metadata
  ├── Extract entities
  ├── Extract claims
  ├── Classify domain/sensitivity
  └── Embed
        ↓
Memory Kernel
  ├── Memory objects
  ├── Revisions
  ├── Provenance
  ├── Temporal validity
  ├── Graph edges
  ├── Beliefs/theses
  ├── Decisions
  ├── Open loops
  └── Project state
        ↓
Retrieval Router + Context Compiler
        ↓
Alice Brain Workers
  ├── Daily brief
  ├── Weekly synthesis
  ├── Connection finder
  ├── Contradiction finder
  ├── Project updater
  ├── Thesis tracker
  ├── Distillation engine
  └── Queue processor
        ↓
Generated Artifacts + Review Queue
        ↓
User Review / Promotion / Correction
        ↓
Memory Revisions + Event Log
```

---

## 7. Storage Strategy

Alice should support two deployment profiles.

## 7.1 Local Simple Profile

For normal users and open-source adoption.

- SQLite as primary database.
- Local file archive for raw evidence.
- Optional SQLite vector extension or local vector index.
- Markdown export/import.
- Desktop app can bundle everything.

## 7.2 Power / Server Profile

For advanced users, agent teams, and heavy workloads.

- Postgres primary database.
- pgvector for embeddings.
- Local filesystem or S3-compatible object store for raw evidence.
- Optional Redis queue for workers.
- Optional Docker Compose deployment.

## 7.3 Storage Abstraction Requirement

All persistence must go through repositories/interfaces so SQLite and Postgres can share business logic.

Required interfaces:

```text
EventStore
SourceStore
MemoryStore
RevisionStore
EmbeddingStore
GraphStore
ArtifactStore
TaskQueueStore
PolicyStore
EvalStore
```

---

## 8. Memory Model

Alice memory is not one table. It is a layered model.

## 8.1 Memory Classes

### L0 — Raw Evidence Memory

Immutable source archive.

Examples:

- PDF
- email
- voice transcript
- screenshot
- webpage
- chat message
- meeting transcript
- note
- calendar event

### L1 — Episode Memory

What happened.

Examples:

- “User had a call with an investor about Lugano.”
- “User recorded a voice note about Alice becoming a second brain.”
- “User read an article about self-writing Obsidian vaults.”

### L2 — Semantic Memory

What the system understands as concepts, claims, entities, and knowledge.

Examples:

- “TEE-based AI compute is relevant to regulated industries.”
- “Alice should remain local-first.”

### L3 — Project Memory

Project-specific state.

Examples:

- Current state
- Decisions
- Open questions
- Roadmap
- Risks
- People
- Timeline

### L4 — Belief / Thesis Memory

Evolving hypotheses and opinions.

Examples:

- “AI agents need private, correctable continuity infrastructure.”
- “The winning Alice architecture is memory substrate first, app second.”

### L5 — People / Relationship Memory

People, relationships, communication preferences, history, promises, and relevant context.

### L6 — Self / Life Memory

Personal, family, health, spiritual, emotional, financial, learning, and values-related memory.

---

## 9. Domain and Sensitivity Model

Every source, memory, artifact, and retrieval request must include domain and sensitivity metadata.

## 9.1 Domains

```text
professional
personal
family
health
spiritual
financial
legal
learning
relationship
project
agent_run
system
unknown
```

## 9.2 Sensitivity Levels

```text
public
internal
private
confidential
highly_sensitive
sacred
regulated
unknown
```

## 9.3 Policy Requirements

- User can set default domain and sensitivity for each connector.
- Retrieval must respect domain/sensitivity filters.
- Generated artifacts inherit the highest sensitivity of their sources.
- Agent context packs must not include restricted memories unless explicitly allowed.
- Work outputs should not include family/spiritual/health content unless the user explicitly requests it.
- Prompt-injection content from sources must never override system/user policies.

---

## 10. Core Data Model

This is a conceptual schema. Agents may implement with SQLAlchemy/Prisma/Drizzle/etc. depending on the existing repo, but the entities and relationships should remain intact.

## 10.1 sources

Represents raw evidence.

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  title TEXT,
  author TEXT,
  uri TEXT,
  raw_path TEXT,
  content_hash TEXT NOT NULL,
  captured_at TIMESTAMP NOT NULL,
  source_created_at TIMESTAMP,
  source_modified_at TIMESTAMP,
  connector_name TEXT,
  external_id TEXT,
  domain TEXT NOT NULL DEFAULT 'unknown',
  sensitivity TEXT NOT NULL DEFAULT 'unknown',
  metadata_json JSON NOT NULL DEFAULT '{}',
  deleted_at TIMESTAMP
);
```

## 10.2 source_chunks

```sql
CREATE TABLE source_chunks (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  token_count INTEGER,
  metadata_json JSON NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL
);
```

## 10.3 memories

Canonical durable memory object.

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  memory_type TEXT NOT NULL,
  title TEXT,
  canonical_text TEXT NOT NULL,
  summary TEXT,
  status TEXT NOT NULL DEFAULT 'candidate',
  confidence REAL NOT NULL DEFAULT 0.5,
  domain TEXT NOT NULL DEFAULT 'unknown',
  sensitivity TEXT NOT NULL DEFAULT 'unknown',
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  first_seen_at TIMESTAMP NOT NULL,
  last_seen_at TIMESTAMP NOT NULL,
  last_reviewed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

### memory_type values

```text
episode
semantic
project_state
decision
belief
thesis
person
relationship
open_loop
preference
value
pattern
contradiction
question
answer
artifact_summary
agent_run
system
```

### status values

```text
candidate
active
accepted
rejected
superseded
archived
needs_review
private_only
```

## 10.4 memory_revisions

Append-only revisions.

```sql
CREATE TABLE memory_revisions (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL REFERENCES memories(id),
  revision_number INTEGER NOT NULL,
  revision_type TEXT NOT NULL,
  text_before TEXT,
  text_after TEXT NOT NULL,
  reason TEXT,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  created_at TIMESTAMP NOT NULL,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

### revision_type values

```text
created
edited
corrected
promoted
rejected
superseded
merged
split
archived
restored
```

## 10.5 provenance_links

Links memories/artifacts to source chunks.

```sql
CREATE TABLE provenance_links (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  source_id TEXT REFERENCES sources(id),
  source_chunk_id TEXT REFERENCES source_chunks(id),
  quote TEXT,
  evidence_role TEXT NOT NULL,
  confidence REAL DEFAULT 0.5,
  created_at TIMESTAMP NOT NULL
);
```

### evidence_role values

```text
supports
contradicts
mentions
inferred_from
quoted_from
summarizes
background
```

## 10.6 graph_edges

Typed relationships between memories, sources, artifacts, people, and projects.

```sql
CREATE TABLE graph_edges (
  id TEXT PRIMARY KEY,
  from_type TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_type TEXT NOT NULL,
  to_id TEXT NOT NULL,
  edge_type TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  explanation TEXT,
  created_by TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

### edge_type values

```text
supports
contradicts
caused_by
influenced_by
similar_to
supersedes
depends_on
mentions
asks
answers
reframes
predicts
invalidates
reopens
same_problem
same_principle
cross_domain_pattern
old_idea_now_relevant
belief_reinforcement
belief_challenge
owned_by
belongs_to_project
related_to_person
```

## 10.7 projects

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active',
  description TEXT,
  current_state TEXT,
  domain TEXT DEFAULT 'professional',
  sensitivity TEXT DEFAULT 'private',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

## 10.8 people

```sql
CREATE TABLE people (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  aliases_json JSON NOT NULL DEFAULT '[]',
  relationship_type TEXT,
  organization TEXT,
  sensitivity TEXT DEFAULT 'private',
  notes TEXT,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

## 10.9 beliefs

Beliefs may be implemented as a specialized memory_type or a separate table. Use a separate table if richer tracking is needed.

```sql
CREATE TABLE beliefs (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL REFERENCES memories(id),
  claim TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  confidence REAL NOT NULL DEFAULT 0.5,
  first_seen_at TIMESTAMP NOT NULL,
  last_reinforced_at TIMESTAMP,
  last_challenged_at TIMESTAMP,
  superseded_by TEXT REFERENCES beliefs(id),
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

## 10.10 open_loops

```sql
CREATE TABLE open_loops (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  priority TEXT DEFAULT 'normal',
  due_at TIMESTAMP,
  project_id TEXT REFERENCES projects(id),
  person_id TEXT REFERENCES people(id),
  source_id TEXT REFERENCES sources(id),
  memory_id TEXT REFERENCES memories(id),
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  closed_at TIMESTAMP,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

## 10.11 generated_artifacts

```sql
CREATE TABLE generated_artifacts (
  id TEXT PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  title TEXT NOT NULL,
  content_markdown TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  domain TEXT NOT NULL DEFAULT 'unknown',
  sensitivity TEXT NOT NULL DEFAULT 'unknown',
  generated_by TEXT NOT NULL,
  prompt_hash TEXT,
  model_info_json JSON NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL,
  reviewed_at TIMESTAMP,
  promoted_at TIMESTAMP,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

### artifact_type values

```text
daily_brief
weekly_synthesis
monthly_distillation
connection_report
contradiction_report
project_update
thesis_report
open_loop_report
queue_result
research_brief
draft
context_pack
agent_resumption_brief
system_report
```

### artifact status values

```text
draft
needs_review
reviewed
accepted
rejected
promoted_to_memory
superseded
archived
```

## 10.12 task_queue

```sql
CREATE TABLE task_queue (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  task_type TEXT NOT NULL,
  instructions TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  requested_by TEXT NOT NULL,
  scope_json JSON NOT NULL DEFAULT '{}',
  allowed_sources_json JSON NOT NULL DEFAULT '[]',
  domain TEXT DEFAULT 'unknown',
  sensitivity TEXT DEFAULT 'unknown',
  write_policy TEXT NOT NULL DEFAULT 'proposal_only',
  scheduled_for TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  failed_at TIMESTAMP,
  error_message TEXT,
  output_artifact_id TEXT REFERENCES generated_artifacts(id),
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  metadata_json JSON NOT NULL DEFAULT '{}'
);
```

### task_type values

```text
research
synthesize
analyze
compare
draft
summarize
connect
find_contradictions
update_project
create_context_pack
review_memory
```

### write_policy values

```text
proposal_only
auto_generate_artifact
requires_review_before_write
admin_only
```

## 10.13 event_log

Append-only system event log.

```sql
CREATE TABLE event_log (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  target_type TEXT,
  target_id TEXT,
  occurred_at TIMESTAMP NOT NULL,
  payload_json JSON NOT NULL DEFAULT '{}',
  trace_id TEXT,
  run_id TEXT,
  integrity_hash TEXT
);
```

### event_type examples

```text
source.captured
source.parsed
source.chunked
source.embedded
memory.candidate_created
memory.promoted
memory.corrected
memory.superseded
memory.rejected
artifact.generated
artifact.reviewed
artifact.promoted
graph.edge_created
graph.edge_rejected
retrieval.query_received
retrieval.context_pack_created
task.created
task.started
task.completed
task.failed
policy.blocked
connector.sync_started
connector.sync_completed
connector.sync_failed
```

---

## 11. Memory Lifecycle

```text
1. Capture
   Raw input arrives from connector or manual upload.

2. Archive
   Raw evidence is stored with hash, metadata, domain, sensitivity, connector, and timestamp.

3. Parse / Normalize
   Extract text, metadata, chunks, language, entities, claims, dates, people, projects.

4. Candidate Generation
   Alice proposes candidate memories, open loops, beliefs, graph edges, and project updates.

5. Review / Policy Decision
   Depending on sensitivity and confidence, candidate is auto-accepted, queued for review, or rejected.

6. Promotion
   Accepted candidates become durable memory objects.

7. Retrieval
   Memories participate in search, graph traversal, context packs, briefs, and agent recall.

8. Correction / Supersession
   User or trusted workflow corrects memory; Alice records revision rather than overwriting history.

9. Distillation
   Repeated patterns and related notes are compressed into higher-level knowledge artifacts.

10. Export / Archive
   User can export or archive memory while preserving provenance.
```

---

## 12. Retrieval Architecture

Alice must not rely on vector search alone. Use a retrieval router.

## 12.1 Retrieval Methods

1. **Keyword/BM25** — exact phrase, names, IDs, terms.
2. **Vector semantic search** — meaning similarity.
3. **Graph traversal** — relationships, projects, people, beliefs, contradictions.
4. **Temporal retrieval** — what changed over time, state at a specific date.
5. **Belief/thesis retrieval** — active, challenged, superseded beliefs.
6. **Open-loop retrieval** — unresolved tasks/questions/promises.
7. **Project retrieval** — project-specific state and timeline.
8. **Artifact retrieval** — previous briefs, syntheses, reports.
9. **Raw evidence retrieval** — only when source-level grounding is needed.

## 12.2 Query Classification

Each user/agent query must be classified before retrieval.

```json
{
  "query_type": "strategic_synthesis | exact_recall | temporal_recall | contradiction_check | project_status | people_context | open_loop_review | draft_generation | agent_context",
  "domains": ["professional", "project"],
  "projects": ["Alice"],
  "people": [],
  "time_window": "all_time_with_recent_boost",
  "sensitivity_allowed": ["public", "internal", "private"],
  "requires_sources": true,
  "requires_contradictions": true,
  "requires_raw_evidence": false
}
```

## 12.3 Context Compiler

The Context Compiler produces a compact context pack.

```text
Context Pack
├── Query interpretation
├── Current known state
├── Relevant memories
├── Relevant beliefs/theses
├── Relevant decisions
├── Relevant open loops
├── Supporting evidence
├── Contradicting evidence
├── Recent changes
├── Historical timeline
├── Missing information
└── Source references
```

## 12.4 Context Pack Requirements

- Must include source/provenance references where available.
- Must distinguish fact, inference, and generated synthesis.
- Must include contradictions for strategic queries by default.
- Must not exceed configured token budget.
- Must respect domain/sensitivity policy.
- Must include trace metadata for eval/debugging.

---

## 13. Alice Brain Workflows

## 13.1 Daily Brief Generator

### Trigger

- Default: every morning, user-configurable.
- Manual trigger from UI/CLI/API.

### Inputs

- Previous daily brief.
- Recent sources from last 24–48 hours.
- Active projects.
- Open loops from last 7–14 days.
- Calendar/events if connector enabled.
- Recent generated artifacts.
- High-priority beliefs/theses.

### Output

`generated_artifacts.artifact_type = daily_brief`

### Required Sections

```text
1. Executive Summary
2. Project Status
3. Open Loops
4. New Connections
5. Contradictions / Tensions
6. Emerging Pattern
7. Suggested Focus
8. Optional: People to Follow Up With
9. Sources Used
```

### Acceptance Criteria

- Produces a dated artifact.
- Includes at least one source reference per factual claim where possible.
- Separates facts from inferences.
- Does not include restricted domains unless allowed.
- Logs `artifact.generated` event.
- Adds candidate open loops if discovered.

---

## 13.2 Weekly Synthesis

### Trigger

- Weekly schedule, user-configurable.
- Manual trigger.

### Inputs

- All sources, memories, artifacts, and open loops from last 7 days.
- Active project changes.
- Belief updates.
- Previous weekly synthesis.

### Output Sections

```text
1. What moved forward
2. What did not move
3. Recurring patterns
4. Contradictions or changed assumptions
5. Emerging thesis
6. Highest-leverage next actions
7. What to stop doing / thinking about
8. Sources Used
```

### Acceptance Criteria

- Must produce at least 3 project/person/concept links where available.
- Must identify at least 1 pattern or explicitly state no strong pattern found.
- Must produce candidate memories for meaningful new insights.
- Must not auto-promote candidate memories without policy approval.

---

## 13.3 Connection Finder

### Trigger

- Weekly schedule.
- Manual trigger.
- After large import.

### Inputs

- New/modified notes from time window.
- Older memory corpus.
- Graph edges.
- Beliefs/theses.

### Connection Types

```text
same_problem
same_principle
cross_domain_pattern
contradiction
supporting_evidence
weak_signal
recurring_theme
forgotten_relevant_note
belief_reinforcement
belief_challenge
old_idea_now_relevant
```

### Output

`connection_report` artifact and candidate graph edges.

### Required Fields Per Connection

```json
{
  "source_item": "...",
  "connected_item": "...",
  "connection_type": "cross_domain_pattern",
  "explanation": "...",
  "why_it_matters": "...",
  "confidence": 0.74,
  "provenance": ["source_chunk_id_1", "source_chunk_id_2"]
}
```

### Acceptance Criteria

- Must avoid obvious/low-value connections.
- Must include confidence and explanation.
- Must write graph edges as candidates unless high-confidence auto-edge policy is enabled.
- Must log all candidate edges.

---

## 13.4 Contradiction Finder

### Trigger

- Daily for new high-signal memories.
- Weekly full pass.
- Manual query: “What contradicts this?”

### Inputs

- New claims.
- Active beliefs/theses.
- Project assumptions.
- Decisions.
- Prior generated artifacts.

### Output

`contradiction_report` artifact and candidate contradiction edges.

### Contradiction Types

```text
factual_conflict
belief_conflict
strategy_conflict
timeline_conflict
priority_conflict
source_conflict
self_inconsistency
```

### Acceptance Criteria

- Must quote or cite both sides from source/provenance where possible.
- Must distinguish contradiction from nuance.
- Must provide recommended action: ignore, review, update belief, supersede memory, request more info.
- Must not overwrite beliefs automatically.

---

## 13.5 Thesis Tracker

### Purpose

Track emerging and active beliefs/theses over time.

### Trigger

- Weekly synthesis.
- New repeated pattern detected.
- User asks about a thesis.

### Outputs

- New or updated `belief` / `thesis` memory.
- `thesis_report` artifact.

### Required Thesis Fields

```json
{
  "claim": "...",
  "status": "emerging | active | challenged | superseded | retired",
  "confidence": 0.0,
  "supporting_sources": [],
  "contradicting_sources": [],
  "first_seen_at": "...",
  "last_reinforced_at": "...",
  "last_challenged_at": "...",
  "related_projects": [],
  "related_people": [],
  "next_question": "..."
}
```

---

## 13.6 Open Loop Tracker

### Purpose

Identify and track unresolved tasks, questions, promises, waiting items, and tensions.

### Open Loop Types

```text
task
promise
question
waiting_on_person
decision_needed
follow_up
research_gap
emotional_tension
project_blocker
```

### Acceptance Criteria

- Must capture source and date.
- Must mark owner where possible.
- Must allow snooze/close/edit from UI.
- Must appear in daily/weekly briefs.
- Must support project/person/domain filtering.

---

## 13.7 Project Auto-Updater

### Purpose

Keep project state current from new notes, decisions, files, conversations, and artifacts.

### Rule

Alice must create a **Project Update Candidate**, not silently rewrite project truth.

### Candidate Format

```text
Project: Alice
Change Detected: User decided Alice should become several layers/products.
Why It Matters: This expands Alice from agent memory into human/agent memory infrastructure.
Suggested Updates:
- current_state.md
- roadmap.md
- open_questions.md
Sources:
- conversation/import/source references
Confidence: 0.91
Actions: Accept / Edit / Reject
```

### Acceptance Criteria

- Candidate update visible in UI.
- Accepting creates memory revisions and event log entries.
- Rejecting logs rejection and prevents repeated suggestion unless new evidence appears.

---

## 13.8 Knowledge Distillation Engine

### Trigger

- Monthly.
- Manual trigger by project/domain.
- After large import.

### Purpose

Compress clusters of related raw notes and memories into durable insight documents.

### Output Sections

```text
1. Key insights
2. What changed
3. What is now clearer
4. What remains uncertain
5. Contradictions
6. Important source notes
7. New candidate beliefs
8. Recommended next research
```

### Acceptance Criteria

- Must link to underlying memories/sources.
- Must not delete or replace raw notes.
- Must generate candidate higher-level memories.
- Must be reviewable before promotion.

---

## 13.9 Queue Processor

### Purpose

Allow asynchronous user tasks.

### User Examples

```text
SYNTHESIZE all notes on Alice memory architecture.
ANALYZE contradictions in my Lugano GTM thinking.
DRAFT a README based on these project notes.
COMPARE Alice against OpenHuman-style products.
FIND old ideas that are relevant to this new note.
```

### Processing Flow

```text
task.created
  ↓
policy check
  ↓
context pack creation
  ↓
model/tool execution
  ↓
artifact generated
  ↓
needs review or completed
  ↓
event log
```

### Acceptance Criteria

- Supports pending/running/completed/failed/needs_review states.
- Produces generated artifact.
- Logs trace and sources.
- Fails safely with useful error message.

---

## 14. Generated Artifacts

Generated artifacts are first-class records.

## 14.1 Artifact Principles

- Generated artifacts are not automatically memory.
- Artifacts can be promoted to memory after review.
- Artifacts inherit sensitivity from inputs.
- Artifacts must have generation trace metadata.
- Artifacts should be exportable as Markdown.

## 14.2 Artifact Review Actions

```text
accept
reject
edit
promote_to_memory
create_open_loop
create_project_update
create_belief
create_graph_edge
archive
```

## 14.3 Artifact File Export Layout

When exporting to Markdown/Obsidian:

```text
/generated/
  daily_briefs/
    2026-05-10-daily-brief.md
  weekly_synthesis/
    2026-W19-weekly-synthesis.md
  connection_reports/
  contradiction_reports/
  project_updates/
  thesis_reports/
  distillations/
```

---

## 15. ALICE.md / Brain Charter

Alice needs an equivalent of a root constitution file. This can be stored as a database profile and exported as `ALICE.md`.

## 15.1 Purpose

The Brain Charter tells Alice who the user is, what matters, what rules to follow, and how autonomous operations are constrained.

## 15.2 Template

```markdown
# ALICE.md — Brain Charter

## Owner
Name:
Primary roles:
Current focus areas:
Long-term goals:

## Memory Philosophy
What should Alice remember?
What should Alice ignore?
What should require review?

## Life Domains
Professional:
Personal:
Family:
Health:
Spiritual:
Financial:
Legal:
Learning:

## Active Projects
- Project name: status, goal, next milestone

## Communication Style
How should Alice write to me?
What tone should Alice use?
What should Alice avoid?

## What Matters Most Right Now
Current priorities:
Current constraints:
Current risks:

## Autonomous Operation Rules
- Never delete raw evidence without explicit user instruction.
- Never silently promote generated content into durable memory when confidence/sensitivity requires review.
- Always preserve provenance.
- Always log writes.
- Always distinguish fact, inference, and suggestion.
- Do not mix family/health/spiritual memories into work outputs unless explicitly requested.
- When uncertain, create a review item instead of acting silently.

## Quality Standard
Good Alice output should be:
- specific
- source-grounded
- concise first, expandable second
- honest about uncertainty
- willing to challenge assumptions
- action-oriented when appropriate
```

---

## 16. API Specification

Base path: `/api/v1`

## 16.1 Sources

```http
POST /sources
GET /sources
GET /sources/{id}
POST /sources/{id}/parse
POST /sources/{id}/embed
DELETE /sources/{id}
```

## 16.2 Memories

```http
POST /memories
GET /memories
GET /memories/{id}
POST /memories/{id}/promote
POST /memories/{id}/correct
POST /memories/{id}/supersede
POST /memories/{id}/reject
GET /memories/{id}/revisions
GET /memories/{id}/provenance
```

## 16.3 Retrieval

```http
POST /retrieve
POST /context-packs
GET /context-packs/{id}
POST /ask
```

### `/retrieve` request

```json
{
  "query": "What am I missing about Alice becoming a second brain?",
  "scope": {
    "projects": ["Alice"],
    "domains": ["professional", "project"],
    "time_window": "all"
  },
  "options": {
    "include_contradictions": true,
    "include_sources": true,
    "max_tokens": 8000
  }
}
```

## 16.4 Artifacts

```http
POST /artifacts/generate/daily-brief
POST /artifacts/generate/weekly-synthesis
POST /artifacts/generate/connections
POST /artifacts/generate/contradictions
POST /artifacts/generate/distillation
GET /artifacts
GET /artifacts/{id}
POST /artifacts/{id}/review
POST /artifacts/{id}/promote
POST /artifacts/{id}/archive
```

## 16.5 Queue

```http
POST /queue/tasks
GET /queue/tasks
GET /queue/tasks/{id}
POST /queue/tasks/{id}/cancel
POST /queue/tasks/{id}/retry
POST /queue/tasks/{id}/approve
```

## 16.6 Projects

```http
POST /projects
GET /projects
GET /projects/{id}
POST /projects/{id}/update-candidate
POST /projects/{id}/accept-update
GET /projects/{id}/timeline
GET /projects/{id}/open-loops
GET /projects/{id}/beliefs
```

## 16.7 Open Loops

```http
POST /open-loops
GET /open-loops
GET /open-loops/{id}
POST /open-loops/{id}/close
POST /open-loops/{id}/snooze
POST /open-loops/{id}/edit
```

## 16.8 Graph

```http
GET /graph/neighborhood
POST /graph/edges
POST /graph/edges/{id}/accept
POST /graph/edges/{id}/reject
GET /graph/search
```

## 16.9 Settings / Policy

```http
GET /settings/brain-charter
PUT /settings/brain-charter
GET /settings/privacy
PUT /settings/privacy
GET /settings/connectors
PUT /settings/connectors/{name}
```

---

## 17. MCP Tool Specification

Alice must expose MCP tools for agent use.

## 17.1 Required MCP Tools

```text
alice_capture
alice_recall
alice_context_pack
alice_recent_decisions
alice_recent_changes
alice_open_loops
alice_memory_review
alice_memory_correct
alice_generate_daily_brief
alice_generate_weekly_synthesis
alice_find_connections
alice_find_contradictions
alice_project_status
alice_queue_task
alice_artifact_get
alice_artifact_promote
```

## 17.2 alice_context_pack

### Input

```json
{
  "query": "Build next sprint plan for Alice Brain",
  "project": "Alice",
  "domains": ["professional", "project"],
  "include_contradictions": true,
  "include_open_loops": true,
  "max_tokens": 12000
}
```

### Output

```json
{
  "context_pack_id": "...",
  "summary": "...",
  "relevant_memories": [],
  "decisions": [],
  "open_loops": [],
  "beliefs": [],
  "contradictions": [],
  "sources": [],
  "warnings": [],
  "trace_id": "..."
}
```

## 17.3 MCP Safety Requirements

- MCP tools must respect sensitivity/domain permissions.
- MCP tools must not expose raw sensitive data unless authorized.
- MCP write tools must use proposal/review flows unless explicitly configured.
- Every MCP call must be logged.

---

## 18. CLI Specification

Alice CLI should remain power-user friendly.

## 18.1 Commands

```bash
alice init
alice status
alice capture <file|text>
alice recall "query"
alice context-pack "query" --project Alice
alice daily-brief --generate
alice weekly-synthesis --generate
alice connections --since 7d
alice contradictions --project Alice
alice queue add --type synthesize --title "Alice v2 spec" --instructions "..."
alice queue list
alice artifact list
alice artifact show <id>
alice artifact promote <id>
alice memory review
alice memory correct <id>
alice open-loops list
alice export markdown
alice eval run
```

---

## 19. UI Specification

## 19.1 Primary Navigation

```text
Home
Inbox
Ask Alice
Daily Brief
Weekly Synthesis
Queue
Generated
Memory Review
Projects
People
Beliefs
Open Loops
Timeline
Graph
Settings
```

## 19.2 Home Dashboard

Must show:

- Today’s brief summary.
- New items needing review.
- Open loops due soon.
- Active projects status.
- Recent connections found.
- Contradictions needing attention.
- Queue status.

## 19.3 Inbox

Shows unprocessed captures and candidate memories.

Actions:

```text
accept
edit
reject
promote
assign_project
set_domain
set_sensitivity
create_open_loop
```

## 19.4 Ask Alice

Chat/search interface that uses context packs.

Must show:

- Answer.
- Sources/provenance.
- Memories used.
- Contradictions considered.
- “Why did Alice say this?” explanation.
- Option to save answer as artifact.

## 19.5 Memory Review

Queue of candidate memories and suggested updates.

Cards should show:

```text
Candidate memory
Why Alice thinks this matters
Sources
Confidence
Domain/sensitivity
Actions: Accept / Edit / Reject / Private / Merge / Supersede
```

## 19.6 Generated Artifacts

List and detail views for briefs, reports, syntheses, distillations.

Actions:

```text
review
edit
promote to memory
create tasks
create project update
archive
export markdown
```

## 19.7 Projects

Each project page:

```text
current state
latest updates
decisions
open loops
people
beliefs/theses
files/sources
connection map
timeline
generated reports
```

## 19.8 Beliefs / Theses

Shows active, emerging, challenged, superseded beliefs.

Each belief page:

```text
claim
status
confidence
supporting evidence
contradicting evidence
history
related projects
related people
candidate updates
```

## 19.9 Graph

Graph UI must support:

- Filter by project/domain/sensitivity.
- Show edge types.
- Click node to inspect sources.
- Toggle raw/generated/memory nodes.
- Show contradictions and supersessions.

---

## 20. Connectors

## 20.1 Connector Interface

Each connector implements:

```text
connect()
sync()
list_items()
fetch_item()
normalize_item()
classify_default_domain()
classify_default_sensitivity()
get_cursor()
set_cursor()
disconnect()
```

## 20.2 Connector Metadata

```json
{
  "connector_name": "telegram",
  "external_id": "...",
  "sync_cursor": "...",
  "captured_at": "...",
  "source_created_at": "...",
  "author": "...",
  "default_domain": "personal",
  "default_sensitivity": "private"
}
```

## 20.3 Phase 1 Connectors

- Local folder watcher.
- Markdown/Obsidian import/export.
- ChatGPT export import.
- Manual file upload.
- Manual text capture.

## 20.4 Phase 2 Connectors

- Telegram capture bot.
- Browser clipper.
- PDF/DOCX/CSV/screenshot processing.
- Voice note transcription using local or configured provider.

## 20.5 Phase 3 Connectors

- Readwise/Kindle/highlights.
- Gmail read-only.
- Calendar read-only.
- Notion import.
- Apple Notes import if practical.

---

## 21. Security, Privacy, and Safety

## 21.1 Security Requirements

- Local-first by default.
- Secrets stored in OS keychain or encrypted local secret store.
- No cloud model call without explicit configuration.
- Sensitive connector defaults must be conservative.
- Every write operation logged.
- Raw evidence deletion requires explicit confirmation.
- Role-based permissions for future multi-user/server mode.

## 21.2 Prompt Injection Defense

Inputs from web pages, emails, PDFs, notes, and transcripts are untrusted.

Required protections:

- Treat source text as data, never instructions.
- Strip or quarantine suspicious instructions.
- Model prompts must include explicit instruction hierarchy.
- Connectors must mark imported content as untrusted.
- Generated actions must pass through policy engine.
- Tool calls from generated source content are forbidden.

## 21.3 Write Safety

Default write policy:

```text
Raw archive: auto-write allowed
Generated artifact: auto-write allowed
Durable memory: review required unless low-risk/high-confidence policy allows
Project state: review required
Belief/thesis changes: review required
Deletion: explicit user confirmation required
```

## 21.4 Auditability

Every operation must be traceable:

```text
who/what initiated it
what inputs were used
what model/tool was used
what was generated
what was written
what sources support it
what policy allowed/blocked it
```

---

## 22. Model Provider Strategy

Alice should be model-agnostic.

## 22.1 Provider Interface

```text
complete(prompt, options)
embed(texts, options)
transcribe(audio, options)
classify(input, schema)
extract(input, schema)
```

## 22.2 Provider Modes

```text
local_only
cloud_allowed
cloud_requires_approval
hybrid
```

## 22.3 Routing Rules

- Highly sensitive/sacred/regulated content defaults to local-only.
- Public/internal content may use cloud if enabled.
- User can preview exact data before cloud call if configured.
- Generated artifacts must record provider/model metadata.

---

## 23. Evaluation Harness

Alice needs proof that memory works.

## 23.1 Benchmark Corpus

Create synthetic benchmark with:

```text
100 people
50 projects
500 notes
100 decisions
100 beliefs
50 contradictions
50 superseded beliefs
100 open loops
50 personal reflections
50 future reminders
50 hidden cross-domain connections
```

## 23.2 Eval Categories

| Eval | Question | Metric |
|---|---|---|
| Exact Recall | What did I decide about X? | Recall@K |
| Temporal Recall | What did I believe before date Y? | Temporal accuracy |
| Contradiction Detection | What contradicts thesis X? | Precision/recall |
| Connection Discovery | What old idea is now relevant? | Human-rated usefulness |
| Provenance | Show sources for claim X | Evidence precision |
| Supersession | What changed in my view? | Correct current state |
| Open Loops | What am I forgetting? | Task recall |
| Privacy Routing | Did restricted memory leak? | Leakage rate |
| Alert Quality | Should this interrupt user? | False positive rate |
| Compression | Did context pack preserve key facts? | Compression fidelity |

## 23.3 Required Eval Commands

```bash
alice eval seed
alice eval run --suite recall
alice eval run --suite contradictions
alice eval run --suite privacy
alice eval run --suite all
alice eval report
```

## 23.4 Minimum Acceptance Targets for v2

Initial targets can be modest but must exist:

```text
Exact recall Recall@5 >= 0.85 on synthetic corpus
Temporal state accuracy >= 0.80
Contradiction detection precision >= 0.70
Provenance precision >= 0.85
Privacy leakage = 0 critical leaks
Open loop recall >= 0.80
```

---

## 24. Observability and Tracing

Every workflow run must produce a trace.

## 24.1 Trace Fields

```json
{
  "trace_id": "...",
  "run_id": "...",
  "workflow": "daily_brief",
  "started_at": "...",
  "completed_at": "...",
  "inputs": [],
  "retrieval_queries": [],
  "retrieval_candidates": [],
  "retrieval_filtered": [],
  "rerank_scores": [],
  "model_calls": [],
  "outputs": [],
  "policy_decisions": [],
  "errors": []
}
```

## 24.2 UI Debug View

Power users should be able to inspect:

- Why a memory was retrieved.
- Why a memory was excluded.
- Why a policy blocked content.
- What sources supported a generated artifact.
- What changed between revisions.

---

## 25. Export / Interoperability

Alice must never trap user memory.

## 25.1 Required Exports

```text
Markdown vault
JSONL event log
SQLite/Postgres dump
Graph export
Generated artifacts as markdown
Sources manifest
Provenance manifest
```

## 25.2 Obsidian-Compatible Export

Suggested layout:

```text
Alice Export/
├── 00 Inbox/
├── 01 Projects/
├── 02 Areas/
├── 03 Resources/
├── 04 Archive/
├── 05 System/
│   └── ALICE.md
├── 06 Daily Notes/
├── 07 Generated/
├── 08 Queue/
├── People/
├── Beliefs/
├── Open Loops/
├── Sources/
└── Graph/
```

---

## 26. Repo Structure

Recommended monorepo structure:

```text
alice/
├── apps/
│   ├── desktop/              # Tauri/Electron/desktop shell if used
│   ├── web/                  # local web UI
│   └── docs/                 # docs site
│
├── packages/
│   ├── core/                 # memory kernel
│   ├── storage/              # SQLite/Postgres adapters
│   ├── retrieval/            # retrieval router/context compiler
│   ├── graph/                # graph service
│   ├── brain/                # daily/weekly/connection workflows
│   ├── connectors/           # connector framework + connectors
│   ├── mcp-server/           # MCP tools
│   ├── cli/                  # Alice CLI
│   ├── evals/                # benchmark harness
│   ├── models/               # model provider abstraction
│   ├── policy/               # privacy/safety/write policy
│   └── shared/               # schemas/types/utils
│
├── workers/
│   ├── intake-worker/
│   ├── normalization-worker/
│   ├── embedding-worker/
│   ├── brain-worker/
│   ├── queue-worker/
│   └── scheduler-worker/
│
├── schemas/
│   ├── memory.schema.json
│   ├── source.schema.json
│   ├── artifact.schema.json
│   ├── graph-edge.schema.json
│   ├── context-pack.schema.json
│   └── event.schema.json
│
├── docs/
│   ├── architecture.md
│   ├── memory-model.md
│   ├── api.md
│   ├── mcp.md
│   ├── privacy.md
│   ├── evals.md
│   └── contributor-guide.md
│
├── migrations/
├── tests/
├── docker-compose.yml
├── README.md
└── ALICE.md.example
```

Adapt to the existing Alice repo structure if needed. Do not reorganize destructively unless the repo integrator approves.

---

## 27. Implementation Phases / Sprints

## Sprint 1 — Architecture Foundation and Schema

### Objective

Establish v2 memory model, event log, artifacts, task queue, domains/sensitivity, and migration foundation.

### Deliverables

- Database schema/migrations for:
  - sources
  - source_chunks
  - memories
  - memory_revisions
  - provenance_links
  - graph_edges
  - projects
  - people
  - beliefs
  - open_loops
  - generated_artifacts
  - task_queue
  - event_log
- Shared JSON schemas/types.
- Storage repository interfaces.
- Event logging utility.
- ALICE.md/Brain Charter model.

### Acceptance Criteria

- Migrations run cleanly.
- Unit tests cover CRUD for all major entities.
- Event log writes for create/update operations.
- No existing Alice functionality broken.
- All new entities have domain/sensitivity where applicable.

---

## Sprint 2 — Capture, Archive, Normalize

### Objective

Implement robust raw evidence intake and normalization.

### Deliverables

- Manual text capture.
- File capture.
- Markdown/Obsidian folder import.
- ChatGPT export import if not already complete.
- Source hashing/deduplication.
- Text extraction/chunking.
- Basic entity/claim extraction pipeline.
- Candidate memory creation.

### Acceptance Criteria

- Import 100 markdown files without duplicates.
- Raw source preserved before normalization.
- Candidate memories link to source chunks.
- Import generates event log entries.
- Failed imports are recoverable and logged.

---

## Sprint 3 — Retrieval Router and Context Packs

### Objective

Implement multi-path retrieval and compact context packs.

### Deliverables

- Query classifier.
- Keyword search.
- Vector search.
- Graph traversal scaffold.
- Temporal filter support.
- Domain/sensitivity filtering.
- Context pack generator.
- API/CLI/MCP command for context packs.

### Acceptance Criteria

- `alice context-pack "query"` returns structured pack.
- Context pack includes memories, sources, contradictions placeholder, open loops placeholder.
- Sensitive memories are filtered according to policy.
- Retrieval trace records candidates/filtering/ranking.

---

## Sprint 4 — Generated Artifacts and Queue

### Objective

Implement generated artifacts and asynchronous task queue.

### Deliverables

- Task queue model/service.
- Queue worker.
- Artifact generator.
- Artifact review actions.
- CLI/API for queue and artifacts.
- Markdown export for artifacts.

### Acceptance Criteria

- User can add queue task.
- Worker processes task and creates artifact.
- Artifact can be reviewed/promoted/rejected.
- All operations logged.
- Failed task produces useful error.

---

## Sprint 5 — Daily Brief and Weekly Synthesis

### Objective

Build first Alice Brain workflows.

### Deliverables

- Daily Brief Generator.
- Weekly Synthesis Generator.
- Scheduler/manual triggers.
- Artifact templates.
- Source/provenance inclusion.

### Acceptance Criteria

- Daily brief generated from recent sources/projects/open loops.
- Weekly synthesis generated from last 7 days.
- Outputs distinguish fact/inference/action.
- Artifacts inherit sensitivity from inputs.
- Works from CLI/API and scheduled worker.

---

## Sprint 6 — Connection Finder and Graph Edges

### Objective

Find non-obvious connections and candidate graph edges.

### Deliverables

- Connection finder workflow.
- Connection report artifact.
- Candidate graph edge creation.
- Review/accept/reject for graph edges.
- Basic graph neighborhood API.

### Acceptance Criteria

- Finds connections between recent and older notes.
- Produces typed edges with explanations/confidence.
- User can accept/reject edges.
- Accepted edges affect future retrieval.

---

## Sprint 7 — Contradiction Finder and Belief Tracking

### Objective

Track evolving beliefs and detect contradictions.

### Deliverables

- Belief/thesis memory UI/API scaffolding.
- Contradiction finder.
- Contradiction report artifact.
- Belief reinforcement/challenge events.
- Supersession workflow.

### Acceptance Criteria

- New claim can challenge active belief.
- Contradiction report shows both sides and provenance.
- User can mark belief as challenged/superseded.
- Temporal state query returns previous/current belief states.

---

## Sprint 8 — Project Auto-Updater and Open Loops

### Objective

Make Alice useful for active projects.

### Deliverables

- Project pages/data model integration.
- Project update candidate workflow.
- Open loop extraction.
- Open loop close/snooze/edit.
- Project timeline.

### Acceptance Criteria

- New project note creates project update candidate.
- User can accept/edit/reject update.
- Open loops appear in daily brief.
- Project page shows state, decisions, open loops, artifacts.

---

## Sprint 9 — UI v1

### Objective

Create user-friendly local UI for Alice Brain.

### Deliverables

- Home dashboard.
- Inbox.
- Ask Alice.
- Daily brief view.
- Generated artifacts view.
- Memory review.
- Queue.
- Projects.
- Settings/privacy.

### Acceptance Criteria

- Non-technical user can capture, review, ask, and read briefs.
- Every generated item has visible sources/provenance.
- Review actions work end-to-end.
- UI respects domain/sensitivity labels.

---

## Sprint 10 — Evals and Hardening

### Objective

Prove the memory system works and harden safety.

### Deliverables

- Synthetic benchmark corpus generator.
- Recall evals.
- Temporal evals.
- Contradiction evals.
- Privacy leakage evals.
- Provenance evals.
- Eval report CLI.
- Prompt-injection test corpus.

### Acceptance Criteria

- `alice eval run --suite all` completes.
- Baseline metrics reported.
- Critical privacy leakage tests pass.
- Prompt-injection sources cannot trigger tool writes.
- Regression tests added to CI.

---

## Sprint 11 — Connector Expansion

### Objective

Add practical capture sources.

### Deliverables

- Telegram capture.
- Browser clipper MVP.
- PDF/DOCX/CSV/screenshot processing.
- Voice transcription pipeline.
- Connector settings UI.

### Acceptance Criteria

- Each connector preserves raw evidence.
- Each connector supports default domain/sensitivity.
- Sync cursors prevent duplicates.
- Connector failures do not corrupt memory.

---

## Sprint 12 — Public Release Polish

### Objective

Prepare open-source launch.

### Deliverables

- README rewrite.
- Quickstart.
- Docker/local install.
- Example ALICE.md.
- Demo dataset.
- Demo video script.
- Contributor guide.
- Security/privacy docs.
- Architecture docs.
- Release checklist.

### Acceptance Criteria

- New user can install and generate first daily brief in under 20 minutes.
- Docs clearly explain Alice Core vs Alice Brain vs Alice Agent Memory.
- Repo passes tests/lint/evals baseline.
- No secrets or private data in repo.

---

## 28. Agent Build Instructions

## 28.1 Control Tower Agent

Responsibilities:

- Own sprint brief.
- Maintain architecture consistency.
- Enforce acceptance criteria.
- Decide whether sprint is merge-ready.
- Track open questions and risks.

## 28.2 Repo Integrator Agent

Responsibilities:

- Create branch per sprint.
- Ensure clean migrations.
- Run tests/lint/typecheck.
- Commit and prepare PR summary.
- Do not merge unless Control Tower gives `merge_approved`.

## 28.3 Builder Agent

Responsibilities:

- Implement sprint deliverables.
- Add tests.
- Avoid unrelated refactors.
- Respect existing repo conventions.

## 28.4 Reviewer Agent

Responsibilities:

- Review implementation against acceptance criteria.
- Identify missing tests, schema gaps, privacy issues.
- Send fixes back to Builder.

## 28.5 Refactor Agent

Responsibilities:

- Only refactor the latest sprint changes.
- Improve structure without altering intended behavior.
- Avoid broad rewrites.

## 28.6 Security/Pentest Agent

Responsibilities:

- Test prompt injection.
- Test unauthorized memory access.
- Test write safety.
- Test sensitive domain leakage.
- Test deletion/rollback safety.

---

## 29. Required Definition of Done

A sprint is not done unless:

```text
- All acceptance criteria pass.
- Tests added or updated.
- Migrations are reversible or clearly documented.
- Event logging implemented for new write paths.
- Domain/sensitivity rules respected.
- No direct uncontrolled memory mutation.
- Generated artifacts are reviewable.
- CLI/API/MCP surfaces documented if changed.
- README/docs updated where user-facing behavior changed.
- Security review completed for new connectors/write paths.
```

---

## 30. Key Open Questions

1. Should the public default be SQLite-only, with Postgres as advanced mode?
2. What existing Alice repo modules should be preserved vs reorganized?
3. Should the UI be web-first, desktop-first, or Tauri shell around local web?
4. Which local model provider should be the default for embeddings?
5. Should Obsidian be a first-class UI target or simply an export/import format?
6. What should the first public demo corpus be?
7. What should be the minimum viable connector set for launch?
8. Should generated artifacts be version-controlled in Git by default?
9. How much automatic promotion should be allowed in v2?
10. What is the exact license strategy for Alice Core vs future hosted products?

---

## 31. Recommended v2 MVP Scope

For the immediate next version, do not try to build every connector.

Build this first:

```text
Alice Core:
- v2 memory schema
- event log
- provenance
- revisions
- domain/sensitivity
- retrieval/context packs

Alice Brain:
- generated artifacts
- task queue
- daily brief
- weekly synthesis
- connection finder
- contradiction finder MVP
- open loop tracker MVP

Interfaces:
- CLI
- MCP
- minimal local web UI

Connectors:
- local files
- markdown/Obsidian
- ChatGPT export
- manual capture
```

This is enough to prove the thesis.

---

## 32. Strategic Differentiation

Alice must be positioned against three weaker categories:

### 1. Notes apps with AI

They store and summarize. Alice remembers, revises, connects, and explains.

### 2. Chatbots with memory

They recall preferences. Alice maintains a provenance-aware memory graph and temporal state.

### 3. Agent frameworks

They run tasks. Alice gives agents durable continuity and context packs.

Alice category:

> Local-first memory infrastructure for humans and agents.

---

## 33. Final Build Mandate

The next version of Alice should make one thing undeniable:

> Alice is no longer just a memory layer for agents. Alice is the private continuity layer for a human life, a body of work, and the agents that help extend both.

Build the kernel first. Make the product useful immediately through daily briefs, queue, generated artifacts, connection discovery, and memory review. Then expand connectors.

Do not chase every integration before the memory model is excellent.

Do not let generated text become unreviewed truth.

Do not sacrifice provenance, correction, and temporal reasoning for demo speed.

Alice wins if it becomes the system people trust with their most important context.

