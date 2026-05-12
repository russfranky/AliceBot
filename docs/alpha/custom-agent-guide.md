# Custom Agent Integration Guide

Any third-party agent should follow the same Alice pattern.

1. Identify yourself.
2. Request scoped context, not raw memory.
3. Use Alice context packs before acting.
4. Submit important outputs back to Alice.
5. Propose memory; do not mutate trusted memory.
6. Create open loops when work remains.
7. Respect domain and sensitivity policy.
8. Use `/vnext` for review, audit, and troubleshooting.

## API Example

```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "agent_identity": {
    "agent_id": "researcher",
    "agent_type": "research_agent",
    "agent_run_id": "research-001",
    "task_id": "market-map",
    "project_scope": ["Alice"],
    "permission_profile": "project_scoped_agent"
  },
  "query": "recent Alice market research decisions",
  "scope": {
    "domains": ["project"]
  },
  "options": {
    "sensitivity_allowed": ["public", "internal", "private", "unknown"],
    "max_items": 8
  }
}
```

## MCP Example

Use `alice_vnext_context_pack` with the same identity fields, then submit output with `alice_vnext_ingest_agent_output`.

## Agent Examples

- Research agent: request research/project context, ingest reports, propose only durable findings.
- Coding agent: request project context, ingest sprint summaries, propose decisions and risks.
- Personal assistant: request personal/professional context only when needed, propose stable preferences.
- Workflow orchestrator: request open-loop context, create new open loops for blocked work.
- Meeting-notes agent: ingest meeting summaries and propose decisions, commitments, and follow-ups.

Review queues:

- Memory Review: candidate memory proposals.
- Generated: agent outputs and generated artifacts.
- Open Loops: unresolved follow-ups.
- Trace: provenance from source to artifact.
