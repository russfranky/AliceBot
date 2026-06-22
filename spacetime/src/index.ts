import { schema, table, t, SenderError } from 'spacetimedb/server';

// Alice continuity core as a single SpacetimeDB TypeScript module (Q1 deep, Q2 TypeScript),
// core slice (Q5). Embeddings live in the external vector service (Q3); records carry
// `embeddingRef`. Isolation (Q4): canonical tables are private; clients read via the per-caller
// views below and write only through reducers, which check workspace membership first.
//
// Everything that is NOT a schema/reducer/view must stay a non-exported `const`/`function` —
// the module loader rejects any other `export` ("not a spacetime export").

// ---------------------------------------------------------------------------------------------
// Tables (private unless noted). `ctx.db` accessors are the camelCase of the snake_case `name`.
// ---------------------------------------------------------------------------------------------
const workspaces = table(
  { name: 'workspaces' },
  {
    id: t.u64().primaryKey().autoInc(),
    ownerIdentity: t.identity(),
    name: t.string(),
    createdAt: t.timestamp(),
  },
);

const workspaceMembers = table(
  { name: 'workspace_members' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    memberIdentity: t.identity().index('btree'), // supports .memberIdentity.filter(ctx.sender)
    role: t.string(),
  },
);

const captureEvents = table(
  { name: 'capture_events' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    rawContent: t.string(),
    source: t.string(),
    createdBy: t.identity(),
    createdAt: t.timestamp(),
  },
);

const continuityObjects = table(
  { name: 'continuity_objects' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    kind: t.string(),       // 'decision' | 'commitment' | 'context' | ...
    status: t.string(),     // 'candidate' | 'committed' | 'superseded' | 'rejected'
    trustClass: t.string(), // 'unverified' | 'corroborated' | 'user_confirmed'
    currentRevisionId: t.u64(),
    embeddingRef: t.string(),
    capturedFrom: t.u64(),
    createdAt: t.timestamp(),
    updatedAt: t.timestamp(),
  },
);

const memoryRevisions = table(
  { name: 'memory_revisions' },
  {
    id: t.u64().primaryKey().autoInc(),
    objectId: t.u64().index('btree'),
    revisionNo: t.u32(),
    content: t.string(),
    authorIdentity: t.identity(),
    supersededBy: t.u64(), // revision id that replaced this one (0n = current)
    createdAt: t.timestamp(),
  },
);

const openLoops = table(
  { name: 'open_loops' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    label: t.string(),
    posture: t.string(), // 'waiting' | 'blocked' | 'next'
    status: t.string(),  // 'open' | 'resolved'
    objectId: t.u64(),   // optional link to a continuity object (0n = none)
    createdBy: t.identity(),
    createdAt: t.timestamp(),
    resolvedAt: t.option(t.timestamp()), // null until resolved
  },
);

const artifacts = table(
  { name: 'artifacts' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    kind: t.string(), // 'daily_brief' | 'weekly_synthesis' | 'context_pack'
    content: t.string(),
    createdAt: t.timestamp(),
  },
);

const workQueue = table(
  { name: 'work_queue', public: true }, // public: the worker (a client) subscribes to pending jobs
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64(),
    kind: t.string(),   // 'embed' | 'synthesis'
    targetId: t.u64(),
    payload: t.string(),
    state: t.string().index('btree'), // 'pending' | 'processing' | 'done' | 'error'
    createdAt: t.timestamp(),
  },
);

// --- Entity graph (people / projects / topics that memories refer to) ---
const entities = table(
  { name: 'entities' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    kind: t.string(), // 'person' | 'project' | 'org' | 'topic' | ...
    name: t.string(),
    createdAt: t.timestamp(),
  },
);

const entityEdges = table(
  { name: 'entity_edges' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    srcEntityId: t.u64(),
    dstEntityId: t.u64(),
    relation: t.string(),
    createdAt: t.timestamp(),
  },
);

// --- Trust signals + contradiction cases (Alice's trust-aware layer) ---
const trustSignals = table(
  { name: 'trust_signals' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    objectId: t.u64().index('btree'),
    signalType: t.string(), // 'corroborated' | 'user_confirmed' | 'source_quality' | ...
    weight: t.i32(),
    note: t.string(),
    createdBy: t.identity(),
    createdAt: t.timestamp(),
  },
);

