# ADR: Port Alice's execution pillar to the SpacetimeDB module — tick-slice

Status: **Execution pillar slice live on maincloud (verified).** Claim+tick+retry, real HTTP
execution, a **scheduled executor** (the worker loop fully in-module), and stuck-`running` recovery
all work against a *stub tool endpoint*; per-run tool config + tools registry + secrets are the
follow-on.

## Context

`workers/alicebot_worker` is a thin **single-tick** driver (`run()` does one tick per invocation,
cron-style) over Alice's **execution pillar** — the action counterpart to the continuity/memory
pillar already ported. Flow: `main` (reads `ALICEBOT_WORKER_USER_ID`, opens a Postgres RLS
connection) → `acquire_and_tick_one_task_run` (claim next `task_run` → execute if ready → else tick
the retry/backoff state machine) → `execute_task_run_if_ready` (if task approved + not yet executed,
run `execute_approved_proxy_request`; classify failures policy/transient).

The pillar underneath is large — ~4,400 LOC (`proxy_execution` 953, `tasks` 1170,
`execution_budgets` 965, `task_runs` 610, `approvals` 607) + ~20 tables (tools registry/allowlist,
approvals, tool_executions, budgets, tasks → task_steps → task_runs, artifacts).

## Decision — function-type mapping

| Worker concept | SpacetimeDB |
|----------------|-------------|
| claim + tick + retry/backoff state machine (DB-only) | **reducers** (atomic transaction, rollback on failure) |
| external tool execution over HTTP | **procedure** (HTTP outside tx, `withTx` to commit; idempotent via the `applied_requests`/`requestId` pattern) |
| "next runnable task_run" / derived reads | **views** (read-only, per-caller) |
| periodic worker tick (external cron + process) | **scheduled reducer** — the worker *process* collapses into the module |

The scheduled-reducer mapping is **empirically verified** (see below); the function-type mapping is
also doc-grounded (reducers/procedures/functions docs).

## This slice (live)

Tables: `tasks` (minimal), `task_runs` (status / stub_mode / stop_reason / retry_posture /
retry_count / retry_cap / failure_class), `tick_schedule` (opt-in scheduler).
Reducers: `create_task`, `enqueue_task_run`, `tick_next_task_run` (manual single tick,
membership-checked), `scheduled_tick` (the scheduled target — a reducer, system tick on the row's
workspace), `arm_ticker` / `disarm_ticker` (opt-in scheduler control).
Views: `my_tasks`, `my_task_runs`.
The stub path (`stub_mode` = `succeed` | `fail_transient` | `fail_policy`) exercises the retry/
failure-class machine with no HTTP.

**Real execution (added):** `tool_executions` table (idempotent ledger, `requestId .unique()`),
`execute_next_task_run` procedure (claims the next run → `'running'`, HTTP-calls the tool *outside*
any tx, then `withTx` records a `tool_executions` row and transitions the run by HTTP status: 2xx →
`succeeded`, else retry-to-cap → `retrying`/`failed`), and `my_tool_executions` view. This is the
real proxy-execution path; it calls a fixed stub endpoint until the tools registry + secrets land.

**Scheduled execution + recovery (added):** `exec_schedule` (opt-in) targets `scheduled_execute` —
a **procedure** that claims a run, HTTP-calls the tool, then records + transitions it; armed via
`arm_executor` / `disarm_executor`. `recover_stuck_runs` requeues runs stuck in `running` (a
procedure that died after claiming) older than a threshold, counting the stuck attempt as a
transient failure. Shared `claimNextRun` / `recordAndTransition` helpers back both the
client-callable and scheduled paths. This is the worker's execution loop fully inside the module.

## Verification (observed on maincloud)

- **Manual ticks** (throwaway db): `succeed` → `succeeded`; `fail_policy` → `failed` /
  `policy_blocked` / `policy` (terminal, no retry); `fail_transient` (cap 2) → retried twice then
  `failed` / `fatal_error` / `transient` at `retry_count 3`.
- **Scheduled reducer** (throwaway db): armed a 3s interval; two queued runs drained to `succeeded`
  with **no manual ticks** — confirming a scheduled table can target a **reducer** (not only a
  procedure, which was verified separately earlier). The worker tick genuinely runs inside the module.
- **Production** (`alice-continuity`): publish was additive (tables/views created, data preserved);
  the continuity regression (`qa_smoke`) stayed **23/23**; a manual production tick succeeded. The
  scheduler is **not armed** on production — it is opt-in via `arm_ticker`.
- **Real execution** (production): an enqueued run was claimed → HTTP 200 → `succeeded` with one
  `tool_executions` row; a replay with the same `requestId` returned the same outcome with **no**
  second row and no re-claim; an empty queue returned `idle`.
- **Scheduled real execution** (throwaway): armed a 3s `exec_schedule`; two queued runs were drained
  to `succeeded` by the **scheduled procedure** (real HTTP), no manual calls. **Stuck recovery**
  (throwaway): a run forced to `running` and aged past the threshold was requeued to `retrying` /
  `retry_count 1` / `transient` (also validating the stored-timestamp comparison). Production:
  published additively (`exec_schedule` created, data preserved), regression 23/23.

## Not done (follow-on, in rough order)

- **Per-run tool config + tools registry/allowlist + secrets:** `execute_next_task_run` calls a
  fixed stub endpoint today; real tools need a registry/allowlist and (for authed tools) the
  secrets-in-procedure pattern.
- **Approval gating** port (the trust layer before execution), **execution budgets** (cost/rate),
  **task_steps / lineage / artifacts**.
- Retire the external worker process once the scheduled tick covers it; re-point the API/CLI surfaces.

## Notes

- `scheduled_tick` runs as a system tick (no per-caller membership) on the scheduled row's
  workspace; the user-callable `tick_next_task_run` is membership-checked. Both share `tickOneTaskRun`.
- Claiming is race-safe without `SELECT … FOR UPDATE`: reducers are serialized transactions.
