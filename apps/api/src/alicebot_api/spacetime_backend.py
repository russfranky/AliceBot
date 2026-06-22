"""Track B: thin SpacetimeDB backend for the Alice CLI (capture + recall).

Routes `alice capture` / `alice recall` to the hosted SpacetimeDB continuity module over plain
HTTP with a per-user token, instead of Postgres. Selected via `--backend spacetimedb` (or
`ALICE_BACKEND=spacetimedb`). Non-destructive: the Postgres path stays the default and is untouched.

State: the non-secret identity + workspace persist in a 0600 file under the user's config dir; the
token is stored in Alice's encrypted `SecretProvider` (ref `spacetime-token:<identity>`, encrypted
at rest and auto-redacted in logs because the ref contains "token"). When the module is loaded
standalone without the app package, it falls back to keeping the token in the 0600 state file.
stdlib transport only; no local database.

Deliberately NOT yet included (follow-up): output parity with the Postgres `format_capture_output`
/ `format_recall_output`. (Write idempotency and SecretProvider-backed tokens are done.)
"""
from __future__ import annotations

import json
import os
import ssl
import stat
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