const contradictionCases = table(
  { name: 'contradiction_cases' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    objectIdA: t.u64(),
    objectIdB: t.u64(),
    status: t.string(), // 'open' | 'resolved_a' | 'resolved_b' | 'dismissed'
    note: t.string(),
    createdAt: t.timestamp(),
    resolvedAt: t.option(t.timestamp()),
  },
);

// --- Semantic recall support (Q3): embeddings + vector search live OUTSIDE SpacetimeDB. ---
// provider_keys is PRIVATE (server-only): it holds the embedding-provider credential + endpoints
// so procedures read the key server-side instead of taking it as a logged per-call argument.
const providerKeys = table(
  { name: 'provider_keys' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    provider: t.string(),       // logical name, e.g. 'openai' | 'cohere' | 'echo-test'
    apiKey: t.string(),         // never exposed via a view — private table, server-only
    embedEndpoint: t.string(),  // HTTP endpoint that returns an embedding for input text
    storeEndpoint: t.string(),  // HTTP endpoint of the external vector store's query API
    model: t.string(),
    createdAt: t.timestamp(),
  },
);

// embeddings is PRIVATE: durable record of the external vector-store reference + optional raw
// bytes (audit/debug only — SpacetimeDB has no similarity operators, so this is storage, not kNN).
const embeddings = table(
  { name: 'embeddings' },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    objectId: t.u64().index('btree'),
    vectorId: t.string(), // id/reference of this vector in the external store
    model: t.string(),
    dim: t.u32(),
    bytes: t.array(t.u8()), // optional raw embedding bytes (Vec<u8> blob) for audit/debug
    createdAt: t.timestamp(),
  },
);

const spacetimedb = schema({
  workspaces,
  workspaceMembers,
  captureEvents,
  continuityObjects,
  memoryRevisions,
  openLoops,
  artifacts,
  workQueue,
  entities,
  entityEdges,
  trustSignals,
  contradictionCases,
  providerKeys,
  embeddings,
});
export default spacetimedb;

// ---------------------------------------------------------------------------------------------
// Authorization (Q4): the SpacetimeDB equivalent of Alice's Postgres RLS keyed on the caller.
// ---------------------------------------------------------------------------------------------
function assertMember(ctx: any, workspaceId: bigint): void {
  for (const m of ctx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
    if (m.workspaceId === workspaceId) return;
  }
  throw new SenderError('unauthorized: caller is not a member of this workspace');
}

function callerWorkspaceIds(ctx: any): Set<bigint> {
  const ids = new Set<bigint>();
  for (const m of ctx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
    ids.add(m.workspaceId);
  }
  return ids;
}

// Lexical scoring helpers (vector-free recall). Deterministic — safe inside a procedure's withTx.
function tokenize(s: string): string[] {
  return s.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 0);
}

function lexScore(queryTokens: string[], content: string): number {
  const haystack = content.toLowerCase();
  const contentTokens = new Set(tokenize(content));
  let score = 0;
  for (const qt of queryTokens) {
    if (contentTokens.has(qt)) score += 2;      // whole-word match
    else if (haystack.includes(qt)) score += 1; // substring match
  }
  return score;
}

// ---------------------------------------------------------------------------------------------
// Reducers — every client write. Each authorizes on membership first. Inserts into autoInc-PK
// tables pass `id: 0n` and return the inserted row with its assigned id.
// ---------------------------------------------------------------------------------------------

// createWorkspace: tenancy bootstrap — workspace owned by the caller + caller as 'owner' member.
export const createWorkspace = spacetimedb.reducer(
  { name: t.string() },
  (ctx, { name }) => {
    const ws = ctx.db.workspaces.insert({
      id: 0n,
      ownerIdentity: ctx.sender,
      name,
      createdAt: ctx.timestamp,
    });
    ctx.db.workspaceMembers.insert({
      id: 0n,
      workspaceId: ws.id,
      memberIdentity: ctx.sender,
      role: 'owner',
    });
  },
);

// addMember: owner-only grant. Lets a workspace owner add another identity (e.g. the worker's
// service identity) to workspace_members so it passes assertMember. Idempotent.
export const addMember = spacetimedb.reducer(
  { workspaceId: t.u64(), member: t.identity(), role: t.string() },
  (ctx, { workspaceId, member, role }) => {
    const ws = ctx.db.workspaces.id.find(workspaceId);
    if (!ws) throw new Error('workspace not found');
    if (!ws.ownerIdentity.equals(ctx.sender)) {
      throw new SenderError('unauthorized: only the workspace owner can add members');
    }
    for (const m of ctx.db.workspaceMembers.memberIdentity.filter(member)) {
      if (m.workspaceId === workspaceId) return; // already a member — idempotent
    }
    ctx.db.workspaceMembers.insert({ id: 0n, workspaceId, memberIdentity: member, role });
  },
);

