# Alice QA / Validation

Canonical source of truth: [`feature-validation-matrix.csv`](feature-validation-matrix.csv).
Runnable test harness (SpacetimeDB surface): [`../../clients/python/qa_smoke.py`](../../clients/python/qa_smoke.py).

## Status legend
- **Pass** — executed with current evidence (this session, on maincloud).
- **Pass (session-verified)** — verified earlier this session; not in today's automated harness.
- **Discovered - not tested** — found in code, recorded; Phases 2/3 not yet done.

## How to run the SpacetimeDB regression (Phase 3 / Phase 5)
```bash
python3 clients/python/qa_smoke.py   # provisions 2 fresh identities; 23 checks; exits non-zero on any FAIL
```
No local database — runs against hosted maincloud (`alice-continuity`). Covers happy path, error
path, boundary (recall limit), cross-tenant permission/security, and write idempotency (replay).

## Scope reality (why coverage is uneven)
The repo has three very different surfaces:
- **SpacetimeDB module + Python client** — runnable on maincloud → taken fully through Phase 1→2→3.
- **`apps/api` (FastAPI, 289 endpoints) + `apps/web` (Next.js, ~16 screens)** — execution needs Postgres
  + the backend running, which the no-local-DB rule excludes. Discovery/test-design (Phases 1-2) are
  possible; execution (Phase 3) is **blocked** in the current environment.
- **`workers/`** — Python; discovery pending.

## Scope decision (2026-06-22)
Per direction, the QA mandate is **scoped to the SpacetimeDB surface**. The legacy `apps/api` /
`apps/web` / `workers` rows stay in the matrix as *Discovered - not tested* and will be promoted to
full Phase 1-3 coverage **per feature as each domain is ported onto SpacetimeDB** — not tested
against the Postgres backend (which the no-local-DB rule excludes).

## Iteration 2 report (2026-06-22)

**1. Coverage summary**
- SpacetimeDB surface: 19 features catalogued; **22 checks executed via `qa_smoke.py` (all PASS)** —
  now incl. boundary + cross-tenant permission/security. 3 platform/security/limitation rows.
- Legacy: 24 rows *Discovered - not tested* (out of scope per the decision above).

**2. Features tested (executed today, 22/22 PASS):** the full continuity cycle (create/capture/
commit/correct), open-loops, entities+link, trust signals, contradictions, lexical recall
(match/miss/limit), set_provider_key, embed_semantic, recall_semantic, embed_via_http, error-path
(unknown object), and **permission/security**: non-member capture rejected, non-member recall
rejected, non-owner set_provider_key rejected, my_workspace_members owner check, and a second
identity seeing **none** of the first's rows.

**3. Defects found:** 0 in the SpacetimeDB surface.

**4. Defects fixed:** 1 latent correctness issue fixed earlier (retry-unsafe `withTx` bodies
accumulating outer state → refactored to the documented `withTx`-returns-a-value idiom; re-verified).

**5. Remaining risks**
- `recall_semantic` neighbor quality **unverified** — needs a real embedding provider + external
  vector store (the only true external dependency).
- `embed_semantic` has two TODOs before production: pack real provider floats into bytes; add the
  external-store upsert call.
- Owner SQL privilege bypass exposes `provider_keys.api_key` to the **operator** (not clients) — by design.
- Legacy surface remains untested **by deliberate scope choice**, not oversight.

**6. Confidence score**
- **SpacetimeDB continuity surface: ~92%** (happy + error + boundary + permission executed; gap =
  real semantic store + the two embed TODOs).
- **Whole product: ~15%** (legacy discovered, intentionally out of scope).

Within the agreed scope (SpacetimeDB surface): all executed tests pass; **no open critical or
high-severity defects; no broken in-scope user journeys.** The only open items are the documented
incomplete-feature TODOs for production semantic recall — not defects.

## Iteration 3 report (2026-06-22)

**1. Coverage summary** — **23/23 checks pass** on `alice-continuity`; added `STDB-IDEM` (write
idempotency). Track B now has idempotent writes.

**2. Feature added & tested:** write idempotency — `applied_requests` table + `requestId` on
`capture_with_embedding` (procedure: replay returns the prior object and skips the embed HTTP) and
`correct_memory` (reducer: atomic no-op on replay). `STDB-IDEM` proves two same-`requestId` captures
create exactly one object; the `.unique()` mechanics (find / checked no-op / duplicate-insert
rollback) were pre-verified on a throwaway db before touching production.

**3. Defects found:** 0 in the module. (One self-inflicted *test-ordering* bug surfaced during the
run — the replay test was inserted between capture and commit, breaking the single-object assumption
of the commit/correct assertions; fixed by moving it to the end. The module logic was correct.)

**4. Defects fixed:** the test-ordering bug above.

**5. Remaining risks** — unchanged: `recall_semantic` neighbor quality + the two `embed_semantic`
production TODOs; legacy surface out of scope by choice.

**6. Confidence** — SpacetimeDB surface **~93%** (idempotent writes add robustness); whole product ~15%.
