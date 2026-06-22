"""QA smoke/regression harness for the Alice-on-SpacetimeDB continuity module (maincloud).

Phase 2 (test suite) + Phase 3 (execution) artifact for the SpacetimeDB surface. Provisions a
FRESH per-user identity (so the run is isolated — it sees only its own workspace) and drives the
full continuity + recall + semantic-index path over plain HTTP, recording PASS/FAIL per feature.
Re-runnable as a regression check (Phase 5). stdlib only; no local DB.

Usage:  python3 clients/python/qa_smoke.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alice_spacetime_reference import SpacetimeClient  # noqa: E402

RESULTS: list[tuple[str, str, bool, str]] = []
S: dict = {}


def step(fid: str, name: str, fn) -> None:
    try:
        ok, detail = fn()
    except Exception as ex:  # a non-200 reducer raises urllib HTTPError — captured, not fatal
        ok, detail = False, f"EXC {type(ex).__name__}: {str(ex)[:80]}"
    RESULTS.append((fid, name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {fid:10} {name:42} {detail[:70]}")


def _unwrap(body: str):
    # procedure HTTP bodies come back as a JSON-encoded string; decode once to the inner JSON text.
    try:
        return json.loads(body)
    except Exception:
        return body


def main() -> None:
    c = SpacetimeClient()
    ident = c.provision_identity()
    tok = ident["token"]
    print(f"identity: {ident['identity'][:18]}...  db={c.db}\n")

    def f_create_ws():
        st = c.call("create_workspace", ["QA Smoke"], tok)
        S["ws"] = c.sql("SELECT id FROM my_workspaces", tok)[0][0]
        return st == 200 and S["ws"] is not None, f"status={st} ws={S['ws']}"
    step("STDB-001", "create_workspace", f_create_ws)

    def f_capture():
        body = c.call_proc("capture_with_embedding", [S["ws"], "invoices are due in Q3", "qa", "decision"], tok)
        rows = c.sql("SELECT id, status, trust_class FROM my_continuity_objects", tok)
        S["obj"] = rows[0][0]
        ref = _unwrap(body)
        return ("vec:" in str(ref)) and rows[0][1] == "candidate" and rows[0][2] == "unverified", f"ref={ref} row={rows[0]}"
    step("STDB-002", "capture_with_embedding -> candidate/unverified", f_capture)

    def f_commit():
        st = c.call("commit_memory", [S["obj"], "user_confirmed"], tok)
        r = c.sql("SELECT status, trust_class FROM my_continuity_objects", tok)[0]
        return st == 200 and r[0] == "committed" and r[1] == "user_confirmed", f"status={st} row={r}"
    step("STDB-003", "commit_memory -> committed", f_commit)

    def f_correct():
        st = c.call("correct_memory", [S["obj"], "invoices moved to Q4"], tok)
        r = c.sql("SELECT status, trust_class, embedding_ref FROM my_continuity_objects", tok)[0]
        return st == 200 and r[1] == "user_confirmed" and r[2] == "", f"status={st} row={r}"
    step("STDB-004", "correct_memory -> supersede + reset ref", f_correct)

    def f_loop():
        s1 = c.call("open_loop_create", [S["ws"], "follow up invoices", "next", 0], tok)
        loops = c.sql("SELECT id, status FROM my_open_loops", tok)
        s2 = c.call("open_loop_resolve", [loops[0][0]], tok)
        rs = c.sql("SELECT status FROM my_open_loops", tok)[0][0]
        return s1 == 200 and s2 == 200 and rs == "resolved", f"{loops} -> {rs}"
    step("STDB-005", "open_loop create + resolve", f_loop)

    def f_entities():
        c.call("create_entity", [S["ws"], "project", "Invoicing"], tok)
        c.call("create_entity", [S["ws"], "person", "CFO"], tok)
        ents = c.sql("SELECT id, kind, name FROM my_entities", tok)
        st = c.call("link_entities", [S["ws"], ents[0][0], ents[1][0], "owned_by"], tok)
        edges = c.sql("SELECT relation FROM my_entity_edges", tok)
        return len(ents) == 2 and st == 200 and edges[0][0] == "owned_by", f"{len(ents)} ents, edge={edges}"
    step("STDB-006", "entities create + link", f_entities)

    def f_trust():
        st = c.call("record_trust_signal", [S["ws"], S["obj"], "user_confirmed", 5, "qa"], tok)
        ts = c.sql("SELECT signal_type, weight FROM my_trust_signals", tok)
        return st == 200 and ts[0][0] == "user_confirmed", f"status={st} {ts}"
    step("STDB-007", "record_trust_signal", f_trust)

    def f_contra():
        c.call_proc("capture_with_embedding", [S["ws"], "invoices are due in Q2", "qa", "decision"], tok)
        ids = [r[0] for r in c.sql("SELECT id FROM my_continuity_objects", tok)]
        o2 = [i for i in ids if i != S["obj"]][0]
        s1 = c.call("open_contradiction", [S["ws"], S["obj"], o2, "q4 vs q2"], tok)
        cases = c.sql("SELECT id, status FROM my_contradictions", tok)
        s2 = c.call("resolve_contradiction", [cases[0][0], "resolved_a"], tok)
        cs = c.sql("SELECT status FROM my_contradictions", tok)[0][0]
        return s1 == 200 and s2 == 200 and cs == "resolved_a", f"{cases} -> {cs}"
    step("STDB-008", "contradiction open + resolve", f_contra)

    def f_recall_hit():
        hits = _unwrap(c.call_proc("recall_lexical", [S["ws"], "invoices", 5], tok))
        return "invoices" in str(hits).lower(), str(hits)[:60]
    step("STDB-009", "recall_lexical (match)", f_recall_hit)

    def f_recall_miss():
        none = _unwrap(c.call_proc("recall_lexical", [S["ws"], "zzqqxx", 5], tok))
        return str(none).strip() in ("[]", '"[]"'), f"got {none!r}"
    step("STDB-009b", "recall_lexical (no match -> [])", f_recall_miss)

    def f_setkey():
        st = c.call("set_provider_key", [S["ws"], "echo-test", "DUMMYKEY", "https://httpbin.org/post", "https://httpbin.org/post", "m"], tok)
        return st == 200, f"status={st}"
    step("STDB-010", "set_provider_key (owner)", f_setkey)

    def f_embed():
        es = _unwrap(c.call_proc("embed_semantic", [S["ws"], S["obj"], "echo-test"], tok))
        d = es if isinstance(es, dict) else json.loads(es)
        return d.get("status") == 200 and d.get("authEcho") == "Bearer DUMMYKEY", f"{d}"
    step("STDB-011", "embed_semantic (key->Authorization roundtrip)", f_embed)

    def f_recall_sem():
        rs = _unwrap(c.call_proc("recall_semantic", [S["ws"], "invoices", "echo-test", 5], tok))
        return str(rs).strip() in ("[]", '"[]"'), f"got {rs!r}"
    step("STDB-012", "recall_semantic (no store -> [])", f_recall_sem)

    def f_err_unknown():
        try:
            st = c.call("commit_memory", [999999999, "x"], tok)
            return st != 200, f"unexpected status={st}"
        except Exception as ex:
            return True, f"rejected: {type(ex).__name__}"
    step("STDB-E01", "error: commit unknown object rejected", f_err_unknown)

    def f_reembed():
        ref = _unwrap(c.call_proc("embed_via_http", [S["obj"]], tok))
        return "vec:http:" in str(ref), str(ref)[:40]
    step("STDB-013", "embed_via_http re-embed", f_reembed)

    def f_recall_limit():
        # ws holds 2 objects containing 'invoices'; limit=1 must return exactly 1 (top-ranked).
        arr = json.loads(_unwrap(c.call_proc("recall_lexical", [S["ws"], "invoices", 1], tok)))
        return len(arr) == 1, f"limit=1 -> {len(arr)} rows"
    step("STDB-009c", "boundary: recall_lexical respects limit", f_recall_limit)

    def f_members_view():
        m = c.sql("SELECT workspace_id, role FROM my_workspace_members", tok)
        return len(m) == 1 and m[0][1] == "owner", f"{m}"
    step("STDB-015d", "my_workspace_members shows caller as owner", f_members_view)

    def f_artifacts_view():
        a = c.sql("SELECT id FROM my_artifacts", tok)
        return a == [], f"inert artifacts -> {a}"
    step("STDB-018b", "my_artifacts (inert legacy) -> []", f_artifacts_view)

    # --- cross-tenant permission/security cases: a SECOND identity (non-member of S['ws']) ---
    identB = c.provision_identity()
    tokB = identB["token"]

    def f_perm_capture():
        try:
            c.call_proc("capture_with_embedding", [S["ws"], "intruder note", "qa", "decision"], tokB)
            return False, "non-member capture was NOT rejected"
        except Exception as ex:
            return True, f"rejected: {type(ex).__name__}"
    step("STDB-015b", "perm: non-member capture rejected", f_perm_capture)

    def f_perm_recall():
        try:
            c.call_proc("recall_lexical", [S["ws"], "invoices", 5], tokB)
            return False, "non-member recall was NOT rejected"
        except Exception as ex:
            return True, f"rejected: {type(ex).__name__}"
    step("STDB-015c", "perm: non-member recall rejected", f_perm_recall)

    def f_perm_setkey():
        try:
            c.call("set_provider_key", [S["ws"], "x", "k", "http://e", "http://s", "m"], tokB)
            return False, "non-owner set_provider_key was NOT rejected"
        except Exception as ex:
            return True, f"rejected: {type(ex).__name__}"
    step("STDB-010b", "perm: non-owner set_provider_key rejected", f_perm_setkey)

    def f_perm_isolation():
        # B sees its own (empty) views, never A's rows.
        objs = c.sql("SELECT id FROM my_continuity_objects", tokB)
        return objs == [], f"B sees {objs} continuity objects"
    step("STDB-015e", "perm: second identity sees none of A's rows", f_perm_isolation)

    p = sum(1 for r in RESULTS if r[2])
    f = len(RESULTS) - p
    print(f"\nSUMMARY: {p} PASS / {f} FAIL  of {len(RESULTS)}")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
