"""Reference thin Python client for Alice-on-SpacetimeDB (Track B prototype).

Demonstrates that Alice's Python surfaces (CLI / MCP / FastAPI) can drive the SpacetimeDB
continuity module over plain HTTP with a per-user Bearer token — reducers via
POST /v1/database/<db>/call/<reducer> (JSON array args), reads via POST .../sql.

This is a STANDALONE reference, not wired into existing Alice code. stdlib only.
"""
from __future__ import annotations

import json
import os
import urllib.request
import uuid

# Hosted SpacetimeDB (maincloud) by default — no local database.
BASE = os.environ.get("ALICE_SPACETIME_BASE", "https://maincloud.spacetimedb.com")
DB = os.environ.get("ALICE_SPACETIME_DB", "alice-continuity")


def _post(path: str, body, token: str | None, content_type: str):
    data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"{BASE}{path}", data=data, method="POST")
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode()


class SpacetimeClient:
    """The entire Track B adapter surface: provision identity, call reducers, run SQL."""

    def __init__(self, base: str = BASE, db: str = DB):
        self.base, self.db = base, db

    def provision_identity(self) -> dict:
        _, body = _post("/v1/identity", None, None, "application/json")
        return json.loads(body)  # {"identity": ..., "token": ...}

    def call(self, reducer: str, args: list, token: str) -> int:
        status, _ = _post(f"/v1/database/{self.db}/call/{reducer}", args, token, "application/json")
        return status

    def call_proc(self, proc: str, args: list, token: str) -> str:
        """Procedures return a value; unlike `call`, hand back the response body."""
        _, body = _post(f"/v1/database/{self.db}/call/{proc}", args, token, "application/json")
        return body

    def sql(self, query: str, token: str) -> list:
        _, body = _post(f"/v1/database/{self.db}/sql", query, token, "text/plain")
        return json.loads(body)[0]["rows"]


def main() -> None:
    c = SpacetimeClient()
    ident = c.provision_identity()
    token = ident["token"]
    print("identity:", ident["identity"][:18], "...")

    print("create_workspace ->", c.call("create_workspace", ["Py Ref WS"], token))
    ws = c.sql("SELECT id FROM my_workspaces", token)[0][0]
    print("workspace id:", ws)

    print("capture_with_embedding ->", c.call("capture_with_embedding", [ws, "remember the python path", "cli", "decision", uuid.uuid4().hex], token))
    objs = c.sql("SELECT id, status, trust_class, embedding_ref FROM my_continuity_objects", token)
    print("my_continuity_objects:", objs)

    obj_id = objs[0][0]
    print("commit_memory ->", c.call("commit_memory", [obj_id, "user_confirmed"], token))
    print("after commit:", c.sql("SELECT id, status, trust_class FROM my_continuity_objects", token))

    # Lexical recall over the just-captured memory (vector-free; no secrets).
    print("recall_lexical 'python' ->", c.call_proc("recall_lexical", [ws, "python", 5], token))
    print("recall_lexical 'zzqqxx' ->", c.call_proc("recall_lexical", [ws, "zzqqxx", 5], token))


if __name__ == "__main__":
    main()
