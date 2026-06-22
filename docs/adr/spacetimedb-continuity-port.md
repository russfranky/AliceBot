# ADR: Port Alice's continuity core to a SpacetimeDB module

Status: **Live on maincloud, worker-less.** The module (`spacetime/src/index.ts`) builds
(`spacetime build`), publishes to **hosted SpacetimeDB (maincloud)** as the `alice-continuity`
database, and the full continuity cycle runs there with verified state (evidence below). There is
**no local database** — maincloud is the only runtime. Embedding integration is folded into the
module's procedures; the external worker has been removed.

## Context

Alice today is FastAPI + SQLAlchemy + Postgres (pgvector, pgcrypto, RLS) + a Next.js console.
We are re-platforming the storage and domain logic onto SpacetimeDB. The Postgres app stays in
place and is retired per-feature only as each domain lands on maincloud and is verified.

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| Q1 | Integration shape | **Deep** — the SpacetimeDB module *is* the backend. Clients call reducers/procedures and subscribe to views. |
| Q2 | Module language | **TypeScript** — grounded in the repo (TS frontend); Python is not a module option. |
| Q3 | Embeddings / vectors | **External vector service, procedure-orchestrated.** SpacetimeDB has no native vector type or similarity operators (blob storage only). A **procedure** calls the embedding provider over HTTP and (for semantic recall) an external vector store, then commits the canonical record + external `vectorId` reference transactionally. The provider key lives in a **private `provider_keys` table** (server-only) and is read inside the procedure — never passed as a per-call argument. |
| Q4 | Per-user/workspace isolation | Private tables + **Views** (recommended; RLS is experimental) filtered by `ctx.sender`, plus membership checks inside every reducer/procedure write. |
| Q5 | First-cut scope | Tenancy + capture → continuity objects → revisions/supersession + open loops + entity graph + trust signals + contradiction cases. Retrieval/eval/provider/vNext domains come later. |

## Architecture (worker-less)

```
clients (CLI / MCP / Python ref / Next.js UI)
        │  call reducers + procedures, subscribe to per-caller views
        ▼
SpacetimeDB module (TS) on maincloud  ──ctx.http.fetch──▶  embedding provider (HTTP)
   private tables · reducers · procedures · per-caller views
```

A **procedure** (`captureWithEmbedding` / `embedViaHttp`) makes the outbound embedding HTTP call
itself (`ctx.http.fetch`, outside any transaction) and then writes the result back via
`ctx.withTx`. This replaced the previous external Node worker + `work_queue` dispatch pattern.

## File layout (new, additive)

```
spacetime/                 SpacetimeDB TypeScript module
  src/index.ts             SINGLE module entry: tables + helpers as non-exported const/function,
                           plus schema (default export), reducers, procedures, and views.
                           SpacetimeDB rejects any export that is not a schema/reducer/view/
                           procedure/lifecycle ("not a spacetime export"), so tables/helpers
                           must stay internal — hence one file rather than a split.
  package.json             spacetimedb (npm package `spacetimedb`, NOT the deprecated
                           `@clockworklabs/spacetimedb-sdk`); build = `spacetime build`
  tsconfig.json
clients/python/
  alice_spacetime_reference.py   stdlib-only thin HTTP client (Track B prototype): provision a
                           per-user token, call reducers/procedures, read views via /sql.
```

The external `worker/` directory has been **deleted** — its only remaining responsibility
(embedding) now lives in the module's procedures.

## Module surface (as published)

Tables (14; private unless noted): `workspaces`, `workspace_members`, `capture_events`,
`continuity_objects`, `memory_revisions`, `open_loops`, `artifacts`, `work_queue` (public),
`entities`, `entity_edges`, `trust_signals`, `contradiction_cases`, `provider_keys` (private —
holds the embedding-provider credential + endpoints), `embeddings` (private — external
`vectorId` reference + optional raw bytes for audit).
`artifacts` and `work_queue` are **inert legacy** from the worker era — kept, not used (see
Migrations below for why they cannot be dropped without wiping the database).

