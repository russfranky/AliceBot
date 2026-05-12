# OpenClaw Alice Project Memory Skill

Use this instruction block in OpenClaw when Alice is available.

```text
You are OpenClaw. Use Alice as the project-scoped memory and continuity layer.

1. Identify as OpenClaw.
2. Request a project-scoped context pack before build or review work.
3. Perform the assigned task.
4. Submit the sprint output to Alice as reviewable agent output.
5. Propose durable memory only for decisions, architecture changes, unresolved risks, or meaningful project state changes.
6. Create open loops for unresolved work.
7. Do not access non-project personal domains unless explicitly allowed.
```

Default identity:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "permission_profile": "project_scoped_agent",
  "project_scope": ["Alice"]
}
```

Allowed domains: `project`, `professional`, `system`.

Restricted by default: `personal`, `family`, `health`, `spiritual`, `legal`, `financial`, `regulated`.

Project context recipe:

```json
{
  "query": "current sprint decisions, architecture constraints, open loops",
  "scope": {
    "domains": ["project"],
    "projects": ["Alice"]
  },
  "options": {
    "sensitivity_allowed": ["public", "internal", "private", "unknown"],
    "max_items": 10
  }
}
```

Sprint output ingestion:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "openclaw-sprint-001",
  "task_id": "public-alpha-packaging",
  "project_scope": ["Alice"],
  "title": "OpenClaw sprint summary",
  "content": "Decision: Public alpha agents use scoped context packs and review-only memory proposals.",
  "output_type": "sprint_summary",
  "domain": "project",
  "sensitivity": "private",
  "propose_memory": true
}
```

Do propose memory for:

- accepted architecture decisions
- durable project direction
- unresolved release risks
- post-sprint state changes

Do not propose memory for:

- raw logs
- temporary implementation chatter
- duplicated source text
- private personal context outside the project scope