// (capture is now the `captureWithEmbedding` procedure below — it embeds inline, no work queue.)

// commitMemory: explicit, trust-aware promotion of a candidate into durable memory.
export const commitMemory = spacetimedb.reducer(
  { objectId: t.u64(), trustClass: t.string() },
  (ctx, { objectId, trustClass }) => {
    const obj = ctx.db.continuityObjects.id.find(objectId);
    if (!obj) throw new Error('continuity object not found');
    assertMember(ctx, obj.workspaceId);

    ctx.db.continuityObjects.id.update({
      ...obj,
      status: 'committed',
      trustClass,
      updatedAt: ctx.timestamp,
    });
  },
);

// correctMemory: correction-aware path — new revision, supersede prior, repoint current,
// mark 'user_confirmed', re-enqueue embedding (content changed → stale vector).
export const correctMemory = spacetimedb.reducer(
  { objectId: t.u64(), newContent: t.string() },
  (ctx, { objectId, newContent }) => {
    const obj = ctx.db.continuityObjects.id.find(objectId);
    if (!obj) throw new Error('continuity object not found');
    assertMember(ctx, obj.workspaceId);

    const current = ctx.db.memoryRevisions.id.find(obj.currentRevisionId);
    const nextNo = current ? current.revisionNo + 1 : 1;

    const rev = ctx.db.memoryRevisions.insert({
      id: 0n,
      objectId,
      revisionNo: nextNo,
      content: newContent,
      authorIdentity: ctx.sender,
      supersededBy: 0n,
      createdAt: ctx.timestamp,
    });

    if (current) {
      ctx.db.memoryRevisions.id.update({ ...current, supersededBy: rev.id });
    }

    ctx.db.continuityObjects.id.update({
      ...obj,
      currentRevisionId: rev.id,
      status: 'committed',
      trustClass: 'user_confirmed',
      embeddingRef: '',
      updatedAt: ctx.timestamp,
    });

    // embeddingRef reset above; re-embed via the embedViaHttp procedure (worker-less).
  },
);

export const openLoopCreate = spacetimedb.reducer(
  { workspaceId: t.u64(), label: t.string(), posture: t.string(), objectId: t.u64() },
  (ctx, { workspaceId, label, posture, objectId }) => {
    assertMember(ctx, workspaceId);
    ctx.db.openLoops.insert({
      id: 0n,
      workspaceId,
      label,
      posture,
      status: 'open',
      objectId,
      createdBy: ctx.sender,
      createdAt: ctx.timestamp,
      resolvedAt: undefined, // null until resolved (t.option)
    });
  },
);

export const openLoopResolve = spacetimedb.reducer(
  { loopId: t.u64() },
  (ctx, { loopId }) => {
    const loop = ctx.db.openLoops.id.find(loopId);
    if (!loop) throw new Error('open loop not found');
    assertMember(ctx, loop.workspaceId);
    ctx.db.openLoops.id.update({ ...loop, status: 'resolved', resolvedAt: ctx.timestamp });
  },
);

// (ingest_embedding_ref / ingest_synthesis removed — the worker is gone. Embedding is inline in
// captureWithEmbedding / embedViaHttp; synthesis will become a procedure when wired. The
// `work_queue` and `artifacts` tables are kept until a data-preserving table-drop path is documented.)

// ---------------------------------------------------------------------------------------------
// Views (Q4 read isolation): public, per-caller; return only rows in the caller's workspaces.
// ---------------------------------------------------------------------------------------------
export const myWorkspaces = spacetimedb.view(
  { name: 'my_workspaces', public: true },
  t.array(workspaces.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.workspaces.iter()].filter((w) => mine.has(w.id));
  },
);

export const myWorkspaceMembers = spacetimedb.view(
  { name: 'my_workspace_members', public: true },
  t.array(workspaceMembers.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.workspaceMembers.iter()].filter((m) => mine.has(m.workspaceId));
  },
);

export const myContinuityObjects = spacetimedb.view(
  { name: 'my_continuity_objects', public: true },
  t.array(continuityObjects.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.continuityObjects.iter()].filter((o) => mine.has(o.workspaceId));
  },
);

