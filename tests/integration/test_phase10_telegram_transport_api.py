from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import anyio

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    encoded_body = b"" if payload is None else json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    request_headers = [(b"content-type", b"application/json")]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode(), value.encode()))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
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
    return start_message["status"], json.loads(body)


def auth_header(session_token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {session_token}"}


def _configure_settings(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
            telegram_link_ttl_seconds=600,
            telegram_bot_username="alicebot",
            telegram_webhook_secret="",
            telegram_bot_token="",
        ),
    )


def _bootstrap_workspace_session() -> tuple[str, str]:
    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": "telegram-builder@example.com"},
    )
    assert start_status == 200

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": start_payload["challenge"]["challenge_token"],
            "device_label": "Telegram Builder Device",
            "device_key": "telegram-builder-device",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "Telegram Builder Workspace"},
        headers=auth_header(session_token),
    )
    assert create_workspace_status == 201
    workspace_id = create_workspace_payload["workspace"]["id"]

    bootstrap_status, bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert bootstrap_status == 200
    assert bootstrap_payload["workspace"]["bootstrap_status"] == "ready"
    return session_token, workspace_id


def _create_and_bootstrap_workspace(session_token: str, workspace_name: str) -> str:
    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": workspace_name},
        headers=auth_header(session_token),
    )
    assert create_workspace_status == 201
    workspace_id = create_workspace_payload["workspace"]["id"]

    bootstrap_status, bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert bootstrap_status == 200
    assert bootstrap_payload["workspace"]["bootstrap_status"] == "ready"
    return workspace_id


def test_phase10_telegram_link_webhook_idempotency_and_dispatch_flow(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session()

    link_start_status, link_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert link_start_status == 200
    challenge_token = link_start_payload["challenge"]["challenge_token"]
    link_code = link_start_payload["challenge"]["link_code"]

    webhook_status, webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 2001,
            "message": {
                "message_id": 501,
                "date": 1710000000,
                "chat": {"id": 9001, "type": "private"},
                "from": {"id": 7001, "username": "builder"},
                "text": f"/link {link_code}",
            },
        },
    )
    assert webhook_status == 200
    assert webhook_payload["ingest"]["duplicate"] is False
    assert webhook_payload["ingest"]["route_status"] == "resolved"
    assert webhook_payload["ingest"]["link_status"] == "confirmed"

    duplicate_webhook_status, duplicate_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 2001,
            "message": {
                "message_id": 501,
                "date": 1710000000,
                "chat": {"id": 9001, "type": "private"},
                "from": {"id": 7001, "username": "builder"},
                "text": f"/link {link_code}",
            },
        },
    )
    assert duplicate_webhook_status == 200
    assert duplicate_webhook_payload["ingest"]["duplicate"] is True

    confirm_status, confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": challenge_token},
        headers=auth_header(session_token),
    )
    assert confirm_status == 201
    assert confirm_payload["identity"]["status"] == "linked"
    assert confirm_payload["identity"]["workspace_id"] == workspace_id

    status_code, status_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/status",
        headers=auth_header(session_token),
    )
    assert status_code == 200
    assert status_payload["linked"] is True
    assert status_payload["identity"]["external_chat_id"] == "9001"

    message_webhook_status, message_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 2002,
            "message": {
                "message_id": 502,
                "date": 1710000005,
                "chat": {"id": 9001, "type": "private"},
                "from": {"id": 7001, "username": "builder"},
                "text": "hello from telegram",
            },
        },
    )
    assert message_webhook_status == 200
    assert message_webhook_payload["ingest"]["route_status"] == "resolved"

    messages_status, messages_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/messages",
        headers=auth_header(session_token),
    )
    assert messages_status == 200
    assert messages_payload["summary"]["total_count"] == 2

    inbound_message = next(
        item for item in messages_payload["items"] if item["provider_update_id"] == "2002"
    )

    threads_status, threads_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/threads",
        headers=auth_header(session_token),
    )
    assert threads_status == 200
    assert threads_payload["summary"]["total_count"] == 1

    dispatch_status, dispatch_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/messages/{inbound_message['id']}/dispatch",
        payload={"text": "acknowledged"},
        headers=auth_header(session_token),
    )
    assert dispatch_status == 201
    assert dispatch_payload["message"]["direction"] == "outbound"
    assert dispatch_payload["receipt"]["status"] == "simulated"

    receipts_status, receipts_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/delivery-receipts",
        headers=auth_header(session_token),
    )
    assert receipts_status == 200
    assert receipts_payload["summary"]["total_count"] == 1
    assert receipts_payload["items"][0]["status"] == "simulated"


