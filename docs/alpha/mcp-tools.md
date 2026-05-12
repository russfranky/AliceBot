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
  "query": "Alice public alpha packaging",
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

No-auto-promotion rule:

- MCP tools can create reviewable sources, artifacts, open loops, and candidate memory proposals.
- They do not directly write trusted memory.
- Human review happens in `/vnext`.

Policy errors:

- restricted domains can be filtered or blocked
- blocked calls return policy reasons such as `all_requested_domains_restricted`
- agents should narrow domains or ask the user for approval instead of retrying broadly