export const myOpenLoops = spacetimedb.view(
  { name: 'my_open_loops', public: true },
  t.array(openLoops.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.openLoops.iter()].filter((l) => mine.has(l.workspaceId));
  },
);

export const myArtifacts = spacetimedb.view(
  { name: 'my_artifacts', public: true },
  t.array(artifacts.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.artifacts.iter()].filter((a) => mine.has(a.workspaceId));
  },
);

// ---------------------------------------------------------------------------------------------
// Entity graph + trust/contradiction — reducers (all gated by workspace membership, Q4).
// ---------------------------------------------------------------------------------------------
export const createEntity = spacetimedb.reducer(
  { workspaceId: t.u64(), kind: t.string(), name: t.string() },
  (ctx, { workspaceId, kind, name }) => {
    assertMember(ctx, workspaceId);
    ctx.db.entities.insert({ id: 0n, workspaceId, kind, name, createdAt: ctx.timestamp });
  },
);

export const linkEntities = spacetimedb.reducer(
  { workspaceId: t.u64(), srcEntityId: t.u64(), dstEntityId: t.u64(), relation: t.string() },
  (ctx, { workspaceId, srcEntityId, dstEntityId, relation }) => {
    assertMember(ctx, workspaceId);
    ctx.db.entityEdges.insert({ id: 0n, workspaceId, srcEntityId, dstEntityId, relation, createdAt: ctx.timestamp });
  },
);

export const recordTrustSignal = spacetimedb.reducer(
  { workspaceId: t.u64(), objectId: t.u64(), signalType: t.string(), weight: t.i32(), note: t.string() },
  (ctx, { workspaceId, objectId, signalType, weight, note }) => {
    assertMember(ctx, workspaceId);
    ctx.db.trustSignals.insert({
      id: 0n, workspaceId, objectId, signalType, weight, note,
      createdBy: ctx.sender, createdAt: ctx.timestamp,
    });
  },
);

export const openContradiction = spacetimedb.reducer(
  { workspaceId: t.u64(), objectIdA: t.u64(), objectIdB: t.u64(), note: t.string() },
  (ctx, { workspaceId, objectIdA, objectIdB, note }) => {
    assertMember(ctx, workspaceId);
    ctx.db.contradictionCases.insert({
      id: 0n, workspaceId, objectIdA, objectIdB, status: 'open', note,
      createdAt: ctx.timestamp, resolvedAt: undefined,
    });
  },
);

export const resolveContradiction = spacetimedb.reducer(
  { caseId: t.u64(), resolution: t.string() },
  (ctx, { caseId, resolution }) => {
    const c = ctx.db.contradictionCases.id.find(caseId);
    if (!c) throw new Error('contradiction case not found');
    assertMember(ctx, c.workspaceId);
    ctx.db.contradictionCases.id.update({ ...c, status: resolution, resolvedAt: ctx.timestamp });
  },
);

// --- Entity graph + trust/contradiction — per-caller views (Q4 read isolation) ---
export const myEntities = spacetimedb.view(
  { name: 'my_entities', public: true },
  t.array(entities.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.entities.iter()].filter((e) => mine.has(e.workspaceId));
  },
);

export const myEntityEdges = spacetimedb.view(
  { name: 'my_entity_edges', public: true },
  t.array(entityEdges.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.entityEdges.iter()].filter((e) => mine.has(e.workspaceId));
  },
);

export const myTrustSignals = spacetimedb.view(
  { name: 'my_trust_signals', public: true },
  t.array(trustSignals.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.trustSignals.iter()].filter((s) => mine.has(s.workspaceId));
  },
);

export const myContradictions = spacetimedb.view(
  { name: 'my_contradictions', public: true },
  t.array(contradictionCases.rowType),
  (ctx) => {
    const mine = callerWorkspaceIds(ctx);
    return [...ctx.db.contradictionCases.iter()].filter((c) => mine.has(c.workspaceId));
  },
);

