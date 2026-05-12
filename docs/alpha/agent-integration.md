# Agent Integration Pack

Agents should use Alice as a durable, private, provenance-aware, reviewable memory layer.

Universal pattern:

1. Identify yourself.
2. Request scoped context, not raw memory.
3. Use Alice context packs before planning or acting.
4. Submit important outputs back to Alice.
5. Propose memory; do not mutate trusted memory.
6. Create open loops when work remains.
7. Respect domain and sensitivity policy.
8. Use `/vnext` for review, audit, and troubleshooting.

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
- `project_scoped_agent`: project context, project outputs, review-only memory proposals
- `trusted_local_agent`: broader local assistant context, still policy-filtered
- `memory_proposal_agent`: proposal-focused agent
- `admin_agent`: scheduler and administrative actions

## CLI Example

```bash
alicebot context-pack "Alice public alpha sprint context" --domain project --project Alice

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
  "Decision: Alice public alpha agents use scoped context packs and review-only memory proposals."
```

## Smoke

```bash
alicebot vnext smoke agent-integration-pack
```

The smoke verifies scoped context, output ingestion, review-only proposal creation, no auto-promotion, event logging, restricted-domain policy blocking, and `/vnext` agent activity visibility.
