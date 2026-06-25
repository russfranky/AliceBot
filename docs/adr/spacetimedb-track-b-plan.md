# Track B plan: re-point Alice's Python surfaces as thin SpacetimeDB HTTP clients

Status: **CLI + MCP + FastAPI surfaces live (continuity + execution).** `alice capture` / `alice
recall` and the `alice exec` group (tasks, tools, approvals, budgets, real HTTP runs) route to the
live module behind `--backend spacetimedb`; the MCP server exposes the same surface as eleven
additive `alice_spacetime_*` tools gated on `ALICE_BACKEND=spacetimedb`; the FastAPI app exposes it
as eleven additive `/spacetime/*` routes (outside `/v0/`) under the same flag. All three are
non-destructive (the Postgres default is untouched when the flag is off). The Next.js console is the
remaining re-point; Track C (data migration) is still deferred.

## Proven foundation

`clients/python/alice_spacetime_reference.py` (standalone, stdlib-only) already drives the live
module over HTTP with a per-user Bearer token: `create_workspace` → `capture_with_embedding` →
`commit_memory` via `POST /call/:name` (reducers and procedures share the endpoint), reads via
`POST /sql` on the `my_*` views. The per-caller view returns only that identity's rows — isolation
holds from Python. So the adapter surface is four methods: `provision_identity()`,
`call(reducer, args, token)`, `call_proc(name, args, token)`, `sql(query, token)`.

## Key simplification

Almost every Alice user operation takes only `u64` + strings — **no identity args**:
`capture_with_embedding(workspaceId, rawContent, source, kind)`, `commit_memory(objectId, trustClass)`,
`correct_memory(objectId, newContent)`, `open_loop_create/resolve(...)`, `create_workspace(name)`.
These JSON-array-encode trivially. The **only** identity-bearing reducer is the admin
`add_member(workspaceId, member: Identity, role)`, which needs SATS identity encoding — so it stays
on the TS tooling (or a small dedicated encoder), not the hot Python path.

## Adapter design

A single `SpacetimeClient` (the reference is the prototype):
- `call(reducer, args: list, token)` → `POST /v1/database/<db>/call/<reducer>`, JSON array body,
  `Authorization: Bearer <token>` (returns status; for reducers).
- `call_proc(name, args, token)` → same `/call/<name>` endpoint but returns the procedure's body —
  used for `capture_with_embedding`, `recall_lexical`, `recall_semantic`, `embed_semantic`.
- `sql(query, token)` → `POST /v1/database/<db>/sql`, text body, `Authorization: Bearer <token>`.
- Reads go to the `my_*` views (per-caller scoped); private tables are never queried directly.

## Operation mapping (existing Alice surface → module)

| Alice operation | Module |
|-----------------|--------|
| capture | `capture_with_embedding` procedure |
| commit / correct memory | `commit_memory` / `correct_memory` reducers |
| open loops | `open_loop_create` / `open_loop_resolve` reducers |
| recall / resume / brief reads | `SELECT … FROM my_continuity_objects / my_open_loops / my_artifacts` |
| list workspaces | `SELECT … FROM my_workspaces` |
| (admin) grant worker membership | `add_member` (TS tooling — identity arg) |
| **exec** task create / register+bind tool | `create_task` / `register_tool` / `bind_task_tool` reducers (`alice exec task-create / tool-register / tool-bind`) |
| **exec** request / resolve approval | `request_approval` / `resolve_approval` reducers (`alice exec approval-request / approval-resolve`) |
| **exec** budget + enqueue + execute | `set_budget` / `enqueue_task_run` reducers + `execute_next_task_run` procedure (`alice exec budget-set / enqueue / execute`) |
| **exec** status reads | `SELECT … FROM my_tasks / my_tools / my_approvals / my_task_runs / my_tool_executions / my_budgets / my_task_artifacts` (`alice exec status`) |

## Token lifecycle & storage (resolved + implemented in the CLI backend — reuses `vnext_secrets.SecretProvider`)

**Done:** `spacetime_backend.py` stores the token via `default_secret_provider().set_secret(
"spacetime-token:<identity>", token)` (encrypted at rest); the local state file holds only the
non-secret identity + workspace + `token_ref`. Verified: an isolated CLI run wrote **no** plaintext
token to the state file and recalled successfully by reading the token back from the secret store. A
standalone fallback (no app package) keeps the token in the 0600 state file. The spec below is the
full design.

Alice already has the right primitive in `apps/api/src/alicebot_api/vnext_secrets.py`: a
`SecretProvider` protocol (`get_secret`/`set_secret`/`has_secret`) with an `env:`-ref provider and a
`LocalEncryptedFileSecretProvider` (encrypted at rest; documented as swappable for Keychain/libsecret).
SpacetimeDB tokens map onto it directly — no new secret mechanism:

- **Mapping table** (non-secret): Alice user/workspace → SpacetimeDB identity hex + the token's
  `secret_ref`. The identity hex is not secret; the token is.
- **Token storage:** `set_secret("spacetime-token:<identity_hex>", token)` on provision;
  `get_secret(ref)` per request → `Authorization: Bearer <token>`.
- **Redaction is free:** `is_secret_key` already matches any field containing "token", so
  `redact_secret_fields` keeps SpacetimeDB tokens out of logs, API responses, and CLI output under
  Alice's existing rule — no new redaction code.
- **Lifecycle:** provision on first use (`POST /v1/identity` → persist identity + token); on `401`,
  re-provision or exchange via `POST /v1/identity/websocket-token`; the worker service identity uses
  the same path under `spacetime-token:worker-service`, granted membership via `add_member`.

## Authentication & identity provider

SpacetimeDB modules are reachable on the open internet, so OIDC authentication is required for any
real multi-user deployment. SpacetimeDB accepts OIDC tokens from any provider; the identity flows to
`ctx.sender` — our isolation key (Q4), so the choice of provider does not change the isolation model.

| Option | What it is | When to use |
|--------|-----------|-------------|
| **Self-provisioned** (`POST /v1/identity`) | Host-issued identity/token, stored in Alice's `SecretProvider`. Proven in the reference adapter. | Dev / single-tenant / now |
| **SpacetimeAuth** (managed OIDC) | SpacetimeDB's managed provider — user management + token issuance. **Beta** (may change), and "not as feature-rich" as third-party. | When onboarding real users and a turnkey managed option is wanted |
| **Third-party OIDC** (Auth0 / Clerk / Keycloak) | Standard OIDC providers, more feature-rich. | When advanced auth features / customization are needed |

Recommendation: stay on self-provisioned for now (proven, dependency-free); adopt an OIDC layer only
when onboarding real end-users. Do **not** enable SpacetimeAuth yet — it's beta, optional, and was
offered for an empty database (`alice`); make it a deliberate decision, not a button click. Whichever
provider, `token → ctx.sender → assertMember`/views is unchanged.

Token-lifecycle caution (from the docs): SpacetimeDB distinguishes **long-lived** server-issued tokens
from **short-lived** WebSocket tokens used by transports that can't send `Authorization` headers (e.g.
Unity WebGL); don't overwrite the long-lived token with the short-lived one on reconnect. For Alice
this is already handled: the Python surfaces use HTTP with `Authorization: Bearer` (header-capable, so
they hold the long-lived token), and the TS worker uses the client SDK, which performs the
`POST /v1/identity/websocket-token` exchange internally. So store only the **long-lived** token in the
`SecretProvider`; let the SDK derive short-lived ws-tokens.

## Rollout strategy (non-destructive)

1. Add a `SpacetimeBackend` behind Alice's existing internal persistence interface — do **not**
   delete the SQLAlchemy/Postgres path. **Done** (`spacetime_backend.py`).
2. Switch one surface at a time (CLI → MCP → FastAPI) behind a config flag once parity is proven.
   **CLI done:** `capture`/`recall` + the `exec` execution group route via `--backend spacetimedb`,
   verified end-to-end on maincloud (approval gate, real HTTP execution, idempotent replay) with
   `qa_smoke` 23/23. **MCP done:** `alice_spacetime_*` tools gated on `ALICE_BACKEND=spacetimedb`
   (hidden + non-dispatchable when off; Postgres 73-tool surface unchanged), same flow verified via
   `call_mcp_tool` on maincloud; MCP unit suite 20/20. **FastAPI done:** eleven `/spacetime/*` routes
   under the same flag (404 when off; mounted outside `/v0/` to bypass legacy-v0 auth; module rejects
   -> 400), same flow verified on maincloud through the route handlers; main unit suite 68/68.
   **Next:** the Next.js console.
3. Keep both backends runnable until Track C migration + parity sign-off.

## Open decisions for execution (need a human call)

- When workspaces are provisioned per Alice user (e.g., `create_workspace` at signup).
- The SATS `Identity` encoder for the rare `add_member` path from Python (or keep it TS-only).
- Idempotency keys for re-pointed writes (capture/commit replay safety). **Confirmed:** SpacetimeDB
  has **no built-in** request-id/dedup mechanism. **Implemented in-module:** an `applied_requests`
  table (`requestId` with `.unique()`) + a `requestId` arg on `capture_with_embedding` (procedure —
  pre-check skips the embed HTTP on replay) and `correct_memory` (reducer — atomic no-op on replay);
  the unique constraint backstops the concurrent race. Verified on maincloud (qa_smoke STDB-IDEM:
  two same-`requestId` captures → one object). The CLI backend generates a `uuid4` per logical write.

## Deferred to Track C

Data migration: read existing Postgres continuity rows and replay them as reducer calls
(workspaces → memberships → objects → revisions → open loops), preserving lineage, idempotent.