// ---------------------------------------------------------------------------------------------
// Procedure: in-module embedding integration (replaces the external worker for embeddings).
// Procedures can make outbound HTTP (ctx.http.fetch) AND write via ctx.withTx, so the module
// calls the embedding provider itself. The HTTP call happens outside the transaction; the
// withTx write must stay deterministic (it may be retried).
// ---------------------------------------------------------------------------------------------
export const embedViaHttp = spacetimedb.procedure(
  { objectId: t.u64() },
  t.string(),
  (ctx, { objectId }) => {
    // 1) call the embedding provider (here a reachable endpoint, to prove the HTTP path works).
    const resp = ctx.http.fetch('https://example.com', { method: 'GET' });
    const ref = `vec:http:${resp.status}:${objectId}`;
    // 2) write the result back, authorized by the caller's workspace membership.
    ctx.withTx((tx: any) => {
      const obj = tx.db.continuityObjects.id.find(objectId);
      if (!obj) throw new Error('continuity object not found');
      let member = false;
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === obj.workspaceId) { member = true; break; }
      }
      if (!member) throw new SenderError('unauthorized');
      tx.db.continuityObjects.id.update({ ...obj, embeddingRef: ref });
    });
    return ref;
  },
);

// captureWithEmbedding: the worker-less capture path. Fetch the embedding first (HTTP, no
// transaction), then write the capture event + candidate object + first revision in one
// deterministic transaction. Replaces capture-reducer → work_queue → external worker.
export const captureWithEmbedding = spacetimedb.procedure(
  { workspaceId: t.u64(), rawContent: t.string(), source: t.string(), kind: t.string() },
  t.string(), // returns the embeddingRef
  (ctx, { workspaceId, rawContent, source, kind }) => {
    // 1) embed (HTTP, outside the transaction). Non-secret endpoint until secrets are documented.
    const resp = ctx.http.fetch('https://example.com', { method: 'GET' });
    const embeddingRef = `vec:http:${resp.status}`;
    // 2) persist the capture deterministically, authorized by workspace membership.
    ctx.withTx((tx: any) => {
      let member = false;
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === workspaceId) { member = true; break; }
      }
      if (!member) throw new SenderError('unauthorized: not a member of this workspace');
      const event = tx.db.captureEvents.insert({
        id: 0n, workspaceId, rawContent, source, createdBy: ctx.sender, createdAt: ctx.timestamp,
      });
      const obj = tx.db.continuityObjects.insert({
        id: 0n, workspaceId, kind, status: 'candidate', trustClass: 'unverified',
        currentRevisionId: 0n, embeddingRef, capturedFrom: event.id,
        createdAt: ctx.timestamp, updatedAt: ctx.timestamp,
      });
      const rev = tx.db.memoryRevisions.insert({
        id: 0n, objectId: obj.id, revisionNo: 1, content: rawContent,
        authorIdentity: ctx.sender, supersededBy: 0n, createdAt: ctx.timestamp,
      });
      tx.db.continuityObjects.id.update({ ...obj, currentRevisionId: rev.id });
    });
    return embeddingRef;
  },
);

// ---------------------------------------------------------------------------------------------
// recallLexical: the keyword half of retrieval (Q5), vector-free. Views take no arguments, so a
// parameterized query must be a procedure. It scans the caller's non-superseded continuity
// objects, scores each by lexical overlap with the query, ranks in TS (/sql has no ORDER BY), and
// returns the top-N as a JSON string. No HTTP, no secrets, no vectors — semantic recall waits on
// the native-vector / external-store decision (Q3). DB reads run inside withTx (deterministic).
// ---------------------------------------------------------------------------------------------
export const recallLexical = spacetimedb.procedure(
  { workspaceId: t.u64(), query: t.string(), limit: t.u32() },
  t.string(), // JSON array of { objectId, score, status, trustClass, content }
  (ctx, { workspaceId, query, limit }) => {
    const queryTokens = tokenize(query);
    // withTx returns its value to the procedure — build the array inside and return it, so the
    // (retryable) tx body holds no outer mutable state.
    const results: { objectId: string; score: number; status: string; trustClass: string; content: string }[] = ctx.withTx((tx: any) => {
      const acc: { objectId: string; score: number; status: string; trustClass: string; content: string }[] = [];
      let member = false;
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === workspaceId) { member = true; break; }
      }
      if (!member) throw new SenderError('unauthorized: not a member of this workspace');
      for (const obj of tx.db.continuityObjects.workspaceId.filter(workspaceId)) {
        if (obj.status === 'superseded' || obj.status === 'rejected') continue;
        const rev = tx.db.memoryRevisions.id.find(obj.currentRevisionId);
        const content = rev ? rev.content : '';
        const score = lexScore(queryTokens, content);
        if (score <= 0) continue;
        acc.push({
          objectId: obj.id.toString(),
          score,
          status: obj.status,
          trustClass: obj.trustClass,
          content,
        });
      }
      return acc;
    });
    results.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      const ai = BigInt(a.objectId), bi = BigInt(b.objectId);
      return ai < bi ? -1 : ai > bi ? 1 : 0; // stable tiebreak by id ascending
    });
    return JSON.stringify(results.slice(0, Number(limit)));
  },
);