def test_phase10_telegram_invalid_link_token_and_unknown_chat_routing(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _workspace_id = _bootstrap_workspace_session()

    invalid_confirm_status, invalid_confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": "invalid-telegram-link-token"},
        headers=auth_header(session_token),
    )
    assert invalid_confirm_status == 400
    assert "invalid" in invalid_confirm_payload["detail"]

    unknown_webhook_status, unknown_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 3101,
            "message": {
                "message_id": 901,
                "date": 1710001000,
                "chat": {"id": 9900, "type": "private"},
                "from": {"id": 8800, "username": "unknown"},
                "text": "hello anyone there",
            },
        },
    )
    assert unknown_webhook_status == 200
    assert unknown_webhook_payload["ingest"]["unknown_chat_routing"] is True
    assert unknown_webhook_payload["ingest"]["route_status"] == "unresolved"

    messages_status, messages_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/messages",
        headers=auth_header(session_token),
    )
    assert messages_status == 200
    assert messages_payload["summary"]["total_count"] == 0

    malformed_webhook_status, malformed_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={"message": {}},
    )
    assert malformed_webhook_status == 400
    assert "update_id" in malformed_webhook_payload["detail"]


def test_phase10_telegram_unlink_and_relink_flow(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session()

    first_start_status, first_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert first_start_status == 200

    first_webhook_status, _first_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 4101,
            "message": {
                "message_id": 1101,
                "date": 1710002000,
                "chat": {"id": 777001, "type": "private"},
                "from": {"id": 77001, "username": "relinker"},
                "text": f"/link {first_start_payload['challenge']['link_code']}",
            },
        },
    )
    assert first_webhook_status == 200

    first_confirm_status, first_confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": first_start_payload["challenge"]["challenge_token"]},
        headers=auth_header(session_token),
    )
    assert first_confirm_status == 201
    assert first_confirm_payload["identity"]["status"] == "linked"

    unlink_status, unlink_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/unlink",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert unlink_status == 200
    assert unlink_payload["identity"]["status"] == "unlinked"

    unresolved_after_unlink_status, unresolved_after_unlink_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 4102,
            "message": {
                "message_id": 1102,
                "date": 1710002010,
                "chat": {"id": 777001, "type": "private"},
                "from": {"id": 77001, "username": "relinker"},
                "text": "post-unlink message",
            },
        },
    )
    assert unresolved_after_unlink_status == 200
    assert unresolved_after_unlink_payload["ingest"]["unknown_chat_routing"] is True

    second_start_status, second_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert second_start_status == 200

    second_webhook_status, second_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 4103,
            "message": {
                "message_id": 1103,
                "date": 1710002020,
                "chat": {"id": 777001, "type": "private"},
                "from": {"id": 77001, "username": "relinker"},
                "text": f"/link {second_start_payload['challenge']['link_code']}",
            },
        },
    )
    assert second_webhook_status == 200
    assert second_webhook_payload["ingest"]["link_status"] == "confirmed"

    second_confirm_status, second_confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": second_start_payload["challenge"]["challenge_token"]},
        headers=auth_header(session_token),
    )
    assert second_confirm_status == 201
    assert second_confirm_payload["identity"]["status"] == "linked"

    final_status_code, final_status_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/status",
        headers=auth_header(session_token),
    )
    assert final_status_code == 200
    assert final_status_payload["linked"] is True
    assert final_status_payload["identity"]["external_chat_id"] == "777001"


def test_phase10_telegram_rejects_confirmed_link_code_replay_from_different_chat(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session()

    link_start_status, link_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert link_start_status == 200
    challenge_token = link_start_payload["challenge"]["challenge_token"]
    link_code = link_start_payload["challenge"]["link_code"]

    first_webhook_status, first_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 5101,
            "message": {
                "message_id": 2101,
                "date": 1710003000,
                "chat": {"id": 880001, "type": "private"},
                "from": {"id": 880001, "username": "linkeduser"},
                "text": f"/link {link_code}",
            },
        },
    )
    assert first_webhook_status == 200
    assert first_webhook_payload["ingest"]["link_status"] == "confirmed"

    confirm_status, confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": challenge_token},
        headers=auth_header(session_token),
    )
    assert confirm_status == 201
    assert confirm_payload["identity"]["external_chat_id"] == "880001"

    replay_status, replay_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 5102,
            "message": {
                "message_id": 2102,
                "date": 1710003010,
                "chat": {"id": 880002, "type": "private"},
                "from": {"id": 880002, "username": "replayuser"},
                "text": f"/link {link_code}",
            },
        },
    )
    assert replay_status == 200
    assert replay_payload["ingest"]["link_status"] == "invalid_link_code"
    assert replay_payload["ingest"]["route_status"] == "unresolved"
    assert replay_payload["ingest"]["unknown_chat_routing"] is True


