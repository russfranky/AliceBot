"""Track B: thin SpacetimeDB backend for the Alice CLI (capture + recall + execution surface).

Routes `alice capture` / `alice recall` and the `alice exec` execution surface (tasks, tools,
approvals, budgets, runs) to the hosted SpacetimeDB continuity/execution module over plain HTTP with
a per-user token, instead of Postgres. Selected via `--backend spacetimedb` (or
`ALICE_BACKEND=spacetimedb`). Non-destructive: the Postgres path stays the default and is untouched.

State: the non-secret identity + workspace persist in a 0600 file under the user's config dir; the
token is stored in Alice's encrypted `SecretProvider` (ref `spacetime-token:<identity>`, encrypted
at rest and auto-redacted in logs because the ref contains "token"). When the module is loaded
standalone without the app package, it falls back to keeping the token in the 0600 state file.
stdlib transport only; no local database.

Deliberately NOT yet included (follow-up): output parity with the Postgres formatters
(`format_capture_output` etc.), and the MCP/FastAPI surfaces. (Write idempotency,
SecretProvider-backed tokens, and the CLI execution surface are done.)
"""
from __future__ import annotations

import json
import os
import ssl
import stat
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("ALICE_SPACETIME_BASE", "https://maincloud.spacetimedb.com")
DB = os.environ.get("ALICE_SPACETIME_DB", "alice-continuity")
_STATE = Path(
    os.environ.get("ALICE_SPACETIME_STATE", str(Path.home() / ".config" / "alice" / "spacetime.json"))
)


def _ssl_context() -> ssl.SSLContext | None:
    # The python.org framework build (used by the app venv) ships no CA bundle; verify against
    # certifi's, like requests/httpx do. Fall back to the default context if certifi is absent.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


_SSL = _ssl_context()


def _secret_provider():
    """Alice's encrypted secret store, if importable (the CLI context). Returns None when the
    backend is loaded standalone without the app package, in which case the caller keeps the token
    in the local state file instead."""
    try:
        from alicebot_api.vnext_secrets import default_secret_provider

        return default_secret_provider()
    except Exception:
        return None


def _post(path: str, body, token: str | None, content_type: str) -> tuple[int, str]:
    data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"{BASE}{path}", data=data, method="POST")
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, context=_SSL) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        # The module throws (e.g. an ungated enqueue, or a not-found id) -> 4xx/5xx. Surface the
        # module's message as a clean ValueError (the CLI's main() maps ValueError to `error: ...`)
        # instead of leaking an HTTPError traceback.
        body = exc.read().decode(errors="replace").strip()
        raise ValueError(f"spacetimedb rejected the call (HTTP {exc.code}): {body[:300]}") from exc


def _decode(body: str):
    """Decode a procedure HTTP body. Procedures return a value that arrives JSON-encoded; a
    procedure returning a JSON string (recall) is double-encoded, while a plain string (an embedding
    ref) is single-encoded. Normalise both to the underlying Python object/string."""
    val = json.loads(body)
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return val
    return val


