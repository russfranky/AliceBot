"""End-to-end demo: the whole Alice stack — memory + action — running on hosted SpacetimeDB.

One command, real maincloud calls, no local DB and no server process. Provisions a fresh isolated
identity, then walks the full loop: capture/commit/correct/recall (continuity) and
register-tool / approve / budget / execute / artifact (execution).

    python3 clients/python/alice_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alice_spacetime_reference import SpacetimeClient  # noqa: E402


def dec(body: str):
    v = json.loads(body)
    return json.loads(v) if isinstance(v, str) else v


def rid() -> str:
    return uuid.uuid4().hex


def main() -> None:
    c = SpacetimeClient()
    ident = c.provision_identity()
    tok = ident["token"]
    print("Alice, running entirely on hosted SpacetimeDB (maincloud) — no local DB, no server\n")
    print(f"  new identity {ident['identity'][:16]}…  (its own private tenant)")

    c.call("create_workspace", ["Demo"], tok)
    ws = c.sql("SELECT id FROM my_workspaces", tok)[0][0]
    print(f"  workspace #{ws} created\n")

    print("── MEMORY (continuity) ──────────────────────────────────")
    c.call_proc("capture_with_embedding", [ws, "Ship the Q3 board pack by Friday", "demo", "commitment", rid()], tok)
    obj = c.sql("SELECT id, status, trust_class FROM my_continuity_objects", tok)[0]
    print(f"  capture  → memory #{obj[0]}: 'Ship the Q3 board pack by Friday'  ({obj[1]}/{obj[2]})")
    c.call("commit_memory", [obj[0], "user_confirmed"], tok)
    print("  commit   → durable, trust = user_confirmed")
    c.call("correct_memory", [obj[0], "Ship the Q3 board pack by Thursday", rid()], tok)
    print("  correct  → 'by Thursday' (prior revision superseded; full audit kept)")
    hit = dec(c.call_proc("recall_lexical", [ws, "board pack", 5], tok))[0]
    print(f"  recall   → 'board pack' returns {hit['content']!r}  (trust={hit['trustClass']})\n")

    print("── ACTION (execution) ───────────────────────────────────")
    c.call("register_tool", [ws, "echo", "https://httpbin.org/get"], tok)
    tool = c.sql("SELECT id FROM my_tools", tok)[0][0]
    print(f"  tool     → registered #{tool} 'echo' (allowlisted) → https://httpbin.org/get")
    c.call("create_task", [ws, "Call the echo tool"], tok)
    task = c.sql("SELECT id FROM my_tasks", tok)[0][0]
    print(f"  task     → #{task} created (status: open)")

    try:
        c.call("enqueue_task_run", [ws, task, "x", 2], tok)
        gate = "NOT blocked — unexpected!"
    except Exception:
        gate = "blocked (approval required before any execution)"
    print(f"  gate     → enqueue before approval: {gate}")

    c.call("request_approval", [ws, task], tok)
    ap = c.sql("SELECT id FROM my_approvals", tok)[0][0]
    c.call("resolve_approval", [ap, "approved"], tok)
    c.call("set_budget", [ws, 5], tok)
    c.call("bind_task_tool", [ws, task, tool], tok)
    print(f"  approve  → approval #{ap} granted; budget set to 5; tool bound")

    c.call("enqueue_task_run", [ws, task, "x", 2], tok)
    res = dec(c.call_proc("execute_next_task_run", [ws, rid()], tok))
    print(f"  execute  → HTTP {res['httpStatus']}, outcome '{res['outcome']}'  (the worker ran *inside* the DB)")

    art = c.sql("SELECT task_run_id, tool_execution_id FROM my_task_artifacts", tok)[0]
    bud = c.sql("SELECT max_executions, consumed FROM my_budgets", tok)[0]
    print(f"  lineage  → artifact for run #{art[0]} → execution #{art[1]} (tool output captured)")
    print(f"  budget   → {bud[1]}/{bud[0]} consumed\n")

    print("Every step above was an HTTP call to a SpacetimeDB module on maincloud:")
    print("  reducers for atomic state, procedures for outbound HTTP, views for per-caller reads.")
    print("  No Postgres, no worker process, no cron — the whole loop lives in the database.")


if __name__ == "__main__":
    main()