def test_phase10_telegram_rejects_cross_workspace_identity_conflict(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session()

    first_link_start_status, first_link_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert first_link_start_status == 200

    first_webhook_status, first_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 6101,
            "message": {
                "message_id": 3101,
                "date": 1710004000,
                "chat": {"id": 990001, "type": "private"},
                "from": {"id": 990001, "username": "workspaceone"},
                "text": f"/link {first_link_start_payload['challenge']['link_code']}",
            },
        },
    )
    assert first_webhook_status == 200
    assert first_webhook_payload["ingest"]["link_status"] == "confirmed"

    first_confirm_status, _first_confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": first_link_start_payload["challenge"]["challenge_token"]},
        headers=auth_header(session_token),
    )
    assert first_confirm_status == 201

    second_workspace_id = _create_and_bootstrap_workspace(
        session_token,
        "Telegram Builder Workspace Two",
    )

    second_link_start_status, second_link_start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": second_workspace_id},
        headers=auth_header(session_token),
    )
    assert second_link_start_status == 200

    second_webhook_status, second_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 6102,
            "message": {
                "message_id": 3102,
                "date": 1710004010,
                "chat": {"id": 990001, "type": "private"},
                "from": {"id": 990001, "username": "workspaceone"},
                "text": f"/link {second_link_start_payload['challenge']['link_code']}",
            },
        },
    )
    assert second_webhook_status == 200
    assert second_webhook_payload["ingest"]["link_status"] == "identity_conflict"

    second_confirm_status, second_confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": second_link_start_payload["challenge"]["challenge_token"]},
        headers=auth_header(session_token),
    )
    assert second_confirm_status == 409
    assert "pending webhook confirmation" in second_confirm_payload["detail"]

    second_status_code, second_status_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/status",
        query_params={"workspace_id": second_workspace_id},
        headers=auth_header(session_token),
    )
    assert second_status_code == 200
    assert second_status_payload["linked"] is False


def test_phase10_telegram_webhook_requires_secret_outside_dev(
    migrated_database_urls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="staging",
            database_url=migrated_database_urls["app"],
            telegram_webhook_secret="",
            telegram_bot_token="",
            telegram_bot_username="alicebot",
        ),
    )

    webhook_status, webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={"update_id": 1, "message": {"message_id": 1}},
    )
    assert webhook_status == 503
    assert webhook_payload == {"detail": "telegram webhook ingress is not configured"}


def test_phase10_telegram_webhook_rate_limit_enforced(
    migrated_database_urls,
    monkeypatch,
) -> None:
    main_module.entrypoint_rate_limiter.reset()
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            telegram_webhook_secret="",
            telegram_bot_token="",
                telegram_bot_username="alicebot",
                telegram_webhook_rate_limit_max_requests=1,
                telegram_webhook_rate_limit_window_seconds=60,
                entrypoint_rate_limit_backend="memory",
            ),
        )

    first_webhook_status, _first_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 7101,
            "message": {
                "message_id": 4001,
                "date": 1710007000,
                "chat": {"id": 12345, "type": "private"},
                "from": {"id": 12345, "username": "ratelimited"},
                "text": "hello",
            },
        },
    )
    assert first_webhook_status == 200

    second_webhook_status, second_webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 7102,
            "message": {
                "message_id": 4002,
                "date": 1710007005,
                "chat": {"id": 12345, "type": "private"},
                "from": {"id": 12345, "username": "ratelimited"},
                "text": "hello again",
            },
        },
    )
    assert second_webhook_status == 429
    assert second_webhook_payload["detail"]["code"] == "telegram_webhook_rate_limit_exceeded"
    assert second_webhook_payload["detail"]["max_requests"] == 1
    assert second_webhook_payload["detail"]["window_seconds"] == 60