Reducers (12): `create_workspace`, `add_member` (owner-only grant), `commit_memory`,
`correct_memory` (revision + supersession), `open_loop_create`, `open_loop_resolve`,
`create_entity`, `link_entities`, `record_trust_signal`, `open_contradiction`,
`resolve_contradiction`, `set_provider_key` (owner-only; writes the provider credential into the
private `provider_keys` table).

Procedures (5): `capture_with_embedding` (capture event + candidate object + first revision, with
the embedding fetched inline), `embed_via_http` (re-embed an existing object), `recall_lexical`
(vector-free keyword recall — scores the caller's non-superseded objects by lexical overlap, ranks
in TS, returns top-N JSON; no HTTP/secrets/vectors), `embed_semantic` (index an object: read
content + server-side key in tx1 → embed over HTTP → store the external `vectorId` + bytes in
tx2), `recall_semantic` (embed the query over HTTP → ask the external vector store for nearest
objectIds over HTTP → read those rows by id in a tx → return ranked JSON).

Views (9, public, per-caller): `my_workspaces`, `my_workspace_members`, `my_continuity_objects`,
`my_open_loops`, `my_artifacts`, `my_entities`, `my_entity_edges`, `my_trust_signals`,
`my_contradictions`.

(Exported camelCase names are snake_case at the call/SQL boundary.)

## Isolation model (Q4)

- `ctx.sender` (SpacetimeDB Identity) replaces Postgres `app.current_user_id`.
- **Writes:** every reducer calls `assertMember(ctx, workspaceId)`; procedures repeat the same
  membership check inside `ctx.withTx` (the caller must be in `workspace_members` for that
  workspace, else `SenderError`).
- **Reads:** canonical tables are private. They are invisible to **non-owner** clients — a
  non-owner `SELECT` on a private table is denied (`"no such table … it may be marked private"`,
  verified). Clients read public per-caller views that return only rows in their workspaces.
- **Owner caveat (verified):** the *database owner* (the publishing identity) has a SQL privilege
  bypass and **can** read private tables, including `provider_keys.api_key`. This is the documented
  operator/owner power, not a client-facing leak — end-user tokens cannot reach it. Do not treat a
  private table as a secret store against the database owner; it *is* secret against everyone else.

## Trust / correction semantics preserved

- `capture_with_embedding` creates a `candidate` object at `trust_class='unverified'` — never
  auto-promoted.
- `commit_memory` is explicit, caller-supplied trust promotion (`status='committed'`).
- `correct_memory` adds a revision, supersedes the prior (`superseded_by`), repoints
  `current_revision_id`, marks `user_confirmed`, and **resets `embedding_ref`** (stale vector);
  re-embedding is done by calling the `embed_via_http` procedure.

## Verification (observed live on maincloud, this session)

CLI identity: `c200765e7a24…` (russfranky), owner of workspace `1` ("russfranky").

| Read | Observed |
|------|----------|
| `SELECT id, name FROM my_workspaces` | `1 | russfranky` |
| `SELECT id, status, trust_class, embedding_ref FROM my_continuity_objects` | `1 committed/user_confirmed/vec:http:200:1`; `3 candidate/unverified/vec:http:200`; `4 candidate/unverified/vec:http:200` |

Object 1 shows the full cycle (captured → committed → corrected → re-embedded via
`embed_via_http`, leaving `vec:http:200:1`); objects 3 and 4 are fresh `capture_with_embedding`
candidates. The `vec:http:200` refs prove the procedure's outbound `ctx.http.fetch` succeeded
(HTTP 200) and the write-back ran inside `ctx.withTx`. Reads go through the per-caller views;
the private tables are not visible to raw SQL, confirming Q4 isolation.

`recall_lexical` verified on the same db: `recall_lexical 1 "worker demo" 10` → object 3,
score 4 (two whole-word hits); `"board"` → object 1, content `"Q3 board pack moved to Friday"`
(its **corrected** revision — recall follows `current_revision_id`); `"zzqqxx"` → `[]`
(zero-score rows filtered). Also verified over plain HTTP through the Python thin-client with a
fresh per-user token: a brand-new identity captured + committed an object and recalled it,
seeing only its own workspace's rows — confirming both the `/call`-returns-procedure-value path
and per-user isolation.

