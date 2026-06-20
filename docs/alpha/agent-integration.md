# Agent Integration Pack

Agents should use Alice as a durable, private, provenance-aware, reviewable memory layer.

Universal pattern:

1. Identify yourself.
2. Request scoped context, not raw memory.
3. Use Alice context packs before planning or acting.
4. Submit important outputs back to Alice.
5. Commit explicit "remember/save/add this to memory" instructions only through Alice's official memory commit path.
6. Propose memory for inferred, external, generated, ambiguous, or lower-confidence facts.
7. Create open loops when work remains.
8. Respect domain and sensitivity policy.
9. Use `/vnext` for review, audit, undo, correction, forget, and troubleshooting.

## Agent Identity Fields

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "run-2026-05-12-001",
  "task_id": "alice-public-alpha",
  "project_scope": ["Alice"],
  "permission_profile": "project_scoped_agent"
}
```

Permission profiles:

- `read_only_agent`: context lookup only
- `project_scoped_agent`: project context, project outputs, explicit project-domain memory commits, and review-only proposals
- `trusted_local_agent`: broader local assistant context, still policy-filtered
- `memory_proposal_agent`: proposal-focused agent
- `admin_agent`: scheduler and administrative actions

## CLI Example

```bash
alicebot context-pack "Alice public preview sprint context" --domain project --project Alice

alicebot vnext agents ingest-output \
  --agent-id openclaw \
  --agent-type coding_agent \
  --agent-run-id run-2026-05-12-001 \
  --project-scope Alice \
  --permission-profile project_scoped_agent \
  --title "OpenClaw sprint summary" \
  --output-type sprint_summary \
  --domain project \
  --sensitivity private \
  --propose-memory \
  "Decision: Alice public preview agents use scoped context packs and review-only memory proposals."

alicebot vnext memories commit \
  --agent-id openclaw \
  --agent-type coding_agent \
  --agent-run-id run-2026-05-12-001 \
  --project-scope Alice \
  --permission-profile project_scoped_agent \
  --title "Release gate decision" \
  --text "Alice public preview release gates require doctor, smokes, evals, and git diff checks before merge." \
  --domain project \
  --sensitivity private \
  --confidence 0.94
```

## Smoke

```bash
alicebot vnext smoke agent-integration-pack
alicebot vnext smoke agentic-memory-commit
```

The smokes verify scoped context, output ingestion, explicit trusted memory commits, inline confirmation, review gating, undo/correction/forget, no direct database mutation, event logging, restricted-domain policy blocking, and `/vnext` agent activity visibility.
