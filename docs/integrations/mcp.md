# MCP Integration

The shipped MCP server for the `v0.5.1` release boundary exposes a deliberately scoped deterministic tool surface over Alice continuity seams.
`v0.5.1` is the current pre-1.0 public release.

## Entrypoints

```bash
./.venv/bin/python -m alicebot_api.mcp_server --help
./.venv/bin/python -m alicebot_api.mcp_server
alicebot-mcp --help
alicebot-mcp
```

`alicebot-mcp` is available after editable install.

## Runtime Scope

MCP uses the same local runtime scope as CLI:

- `DATABASE_URL`
- `ALICEBOT_AUTH_USER_ID`

## Shipped Tool Surface

- `alice_brief`
- `alice_capture`
- `alice_capture_candidates`
- `alice_commit_captures`
- `alice_recall`
- `alice_state_at`
- `alice_resume`
- `alice_prefetch_context`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_timeline`
- `alice_review_queue`
- `alice_review_apply`
- `alice_memory_review` (legacy alias)
- `alice_memory_correct` (legacy alias)
- `alice_explain`
- `alice_context_pack`
- `alice_vnext_context_pack`
- `alice_vnext_capture`
- `alice_vnext_queue_task`
- `alice_vnext_generate_artifact`
- `alice_vnext_project_dashboard`
- `alice_vnext_open_loops`
- `alice_vnext_recent_decisions`
- `alice_vnext_recent_changes`
- `alice_vnext_find_connections`
- `alice_vnext_find_contradictions`
- `alice_vnext_propose_memory`
- `alice_vnext_review_items`
- `alice_vnext_artifact_get`
- `alice_vnext_artifact_review`
- `alice_vnext_scheduler_status`
- `alice_vnext_scheduler_run_now`
- `alice_vnext_scheduler_run_due`
- `alice_vnext_scheduler_pause`
- `alice_vnext_scheduler_resume`

`alice_brief` is the default external-agent continuity lookup. It returns one continuity bundle with relevant facts, recent changes, open loops, conflicts, timeline highlights, provenance, trust posture, and a next suggested action.
`alice_explain` now accepts either `continuity_object_id` for evidence-chain inspection or `entity_id` plus optional `at` for temporal explain output.
`alice_prefetch_context` provides an automation-oriented pre-turn context assembly surface using the same continuity resumption semantics shipped for `alice_resume`.
`alice_capture_candidates` and `alice_commit_captures` provide the B2 bridge auto-capture pipeline over user/assistant turns with `manual`/`assist`/`auto` commit policy support.
`alice_review_queue` and `alice_review_apply` provide B3 review operations (`approve`, `edit-and-approve`, `reject`, `supersede-existing`) with deterministic recall/resume effects after approved actions.

The `alice_vnext_*` tools carry the agentic control-plane contract. Agent callers can include `agent_id`, `agent_type`, `agent_run_id`, `task_id`, `project_scope`, `permission_profile`, domain filters, and sensitivity filters. Policy decisions are logged, restricted requests are filtered or blocked, memory writes stay proposal/review-only, and scheduler actions create governed run records with trace IDs.

## Example: Claude Desktop MCP Config

```json
{
  "mcpServers": {
    "alice-core": {
      "command": "/ABSOLUTE/PATH/TO/AliceBot/.venv/bin/python",
      "args": ["-m", "alicebot_api.mcp_server"],
      "cwd": "/ABSOLUTE/PATH/TO/AliceBot",
      "env": {
        "DATABASE_URL": "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot",
        "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```

## Hermes

For Hermes Agent-specific setup, prompts, and troubleshooting:

- `docs/integrations/hermes-bridge-operator-guide.md` (recommended provider+MCP path)
- `docs/integrations/hermes.md`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/hermes-skill-pack.md`

Recommended bridge deployment shape:

- provider plus MCP is the default operator path
- MCP-only remains available as fallback when provider install is blocked

One-command bridge demo:

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

## Contract Guardrails

- tool set is intentionally narrow and stable
- tool output is deterministic for parity testing
- MCP does not widen core product semantics beyond the shipped Phase 13 baseline and Bridge `B1` through `B4`
- `alice_brief` is the preferred first call for external runtimes that need continuity in one request
- vNext agent tools preserve the no-auto-promotion rule and require review for agent-proposed memory

See tests:

- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `tests/integration/test_temporal_state_mcp_cli.py`
- `tests/integration/test_openclaw_mcp_integration.py`
- `docs/integrations/one-call-continuity.md`
