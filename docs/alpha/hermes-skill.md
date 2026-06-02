# Hermes Alice Memory Skill

Use this instruction block in Hermes when Alice is available.

```text
You are connected to Alice, the user's local-first memory and continuity layer.

Before planning, answering, or acting on important user context, request a scoped context pack from Alice.
When the user explicitly says to remember, save, or add a durable fact to memory, call Alice's memory commit path.
When the write is sensitive, contradictory, external-source-derived, ambiguous, or low-confidence, stop at Alice's returned inline confirmation or dashboard review state.
When you create summaries, plans, follow-ups, meeting notes, or daily briefings, ingest them into Alice as reviewable agent outputs.
Never directly mutate trusted memory.
Never write directly to Postgres.
Never bypass Alice policy.
Never request sensitive domains unless needed and allowed.
Use /vnext review queues for human approval, audit, undo, correction, and forget flows.
```

Default identity:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "project_scope": []
}
```

Default permissions:

- scope: broad but policy-filtered
- allowed domains: `professional`, `project`, `personal` where configured
- restricted by default: `health`, `family`, `spiritual`, `legal`, `financial`, `regulated`

Recipes:

- Daily planning context: ask for today's project, professional, and open-loop context.
- Meeting preparation context: query the meeting name and attendees with `professional` and `project` domains.
- Follow-up context: query open loops and recent decisions.
- Project briefing context: use project-scoped context before advising.
- Personal assistant memory commit: commit only explicit stable preferences or durable decisions through Alice.
- Quote memory commit: use `memory_type=semantic`; if a domain is needed for quote collections, use `domain=learning`.
- Personal assistant memory proposal: propose inferred, external, or lower-confidence facts for review.
- Artifact submission: ingest plans and summaries as reviewable agent outputs.

Use only schema-backed enum values for persisted fields. Do not send invented labels such as `memory_type=quote`, `domain=quotes`, or `sensitivity=sensitive`; Alice normalizes common aliases, but canonical values keep MCP calls predictable.

Good explicit commit:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "intent": "explicit_remember",
  "title": "Preferred daily planning format",
  "canonical_text": "The user prefers daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.93,
  "source_type": "direct_user_instruction"
}
```

Expected outcomes:

- `committed`: Alice stored the memory as active and auditable.
- `confirmation_required`: show the proposed text and call `alice_vnext_confirm_memory` only after the user confirms.
- `review_required`: leave the candidate in `/vnext` review.
- `rejected`: do not retry without narrowing scope or asking the user.

Good proposal:

```json
{
  "title": "Preferred daily planning format",
  "canonical_text": "The user prefers daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.84,
  "rationale": "The user stated this preference explicitly."
}
```

Bad proposal:

```json
{
  "canonical_text": "The user might dislike long reports.",
  "confidence": 0.31,
  "rationale": "Speculative inference from one short reply."
}
```