**Semantic indexing (`embed_semantic`) verified end-to-end** against a real external endpoint
(httpbin echo) with a **dummy** key stored via `set_provider_key`. `embed_semantic 1 3 echo-test`
returned `status 200`, `authEcho "Bearer DUMMYKEY123"` (httpbin echoed the exact Authorization
header — proving the key was read from the private `provider_keys` table server-side and was
**never** a call argument), `inputEcho "remember the worker-less demo"` (tx1 read the object's
current-revision content), `dim 32`, `embeddingRowId 1`. Independently confirmed via the public
view: object 3's `embedding_ref` became `ext:echo-test:1:3` (the tx2 write landed). Isolation
re-verified: a non-owner token reading `provider_keys`/`continuity_objects` is denied, while the
owner CLI can read them (owner privilege bypass). `recall_semantic` returns `[]` when pointed at a
non-store endpoint (no nearest-neighbor ids) — its embed + read-by-id legs use the same SDK calls
as the verified `recall_lexical`; the **only** unverified seam is a real external vector store.

## Resolved SDK details

1. Identity / time columns: `t.identity()` / `t.timestamp()`.
2. Secondary indexes: inline `colName: t.u64().index('btree')`.
3. `ctx.db.<table>.insert(row)` returns the inserted row with the assigned autoInc id (`id: 0n`).
4. Row type for views: `<tableConst>.rowType` — requires standalone `const` tables.
5. Module entry: **single file**; only schema/reducer/view/procedure/lifecycle may be exported.
6. Nullable column: `t.option(t.timestamp())`, inserted as `undefined`.
7. Auth: `throw new SenderError(...)`; reducer/SQL boundary uses **snake_case** names.
8. Procedure: `procedure({args}, returnType, (ctx,args)=>…)`; `ctx.http.fetch(url,{method,headers,
   body,timeout})` is synchronous (`.status` / `.text()` / `.json()`) and must run **outside** the
   transaction; DB access only inside `ctx.withTx`, which is deterministic and may be retried.
9. **`ctx.withTx` returns a value** — its callback's return value is returned to the procedure.
   That is the idiom for reading data *out* of a transaction; we use it everywhere instead of
   assigning to outer-scope variables (which the retry semantics make unsafe). No `withTx` body in
   this module mutates outer state.
10. **Throwing inside `withTx` (incl. `SenderError`) rolls back that transaction** — used for the
    in-tx membership re-check on writes.
