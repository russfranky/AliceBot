# MCP Tool Quickstart

Expose Alice MCP over stdio:

```bash
alicebot-mcp --help
alicebot-mcp
```

Editable install equivalent:

```bash
./.venv/bin/python -m alicebot_api.mcp_server
```

Claude Desktop style config:

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

## End-to-end OpenClaw Example

Request scoped context with `alice_vnext_context_pack`:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "openclaw-alpha-001",
  "task_id": "public-alpha-docs",
  "project_scope": ["Alice"],
  "permission_profile": "project_scoped_agent",
  "query": "Alice public preview packaging",
  "scope": {
    "domains": ["project"],
    "projects": ["Alice"]
  },
  "options": {
    "sensitivity_allowed": ["public", "internal", "private", "unknown"],
    "max_items": 8
  }
}
```

Submit output with `alice_vnext_ingest_agent_output`:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "openclaw-alpha-001",
  "task_id": "public-alpha-docs",
  "project_scope": ["Alice"],
  "permission_profile": "project_scoped_agent",
  "title": "Public alpha sprint summary",
  "content": "Decision: Agent outputs are captured as reviewable evidence.",
  "output_type": "sprint_summary",
  "domain": "project",
  "sensitivity": "private",
  "propose_memory": true
}
```

Agentic memory commit:

Trusted agents can write explicit "remember/save/add this to memory" instructions through `alice_vnext_commit_memory`. Alice still decides the outcome:

- `committed`: direct active memory with provenance, event log, and revision.
- `confirmation_required`: sensitive, contradictory, or ambiguous memory waits for `alice_vnext_confirm_memory`.
- `review_required`: external, generated, low-confidence, or review-only-agent memory stays in `/vnext`.
- `rejected`: read-only, out-of-scope, unsafe, or policy-bypass attempts are blocked.

Use canonical schema values for persisted labels. For quote saves, use `memory_type=semantic`; use `domain=learning` only when a quote collection needs an explicit domain. Avoid invented values like `memory_type=quote`, `domain=quotes`, or `sensitivity=sensitive`.

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "intent": "explicit_remember",
  "title": "Preferred daily planning format",
  "canonical_text": "The user prefers daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.93,
  "source_type": "direct_user_instruction"
}
```

Memory repair and audit tools:

- `alice_vnext_confirm_memory`
- `alice_vnext_undo_memory`
- `alice_vnext_correct_memory`
- `alice_vnext_forget_memory`
- `alice_vnext_recent_memory_commits`
- `alice_vnext_memory_audit`

No-direct-database rule:

- MCP tools can create reviewable sources, artifacts, open loops, and candidate memory proposals.
- Trusted writes use Alice's memory commit policy engine, never direct Postgres mutation.
- Human review, inline confirmation, audit, undo, correction, and forget flows happen in `/vnext`.

Policy errors:

- restricted domains can be filtered or blocked
- blocked calls return policy reasons such as `all_requested_domains_restricted`
- agents should narrow domains or ask the user for approval instead of retrying broadly