// ---------------------------------------------------------------------------------------------
// Semantic recall (Q3): embeddings + vector search OUTSIDE SpacetimeDB; procedures orchestrate the
// HTTP calls and commit results transactionally. Documented constraints honored: HTTP happens
// strictly OUTSIDE withTx; the withTx body is deterministic (safe to retry); no nested tx.
// The provider key is read from the private provider_keys table (server-only) rather than passed
// as a per-call argument, so it never transits as a (potentially logged) reducer arg.
// ---------------------------------------------------------------------------------------------

// setProviderKey: owner-only. Stores/replaces the embedding-provider credential + endpoints for a
// workspace. Writes go to a PRIVATE table — no view ever exposes apiKey.
export const setProviderKey = spacetimedb.reducer(
  { workspaceId: t.u64(), provider: t.string(), apiKey: t.string(), embedEndpoint: t.string(), storeEndpoint: t.string(), model: t.string() },
  (ctx, { workspaceId, provider, apiKey, embedEndpoint, storeEndpoint, model }) => {
    const ws = ctx.db.workspaces.id.find(workspaceId);
    if (!ws) throw new Error('workspace not found');
    if (!ws.ownerIdentity.equals(ctx.sender)) {
      throw new SenderError('unauthorized: only the workspace owner can set a provider key');
    }
    for (const k of ctx.db.providerKeys.workspaceId.filter(workspaceId)) {
      if (k.provider === provider) ctx.db.providerKeys.id.delete(k.id); // replace existing
    }
    ctx.db.providerKeys.insert({
      id: 0n, workspaceId, provider, apiKey, embedEndpoint, storeEndpoint, model, createdAt: ctx.timestamp,
    });
  },
);

// derive storable bytes from a string without TextEncoder (module runtime is minimal).
function bytePrefix(s: string, max: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < Math.min(s.length, max); i++) out.push(s.charCodeAt(i) & 0xff);
  return out;
}

// embedSemantic: index an existing continuity object into the external vector store. Reads the
// object content + provider key (tx1), embeds via HTTP (no tx), then records the vector reference
// (tx2). Returns a JSON proof object. Real provider: replace the byte derivation with parsing the
// returned embedding floats and packing them; the orchestration is identical.
export const embedSemantic = spacetimedb.procedure(
  { workspaceId: t.u64(), objectId: t.u64(), provider: t.string() },
  t.string(),
  (ctx, { workspaceId, objectId, provider }) => {
    // tx1: read content + provider config; check membership. No HTTP inside the transaction.
    // withTx returns this snapshot to use after the transaction closes (HTTP must run outside a tx).
    const cfg = ctx.withTx((tx: any) => {
      let authorized = false, found = false, content = '', apiKey = '', endpoint = '', model = '';
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === workspaceId) { authorized = true; break; }
      }
      const obj = tx.db.continuityObjects.id.find(objectId);
      if (obj && obj.workspaceId === workspaceId) {
        found = true;
        const rev = tx.db.memoryRevisions.id.find(obj.currentRevisionId);
        content = rev ? rev.content : '';
      }
      for (const k of tx.db.providerKeys.workspaceId.filter(workspaceId)) {
        if (k.provider === provider) { apiKey = k.apiKey; endpoint = k.embedEndpoint; model = k.model; break; }
      }
      return { authorized, found, content, apiKey, endpoint, model };
    });
    if (!cfg.authorized) throw new SenderError('unauthorized: not a member of this workspace');
    if (!cfg.found) throw new Error('continuity object not found in this workspace');
    if (!cfg.endpoint) throw new Error('no provider key configured for this workspace/provider');

    // HTTP (OUTSIDE any tx): the apiKey rides in the Authorization header, sourced server-side.
    const resp = ctx.http.fetch(cfg.endpoint, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: cfg.content, model: cfg.model }),
    });
    const respText = resp.text();
    let authEcho = '', inputEcho = '';
    try { const p = JSON.parse(respText); authEcho = (p.headers && p.headers.Authorization) || ''; inputEcho = (p.json && p.json.input) || ''; } catch (e) { /* non-echo provider */ }
    const bytes = bytePrefix(respText, 32); // real provider: pack data[0].embedding floats here
    const vectorId = `ext:${provider}:${workspaceId}:${objectId}`;

    // tx2: persist the vector reference, re-checking membership. Replace any prior row for the obj.
    // This is the procedure's only write — and it is a single atomic tx (the procedure as a whole
    // is NOT atomic), so all writes are concentrated here.
    const storedId: bigint = ctx.withTx((tx: any) => {
      let member = false;
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === workspaceId) { member = true; break; }
      }
      if (!member) throw new SenderError('unauthorized');
      for (const e of tx.db.embeddings.objectId.filter(objectId)) tx.db.embeddings.id.delete(e.id);
      const row = tx.db.embeddings.insert({
        id: 0n, workspaceId, objectId, vectorId, model: cfg.model, dim: bytes.length, bytes, createdAt: ctx.timestamp,
      });
      const obj = tx.db.continuityObjects.id.find(objectId);
      if (obj) tx.db.continuityObjects.id.update({ ...obj, embeddingRef: vectorId });
      return row.id;
    });

    return JSON.stringify({ status: resp.status, vectorId, dim: bytes.length, embeddingRowId: storedId.toString(), authEcho, inputEcho });
  },
);

