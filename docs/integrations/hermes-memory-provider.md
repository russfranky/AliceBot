# Hermes External Memory Provider: Alice

This guide installs Alice as a Hermes **external memory provider**.
For the canonical bridge operator path and config examples, see:

- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/integrations/hermes-provider-plus-mcp-why.md`

Hermes behavior with this provider:

- built-in `MEMORY.md` and `USER.md` stay active
- one external provider can be active at a time (`memory.provider`)
- Alice provider adds continuity recall/resumption/open-loop tools and prefetch

## What The Provider Adds

- `alice_recall`: deterministic continuity recall with provenance
- `alice_resumption_brief`: last decision, next action, open loops, recent changes
- `alice_open_loops`: open-loop dashboard retrieval
- prefetch: turn-start context assembled from Alice resumption brief
- bridge-phase lifecycle contract for `prefetch`, `queue_prefetch`, `sync_turn`, and `on_session_end`
- deterministic capture dedupe for repeated callback execution
- B2 auto-capture pipeline for `sync_turn`: `alice_capture_candidates` then `alice_commit_captures`
- capture mode policy support: `manual`, `assist` (default), `auto`
- local status readiness reporting without live network calls

## Continuity Model Mapping

The provider maps Alice continuity responses into Hermes provider hooks:

| Hermes provider hook | Alice endpoint | Mapping |
|---|---|---|
| `prefetch(query)` | `GET /v0/continuity/resumption-brief` | renders last decision, next action, open loops, and recent changes into ephemeral context |
| `queue_prefetch(query)` | `GET /v0/continuity/resumption-brief` | asynchronously prebuilds pre-turn context cache for next `prefetch` |
| `sync_turn(user, assistant)` | `POST /v0/continuity/captures/candidates` + `POST /v0/continuity/captures/commit` | post-turn extraction/commit pipeline with mode policy and duplicate-write suppression |
| `on_session_end()` | same as queued `sync_turn` pipeline work | deterministic flush of pending capture/commit work before provider shutdown |
| `alice_recall` tool | `GET /v0/continuity/recall` | returns ranked continuity objects with provenance and scope filters |
| `alice_resumption_brief` tool | `GET /v0/continuity/resumption-brief` | returns structured resume sections for deterministic follow-through |
| `alice_open_loops` tool | `GET /v0/continuity/open-loops` | returns waiting/blocker/stale/next-action open-loop groups |

## Install

Install into the Hermes memory plugin directory used by your active Hermes Python environment:

```bash
./scripts/install_hermes_alice_memory_provider.py
```

Optional flags:

- `--force` to replace an existing install
- `--symlink` for local development iteration
- `--destination-root /path/to/hermes/plugins/memory` to target a specific Hermes install

## Configure

Recommended Hermes `config.yaml` examples are published here:

- `docs/integrations/examples/hermes-config.provider-plus-mcp.yaml` (recommended)
- `docs/integrations/examples/hermes-config.mcp-only.yaml` (fallback)

Use the Hermes setup flow:

```bash
hermes memory setup
```

Select `alice` and provide:

- `base_url`: Alice API base URL (example `http://127.0.0.1:8000`)
- `user_id`: Alice user UUID scope

Security rules enforced by the provider:

- `https://` is required for non-loopback hosts.
- `http://` is only allowed for loopback/local development hosts (`localhost`, `127.0.0.1`, `::1`).
- the provider sends user scope in `X-AliceBot-User-Id` header (not URL query params).

Config is saved to:

- `$HERMES_HOME/alice_memory_provider.json`

Manual activation:

```bash
hermes config set memory.provider alice
```

## Verify

Check provider selection:

```bash
hermes memory status
```

Run provider smoke validation from this repository:

```bash
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py
```

Run the one-command bridge demo (provider smoke + MCP smoke):

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

Smoke output includes `structural.bridge_status` with:

- `ready`: bridge-phase config readiness
- `errors`: invalid config state details (if any)
- `legacy_config_keys`: legacy keys still accepted for compatibility
- `lifecycle_hooks`: readiness for `prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`

Optional live prefetch test:

```bash
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py \
  --live-prefetch-query "release gating decision" \
  --alice-base-url "http://127.0.0.1:8000" \
  --alice-user-id "00000000-0000-0000-0000-000000000001"
```

## Single-External-Provider Model

Hermes MemoryManager allows:

- built-in provider (`builtin`) always
- plus at most one external provider (`alice`, `mem0`, `honcho`, etc.)

If a second external provider is registered, Hermes rejects it and keeps the first.

`run_hermes_memory_provider_smoke.py` validates this behavior directly.

## Provider vs MCP vs Skill Pack

Use this split to avoid overlapping integrations:

| Integration | Best for | Runtime shape |
|---|---|---|
| Alice memory provider | always-on continuity prefetch + memory tools inside Hermes memory stack | one external memory provider + built-in `MEMORY.md`/`USER.md` |
| Alice MCP server | broad Alice tool surface in Hermes (`alice_recall`, `alice_resume`, `alice_review_queue`, `alice_review_apply`) | MCP server attached under `mcp_servers` |
| Hermes Alice skill pack | policy and prompting guidance on when/how to call Alice tools | skill instructions layered on top of provider or MCP |

Practical default:

- choose provider plus MCP as the default deployment shape
- choose MCP-only only when provider install is temporarily blocked
- add skill pack when you want stricter workflow prompting and response policy

## Provider Config Keys

`$HERMES_HOME/alice_memory_provider.json` supports:

- `base_url` (string)
- `user_id` (UUID string)
- `timeout_seconds` (float)
- `prefetch_recall_limit` (int)
- `prefetch_max_recent_changes` (int)
- `prefetch_max_open_loops` (int)
- `prefetch_include_non_promotable_facts` (bool)
- `sync_turn_capture_enabled` (bool, default `false`; when omitted, an explicitly configured `bridge_mode: assist` or `bridge_mode: auto` enables `sync_turn` capture)
- `memory_write_capture_enabled` (bool, default `false`)
- `bridge_mode` (string enum: `manual`, `assist`, `auto`; default `assist`)
- `session_end_flush_timeout_seconds` (float, default `5.0`)

`sync_turn_capture_enabled: false` always wins. Use that when you want bridge recall/prefetch behavior without post-turn capture, even if `bridge_mode` is `assist` or `auto`.

Legacy compatibility keys still accepted for shipped configs:

- `prefetch_limit`
- `max_recent_changes`
- `max_open_loops`
- `include_non_promotable_facts`
- `auto_capture`
- `mirror_memory_writes`
- `capture_mode`
