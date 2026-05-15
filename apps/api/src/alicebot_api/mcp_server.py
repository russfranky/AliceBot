from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, BinaryIO, Literal
from uuid import UUID

from alicebot_api import __version__
from alicebot_api.config import Settings, get_settings
from alicebot_api.mcp_tools import (
    MCPRuntimeContext,
    MCPToolError,
    MCPToolNotFoundError,
    call_mcp_tool,
    list_mcp_tools,
)


_JSONRPC_VERSION = "2.0"
_MCP_PROTOCOL_VERSION = "2024-11-05"
_MCP_SERVER_NAME = "alice-core-mcp"
_DEFAULT_MCP_USER_ID = "00000000-0000-0000-0000-000000000001"
_TRANSPORT_CONTENT_LENGTH = "content-length"
_TRANSPORT_JSON_LINE = "json-line"
_TransportMode = Literal["content-length", "json-line"]


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID value: {value}") from exc


def _resolve_user_id(settings: Settings, user_id_flag: str | None) -> UUID:
    if user_id_flag is not None:
        return _parse_uuid(user_id_flag)
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)
    return UUID(os.getenv("ALICEBOT_AUTH_USER_ID", _DEFAULT_MCP_USER_ID))


def _build_runtime_context(args: argparse.Namespace) -> MCPRuntimeContext:
    settings = get_settings()
    database_url = args.database_url if args.database_url is not None else settings.database_url
    user_id = _resolve_user_id(settings, args.user_id)
    return MCPRuntimeContext(database_url=database_url, user_id=user_id)


def _parse_json_rpc_payload(raw_payload: str) -> dict[str, Any]:
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("JSON-RPC payload must be an object")
    return payload


def _read_message(stream: BinaryIO) -> tuple[dict[str, Any], _TransportMode] | None:
    first_line = stream.readline()
    if first_line == b"":
        return None

    # MCP SDK >=1.0 stdio transport sends one JSON-RPC message per line.
    stripped_first_line = first_line.strip()
    if stripped_first_line.startswith(b"{"):
        payload = _parse_json_rpc_payload(stripped_first_line.decode("utf-8"))
        return payload, _TRANSPORT_JSON_LINE

    headers: dict[str, str] = {}
    line = first_line
    while True:
        if line in {b"\r\n", b"\n"}:
            break

        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            raise ValueError("invalid MCP header line")
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

        line = stream.readline()
        if line == b"":
            return None

    content_length_raw = headers.get("content-length")
    if content_length_raw is None:
        raise ValueError("missing Content-Length header")
    try:
        content_length = int(content_length_raw)
    except ValueError as exc:
        raise ValueError("invalid Content-Length header") from exc
    if content_length < 0:
        raise ValueError("invalid Content-Length header")

    body = stream.read(content_length)
    if len(body) != content_length:
        return None
    payload = _parse_json_rpc_payload(body.decode("utf-8"))
    return payload, _TRANSPORT_CONTENT_LENGTH


def _write_message(
    stream: BinaryIO,
    message: dict[str, Any],
    *,
    transport_mode: _TransportMode,
) -> None:
    encoded = json.dumps(message, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if transport_mode == _TRANSPORT_JSON_LINE:
        stream.write(encoded + b"\n")
    else:
        header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii")
        stream.write(header)
        stream.write(encoded)
    stream.flush()


def _response_success(request_id: object, *, result: object) -> dict[str, Any]:
    return {
        "jsonrpc": _JSONRPC_VERSION,
        "id": request_id,
        "result": result,
    }


def _response_error(request_id: object, *, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": _JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


class MCPServer:
    def __init__(self, *, context: MCPRuntimeContext, input_stream: BinaryIO, output_stream: BinaryIO) -> None:
        self._context = context
        self._input_stream = input_stream
        self._output_stream = output_stream
        self._transport_mode: _TransportMode = _TRANSPORT_CONTENT_LENGTH

    def _handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if request.get("jsonrpc") != _JSONRPC_VERSION:
            return _response_error(request.get("id"), code=-32600, message="invalid jsonrpc version")

        method = request.get("method")
        if not isinstance(method, str):
            return _response_error(request.get("id"), code=-32600, message="method must be a string")

        request_id = request.get("id")
        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return _response_error(request_id, code=-32602, message="params must be a JSON object")

        if method == "notifications/initialized":
            return None

        if request_id is None:
            return None

        if method == "initialize":
            return _response_success(
                request_id,
                result={
                    "protocolVersion": _MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": _MCP_SERVER_NAME,
                        "version": __version__,
                    },
                },
            )

        if method == "ping":
            return _response_success(request_id, result={})

        if method == "tools/list":
            return _response_success(
                request_id,
                result={
                    "tools": list_mcp_tools(),
                },
            )

        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                return _response_error(request_id, code=-32602, message="tools/call requires string name")

            arguments = params.get("arguments")
            try:
                structured = call_mcp_tool(
                    self._context,
                    name=name,
                    arguments=arguments,
                )
            except (MCPToolError, MCPToolNotFoundError) as exc:
                return _response_success(
                    request_id,
                    result={
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                )
            except Exception as exc:
                print(f"error: MCP tool call failed unexpectedly: {type(exc).__name__}", file=sys.stderr)
                return _response_success(
                    request_id,
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Tool execution failed unexpectedly. "
                                    f"Check Alice MCP server logs for {type(exc).__name__}."
                                ),
                            }
                        ],
                        "isError": True,
                    },
                )

            return _response_success(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(structured, separators=(",", ":"), sort_keys=True),
                        }
                    ],
                    "structuredContent": structured,
                    "isError": False,
                },
            )

        return _response_error(request_id, code=-32601, message=f"method not found: {method}")

    def run(self) -> int:
        while True:
            try:
                framed_request = _read_message(self._input_stream)
            except json.JSONDecodeError as exc:
                response = _response_error(None, code=-32700, message=f"parse error: {exc.msg}")
                _write_message(
                    self._output_stream,
                    response,
                    transport_mode=self._transport_mode,
                )
                continue
            except ValueError as exc:
                response = _response_error(None, code=-32600, message=str(exc))
                _write_message(
                    self._output_stream,
                    response,
                    transport_mode=self._transport_mode,
                )
                continue

            if framed_request is None:
                return 0

            request, transport_mode = framed_request
            self._transport_mode = transport_mode
            response = self._handle_request(request)
            if response is not None:
                _write_message(
                    self._output_stream,
                    response,
                    transport_mode=self._transport_mode,
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alicebot-mcp",
        description="Deterministic local MCP server for Alice continuity workflows.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override database URL. Defaults to settings/env DATABASE_URL.",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help=(
            "Override acting user UUID. Defaults to ALICEBOT_AUTH_USER_ID when set, "
            f"otherwise {_DEFAULT_MCP_USER_ID}."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        context = _build_runtime_context(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    server = MCPServer(
        context=context,
        input_stream=sys.stdin.buffer,
        output_stream=sys.stdout.buffer,
    )
    return server.run()


__all__ = ["MCPServer", "build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