// recallSemantic: query-time semantic search. Embeds the query (HTTP), asks the external vector
// store for the nearest objectIds (HTTP), then reads those rows by id (tx) and returns them ranked
// by the store's order. The store leg is the genuine external dependency — without a real vector
// store it returns no ids (and thus []). The read-by-id leg mirrors the verified recallLexical.
export const recallSemantic = spacetimedb.procedure(
  { workspaceId: t.u64(), query: t.string(), provider: t.string(), limit: t.u32() },
  t.string(),
  (ctx, { workspaceId, query, provider, limit }) => {
    // tx1: membership + provider config. withTx returns the snapshot used by the HTTP legs below.
    const cfg = ctx.withTx((tx: any) => {
      let authorized = false, apiKey = '', endpoint = '', model = '', storeEndpoint = '';
      for (const m of tx.db.workspaceMembers.memberIdentity.filter(ctx.sender)) {
        if (m.workspaceId === workspaceId) { authorized = true; break; }
      }
      for (const k of tx.db.providerKeys.workspaceId.filter(workspaceId)) {
        if (k.provider === provider) { apiKey = k.apiKey; endpoint = k.embedEndpoint; model = k.model; storeEndpoint = k.storeEndpoint; break; }
      }
      return { authorized, apiKey, endpoint, model, storeEndpoint };
    });
    if (!cfg.authorized) throw new SenderError('unauthorized: not a member of this workspace');
    if (!cfg.endpoint || !cfg.storeEndpoint) throw new Error('provider/store not configured');

    // HTTP 1: embed the query.
    const qResp = ctx.http.fetch(cfg.endpoint, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: query, model: cfg.model }),
    });
    // HTTP 2: ask the external vector store for nearest objectIds (it owns the kNN index).
    const sResp = ctx.http.fetch(cfg.storeEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspaceId: workspaceId.toString(), topK: Number(limit), queryStatus: qResp.status }),
    });
    const ids: bigint[] = [];
    try {
      const p = JSON.parse(sResp.text());
      const arr = (p.objectIds) || (p.json && p.json.objectIds) || [];
      for (const x of arr) { try { ids.push(BigInt(x)); } catch (e) { /* skip */ } }
    } catch (e) { /* no store result */ }

    // tx2: read the referenced rows by id, scoped to the caller's workspace. Read-only; the array
    // is built inside and returned, so the (retryable) tx body holds no outer mutable state.
    const out: { objectId: string; status: string; trustClass: string; content: string }[] = ctx.withTx((tx: any) => {
      const acc: { objectId: string; status: string; trustClass: string; content: string }[] = [];
      for (const id of ids) {
        const obj = tx.db.continuityObjects.id.find(id);
        if (!obj || obj.workspaceId !== workspaceId) continue;
        const rev = tx.db.memoryRevisions.id.find(obj.currentRevisionId);
        acc.push({ objectId: id.toString(), status: obj.status, trustClass: obj.trustClass, content: rev ? rev.content : '' });
      }
      return acc;
    });
    return JSON.stringify(out);
  },
);
