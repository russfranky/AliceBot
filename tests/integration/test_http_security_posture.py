from __future__ import annotations

import json

import anyio

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings


def invoke_request(
    method: str,
    path: str,
    *,
    scheme: str = "http",
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    messages: list[dict[str, object]] = []
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}
        request_received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    request_headers = [(b"content-type", b"application/json")]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": scheme,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": request_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("utf-8").lower(): value.decode("utf-8")
        for key, value in start_message["headers"]
    }
    return start_message["status"], response_headers, body


def test_security_headers_are_applied_to_api_responses(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            redis_url="redis://localhost:6379/0",
            s3_endpoint_url="http://localhost:9000",
        ),
    )
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: True)

    status_code, headers, body = invoke_request("GET", "/healthz")

    assert status_code == 200
    assert json.loads(body)["status"] == "ok"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "permissions-policy" in headers
    assert "strict-transport-security" not in headers


def test_security_headers_include_hsts_for_https_outside_dev(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="staging",
            database_url="postgresql://db",
            security_headers_hsts_max_age_seconds=86_400,
            security_headers_hsts_include_subdomains=True,
        ),
    )
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: True)

    status_code, headers, _body = invoke_request("GET", "/healthz", scheme="https")

    assert status_code == 200
    assert headers["strict-transport-security"] == "max-age=86400; includeSubDomains"


def test_cors_empty_allowlist_still_allows_non_browser_request(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=(),
        ),
    )
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: True)

    status_code, headers, body = invoke_request("GET", "/healthz")

    assert status_code == 200
    assert json.loads(body)["status"] == "ok"
    assert "access-control-allow-origin" not in headers


def test_cors_preflight_allows_configured_origin(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=("https://app.example.com",),
            cors_allowed_methods=("GET", "POST", "OPTIONS"),
            cors_allowed_headers=("Authorization", "Content-Type"),
            cors_allow_credentials=True,
            cors_preflight_max_age_seconds=900,
        ),
    )

    status_code, headers, body = invoke_request(
        "OPTIONS",
        "/healthz",
        headers={
            "origin": "https://app.example.com",
            "access-control-request-method": "GET",
            "access-control-request-headers": "authorization,content-type",
        },
    )

    assert status_code == 204
    assert body == b""
    assert headers["access-control-allow-origin"] == "https://app.example.com"
    assert headers["access-control-allow-methods"] == "GET, POST, OPTIONS"
    assert headers["access-control-allow-headers"] == "Authorization, Content-Type"
    assert headers["access-control-allow-credentials"] == "true"
    assert headers["access-control-max-age"] == "900"


def test_cors_preflight_allows_local_alpha_origins_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=("http://127.0.0.1:3000", "http://localhost:3000"),
            cors_allowed_methods=("GET", "OPTIONS"),
            cors_allowed_headers=("Content-Type",),
        ),
    )

    for origin in ("http://127.0.0.1:3000", "http://localhost:3000"):
        status_code, headers, body = invoke_request(
            "OPTIONS",
            "/healthz",
            headers={
                "origin": origin,
                "access-control-request-method": "GET",
            },
        )

        assert status_code == 204
        assert body == b""
        assert headers["access-control-allow-origin"] == origin
        assert headers["access-control-allow-methods"] == "GET, OPTIONS"


def test_cors_preflight_rejects_disallowed_origin(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=("https://app.example.com",),
        ),
    )

    status_code, headers, body = invoke_request(
        "OPTIONS",
        "/healthz",
        headers={
            "origin": "https://evil.example.com",
            "access-control-request-method": "GET",
        },
    )

    assert status_code == 403
    assert json.loads(body) == {"detail": "CORS origin is not allowed"}
    assert headers["x-content-type-options"] == "nosniff"


def test_cors_preflight_rejects_origin_when_allowlist_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=(),
        ),
    )

    status_code, _headers, body = invoke_request(
        "OPTIONS",
        "/healthz",
        headers={
            "origin": "http://127.0.0.1:3000",
            "access-control-request-method": "GET",
        },
    )

    assert status_code == 403
    assert json.loads(body) == {"detail": "CORS origin is not allowed"}


def test_cors_get_from_allowed_local_origin_includes_allow_origin(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url="postgresql://db",
            cors_allowed_origins=("http://127.0.0.1:3000", "http://localhost:3000"),
        ),
    )
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: True)

    status_code, headers, body = invoke_request(
        "GET",
        "/healthz",
        headers={"origin": "http://127.0.0.1:3000"},
    )

    assert status_code == 200
    assert json.loads(body)["status"] == "ok"
    assert headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert headers["vary"] == "Origin"
