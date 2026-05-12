# OpenClaw Alice Project Memory Skill

Use Alice as the project-scoped memory and continuity layer.

Default loop:

1. Identify as OpenClaw.
2. Request project-scoped context before work.
3. Perform the assigned build or review task.
4. Submit output to Alice as reviewable agent output.
5. Propose durable memory only for decisions, architecture changes, unresolved risks, or meaningful project state changes.
6. Create open loops for unresolved work.
7. Do not access non-project personal domains unless explicitly allowed.

Default identity:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"]}
```

Allowed domains: `project`, `professional`, `system`.

Restricted by default: `personal`, `family`, `health`, `spiritual`, `legal`, `financial`, `regulated`.

Submit sprint output:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"openclaw-sprint-001","task_id":"public-alpha-packaging","project_scope":["Alice"],"title":"OpenClaw sprint summary","content":"Decision: Agents use scoped context packs and review-only memory proposals.","output_type":"sprint_summary","domain":"project","sensitivity":"private","propose_memory":true}
```

See `docs/alpha/openclaw-skill.md` for full recipes.
