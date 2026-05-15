# Hermes Alice Memory Skill

Use Alice as the user's durable local memory and continuity layer.

Before planning, answering, or acting on important user context, request a scoped context pack from Alice.
When the user explicitly says to remember, save, or add a durable fact to memory, commit through Alice's official memory commit tool.
When the fact is sensitive, contradictory, external-source-derived, ambiguous, or low-confidence, let Alice return inline confirmation or dashboard review instead of forcing a write.
When you create summaries, plans, follow-ups, meeting notes, or daily briefings, ingest them into Alice as reviewable agent outputs.

Rules:

- never directly mutate trusted memory or the database
- never bypass Alice policy
- never request sensitive domains unless needed and allowed
- use `/vnext` review queues for human approval, audit, undo, correction, and forget flows

Default identity:

```json
{"agent_id":"hermes","agent_type":"personal_assistant","permission_profile":"trusted_local_agent","project_scope":[]}
```

Default scope is broad but policy-filtered. Avoid `health`, `family`, `spiritual`, `legal`, `financial`, and `regulated` unless the user explicitly enables that scope.

Good memory proposal:

```json
{"canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.84}
```

Good explicit commit:

```json
{"agent_id":"hermes","permission_profile":"trusted_local_agent","intent":"explicit_remember","title":"Preferred daily planning format","canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.93,"source_type":"direct_user_instruction"}
```

If Alice returns `confirmation_required`, show the proposed text and call `alice_vnext_confirm_memory` only after the user confirms. If Alice returns `review_required`, do not retry broadly; leave it for `/vnext` review.

Bad memory proposal:

```json
{"canonical_text":"The user might dislike long reports.","confidence":0.31}
```

See `docs/alpha/hermes-skill.md` for full recipes.
