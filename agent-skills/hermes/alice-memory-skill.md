# Hermes Alice Memory Skill

Use Alice as the user's durable local memory and continuity layer.

Before planning, answering, or acting on important user context, request a scoped context pack from Alice.
When the user makes a durable decision, states a stable preference, creates an open loop, or changes project direction, propose memory to Alice.
When you create summaries, plans, follow-ups, meeting notes, or daily briefings, ingest them into Alice as reviewable agent outputs.

Rules:

- never directly mutate trusted memory
- never bypass Alice policy
- never request sensitive domains unless needed and allowed
- use `/vnext` review queues for human approval

Default identity:

```json
{"agent_id":"hermes","agent_type":"personal_assistant","permission_profile":"trusted_local_agent","project_scope":[]}
```

Default scope is broad but policy-filtered. Avoid `health`, `family`, `spiritual`, `legal`, `financial`, and `regulated` unless the user explicitly enables that scope.

Good memory proposal:

```json
{"canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.84}
```

Bad memory proposal:

```json
{"canonical_text":"The user might dislike long reports.","confidence":0.31}
```

See `docs/alpha/hermes-skill.md` for full recipes.
