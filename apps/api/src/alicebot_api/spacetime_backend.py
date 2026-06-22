"""Track B: thin SpacetimeDB backend for the Alice CLI (capture + recall).

Routes `alice capture` / `alice recall` to the hosted SpacetimeDB continuity module over plain
HTTP with a per-user token, instead of Postgres. Selected via `--backend spacetimedb` (or
`ALICE_BACKEND=spacetimedb`). Non-destructive: the Postgres path stays the default and is untouched.

Identity + token + workspace persist in a 0600 file under the user's config dir so repeat
invocations reuse the same tenant. stdlib only; no local database.

This is the first Track-B slice. Deliberately NOT yet included (follow-ups):
  * in-module idempotency on writes (request-id + unique constraint; SpacetimeDB has no built-in);
  * output parity with the Postgres `format_capture_output` / `format_recall_output`;
  * token storage via `vnext_secrets.SecretProvider` (currently a local 0600 state file).
"""
from __future__ import annotations

import json
import os
import ssl
import stat
import urllib.request
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


def _post(path: str, body, token: str | None, content_type: str) -> tuple[int, str]:
    data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"{BASE}{path}", data=data, method="POST")
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, context=_SSL) as resp:
        return resp.status, resp.read().decode()


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
        self._state = self._load_or_provision()

    # --- identity / token / workspace state ----------------------------------------------
    def _load_or_provision(self) -> dict:
        if _STATE.exists():
            state = json.loads(_STATE.read_text())
            if state.get("token") and state.get("workspace_id") is not None:
                return state
        _, body = _post("/v1/identity", None, None, "application/json")
        ident = json.loads(body)
        token = ident["token"]
        self._call("create_workspace", ["Alice CLI"], token)
        ws = self._sql("SELECT id FROM my_workspaces", token)[0][0]
        state = {"identity": ident["identity"], "token": token, "workspace_id": ws}
        self._save(state)
        return state

    def _save(self, state: dict) -> None:
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(state))
        try:
            _STATE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600 — the token is a secret
        except OSError:
            pass

    # --- transport ------------------------------------------------------------------------
    def _token(self, override: str | None = None) -> str:
        return override or self._state["token"]

    def _call(self, reducer: str, args: list, token: str | None = None) -> int:
        status, _ = _post(f"/v1/database/{DB}/call/{reducer}", args, self._token(token), "application/json")
        return status

    def _call_proc(self, name: str, args: list, token: str | None = None):
        _, body = _post(f"/v1/database/{DB}/call/{name}", args, self._token(token), "application/json")
        return _decode(body)

    def _sql(self, query: str, token: str | None = None) -> list:
        _, body = _post(f"/v1/database/{DB}/sql", query, self._token(token), "text/plain")
        return json.loads(body)[0]["rows"]

    # --- operations -----------------------------------------------------------------------
    def capture(self, raw_content: str, explicit_signal: str | None) -> dict:
        ws = self._state["workspace_id"]
        ref = self._call_proc("capture_with_embedding", [ws, raw_content, "cli", explicit_signal or "note"])
        rows = self._sql("SELECT id, status, trust_class, embedding_ref FROM my_continuity_objects")
        latest = max(rows, key=lambda r: r[0]) if rows else None
        return {
            "backend": "spacetimedb",
            "workspace_id": ws,
            "embedding_ref": ref,
            "object": (
                {"id": latest[0], "status": latest[1], "trust_class": latest[2], "embedding_ref": latest[3]}
                if latest
                else None
            ),
        }

    def recall(self, query: str, limit: int) -> dict:
        hits = self._call_proc("recall_lexical", [self._state["workspace_id"], query or "", limit])
        return {"backend": "spacetimedb", "query": query, "results": hits}