class SpacetimeBackend:
    """The entire Track-B CLI adapter: provision a tenant, capture, recall."""

    def __init__(self) -> None:
        self._provider = _secret_provider()
        self._identity, self._workspace, self._token = self._load_or_provision()

    # --- identity / token / workspace state ----------------------------------------------
    def _load_or_provision(self) -> tuple[str, int, str]:
        if _STATE.exists():
            st = json.loads(_STATE.read_text())
            token: str | None = None
            if self._provider and st.get("token_ref"):
                token = self._provider.get_secret(st["token_ref"])
            elif st.get("token"):  # legacy/standalone plaintext token
                token = st["token"]
            if token and st.get("identity") and st.get("workspace_id") is not None:
                return st["identity"], st["workspace_id"], token
        # provision a fresh identity + workspace (caller becomes owner+member)
        _, body = _post("/v1/identity", None, None, "application/json")
        ident = json.loads(body)
        identity, token = ident["identity"], ident["token"]
        _post(f"/v1/database/{DB}/call/create_workspace", ["Alice CLI"], token, "application/json")
        _, sb = _post(f"/v1/database/{DB}/sql", "SELECT id FROM my_workspaces", token, "text/plain")
        ws = json.loads(sb)[0]["rows"][0][0]
        self._persist(identity, ws, token)
        return identity, ws, token

    def _persist(self, identity: str, ws: int, token: str) -> None:
        st: dict = {"identity": identity, "workspace_id": ws}
        if self._provider:
            ref = f"spacetime-token:{identity}"  # "token" in the ref -> auto-redacted by is_secret_key
            self._provider.set_secret(ref, token)  # encrypted at rest by the secret store
            st["token_ref"] = ref
        else:
            st["token"] = token  # standalone fallback: no app secret store available
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(st))
        try:
            _STATE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 (only holds non-secrets when provider present)
        except OSError:
            pass

    # --- transport ------------------------------------------------------------------------
    def _call(self, reducer: str, args: list, token: str | None = None) -> int:
        status, _ = _post(f"/v1/database/{DB}/call/{reducer}", args, token or self._token, "application/json")
        return status

    def _call_proc(self, name: str, args: list, token: str | None = None):
        _, body = _post(f"/v1/database/{DB}/call/{name}", args, token or self._token, "application/json")
        return _decode(body)

    def _sql(self, query: str, token: str | None = None) -> list:
        _, body = _post(f"/v1/database/{DB}/sql", query, token or self._token, "text/plain")
        return json.loads(body)[0]["rows"]

    # --- operations -----------------------------------------------------------------------
    def capture(self, raw_content: str, explicit_signal: str | None, request_id: str | None = None) -> dict:
        # requestId makes the write idempotent: a retry of the same logical capture reuses the id and
        # the module returns the existing object instead of creating a duplicate.
        ref = self._call_proc(
            "capture_with_embedding",
            [self._workspace, raw_content, "cli", explicit_signal or "note", request_id or uuid.uuid4().hex],
        )
        rows = self._sql("SELECT id, status, trust_class, embedding_ref FROM my_continuity_objects")
        latest = max(rows, key=lambda r: r[0]) if rows else None
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "embedding_ref": ref,
            "object": (
                {"id": latest[0], "status": latest[1], "trust_class": latest[2], "embedding_ref": latest[3]}
                if latest
                else None
            ),
        }

    def recall(self, query: str, limit: int) -> dict:
        hits = self._call_proc("recall_lexical", [self._workspace, query or "", limit])
        return {"backend": "spacetimedb", "query": query, "results": hits}

    # --- execution pillar (Track B) -------------------------------------------------------
    # Each method drives one module reducer/procedure, then reads the affected row back through a
    # per-caller view so the CLI can echo the resulting state. Reads use the same private-table ->
    # public-view isolation as capture/recall; writes are membership-checked server-side.
    def _latest(self, query: str):
        rows = self._sql(query)
        return max(rows, key=lambda r: r[0]) if rows else None

    def create_task(self, title: str) -> dict:
        self._call("create_task", [self._workspace, title])
        row = self._latest("SELECT id, title, status FROM my_tasks")
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "task": ({"id": row[0], "title": row[1], "status": row[2]} if row else None),
        }

    def register_tool(self, name: str, endpoint: str) -> dict:
        self._call("register_tool", [self._workspace, name, endpoint])
        row = self._latest("SELECT id, name, endpoint FROM my_tools")
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "tool": ({"id": row[0], "name": row[1], "endpoint": row[2]} if row else None),
        }

    def bind_task_tool(self, task_id: int, tool_id: int) -> dict:
        self._call("bind_task_tool", [self._workspace, task_id, tool_id])
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "bound": {"task_id": task_id, "tool_id": tool_id},
        }

    def request_approval(self, task_id: int) -> dict:
        self._call("request_approval", [self._workspace, task_id])
        row = self._latest("SELECT id, task_id, status FROM my_approvals")
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "approval": ({"id": row[0], "task_id": row[1], "status": row[2]} if row else None),
        }

    def resolve_approval(self, approval_id: int, decision: str) -> dict:
        self._call("resolve_approval", [approval_id, decision])
        rows = self._sql("SELECT id, task_id, status FROM my_approvals")
        row = next((r for r in rows if r[0] == approval_id), None)
        return {
            "backend": "spacetimedb",
            "approval": ({"id": row[0], "task_id": row[1], "status": row[2]} if row else None),
        }

    def set_budget(self, max_executions: int) -> dict:
        self._call("set_budget", [self._workspace, max_executions])
        row = self._latest("SELECT id, max_executions, consumed FROM my_budgets")
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "budget": ({"max_executions": row[1], "consumed": row[2]} if row else None),
        }

    def enqueue(self, task_id: int, stub_mode: str, retry_cap: int) -> dict:
        # Gated server-side: only an approved task may be enqueued (otherwise the module throws and
        # _post raises a clean ValueError).
        self._call("enqueue_task_run", [self._workspace, task_id, stub_mode, retry_cap])
        row = self._latest("SELECT id, task_id, status FROM my_task_runs")
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "run": ({"id": row[0], "task_id": row[1], "status": row[2]} if row else None),
        }

    def execute(self, request_id: str | None = None) -> dict:
        # The real execution path: claim the next runnable run, HTTP-call its bound tool, record +
        # transition. Idempotent on requestId. Returns the procedure's decoded result object.
        result = self._call_proc(
            "execute_next_task_run", [self._workspace, request_id or uuid.uuid4().hex]
        )
        return {"backend": "spacetimedb", "workspace_id": self._workspace, "result": result}

    def exec_status(self) -> dict:
        return {
            "backend": "spacetimedb",
            "workspace_id": self._workspace,
            "tasks": self._sql("SELECT id, title, status FROM my_tasks"),
            "tools": self._sql("SELECT id, name, endpoint FROM my_tools"),
            "approvals": self._sql("SELECT id, task_id, status FROM my_approvals"),
            "runs": self._sql(
                "SELECT id, task_id, status, retry_count, failure_class, stop_reason FROM my_task_runs"
            ),
            "executions": self._sql(
                "SELECT id, task_run_id, http_status, outcome FROM my_tool_executions"
            ),
            "budgets": self._sql("SELECT max_executions, consumed FROM my_budgets"),
            "artifacts": self._sql(
                "SELECT task_run_id, tool_execution_id, content FROM my_task_artifacts"
            ),
        }