11. **A procedure may open multiple sequential transactions**, each individually atomic, but the
    **procedure as a whole is NOT atomic**
    ([transactions/atomicity](https://spacetimedb.com/docs/databases/transactions-atomicity)). So
    HTTP runs *between* transactions, and **all writes are concentrated in a single final tx**
    (`embed_semantic` writes only in tx2; the recall procedures don't write) — there is no
    multi-write partial-failure exposure.
12. **Inside `withTx`, the tx accesses the database "in all the same ways as a `ReducerContext`"**
    (procedures doc). So `tx.db.<table>.id.find/.update/.delete(...)` and `.<indexedCol>.filter(value)`
    — the same table API the reducers use — are valid inside a procedure transaction. Confirmed
    transitively by the docs and directly on maincloud (`embed_semantic` finds/inserts/updates/
    deletes inside tx2 and the writes land).

## Schema migrations — what maincloud allows (cited)

Republishing attempts an automatic migration, and SpacetimeDB classifies each change as **safe**,
**breaking**, or **forbidden** ([Automatic Migrations](https://spacetimedb.com/docs/databases/automatic-migrations)):

- **Safe (data preserved, no client break):** adding tables, adding indexes, adding/removing
  AutoInc, private→public, adding reducers, removing Unique constraints.
- **Breaking (data preserved, may break outdated clients):** adding a column **at the end of the
  table with a default**, changing/removing reducers, public→private, removing Primary Key,
  removing indexes.
- **Forbidden (automatic migration fails):** **removing tables**, **removing/modifying/renaming/
  reordering columns**, adding a column mid-table or without a default, changing scheduling-table
  status, adding Unique/Primary-Key constraints.

For a forbidden change the only override is `spacetime publish --delete-data`, which **resets the
entire database (all data lost)** — unacceptable on the live db. The documented data-preserving
alternative, [Incremental Migrations](https://spacetimedb.com/docs/databases/incremental-migrations),
is **additive only**: "SpacetimeDB does not provide built-in support for general schema-modifying
migrations" — you create a `table_v2`, read-through/lazy-copy from the old table, and keep both in
sync. It provides **no mechanism to drop a table or column while preserving data**.

**Consequence:** the inert `work_queue` / `artifacts` tables **cannot be dropped** on the populated
maincloud db without `--delete-data` (total wipe). They stay as harmless legacy. Removing them is
only possible during a future clean rebuild/migration of the whole database. This is now a
documented limitation, not a pending task.

This also constrains future schema work: `embedding_ref` is `t.string()` and its **type cannot be
changed** in place. A real vector type would arrive as a **new appended column with a default**, or
a `continuity_objects_v2` table via the incremental pattern — never an in-place column rewrite.

## Open questions (status)

- **Table/column drops with data preserved** — **ANSWERED (above):** not supported; keep the
  legacy tables.
- **Secrets / API-key handling inside procedures** — **RESOLVED.** Pattern: store the credential in
  a **private table** (`provider_keys`), written by an owner-only reducer, and read it inside the
  procedure — so the key never transits as a (loggable) per-call argument. Verified: a non-owner
  cannot read the table; the procedure reads the key server-side and sends it in the outbound
  `Authorization` header (httpbin echoed it back). Caveat recorded above: the *database owner* can
  still read the key via SQL — it is secret against clients, not against the operator. (The docs'
  alternative — client passes `apiKey` per call — is also supported but less safe; not used.)
- **Native vectors / similarity search** — **answered: none in-module.** SpacetimeDB stores
  embeddings only as a binary blob (`t.array(t.u8())`) with no similarity/kNN operators, so the
  nearest-neighbor search lives in an **external vector store** the procedure queries over HTTP
  (`recall_semantic`). The **lexical** half (`recall_lexical`) is fully live; the **semantic** half
  is built and its HTTP+transaction orchestration is verified. To make it production-real:
  1. `set_provider_key` with a **real** embedding endpoint + key + an external vector-store query
     endpoint (config only — no code change).
  2. Two small code edits in `embed_semantic`: (a) parse the provider's returned embedding floats
     and pack them into `bytes` (it currently stores a byte-prefix of the echo response as a
     placeholder); (b) add the external-store **upsert** HTTP call so the vector is indexed (today
     it stores the `vectorId` reference locally but does not push the vector out — only the query
     leg exists, in `recall_semantic`).
  The hard parts — server-side key handling, HTTP-outside-tx orchestration, retry-safe `withTx`
  bodies, per-caller isolation — are done and verified.
- **`/sql` feature matrix** — `ORDER BY` is unsupported (observed); the full matrix
  (joins/aggregations) is not documented in sources reviewed.
- **Maincloud limits / cost / backups** — maincloud is documented as managed (scales to zero,
  handles backups); concrete limits/retention/pricing not enumerated in sources reviewed.

## Explicitly NOT done in this cut

- No destructive changes to the Postgres app. SQLAlchemy, Alembic, the FastAPI routes, the CLI,
  and MCP remain in place; they will later be **re-pointed** as thin SpacetimeDB clients (see
  `spacetimedb-track-b-plan.md`), not deleted, and only with explicit scope-and-data sign-off.
- The Next.js UI is untouched.
- No data migration from the existing Postgres yet.
- The embedding HTTP call is a stub endpoint pending the secrets answer; the write-back path is
  validated by the `vec:http:200` evidence above.

## How to run (maincloud — no local database)

```bash
# build + publish the module to maincloud (requires `spacetime login`)
spacetime publish --server maincloud -y -p spacetime alice-continuity

# exercise the cycle as your logged-in identity
spacetime call --server maincloud -y alice-continuity create_workspace "My Workspace"
spacetime call --server maincloud -y alice-continuity capture_with_embedding 1 "remember the Q3 board pack" "cli" "decision"
spacetime sql  --server maincloud -y alice-continuity "SELECT id, status, trust_class, embedding_ref FROM my_continuity_objects"

# Python client (defaults to maincloud / alice-continuity, no local DB)
python3 clients/python/alice_spacetime_reference.py
```
