# Custom Agent Integration Guide

Any third-party agent should follow the same Alice pattern.

1. Identify yourself.
2. Request scoped context, not raw memory.
3. Use Alice context packs before acting.
4. Submit important outputs back to Alice.
5. Commit explicit memory only through Alice's memory commit API/MCP/CLI path.
6. Propose memory for inferred, external-source-derived, generated, ambiguous, or lower-confidence facts.
7. Create open loops when work remains.
8. Respect domain and sensitivity policy.
9. Use `/vnext` for review, audit, undo, correction, forget, and troubleshooting.

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

For explicit "remember this" instructions, use `alice_vnext_commit_memory`:

```json
{
  "agent_id": "researcher",
  "agent_type": "research_agent",
  "permission_profile": "project_scoped_agent",
  "project_scope": ["Alice"],
  "intent": "explicit_remember",
  "title": "Research source rule",
  "canonical_text": "Alice project research briefs must separate quoted evidence from model interpretation.",
  "domain": "project",
  "sensitivity": "private",
  "confidence": 0.92,
  "source_type": "direct_user_instruction"
}
```

Alice returns one of four outcomes:

- `committed`: active memory, with event and revision audit trail.
- `confirmation_required`: call `alice_vnext_confirm_memory` only after the user confirms or edits the text.
- `review_required`: the item is in `/vnext` dashboard review.
- `rejected`: the agent should narrow scope or ask the user instead of retrying broadly.

Repair tools:

- `alice_vnext_undo_memory`
- `alice_vnext_correct_memory`
- `alice_vnext_forget_memory`
- `alice_vnext_recent_memory_commits`
- `alice_vnext_memory_audit`

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
