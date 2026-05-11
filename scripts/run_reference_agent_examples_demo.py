#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXAMPLE = REPO_ROOT / "docs" / "examples" / "generic_python_agent.py"
TYPESCRIPT_EXAMPLE = REPO_ROOT / "docs" / "examples" / "generic_typescript_agent.ts"
CANONICAL_BRIEF_FIXTURE = (
    REPO_ROOT / "fixtures" / "reference_integrations" / "continuity_brief_agent_handoff_v1.json"
)
TYPESCRIPT_PACKAGE = REPO_ROOT / "apps" / "web" / "node_modules" / "typescript"


def _brief_payload() -> dict[str, Any]:
    return json.loads(CANONICAL_BRIEF_FIXTURE.read_text(encoding="utf-8"))


class _DemoHandler(BaseHTTPRequestHandler):
    server_version = "AliceReferenceDemo/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/continuity/brief":
            self.send_error(404)
            return

        authorization = self.headers.get("Authorization")
        if authorization != "Bearer demo-session-token":
            self._write_json(401, {"detail": "invalid session token"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        request_payload = json.loads(body.decode("utf-8"))
        requested_brief_type = request_payload.get("brief_type")
        payload = _brief_payload()
        if isinstance(requested_brief_type, str) and requested_brief_type != "":
            payload["brief"]["brief_type"] = requested_brief_type
        self._write_json(200, payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        del format, args

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_demo_server() -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    port = _find_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{port}"


def _run_step(*, name: str, command: list[str], env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    parsed_stdout: dict[str, Any] | None = None
    stripped_stdout = completed.stdout.strip()
    if stripped_stdout:
        try:
            candidate = json.loads(stripped_stdout)
        except json.JSONDecodeError:
            candidate = None
        if isinstance(candidate, dict):
            parsed_stdout = candidate

    return {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "stdout": parsed_stdout,
        "stderr": completed.stderr.strip(),
    }


def _node_supports_strip_types(env: dict[str, str]) -> bool:
    completed = subprocess.run(
        ["node", "--experimental-strip-types", "--version"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _run_typescript_step(env: dict[str, str]) -> dict[str, Any]:
    if _node_supports_strip_types(env):
        return _run_step(
            name="typescript_example",
            command=["node", "--experimental-strip-types", str(TYPESCRIPT_EXAMPLE)],
            env=env,
        )

    with tempfile.TemporaryDirectory(prefix="alice-reference-agent-ts-") as temp_dir:
        compiled_path = Path(temp_dir) / "generic_typescript_agent.js"
        transpile_script = """
const fs = require("fs");
const ts = require(process.argv[1]);
const sourcePath = process.argv[2];
const outputPath = process.argv[3];
const source = fs.readFileSync(sourcePath, "utf8");
const output = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
  },
});
fs.writeFileSync(outputPath, output.outputText);
"""
        transpile = subprocess.run(
            ["node", "-e", transpile_script, str(TYPESCRIPT_PACKAGE), str(TYPESCRIPT_EXAMPLE), str(compiled_path)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if transpile.returncode != 0:
            return {
                "name": "typescript_example",
                "command": ["node", "--experimental-strip-types", str(TYPESCRIPT_EXAMPLE)],
                "returncode": transpile.returncode,
                "stdout": None,
                "stderr": transpile.stderr.strip(),
            }
        return _run_step(
            name="typescript_example",
            command=["node", str(compiled_path)],
            env=env,
        )


def main() -> int:
    server, thread, base_url = _start_demo_server()
    env = os.environ.copy()
    env.update(
        {
            "ALICE_API_BASE_URL": base_url,
            "ALICE_SESSION_TOKEN": "demo-session-token",
            "ALICE_BRIEF_TYPE": "agent_handoff",
            "ALICE_QUERY": "release handoff",
        }
    )

    try:
        python_step = _run_step(
            name="python_example",
            command=[sys.executable, str(PYTHON_EXAMPLE)],
            env=env,
        )
        typescript_step = _run_typescript_step(env)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    python_stdout = python_step["stdout"]
    typescript_stdout = typescript_step["stdout"]
    outputs_match = (
        isinstance(python_stdout, dict)
        and isinstance(typescript_stdout, dict)
        and python_stdout == typescript_stdout
    )

    ok = (
        python_step["returncode"] == 0
        and typescript_step["returncode"] == 0
        and outputs_match
    )

    payload = {
        "status": "pass" if ok else "fail",
        "demo_base_path": "/v1/continuity/brief",
        "contract_fixture": str(CANONICAL_BRIEF_FIXTURE.relative_to(REPO_ROOT)),
        "python_example": {
            "returncode": python_step["returncode"],
            "stdout": python_stdout,
            "stderr": python_step["stderr"],
        },
        "typescript_example": {
            "returncode": typescript_step["returncode"],
            "stdout": typescript_stdout,
            "stderr": typescript_step["stderr"],
        },
        "outputs_match": outputs_match,
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
