# OpenClaw Alice Project Memory Skill

Use Alice as the project-scoped memory and continuity layer.

Default loop:

1. Identify as OpenClaw.
2. Request project-scoped context before work.
3. Perform the assigned build or review task.
4. Submit output to Alice as reviewable agent output.
5. Commit explicit project-scoped memory only when the user directly asks to remember/save/add it and the domain is `project`.
6. Propose review-only memory for external evidence, generated summaries, ambiguous facts, contradictions, or lower-confidence project state.
7. Create open loops for unresolved work.
8. Do not access or write non-project personal domains.

Default identity:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"]}
```

Allowed direct commit domain: `project`.

Context/read domains may include `project`, `professional`, and `system` when policy allows.

Restricted by default: `personal`, `family`, `health`, `spiritual`, `legal`, `financial`, `regulated`.

Submit sprint output:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"openclaw-sprint-001","task_id":"public-alpha-packaging","project_scope":["Alice"],"title":"OpenClaw sprint summary","content":"Decision: Agents use scoped context packs and review-only memory proposals.","output_type":"sprint_summary","domain":"project","sensitivity":"private","propose_memory":true}
```

Explicit project memory commit:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"],"intent":"explicit_remember","title":"Release gate decision","canonical_text":"Alice public alpha release gates require doctor, smokes, evals, and git diff checks before merge.","domain":"project","sensitivity":"private","confidence":0.94,"source_type":"direct_user_instruction"}
```

Use `alice_vnext_undo_memory`, `alice_vnext_correct_memory`, or `alice_vnext_forget_memory` through Alice if a committed project memory needs reversal or repair. Never edit Postgres directly.

See `docs/alpha/openclaw-skill.md` for full recipes.
