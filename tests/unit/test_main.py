from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.responses import Response
import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.artifacts import TaskArtifactNotFoundError
from alicebot_api.compiler import CompiledTraceRun
from alicebot_api.contracts import AdmissionDecisionOutput
from alicebot_api.embedding import (
    EmbeddingConfigValidationError,
    MemoryEmbeddingNotFoundError,
    MemoryEmbeddingValidationError,
    TaskArtifactChunkEmbeddingNotFoundError,
    TaskArtifactChunkEmbeddingValidationError,
)
from alicebot_api.entity import EntityNotFoundError, EntityValidationError
from alicebot_api.entity_edge import EntityEdgeValidationError
from alicebot_api.memory import (
    MemoryAdmissionValidationError,
    MemoryReviewNotFoundError,
    OpenLoopNotFoundError,
    OpenLoopValidationError,
)
from alicebot_api.response_generation import ResponseFailure
from alicebot_api.semantic_retrieval import (
    SemanticArtifactChunkRetrievalValidationError,
    SemanticMemoryRetrievalValidationError,
)
from alicebot_api.store import ContinuityStoreInvariantError


def test_healthcheck_reports_ok_when_database_is_reachable(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=7,
    )
    ping_calls: list[tuple[str, int]] = []

    def fake_get_settings() -> Settings:
        return settings

    def fake_ping_database(database_url: str, timeout_seconds: int) -> bool:
        ping_calls.append((database_url, timeout_seconds))
        return True

    monkeypatch.setattr(main_module, "get_settings", fake_get_settings)
    monkeypatch.setattr(main_module, "ping_database", fake_ping_database)

    response = main_module.healthcheck()

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "environment": "test",
        "services": {
            "database": {"status": "ok"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }
    assert ping_calls == [("postgresql://db", 7)]


def test_healthcheck_reports_degraded_when_database_is_unreachable(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=4,
    )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: False)

    response = main_module.healthcheck()

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "environment": "test",
        "services": {
            "database": {"status": "unreachable"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }


def test_healthcheck_route_is_registered() -> None:
    route_paths = {route.path for route in main_module.app.routes}

    assert "/healthz" in route_paths
    assert "/v0/context/compile" in route_paths
    assert "/v0/responses" in route_paths
    assert "/v0/memories/admit" in route_paths
    assert "/v0/open-loops" in route_paths
    assert "/v0/open-loops/{open_loop_id}" in route_paths
    assert "/v0/open-loops/{open_loop_id}/status" in route_paths
    assert "/v0/consents" in route_paths
    assert "/v0/policies" in route_paths
    assert "/v0/policies/{policy_id}" in route_paths
    assert "/v0/policies/evaluate" in route_paths
    assert "/v0/memories/extract-explicit-preferences" in route_paths
    assert "/v0/open-loops/extract-explicit-commitments" in route_paths
    assert "/v0/memories/capture-explicit-signals" in route_paths
    assert "/v0/memories" in route_paths
    assert "/v0/memories/review-queue" in route_paths
    assert "/v0/memories/quality-gate" in route_paths
    assert "/v0/memories/hygiene-dashboard" in route_paths
    assert "/v0/memories/evaluation-summary" in route_paths
    assert "/v0/memories/semantic-retrieval" in route_paths
    assert "/v0/memories/{memory_id}" in route_paths
    assert "/v0/memories/{memory_id}/revisions" in route_paths
    assert "/v0/memories/{memory_id}/labels" in route_paths
    assert "/v0/embedding-configs" in route_paths
    assert "/v0/memory-embeddings" in route_paths
    assert "/v0/memories/{memory_id}/embeddings" in route_paths
    assert "/v0/memory-embeddings/{memory_embedding_id}" in route_paths
    assert "/v0/admin/debug/continuity/lifecycle" in route_paths
    assert "/v0/admin/debug/continuity/lifecycle/{continuity_object_id}" in route_paths
    assert "/v0/admin/debug/continuity/artifacts/{artifact_id}" in route_paths
    assert "/v0/continuity/explain/{continuity_object_id}" in route_paths
    assert "/v1/contradictions/detect" in route_paths
    assert "/v1/contradictions/cases" in route_paths
    assert "/v1/contradictions/cases/{contradiction_case_id}" in route_paths
    assert "/v1/contradictions/cases/{contradiction_case_id}/resolve" in route_paths
    assert "/v1/trust/signals" in route_paths
    assert "/v1/evals/suites" in route_paths
    assert "/v1/evals/runs" in route_paths
    assert "/v1/evals/runs/{eval_run_id}" in route_paths
    assert "/v0/patterns" in route_paths
    assert "/v0/patterns/{pattern_id}" in route_paths
    assert "/v0/playbooks" in route_paths
    assert "/v0/playbooks/{playbook_id}" in route_paths
    assert "/v0/task-artifact-chunk-embeddings" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}/chunk-embeddings" in route_paths
    assert "/v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings" in route_paths
    assert "/v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}" in route_paths
    assert "/v0/entities" in route_paths
    assert "/v0/entity-edges" in route_paths
    assert "/v0/tools/route" in route_paths
    assert "/v0/execution-budgets" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}/deactivate" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}/supersede" in route_paths
    assert "/v0/tool-executions" in route_paths
    assert "/v0/tool-executions/{execution_id}" in route_paths
    assert "/v0/tasks" in route_paths
    assert "/v0/tasks/{task_id}" in route_paths
    assert "/v0/tasks/{task_id}/workspace" in route_paths
    assert "/v0/tasks/{task_id}/steps" in route_paths
    assert "/v0/threads/health-dashboard" in route_paths
    assert "/v0/threads/{thread_id}/resumption-brief" in route_paths
    assert "/v0/task-workspaces" in route_paths
    assert "/v0/task-workspaces/{task_workspace_id}" in route_paths
    assert "/v0/task-workspaces/{task_workspace_id}/artifacts" in route_paths
    assert "/v0/task-artifacts" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}/ingest" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}/chunks" in route_paths
    assert "/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval" in route_paths
    assert "/v0/task-steps/{task_step_id}" in route_paths
    assert "/v0/task-steps/{task_step_id}/transition" in route_paths
    assert "/v0/entities/{entity_id}" in route_paths
    assert "/v0/entities/{entity_id}/edges" in route_paths
    assert "/v1/channels/telegram/daily-brief" in route_paths
    assert "/v1/channels/telegram/daily-brief/deliver" in route_paths
    assert "/v1/channels/telegram/notification-preferences" in route_paths
    assert "/v1/channels/telegram/open-loop-prompts" in route_paths
    assert "/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver" in route_paths
    assert "/v1/channels/telegram/scheduler/jobs" in route_paths
    assert "/v1/admin/hosted/design-partners" in route_paths
    assert "/v1/admin/hosted/design-partners/dashboard" in route_paths
    assert "/v1/admin/hosted/design-partners/{design_partner_id}" in route_paths
    assert "/v1/admin/hosted/design-partners/{design_partner_id}/workspaces" in route_paths
    assert "/v1/admin/hosted/design-partners/{design_partner_id}/feedback" in route_paths


def test_spacetime_routes_registered() -> None:
    route_paths = {route.path for route in main_module.app.routes}
    for path in (
        "/spacetime/capture",
        "/spacetime/recall",
        "/spacetime/exec/tasks",
        "/spacetime/exec/tools",
        "/spacetime/exec/tasks/{task_id}/tool",
        "/spacetime/exec/tasks/{task_id}/approval",
        "/spacetime/exec/approvals/{approval_id}",
        "/spacetime/exec/budget",
        "/spacetime/exec/tasks/{task_id}/enqueue",
        "/spacetime/exec/execute",
        "/spacetime/exec/status",
    ):
        assert path in route_paths


def test_spacetime_routes_return_404_without_flag(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_BACKEND", raising=False)
    response = main_module.spacetime_exec_status()
    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "spacetimedb backend is not enabled"}


def test_spacetime_route_dispatches_to_backend_with_flag(monkeypatch) -> None:
    monkeypatch.setenv("ALICE_BACKEND", "spacetimedb")

    class _FakeBackend:
        def exec_status(self) -> dict:
            return {"backend": "spacetimedb", "runs": []}

        def enqueue(self, task_id: int, stub_mode: str, retry_cap: int) -> dict:
            raise ValueError("spacetimedb rejected the call (HTTP 530): task is not approved")

    monkeypatch.setattr(main_module, "_spacetime_backend_or_none", lambda: _FakeBackend())

    ok = main_module.spacetime_exec_status()
    assert ok.status_code == 200
    assert json.loads(ok.body) == {"backend": "spacetimedb", "runs": []}

    # A module reject (SpacetimeBackend raises ValueError) maps to a clean 400, not a 500.
    rejected = main_module.spacetime_exec_enqueue(1, main_module.SpacetimeEnqueueRequest())
    assert rejected.status_code == 400
    assert "task is not approved" in json.loads(rejected.body)["detail"]


def test_redact_url_credentials_strips_embedded_secrets() -> None:
    assert main_module.redact_url_credentials("redis://alicebot:supersecret@cache:6379/0") == (
        "redis://cache:6379/0"
    )
    assert main_module.redact_url_credentials("redis://cache:6379/0") == "redis://cache:6379/0"


def test_build_healthcheck_payload_keeps_boundary_statuses_consistent() -> None:
    settings = Settings(
        app_env="test",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
    )

    assert main_module.build_healthcheck_payload(settings, database_ok=True) == {
        "status": "ok",
        "environment": "test",
        "services": {
            "database": {"status": "ok"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }
    assert main_module.build_healthcheck_payload(settings, database_ok=False)["services"][
        "database"
    ] == {"status": "unreachable"}


def _build_request(
    *,
    method: str,
    path: str,
    query_string: str = "",
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    client_host: str = "127.0.0.1",
) -> Request:
    encoded_headers = [
        (key.lower().encode("utf-8"), value.encode("utf-8"))
        for key, value in (headers or {}).items()
    ]

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string.encode("utf-8"),
            "headers": encoded_headers,
            "client": (client_host, 12345),
            "server": ("testserver", 80),
        },
        receive,
    )


def test_resolve_authenticated_user_id_prefers_configured_identity() -> None:
    configured_user_id = uuid4()
    request = _build_request(
        method="GET",
        path="/v0/threads",
        headers={"x-alicebot-user-id": str(uuid4())},
    )

    resolved = main_module._resolve_authenticated_user_id(
        Settings(app_env="test", auth_user_id=str(configured_user_id)),
        request,
    )

    assert resolved == configured_user_id


def test_resolve_authenticated_user_id_allows_dev_without_header() -> None:
    request = _build_request(method="GET", path="/v0/threads")

    resolved = main_module._resolve_authenticated_user_id(
        Settings(app_env="test", auth_user_id=""),
        request,
    )

    assert resolved is None


def test_request_client_is_loopback_accepts_localhost() -> None:
    request = _build_request(method="GET", path="/v0/threads")

    assert main_module._request_client_is_loopback(request, Settings()) is True


def test_request_client_is_loopback_rejects_remote_clients() -> None:
    request = _build_request(
        method="GET",
        path="/v0/threads",
        client_host="203.0.113.10",
    )

    assert main_module._request_client_is_loopback(request, Settings()) is False


def test_v0_middleware_blocks_non_dev_when_legacy_api_disabled(monkeypatch) -> None:
    request = _build_request(method="GET", path="/v0/threads")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(app_env="production", auth_user_id=str(uuid4())),
    )

    async def call_next(_: Request) -> Response:
        return Response(status_code=204)

    response = asyncio.run(main_module.enforce_authenticated_user_identity(request, call_next))

    assert response.status_code == 404


def test_v0_middleware_blocks_remote_clients_outside_dev(monkeypatch) -> None:
    request = _build_request(
        method="GET",
        path="/v0/threads",
        client_host="203.0.113.10",
    )
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="production",
            auth_user_id=str(uuid4()),
            legacy_v0_enabled_outside_dev=True,
        ),
    )

    async def call_next(_: Request) -> Response:
        return Response(status_code=204)

    response = asyncio.run(main_module.enforce_authenticated_user_identity(request, call_next))

    assert response.status_code == 403


def test_rewrite_user_id_query_param_rejects_mismatch() -> None:
    request = _build_request(
        method="GET",
        path="/v0/threads",
        query_string="user_id=00000000-0000-0000-0000-000000000002",
    )

    with pytest.raises(ValueError, match="query user_id does not match authenticated user"):
        main_module._rewrite_user_id_query_param(
            request,
            uuid4(),
        )


def test_rewrite_user_id_json_body_injects_missing_user_id() -> None:
    authenticated_user_id = uuid4()
    thread_id = uuid4()
    request = _build_request(
        method="POST",
        path="/v0/responses",
        body=json.dumps({"thread_id": str(thread_id), "message": "hello"}).encode("utf-8"),
        headers={"content-type": "application/json"},
    )

    rewritten_request = asyncio.run(
        main_module._rewrite_user_id_json_body(request, authenticated_user_id)
    )
    rewritten_body = asyncio.run(rewritten_request.body())

    assert json.loads(rewritten_body) == {
        "thread_id": str(thread_id),
        "message": "hello",
        "user_id": str(authenticated_user_id),
    }


def test_rewrite_user_id_json_body_rejects_mismatch() -> None:
    request = _build_request(
        method="POST",
        path="/v0/responses",
        body=json.dumps(
            {
                "user_id": "00000000-0000-0000-0000-000000000001",
                "thread_id": str(uuid4()),
                "message": "hello",
            }
        ).encode("utf-8"),
        headers={"content-type": "application/json"},
    )

    with pytest.raises(ValueError, match="request user_id does not match authenticated user"):
        asyncio.run(main_module._rewrite_user_id_json_body(request, uuid4()))


def test_request_client_identifier_ignores_forwarded_header_when_proxy_not_trusted() -> None:
    request = _build_request(
        method="POST",
        path="/v1/auth/magic-link/start",
        headers={"x-forwarded-for": "203.0.113.9, 127.0.0.1"},
    )

    client_identifier = main_module._request_client_identifier(
        request,
        Settings(database_url="postgresql://app"),
    )

    assert client_identifier == "127.0.0.1"


def test_request_client_identifier_uses_forwarded_header_for_trusted_proxy() -> None:
    request = _build_request(
        method="POST",
        path="/v1/auth/magic-link/start",
        headers={"x-forwarded-for": "203.0.113.9, 127.0.0.1"},
    )

    client_identifier = main_module._request_client_identifier(
        request,
        Settings(
            database_url="postgresql://app",
            trust_proxy_headers=True,
            trusted_proxy_ips=("127.0.0.1",),
        ),
    )

    assert client_identifier == "203.0.113.9"


def test_entrypoint_rate_limit_memory_backend_enforces_limits() -> None:
    settings = Settings(
        database_url="postgresql://app",
        entrypoint_rate_limit_backend="memory",
    )

    main_module.entrypoint_rate_limiter.reset()
    first_result = main_module._enforce_entrypoint_rate_limit(
        settings=settings,
        key="entrypoint-test-memory-backend",
        max_requests=1,
        window_seconds=60,
        detail_code="entrypoint_test_limited",
        message="entrypoint test limit exceeded",
    )
    second_result = main_module._enforce_entrypoint_rate_limit(
        settings=settings,
        key="entrypoint-test-memory-backend",
        max_requests=1,
        window_seconds=60,
        detail_code="entrypoint_test_limited",
        message="entrypoint test limit exceeded",
    )
    main_module.entrypoint_rate_limiter.reset()

    assert first_result is None
    assert second_result is not None
    assert second_result.status_code == 429
    assert json.loads(second_result.body)["detail"]["code"] == "entrypoint_test_limited"


def test_entrypoint_rate_limit_returns_503_when_redis_backend_is_unavailable(monkeypatch) -> None:
    settings = Settings(
        app_env="staging",
        database_url="postgresql://app",
        entrypoint_rate_limit_backend="redis",
    )
    main_module.entrypoint_rate_limiter.reset()
    monkeypatch.setattr(main_module, "redis", None)

    limited = main_module._enforce_entrypoint_rate_limit(
        settings=settings,
        key="entrypoint-test-redis-unavailable",
        max_requests=1,
        window_seconds=60,
        detail_code="entrypoint_test_limited",
        message="entrypoint test limit exceeded",
    )

    assert limited is not None
    assert limited.status_code == 503
    assert json.loads(limited.body) == {
        "detail": {
            "code": "entrypoint_rate_limiter_unavailable",
            "message": "entrypoint rate limiter backend is unavailable",
        }
    }


def test_compile_context_returns_trace_and_context_pack(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_compile_and_persist_trace(
        store,
        *,
        user_id,
        thread_id,
        limits,
        semantic_retrieval,
        artifact_retrieval,
        semantic_artifact_retrieval,
    ):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["limits"] = limits
        captured["semantic_retrieval"] = semantic_retrieval
        captured["artifact_retrieval"] = artifact_retrieval
        captured["semantic_artifact_retrieval"] = semantic_artifact_retrieval
        return CompiledTraceRun(
            trace_id="trace-123",
            trace_event_count=5,
            context_pack={
                "compiler_version": "continuity_v0",
                "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
                "limits": {
                    "max_sessions": 2,
                    "max_events": 4,
                    "max_memories": 3,
                    "max_entities": 2,
                    "max_entity_edges": 6,
                },
                "user": {
                    "id": str(user_id),
                    "email": "owner@example.com",
                    "display_name": "Owner",
                    "created_at": "2026-03-11T09:00:00+00:00",
                },
                "thread": {
                    "id": str(thread_id),
                    "title": "Thread",
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:01:00+00:00",
                },
                "sessions": [],
                "events": [],
                "memories": [
                    {
                        "id": "memory-123",
                        "memory_key": "user.preference.coffee",
                        "value": {"likes": "oat milk"},
                        "status": "active",
                        "source_event_ids": ["event-1"],
                        "created_at": "2026-03-11T09:00:00+00:00",
                        "updated_at": "2026-03-11T09:02:00+00:00",
                        "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
                    }
                ],
                "memory_summary": {
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_deleted_count": 1,
                    "excluded_limit_count": 0,
                    "hybrid_retrieval": {
                        "requested": False,
                        "embedding_config_id": None,
                        "query_vector_dimensions": 0,
                        "semantic_limit": 0,
                        "symbolic_selected_count": 1,
                        "semantic_selected_count": 0,
                        "merged_candidate_count": 1,
                        "deduplicated_count": 0,
                        "included_symbolic_only_count": 1,
                        "included_semantic_only_count": 0,
                        "included_dual_source_count": 0,
                        "similarity_metric": None,
                        "source_precedence": ["symbolic", "semantic"],
                        "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
                        "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
                    },
                },
                "artifact_chunks": [],
                "artifact_chunk_summary": {
                    "requested": False,
                    "lexical_requested": False,
                    "semantic_requested": False,
                    "scope": None,
                    "query": None,
                    "query_terms": [],
                    "embedding_config_id": None,
                    "query_vector_dimensions": 0,
                    "limit": 0,
                    "lexical_limit": 0,
                    "semantic_limit": 0,
                    "searched_artifact_count": 0,
                    "lexical_candidate_count": 0,
                    "semantic_candidate_count": 0,
                    "merged_candidate_count": 0,
                    "deduplicated_count": 0,
                    "included_count": 0,
                    "included_lexical_only_count": 0,
                    "included_semantic_only_count": 0,
                    "included_dual_source_count": 0,
                    "excluded_uningested_artifact_count": 0,
                    "excluded_limit_count": 0,
                    "matching_rule": None,
                    "similarity_metric": None,
                    "source_precedence": ["lexical", "semantic"],
                    "lexical_order": [
                        "matched_query_term_count_desc",
                        "first_match_char_start_asc",
                        "relative_path_asc",
                        "sequence_no_asc",
                        "id_asc",
                    ],
                    "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
                    "merged_order": [
                        "source_precedence_asc",
                        "lexical_rank_asc",
                        "semantic_rank_asc",
                        "relative_path_asc",
                        "sequence_no_asc",
                        "id_asc",
                    ],
                },
                "entities": [
                    {
                        "id": "entity-123",
                        "entity_type": "project",
                        "name": "AliceBot",
                        "source_memory_ids": ["memory-123"],
                        "created_at": "2026-03-11T09:03:00+00:00",
                    }
                ],
                "entity_summary": {
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_limit_count": 1,
                },
                "entity_edges": [
                    {
                        "id": "edge-123",
                        "from_entity_id": "entity-123",
                        "to_entity_id": "entity-999",
                        "relationship_type": "depends_on",
                        "valid_from": "2026-03-11T09:04:00+00:00",
                        "valid_to": None,
                        "source_memory_ids": ["memory-123"],
                        "created_at": "2026-03-11T09:04:00+00:00",
                    }
                ],
                "entity_edge_summary": {
                    "anchor_entity_count": 1,
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_limit_count": 1,
                },
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": user_id,
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(main_module, "compile_and_persist_trace", fake_compile_and_persist_trace)

    response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            max_sessions=2,
            max_events=4,
            max_memories=3,
            max_entities=2,
            max_entity_edges=6,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "trace_id": "trace-123",
        "trace_event_count": 5,
        "context_pack": {
            "compiler_version": "continuity_v0",
            "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
            "limits": {
                "max_sessions": 2,
                "max_events": 4,
                "max_memories": 3,
                "max_entities": 2,
                "max_entity_edges": 6,
            },
            "user": {
                "id": str(user_id),
                "email": "owner@example.com",
                "display_name": "Owner",
                "created_at": "2026-03-11T09:00:00+00:00",
            },
            "thread": {
                "id": str(thread_id),
                "title": "Thread",
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:01:00+00:00",
            },
            "sessions": [],
            "events": [],
            "memories": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:02:00+00:00",
                    "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
                }
            ],
            "memory_summary": {
                "candidate_count": 2,
                "included_count": 1,
                "excluded_deleted_count": 1,
                "excluded_limit_count": 0,
                "hybrid_retrieval": {
                    "requested": False,
                    "embedding_config_id": None,
                    "query_vector_dimensions": 0,
                    "semantic_limit": 0,
                    "symbolic_selected_count": 1,
                    "semantic_selected_count": 0,
                    "merged_candidate_count": 1,
                    "deduplicated_count": 0,
                    "included_symbolic_only_count": 1,
                    "included_semantic_only_count": 0,
                    "included_dual_source_count": 0,
                    "similarity_metric": None,
                    "source_precedence": ["symbolic", "semantic"],
                    "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
                    "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
                },
            },
            "artifact_chunks": [],
            "artifact_chunk_summary": {
                "requested": False,
                "lexical_requested": False,
                "semantic_requested": False,
                "scope": None,
                "query": None,
                "query_terms": [],
                "embedding_config_id": None,
                "query_vector_dimensions": 0,
                "limit": 0,
                "lexical_limit": 0,
                "semantic_limit": 0,
                "searched_artifact_count": 0,
                "lexical_candidate_count": 0,
                "semantic_candidate_count": 0,
                "merged_candidate_count": 0,
                "deduplicated_count": 0,
                "included_count": 0,
                "included_lexical_only_count": 0,
                "included_semantic_only_count": 0,
                "included_dual_source_count": 0,
                "excluded_uningested_artifact_count": 0,
                "excluded_limit_count": 0,
                "matching_rule": None,
                "similarity_metric": None,
                "source_precedence": ["lexical", "semantic"],
                "lexical_order": [
                    "matched_query_term_count_desc",
                    "first_match_char_start_asc",
                    "relative_path_asc",
                    "sequence_no_asc",
                    "id_asc",
                ],
                "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
                "merged_order": [
                    "source_precedence_asc",
                    "lexical_rank_asc",
                    "semantic_rank_asc",
                    "relative_path_asc",
                    "sequence_no_asc",
                    "id_asc",
                ],
            },
            "entities": [
                {
                    "id": "entity-123",
                    "entity_type": "project",
                    "name": "AliceBot",
                    "source_memory_ids": ["memory-123"],
                    "created_at": "2026-03-11T09:03:00+00:00",
                }
            ],
            "entity_summary": {
                "candidate_count": 2,
                "included_count": 1,
                "excluded_limit_count": 1,
            },
            "entity_edges": [
                {
                    "id": "edge-123",
                    "from_entity_id": "entity-123",
                    "to_entity_id": "entity-999",
                    "relationship_type": "depends_on",
                    "valid_from": "2026-03-11T09:04:00+00:00",
                    "valid_to": None,
                    "source_memory_ids": ["memory-123"],
                    "created_at": "2026-03-11T09:04:00+00:00",
                }
            ],
                "entity_edge_summary": {
                    "anchor_entity_count": 1,
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_limit_count": 1,
                },
            },
            "metadata": {
                "agent_profile_id": "assistant_default",
            },
        }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["thread_id"] == thread_id
    assert captured["limits"].max_sessions == 2
    assert captured["limits"].max_events == 4
    assert captured["limits"].max_memories == 3
    assert captured["limits"].max_entities == 2
    assert captured["limits"].max_entity_edges == 6
    assert captured["semantic_retrieval"] is None
    assert captured["artifact_retrieval"] is None
    assert captured["semantic_artifact_retrieval"] is None


def test_compile_context_returns_not_found_when_scope_row_is_missing(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": uuid4(),
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(
        main_module,
        "compile_and_persist_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ContinuityStoreInvariantError("get_thread did not return a row from the database")
        ),
    )

    response = main_module.compile_context(
        main_module.CompileContextRequest(user_id=uuid4(), thread_id=uuid4())
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": "get_thread did not return a row from the database",
    }


def test_compile_context_routes_semantic_and_artifact_inputs_and_validation_errors(
    monkeypatch,
) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_compile_and_persist_trace(
        store,
        *,
        user_id,
        thread_id,
        limits,
        semantic_retrieval,
        artifact_retrieval,
        semantic_artifact_retrieval,
    ):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["limits"] = limits
        captured["semantic_retrieval"] = semantic_retrieval
        captured["artifact_retrieval"] = artifact_retrieval
        captured["semantic_artifact_retrieval"] = semantic_artifact_retrieval
        return CompiledTraceRun(
            trace_id="trace-semantic",
            trace_event_count=7,
            context_pack={
                "compiler_version": "continuity_v0",
                "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
                "limits": {
                    "max_sessions": 3,
                    "max_events": 8,
                    "max_memories": 5,
                    "max_entities": 5,
                    "max_entity_edges": 10,
                },
                "user": {
                    "id": str(user_id),
                    "email": "owner@example.com",
                    "display_name": "Owner",
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
                "thread": {
                    "id": str(thread_id),
                    "title": "Thread",
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:01:00+00:00",
                },
                "sessions": [],
                "events": [],
                "memories": [
                    {
                        "id": "memory-123",
                        "memory_key": "user.preference.coffee",
                        "value": {"likes": "oat milk"},
                        "status": "active",
                        "source_event_ids": ["event-123"],
                        "created_at": "2026-03-12T09:00:00+00:00",
                        "updated_at": "2026-03-12T09:00:00+00:00",
                        "source_provenance": {
                            "sources": ["symbolic", "semantic"],
                            "semantic_score": 0.99,
                        },
                    }
                ],
                "memory_summary": {
                    "candidate_count": 1,
                    "included_count": 1,
                    "excluded_deleted_count": 0,
                    "excluded_limit_count": 0,
                    "hybrid_retrieval": {
                        "requested": True,
                        "embedding_config_id": str(config_id),
                        "query_vector_dimensions": 3,
                        "semantic_limit": 2,
                        "symbolic_selected_count": 1,
                        "semantic_selected_count": 1,
                        "merged_candidate_count": 1,
                        "deduplicated_count": 1,
                        "included_symbolic_only_count": 0,
                        "included_semantic_only_count": 0,
                        "included_dual_source_count": 1,
                        "similarity_metric": "cosine_similarity",
                        "source_precedence": ["symbolic", "semantic"],
                        "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
                        "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
                    },
                },
                "artifact_chunks": [
                    {
                        "id": "chunk-123",
                        "task_id": "task-123",
                        "task_artifact_id": "artifact-123",
                        "relative_path": "docs/spec.txt",
                        "media_type": "text/plain",
                        "sequence_no": 1,
                        "char_start": 0,
                        "char_end_exclusive": 16,
                        "text": "alpha beta spec",
                        "source_provenance": {
                            "sources": ["lexical", "semantic"],
                            "lexical_match": {
                                "matched_query_terms": ["alpha", "beta"],
                                "matched_query_term_count": 2,
                                "first_match_char_start": 0,
                            },
                            "semantic_score": 0.99,
                        },
                    }
                ],
                "artifact_chunk_summary": {
                    "requested": True,
                    "lexical_requested": True,
                    "semantic_requested": True,
                    "scope": {"kind": "task", "task_id": "task-123"},
                    "query": "alpha beta",
                    "query_terms": ["alpha", "beta"],
                    "embedding_config_id": str(config_id),
                    "query_vector_dimensions": 3,
                    "limit": 2,
                    "lexical_limit": 2,
                    "semantic_limit": 2,
                    "searched_artifact_count": 1,
                    "lexical_candidate_count": 1,
                    "semantic_candidate_count": 1,
                    "merged_candidate_count": 1,
                    "deduplicated_count": 1,
                    "included_count": 1,
                    "included_lexical_only_count": 0,
                    "included_semantic_only_count": 0,
                    "included_dual_source_count": 1,
                    "excluded_uningested_artifact_count": 0,
                    "excluded_limit_count": 0,
                    "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
                    "similarity_metric": "cosine_similarity",
                    "source_precedence": ["lexical", "semantic"],
                    "lexical_order": [
                        "matched_query_term_count_desc",
                        "first_match_char_start_asc",
                        "relative_path_asc",
                        "sequence_no_asc",
                        "id_asc",
                    ],
                    "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
                    "merged_order": [
                        "source_precedence_asc",
                        "lexical_rank_asc",
                        "semantic_rank_asc",
                        "relative_path_asc",
                        "sequence_no_asc",
                        "id_asc",
                    ],
                },
                "entities": [],
                "entity_summary": {
                    "candidate_count": 0,
                    "included_count": 0,
                    "excluded_limit_count": 0,
                },
                "entity_edges": [],
                "entity_edge_summary": {
                    "anchor_entity_count": 0,
                    "candidate_count": 0,
                    "included_count": 0,
                    "excluded_limit_count": 0,
                },
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": user_id,
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(main_module, "compile_and_persist_trace", fake_compile_and_persist_trace)

    response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            semantic=main_module.CompileContextSemanticRequest(
                embedding_config_id=config_id,
                query_vector=[0.1, 0.2, 0.3],
                limit=2,
            ),
            artifact_retrieval=main_module.CompileContextTaskScopedArtifactRetrievalRequest(
                kind="task",
                task_id=uuid4(),
                query="alpha beta",
                limit=2,
            ),
            semantic_artifact_retrieval=(
                main_module.CompileContextTaskScopedSemanticArtifactRetrievalRequest(
                    kind="task",
                    task_id=uuid4(),
                    embedding_config_id=config_id,
                    query_vector=[0.1, 0.2, 0.3],
                    limit=2,
                )
            ),
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["context_pack"]["memory_summary"]["hybrid_retrieval"] == {
        "requested": True,
        "embedding_config_id": str(config_id),
        "query_vector_dimensions": 3,
        "semantic_limit": 2,
        "symbolic_selected_count": 1,
        "semantic_selected_count": 1,
        "merged_candidate_count": 1,
        "deduplicated_count": 1,
        "included_symbolic_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 1,
        "similarity_metric": "cosine_similarity",
        "source_precedence": ["symbolic", "semantic"],
        "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
        "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["semantic_retrieval"].embedding_config_id == config_id
    assert captured["semantic_retrieval"].query_vector == (0.1, 0.2, 0.3)
    assert captured["semantic_retrieval"].limit == 2
    assert captured["artifact_retrieval"].task_id is not None
    assert captured["artifact_retrieval"].query == "alpha beta"
    assert captured["artifact_retrieval"].limit == 2
    assert captured["semantic_artifact_retrieval"].task_id is not None
    assert captured["semantic_artifact_retrieval"].embedding_config_id == config_id
    assert captured["semantic_artifact_retrieval"].query_vector == (0.1, 0.2, 0.3)
    assert captured["semantic_artifact_retrieval"].limit == 2

    monkeypatch.setattr(
        main_module,
        "compile_and_persist_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SemanticMemoryRetrievalValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            semantic=main_module.CompileContextSemanticRequest(
                embedding_config_id=config_id,
                query_vector=[0.1, 0.2, 0.3],
                limit=2,
            ),
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }

    monkeypatch.setattr(
        main_module,
        "compile_and_persist_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SemanticArtifactChunkRetrievalValidationError(
                "query_vector length must match embedding config dimensions (3): 2"
            )
        ),
    )

    semantic_artifact_error_response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            semantic_artifact_retrieval=(
                main_module.CompileContextTaskScopedSemanticArtifactRetrievalRequest(
                    kind="task",
                    task_id=uuid4(),
                    embedding_config_id=config_id,
                    query_vector=[0.1, 0.2],
                    limit=2,
                )
            ),
        )
    )

    assert semantic_artifact_error_response.status_code == 400
    assert json.loads(semantic_artifact_error_response.body) == {
        "detail": "query_vector length must match embedding config dimensions (3): 2"
    }


def test_compile_context_request_rejects_invalid_artifact_scope_shape() -> None:
    with pytest.raises(Exception) as exc_info:
        main_module.CompileContextRequest(
            user_id=uuid4(),
            thread_id=uuid4(),
            artifact_retrieval={
                "kind": "task",
                "task_artifact_id": str(uuid4()),
                "query": "alpha beta",
            },
        )

    assert "task_id" in str(exc_info.value)


def test_compile_context_request_rejects_invalid_semantic_artifact_scope_shape() -> None:
    with pytest.raises(Exception) as exc_info:
        main_module.CompileContextRequest(
            user_id=uuid4(),
            thread_id=uuid4(),
            semantic_artifact_retrieval={
                "kind": "task",
                "task_artifact_id": str(uuid4()),
                "embedding_config_id": str(uuid4()),
                "query_vector": [0.1, 0.2, 0.3],
            },
        )

    assert "task_id" in str(exc_info.value)


def test_generate_assistant_response_returns_assistant_and_trace_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(
        database_url="postgresql://app",
        model_provider="openai_responses",
        model_name="gpt-5-mini",
    )
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_generate_response(store, *, settings, user_id, thread_id, message_text, limits):
        captured["store_type"] = type(store).__name__
        captured["settings"] = settings
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["message_text"] = message_text
        captured["limits"] = limits
        return {
            "assistant": {
                "event_id": "assistant-event-123",
                "sequence_no": 5,
                "text": "Hello back.",
                "model_provider": "openai_responses",
                "model": "gpt-5-mini",
            },
            "trace": {
                "compile_trace_id": "compile-trace-123",
                "compile_trace_event_count": 11,
                "response_trace_id": "response-trace-123",
                "response_trace_event_count": 2,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": user_id,
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(main_module, "generate_response", fake_generate_response)

    response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello?",
            max_sessions=2,
            max_events=4,
            max_memories=3,
            max_entities=2,
            max_entity_edges=6,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "assistant": {
            "event_id": "assistant-event-123",
            "sequence_no": 5,
            "text": "Hello back.",
            "model_provider": "openai_responses",
            "model": "gpt-5-mini",
        },
        "trace": {
            "compile_trace_id": "compile-trace-123",
            "compile_trace_event_count": 11,
            "response_trace_id": "response-trace-123",
            "response_trace_event_count": 2,
        },
        "metadata": {
            "agent_profile_id": "assistant_default",
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["thread_id"] == thread_id
    assert captured["message_text"] == "Hello?"
    assert captured["limits"].max_sessions == 2
    assert captured["limits"].max_events == 4
    assert captured["limits"].max_memories == 3
    assert captured["limits"].max_entities == 2
    assert captured["limits"].max_entity_edges == 6


def test_generate_assistant_response_returns_502_with_trace_when_model_invocation_fails(
    monkeypatch,
) -> None:
    user_id = uuid4()
    thread_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": user_id,
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(
        main_module,
        "generate_response",
        lambda *_args, **_kwargs: ResponseFailure(
            detail="upstream timeout",
            trace={
                "compile_trace_id": "compile-trace-123",
                "compile_trace_event_count": 9,
                "response_trace_id": "response-trace-123",
                "response_trace_event_count": 2,
            },
        ),
    )

    response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello?",
        )
    )

    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": "upstream timeout",
        "trace": {
            "compile_trace_id": "compile-trace-123",
            "compile_trace_event_count": 9,
            "response_trace_id": "response-trace-123",
            "response_trace_event_count": 2,
        },
        "metadata": {
            "agent_profile_id": "assistant_default",
        },
    }


def test_generate_assistant_response_enforces_rate_limit(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(
        app_env="test",
        database_url="postgresql://app",
        response_rate_limit_max_requests=1,
        response_rate_limit_window_seconds=60,
    )

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module.ContinuityStore,
        "get_thread",
        lambda _self, thread_id: {
            "id": thread_id,
            "user_id": user_id,
            "title": "Thread",
            "agent_profile_id": "assistant_default",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    )
    monkeypatch.setattr(
        main_module,
        "generate_response",
        lambda *_args, **_kwargs: {
            "assistant": {
                "event_id": "assistant-event-123",
                "sequence_no": 5,
                "text": "Hello back.",
                "model_provider": "openai_responses",
                "model": "gpt-5-mini",
            },
            "trace": {
                "compile_trace_id": "compile-trace-123",
                "compile_trace_event_count": 11,
                "response_trace_id": "response-trace-123",
                "response_trace_event_count": 2,
            },
        },
    )
    main_module.response_rate_limiter.reset()

    first_response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello?",
        )
    )
    second_response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello again?",
        )
    )
    main_module.response_rate_limiter.reset()

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    retry_after = int(second_response.headers["Retry-After"])
    assert 1 <= retry_after <= 60
    assert json.loads(second_response.body) == {
        "detail": {
            "code": "response_rate_limit_exceeded",
            "message": "response generation rate limit exceeded; max 1 requests per 60 seconds",
            "retry_after_seconds": retry_after,
        }
    }


def test_admit_memory_returns_decision_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_admit_memory_candidate(store, *, user_id, candidate):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["candidate"] = candidate
        return AdmissionDecisionOutput(
            action="ADD",
            reason="source_backed_add",
            memory={
                "id": "memory-123",
                "user_id": str(user_id),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:00:00+00:00",
                "deleted_at": None,
            },
            revision={
                "id": "revision-123",
                "user_id": str(user_id),
                "memory_id": "memory-123",
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "oat milk"},
                "source_event_ids": ["event-1"],
                "candidate": {
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "source_event_ids": ["event-1"],
                    "delete_requested": False,
                },
                "created_at": "2026-03-11T09:00:00+00:00",
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "admit_memory_candidate", fake_admit_memory_candidate)

    response = main_module.admit_memory(
        main_module.AdmitMemoryRequest(
            user_id=user_id,
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            source_event_ids=[uuid4()],
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "decision": "ADD",
        "reason": "source_backed_add",
        "memory": {
            "id": "memory-123",
            "user_id": str(user_id),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-1"],
            "created_at": "2026-03-11T09:00:00+00:00",
            "updated_at": "2026-03-11T09:00:00+00:00",
            "deleted_at": None,
        },
        "revision": {
            "id": "revision-123",
            "user_id": str(user_id),
            "memory_id": "memory-123",
            "sequence_no": 1,
            "action": "ADD",
            "memory_key": "user.preference.coffee",
            "previous_value": None,
            "new_value": {"likes": "oat milk"},
            "source_event_ids": ["event-1"],
            "candidate": {
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "source_event_ids": ["event-1"],
                "delete_requested": False,
            },
            "created_at": "2026-03-11T09:00:00+00:00",
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["candidate"].memory_key == "user.preference.coffee"


def test_admit_memory_includes_open_loop_payload_when_created(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    def fake_admit_memory_candidate(_store, *, user_id, candidate):
        captured["user_id"] = user_id
        captured["candidate"] = candidate
        return AdmissionDecisionOutput(
            action="NOOP",
            reason="memory_unchanged",
            memory=None,
            revision=None,
            open_loop={
                "id": "loop-123",
                "memory_id": "memory-123",
                "title": "Confirm before reorder",
                "status": "open",
                "opened_at": "2026-03-23T10:00:00+00:00",
                "due_at": "2026-03-25T10:00:00+00:00",
                "resolved_at": None,
                "resolution_note": None,
                "created_at": "2026-03-23T10:00:00+00:00",
                "updated_at": "2026-03-23T10:00:00+00:00",
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "admit_memory_candidate", fake_admit_memory_candidate)

    response = main_module.admit_memory(
        main_module.AdmitMemoryRequest(
            user_id=user_id,
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            source_event_ids=[uuid4()],
            open_loop=main_module.AdmitMemoryOpenLoopRequest(
                title="Confirm before reorder",
                due_at="2026-03-25T10:00:00+00:00",
            ),
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["open_loop"] == {
        "id": "loop-123",
        "memory_id": "memory-123",
        "title": "Confirm before reorder",
        "status": "open",
        "opened_at": "2026-03-23T10:00:00+00:00",
        "due_at": "2026-03-25T10:00:00+00:00",
        "resolved_at": None,
        "resolution_note": None,
        "created_at": "2026-03-23T10:00:00+00:00",
        "updated_at": "2026-03-23T10:00:00+00:00",
    }
    assert captured["candidate"].open_loop is not None
    assert captured["candidate"].open_loop.title == "Confirm before reorder"


def test_admit_memory_returns_bad_request_when_source_validation_fails(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "admit_memory_candidate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryAdmissionValidationError("source_event_ids must all reference existing events owned by the user")
        ),
    )

    response = main_module.admit_memory(
        main_module.AdmitMemoryRequest(
            user_id=uuid4(),
            memory_key="user.preference.coffee",
            value={"likes": "black"},
            source_event_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_ids must all reference existing events owned by the user",
    }


def test_extract_explicit_preferences_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    source_event_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_extract_and_admit_explicit_preferences(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "candidates": [
                {
                    "memory_key": "user.preference.black_coffee",
                    "value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "delete_requested": False,
                    "pattern": "i_like",
                    "subject_text": "black coffee",
                }
            ],
            "admissions": [
                {
                    "decision": "ADD",
                    "reason": "source_backed_add",
                    "memory": {
                        "id": "memory-123",
                        "user_id": str(user_id),
                        "memory_key": "user.preference.black_coffee",
                        "value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "status": "active",
                        "source_event_ids": [str(source_event_id)],
                        "created_at": "2026-03-12T09:00:00+00:00",
                        "updated_at": "2026-03-12T09:00:00+00:00",
                        "deleted_at": None,
                    },
                    "revision": {
                        "id": "revision-123",
                        "user_id": str(user_id),
                        "memory_id": "memory-123",
                        "sequence_no": 1,
                        "action": "ADD",
                        "memory_key": "user.preference.black_coffee",
                        "previous_value": None,
                        "new_value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "candidate": {
                            "memory_key": "user.preference.black_coffee",
                            "value": {
                                "kind": "explicit_preference",
                                "preference": "like",
                                "text": "black coffee",
                            },
                            "source_event_ids": [str(source_event_id)],
                            "delete_requested": False,
                        },
                        "created_at": "2026-03-12T09:00:00+00:00",
                    },
                }
            ],
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 1,
                "admission_count": 1,
                "persisted_change_count": 1,
                "noop_count": 0,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_preferences",
        fake_extract_and_admit_explicit_preferences,
    )

    response = main_module.extract_explicit_preferences(
        main_module.ExtractExplicitPreferencesRequest(
            user_id=user_id,
            source_event_id=source_event_id,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "candidates": [
            {
                "memory_key": "user.preference.black_coffee",
                "value": {
                    "kind": "explicit_preference",
                    "preference": "like",
                    "text": "black coffee",
                },
                "source_event_ids": [str(source_event_id)],
                "delete_requested": False,
                "pattern": "i_like",
                "subject_text": "black coffee",
            }
        ],
        "admissions": [
            {
                "decision": "ADD",
                "reason": "source_backed_add",
                "memory": {
                    "id": "memory-123",
                    "user_id": str(user_id),
                    "memory_key": "user.preference.black_coffee",
                    "value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "status": "active",
                    "source_event_ids": [str(source_event_id)],
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:00:00+00:00",
                    "deleted_at": None,
                },
                "revision": {
                    "id": "revision-123",
                    "user_id": str(user_id),
                    "memory_id": "memory-123",
                    "sequence_no": 1,
                    "action": "ADD",
                    "memory_key": "user.preference.black_coffee",
                    "previous_value": None,
                    "new_value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "candidate": {
                        "memory_key": "user.preference.black_coffee",
                        "value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "delete_requested": False,
                    },
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
            }
        ],
        "summary": {
            "source_event_id": str(source_event_id),
            "source_event_kind": "message.user",
            "candidate_count": 1,
            "admission_count": 1,
            "persisted_change_count": 1,
            "noop_count": 0,
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].source_event_id == source_event_id


def test_extract_explicit_preferences_returns_bad_request_when_source_event_is_invalid(
    monkeypatch,
) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_preferences",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.ExplicitPreferenceExtractionValidationError(
                "source_event_id must reference an existing message.user event owned by the user"
            )
        ),
    )

    response = main_module.extract_explicit_preferences(
        main_module.ExtractExplicitPreferencesRequest(
            user_id=uuid4(),
            source_event_id=uuid4(),
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_id must reference an existing message.user event owned by the user",
    }


def test_extract_explicit_commitments_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    source_event_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_extract_and_admit_explicit_commitments(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "candidates": [
                {
                    "memory_key": "user.commitment.submit_tax_forms",
                    "value": {
                        "kind": "explicit_commitment",
                        "text": "submit tax forms",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "delete_requested": False,
                    "pattern": "remind_me_to",
                    "commitment_text": "submit tax forms",
                    "open_loop_title": "Remember to submit tax forms",
                }
            ],
            "admissions": [
                {
                    "decision": "ADD",
                    "reason": "source_backed_add",
                    "memory": {
                        "id": "memory-123",
                        "user_id": str(user_id),
                        "memory_key": "user.commitment.submit_tax_forms",
                        "value": {
                            "kind": "explicit_commitment",
                            "text": "submit tax forms",
                        },
                        "status": "active",
                        "source_event_ids": [str(source_event_id)],
                        "memory_type": "commitment",
                        "created_at": "2026-03-23T09:00:00+00:00",
                        "updated_at": "2026-03-23T09:00:00+00:00",
                        "deleted_at": None,
                    },
                    "revision": {
                        "id": "revision-123",
                        "user_id": str(user_id),
                        "memory_id": "memory-123",
                        "sequence_no": 1,
                        "action": "ADD",
                        "memory_key": "user.commitment.submit_tax_forms",
                        "previous_value": None,
                        "new_value": {
                            "kind": "explicit_commitment",
                            "text": "submit tax forms",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "candidate": {
                            "memory_key": "user.commitment.submit_tax_forms",
                            "value": {
                                "kind": "explicit_commitment",
                                "text": "submit tax forms",
                            },
                            "source_event_ids": [str(source_event_id)],
                            "delete_requested": False,
                            "memory_type": "commitment",
                        },
                        "created_at": "2026-03-23T09:00:00+00:00",
                    },
                    "open_loop": {
                        "decision": "CREATED",
                        "reason": "created_open_loop_for_memory",
                        "open_loop": {
                            "id": "loop-123",
                            "memory_id": "memory-123",
                            "title": "Remember to submit tax forms",
                            "status": "open",
                            "opened_at": "2026-03-23T09:00:00+00:00",
                            "due_at": None,
                            "resolved_at": None,
                            "resolution_note": None,
                            "created_at": "2026-03-23T09:00:00+00:00",
                            "updated_at": "2026-03-23T09:00:00+00:00",
                        },
                    },
                }
            ],
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 1,
                "admission_count": 1,
                "persisted_change_count": 1,
                "noop_count": 0,
                "open_loop_created_count": 1,
                "open_loop_noop_count": 0,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_commitments",
        fake_extract_and_admit_explicit_commitments,
    )

    response = main_module.extract_explicit_commitments(
        main_module.ExtractExplicitCommitmentsRequest(
            user_id=user_id,
            source_event_id=source_event_id,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "source_event_id": str(source_event_id),
        "source_event_kind": "message.user",
        "candidate_count": 1,
        "admission_count": 1,
        "persisted_change_count": 1,
        "noop_count": 0,
        "open_loop_created_count": 1,
        "open_loop_noop_count": 0,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].source_event_id == source_event_id


def test_extract_explicit_commitments_returns_bad_request_when_source_event_is_invalid(
    monkeypatch,
) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_commitments",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.ExplicitCommitmentExtractionValidationError(
                "source_event_id must reference an existing message.user event owned by the user"
            )
        ),
    )

    response = main_module.extract_explicit_commitments(
        main_module.ExtractExplicitCommitmentsRequest(
            user_id=uuid4(),
            source_event_id=uuid4(),
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_id must reference an existing message.user event owned by the user",
    }


def test_capture_explicit_signals_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    source_event_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_extract_and_admit_explicit_signals(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "preferences": {
                "candidates": [],
                "admissions": [],
                "summary": {
                    "source_event_id": str(source_event_id),
                    "source_event_kind": "message.user",
                    "candidate_count": 0,
                    "admission_count": 0,
                    "persisted_change_count": 0,
                    "noop_count": 0,
                },
            },
            "commitments": {
                "candidates": [
                    {
                        "memory_key": "user.commitment.submit_tax_forms",
                        "value": {
                            "kind": "explicit_commitment",
                            "text": "submit tax forms",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "delete_requested": False,
                        "pattern": "remind_me_to",
                        "commitment_text": "submit tax forms",
                        "open_loop_title": "Remember to submit tax forms",
                    }
                ],
                "admissions": [],
                "summary": {
                    "source_event_id": str(source_event_id),
                    "source_event_kind": "message.user",
                    "candidate_count": 1,
                    "admission_count": 0,
                    "persisted_change_count": 0,
                    "noop_count": 0,
                    "open_loop_created_count": 0,
                    "open_loop_noop_count": 0,
                },
            },
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 1,
                "admission_count": 0,
                "persisted_change_count": 0,
                "noop_count": 0,
                "open_loop_created_count": 0,
                "open_loop_noop_count": 0,
                "preference_candidate_count": 0,
                "preference_admission_count": 0,
                "commitment_candidate_count": 1,
                "commitment_admission_count": 0,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_signals",
        fake_extract_and_admit_explicit_signals,
    )

    response = main_module.capture_explicit_signals(
        main_module.CaptureExplicitSignalsRequest(
            user_id=user_id,
            source_event_id=source_event_id,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "source_event_id": str(source_event_id),
        "source_event_kind": "message.user",
        "candidate_count": 1,
        "admission_count": 0,
        "persisted_change_count": 0,
        "noop_count": 0,
        "open_loop_created_count": 0,
        "open_loop_noop_count": 0,
        "preference_candidate_count": 0,
        "preference_admission_count": 0,
        "commitment_candidate_count": 1,
        "commitment_admission_count": 0,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].source_event_id == source_event_id


def test_capture_explicit_signals_returns_bad_request_when_source_event_is_invalid(
    monkeypatch,
) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_signals",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.ExplicitSignalCaptureValidationError(
                "source_event_id must reference an existing message.user event owned by the user"
            )
        ),
    )

    response = main_module.capture_explicit_signals(
        main_module.CaptureExplicitSignalsRequest(
            user_id=uuid4(),
            source_event_id=uuid4(),
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_id must reference an existing message.user event owned by the user",
    }


def test_list_memories_returns_review_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_records(store, *, user_id, status, limit):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["status"] = status
        captured["limit"] = limit
        return {
            "items": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:02:00+00:00",
                    "deleted_at": None,
                }
            ],
            "summary": {
                "status": "active",
                "limit": 10,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["updated_at_desc", "created_at_desc", "id_desc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_memory_review_records", fake_list_memory_review_records)

    response = main_module.list_memories(user_id=user_id, status="active", limit=10)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "memory-123",
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:02:00+00:00",
                "deleted_at": None,
            }
        ],
        "summary": {
            "status": "active",
            "limit": 10,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": ["updated_at_desc", "created_at_desc", "id_desc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["status"] == "active"
    assert captured["limit"] == 10


def test_open_loop_routes_return_payload_and_errors(monkeypatch) -> None:
    user_id = uuid4()
    open_loop_id = uuid4()
    memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_open_loop_records(store, *, user_id, status, limit):
        captured["list_store_type"] = type(store).__name__
        captured["list_user_id"] = user_id
        captured["list_status"] = status
        captured["list_limit"] = limit
        return {
            "items": [
                {
                    "id": str(open_loop_id),
                    "memory_id": str(memory_id),
                    "title": "Follow up",
                    "status": "open",
                    "opened_at": "2026-03-23T09:00:00+00:00",
                    "due_at": None,
                    "resolved_at": None,
                    "resolution_note": None,
                    "created_at": "2026-03-23T09:00:00+00:00",
                    "updated_at": "2026-03-23T09:00:00+00:00",
                }
            ],
            "summary": {
                "status": "open",
                "limit": 10,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["opened_at_desc", "created_at_desc", "id_desc"],
            },
        }

    def fake_get_open_loop_record(_store, *, user_id, open_loop_id):
        captured["detail_user_id"] = user_id
        captured["detail_open_loop_id"] = open_loop_id
        return {
            "open_loop": {
                "id": str(open_loop_id),
                "memory_id": str(memory_id),
                "title": "Follow up",
                "status": "open",
                "opened_at": "2026-03-23T09:00:00+00:00",
                "due_at": None,
                "resolved_at": None,
                "resolution_note": None,
                "created_at": "2026-03-23T09:00:00+00:00",
                "updated_at": "2026-03-23T09:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_open_loop_records", fake_list_open_loop_records)
    monkeypatch.setattr(main_module, "get_open_loop_record", fake_get_open_loop_record)

    list_response = main_module.list_open_loops(user_id=user_id, status="open", limit=10)
    detail_response = main_module.get_open_loop(open_loop_id=open_loop_id, user_id=user_id)

    assert list_response.status_code == 200
    assert json.loads(list_response.body)["summary"]["status"] == "open"
    assert detail_response.status_code == 200
    assert json.loads(detail_response.body)["open_loop"]["id"] == str(open_loop_id)
    assert captured["list_status"] == "open"
    assert captured["list_limit"] == 10
    assert captured["detail_open_loop_id"] == open_loop_id

    monkeypatch.setattr(
        main_module,
        "get_open_loop_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OpenLoopNotFoundError("open loop hidden")),
    )
    not_found_response = main_module.get_open_loop(open_loop_id=open_loop_id, user_id=user_id)
    assert not_found_response.status_code == 404
    assert json.loads(not_found_response.body) == {"detail": "open loop hidden"}


def test_open_loop_mutation_routes_handle_create_and_status_validation(monkeypatch) -> None:
    user_id = uuid4()
    open_loop_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_open_loop_record(_store, *, user_id, open_loop):
        captured["create_user_id"] = user_id
        captured["create_open_loop"] = open_loop
        return {
            "open_loop": {
                "id": str(open_loop_id),
                "memory_id": None,
                "title": open_loop.title,
                "status": "open",
                "opened_at": "2026-03-23T09:00:00+00:00",
                "due_at": None,
                "resolved_at": None,
                "resolution_note": None,
                "created_at": "2026-03-23T09:00:00+00:00",
                "updated_at": "2026-03-23T09:00:00+00:00",
            }
        }

    def fake_update_open_loop_status_record(_store, *, user_id, open_loop_id, request):
        captured["status_user_id"] = user_id
        captured["status_open_loop_id"] = open_loop_id
        captured["status_request"] = request
        return {
            "open_loop": {
                "id": str(open_loop_id),
                "memory_id": None,
                "title": "Follow up",
                "status": "resolved",
                "opened_at": "2026-03-23T09:00:00+00:00",
                "due_at": None,
                "resolved_at": "2026-03-24T09:00:00+00:00",
                "resolution_note": "Resolved",
                "created_at": "2026-03-23T09:00:00+00:00",
                "updated_at": "2026-03-24T09:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_open_loop_record", fake_create_open_loop_record)
    monkeypatch.setattr(main_module, "update_open_loop_status_record", fake_update_open_loop_status_record)

    create_response = main_module.create_open_loop(
        main_module.CreateOpenLoopRequest(
            user_id=user_id,
            title="Follow up",
        )
    )
    status_response = main_module.update_open_loop_status(
        open_loop_id=open_loop_id,
        request=main_module.UpdateOpenLoopStatusRequest(
            user_id=user_id,
            status="resolved",
            resolution_note="Resolved",
        ),
    )

    assert create_response.status_code == 201
    assert json.loads(create_response.body)["open_loop"]["title"] == "Follow up"
    assert status_response.status_code == 200
    assert json.loads(status_response.body)["open_loop"]["status"] == "resolved"
    assert captured["status_request"].status == "resolved"

    monkeypatch.setattr(
        main_module,
        "update_open_loop_status_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OpenLoopValidationError("status invalid")),
    )
    bad_status_response = main_module.update_open_loop_status(
        open_loop_id=open_loop_id,
        request=main_module.UpdateOpenLoopStatusRequest(user_id=user_id, status="invalid"),
    )
    assert bad_status_response.status_code == 400
    assert json.loads(bad_status_response.body) == {"detail": "status invalid"}


def test_get_memory_returns_not_found_when_memory_is_inaccessible(monkeypatch) -> None:
    memory_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_memory_review_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.MemoryReviewNotFoundError(f"memory {memory_id} was not found")
        ),
    )

    response = main_module.get_memory(memory_id=memory_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"memory {memory_id} was not found",
    }


def test_list_memory_review_queue_returns_unlabeled_active_queue_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_queue_records(store, *, user_id, limit, priority_mode):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["limit"] = limit
        captured["priority_mode"] = priority_mode
        return {
            "items": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "is_high_risk": True,
                    "is_stale_truth": False,
                    "queue_priority_mode": "high_risk_first",
                    "priority_reason": "high_risk",
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:02:00+00:00",
                }
            ],
            "summary": {
                "memory_status": "active",
                "review_state": "unlabeled",
                "priority_mode": "high_risk_first",
                "available_priority_modes": [
                    "oldest_first",
                    "recent_first",
                    "high_risk_first",
                    "stale_truth_first",
                ],
                "limit": 7,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": [
                    "is_high_risk_desc",
                    "confidence_asc_nulls_first",
                    "updated_at_desc",
                    "created_at_desc",
                    "id_desc",
                ],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_memory_review_queue_records", fake_list_memory_review_queue_records)

    response = main_module.list_memory_review_queue(
        user_id=user_id,
        limit=7,
        priority_mode="high_risk_first",
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "memory-123",
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "is_high_risk": True,
                "is_stale_truth": False,
                "queue_priority_mode": "high_risk_first",
                "priority_reason": "high_risk",
                "created_at": "2026-03-12T09:00:00+00:00",
                "updated_at": "2026-03-12T09:02:00+00:00",
            }
        ],
        "summary": {
            "memory_status": "active",
            "review_state": "unlabeled",
            "priority_mode": "high_risk_first",
            "available_priority_modes": [
                "oldest_first",
                "recent_first",
                "high_risk_first",
                "stale_truth_first",
            ],
            "limit": 7,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": [
                "is_high_risk_desc",
                "confidence_asc_nulls_first",
                "updated_at_desc",
                "created_at_desc",
                "id_desc",
            ],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["limit"] == 7
    assert captured["priority_mode"] == "high_risk_first"


def test_get_memories_evaluation_summary_returns_aggregate_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_memory_evaluation_summary(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "summary": {
                "total_memory_count": 4,
                "active_memory_count": 3,
                "deleted_memory_count": 1,
                "labeled_memory_count": 2,
                "unlabeled_memory_count": 2,
                "total_label_row_count": 3,
                "label_row_counts_by_value": {
                    "correct": 1,
                    "incorrect": 0,
                    "outdated": 1,
                    "insufficient_evidence": 1,
                },
                "label_value_order": [
                    "correct",
                    "incorrect",
                    "outdated",
                    "insufficient_evidence",
                ],
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_memory_evaluation_summary", fake_get_memory_evaluation_summary)

    response = main_module.get_memories_evaluation_summary(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "summary": {
            "total_memory_count": 4,
            "active_memory_count": 3,
            "deleted_memory_count": 1,
            "labeled_memory_count": 2,
            "unlabeled_memory_count": 2,
            "total_label_row_count": 3,
            "label_row_counts_by_value": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 1,
                "insufficient_evidence": 1,
            },
            "label_value_order": [
                "correct",
                "incorrect",
                "outdated",
                "insufficient_evidence",
            ],
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_get_memories_quality_gate_returns_canonical_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_memory_quality_gate_summary(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "summary": {
                "status": "needs_review",
                "precision": 0.9,
                "precision_target": 0.8,
                "adjudicated_sample_count": 10,
                "minimum_adjudicated_sample": 10,
                "remaining_to_minimum_sample": 0,
                "unlabeled_memory_count": 1,
                "high_risk_memory_count": 1,
                "stale_truth_count": 0,
                "superseded_active_conflict_count": 0,
                "counts": {
                    "active_memory_count": 11,
                    "labeled_active_memory_count": 10,
                    "adjudicated_correct_count": 9,
                    "adjudicated_incorrect_count": 1,
                    "outdated_label_count": 0,
                    "insufficient_evidence_label_count": 0,
                },
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_memory_quality_gate_summary", fake_get_memory_quality_gate_summary)

    response = main_module.get_memories_quality_gate(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "summary": {
            "status": "needs_review",
            "precision": 0.9,
            "precision_target": 0.8,
            "adjudicated_sample_count": 10,
            "minimum_adjudicated_sample": 10,
            "remaining_to_minimum_sample": 0,
            "unlabeled_memory_count": 1,
            "high_risk_memory_count": 1,
            "stale_truth_count": 0,
            "superseded_active_conflict_count": 0,
            "counts": {
                "active_memory_count": 11,
                "labeled_active_memory_count": 10,
                "adjudicated_correct_count": 9,
                "adjudicated_incorrect_count": 1,
                "outdated_label_count": 0,
                "insufficient_evidence_label_count": 0,
            },
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_get_memories_hygiene_dashboard_returns_canonical_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_memory_hygiene_dashboard_summary(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "dashboard": {
                "posture": "watch",
                "reason": "Duplicate and contradiction pressure is visible.",
                "duplicate_group_count": 1,
                "duplicate_memory_count": 2,
                "stale_fact_count": 1,
                "unresolved_contradiction_count": 1,
                "weak_trust_count": 2,
                "review_queue_pressure": {
                    "posture": "watch",
                    "total_count": 2,
                    "stale_over_72h_count": 0,
                    "aging_24h_to_72h_count": 1,
                    "reason": "Backlog exists and should be drained before it becomes stale.",
                },
                "duplicate_groups": [
                    {
                        "group_key": "preference:{\"merchant\":\"Fixture\"}",
                        "memory_type": "preference",
                        "normalized_value": "{\"merchant\":\"Fixture\"}",
                        "count": 2,
                        "memory_ids": ["memory-1", "memory-2"],
                        "memory_keys": ["user.preference.primary", "user.preference.secondary"],
                        "latest_updated_at": "2026-03-18T10:05:00+00:00",
                    }
                ],
                "focus": [
                    {
                        "kind": "duplicates",
                        "posture": "watch",
                        "count": 2,
                        "reason": "Multiple active memories share the same normalized value.",
                        "action": "Review duplicate groups and keep one canonical fact per repeated value.",
                        "sample_ids": ["memory-1", "memory-2"],
                    }
                ],
                "sources": ["memories", "contradiction_cases", "trust_signals", "continuity_recall"],
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_memory_hygiene_dashboard_summary",
        fake_get_memory_hygiene_dashboard_summary,
    )

    response = main_module.get_memories_hygiene_dashboard(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "dashboard": {
            "posture": "watch",
            "reason": "Duplicate and contradiction pressure is visible.",
            "duplicate_group_count": 1,
            "duplicate_memory_count": 2,
            "stale_fact_count": 1,
            "unresolved_contradiction_count": 1,
            "weak_trust_count": 2,
            "review_queue_pressure": {
                "posture": "watch",
                "total_count": 2,
                "stale_over_72h_count": 0,
                "aging_24h_to_72h_count": 1,
                "reason": "Backlog exists and should be drained before it becomes stale.",
            },
            "duplicate_groups": [
                {
                    "group_key": "preference:{\"merchant\":\"Fixture\"}",
                    "memory_type": "preference",
                    "normalized_value": "{\"merchant\":\"Fixture\"}",
                    "count": 2,
                    "memory_ids": ["memory-1", "memory-2"],
                    "memory_keys": ["user.preference.primary", "user.preference.secondary"],
                    "latest_updated_at": "2026-03-18T10:05:00+00:00",
                }
            ],
            "focus": [
                {
                    "kind": "duplicates",
                    "posture": "watch",
                    "count": 2,
                    "reason": "Multiple active memories share the same normalized value.",
                    "action": "Review duplicate groups and keep one canonical fact per repeated value.",
                    "sample_ids": ["memory-1", "memory-2"],
                }
            ],
            "sources": ["memories", "contradiction_cases", "trust_signals", "continuity_recall"],
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_get_threads_health_dashboard_returns_canonical_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_thread_health_dashboard(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "dashboard": {
                "posture": "critical",
                "total_thread_count": 2,
                "recent_thread_count": 1,
                "stale_thread_count": 0,
                "risky_thread_count": 1,
                "watch_thread_count": 0,
                "thresholds": {
                    "recent_window_hours": 24.0,
                    "stale_window_hours": 72.0,
                    "risky_score_threshold": 2,
                },
                "recent_threads": [
                    {
                        "thread": {
                            "id": "thread-1",
                            "title": "Recent thread",
                            "agent_profile_id": "assistant_default",
                            "created_at": "2026-03-18T09:00:00+00:00",
                            "updated_at": "2026-03-18T10:00:00+00:00",
                        },
                        "health_posture": "healthy",
                        "activity_posture": "recent",
                        "risk_posture": "normal",
                        "risk_score": 0,
                        "last_activity_at": "2026-03-18T10:00:00+00:00",
                        "last_conversation_at": "2026-03-18T10:00:00+00:00",
                        "hours_since_last_activity": 2.0,
                        "conversation_event_count": 3,
                        "operational_event_count": 1,
                        "active_session_count": 1,
                        "open_loop_count": 0,
                        "stale_open_loop_count": 0,
                        "unresolved_contradiction_count": 0,
                        "weak_trust_signal_count": 0,
                        "reasons": [
                            "No active contradiction, stale open-loop, or weak-trust pressure is currently visible."
                        ],
                        "recommended_action": "No immediate intervention required.",
                    }
                ],
                "stale_threads": [],
                "risky_threads": [
                    {
                        "thread": {
                            "id": "thread-2",
                            "title": "Risky thread",
                            "agent_profile_id": "assistant_default",
                            "created_at": "2026-03-18T09:00:00+00:00",
                            "updated_at": "2026-03-18T08:00:00+00:00",
                        },
                        "health_posture": "critical",
                        "activity_posture": "current",
                        "risk_posture": "risky",
                        "risk_score": 3,
                        "last_activity_at": "2026-03-18T08:00:00+00:00",
                        "last_conversation_at": "2026-03-18T08:00:00+00:00",
                        "hours_since_last_activity": 26.0,
                        "conversation_event_count": 2,
                        "operational_event_count": 0,
                        "active_session_count": 0,
                        "open_loop_count": 1,
                        "stale_open_loop_count": 1,
                        "unresolved_contradiction_count": 1,
                        "weak_trust_signal_count": 1,
                        "reasons": ["1 unresolved contradiction case(s).", "1 stale open-loop item(s)."],
                        "recommended_action": "Resolve contradiction cases before trusting this thread for recall or briefing.",
                    }
                ],
                "items": [],
                "sources": [
                    "threads",
                    "thread_sessions",
                    "thread_events",
                    "continuity_recall",
                    "contradiction_cases",
                    "trust_signals",
                ],
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_thread_health_dashboard",
        fake_get_thread_health_dashboard,
    )

    response = main_module.get_threads_health_dashboard(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "dashboard": {
            "posture": "critical",
            "total_thread_count": 2,
            "recent_thread_count": 1,
            "stale_thread_count": 0,
            "risky_thread_count": 1,
            "watch_thread_count": 0,
            "thresholds": {
                "recent_window_hours": 24.0,
                "stale_window_hours": 72.0,
                "risky_score_threshold": 2,
            },
            "recent_threads": [
                {
                    "thread": {
                        "id": "thread-1",
                        "title": "Recent thread",
                        "agent_profile_id": "assistant_default",
                        "created_at": "2026-03-18T09:00:00+00:00",
                        "updated_at": "2026-03-18T10:00:00+00:00",
                    },
                    "health_posture": "healthy",
                    "activity_posture": "recent",
                    "risk_posture": "normal",
                    "risk_score": 0,
                    "last_activity_at": "2026-03-18T10:00:00+00:00",
                    "last_conversation_at": "2026-03-18T10:00:00+00:00",
                    "hours_since_last_activity": 2.0,
                    "conversation_event_count": 3,
                    "operational_event_count": 1,
                    "active_session_count": 1,
                    "open_loop_count": 0,
                    "stale_open_loop_count": 0,
                    "unresolved_contradiction_count": 0,
                    "weak_trust_signal_count": 0,
                    "reasons": [
                        "No active contradiction, stale open-loop, or weak-trust pressure is currently visible."
                    ],
                    "recommended_action": "No immediate intervention required.",
                }
            ],
            "stale_threads": [],
            "risky_threads": [
                {
                    "thread": {
                        "id": "thread-2",
                        "title": "Risky thread",
                        "agent_profile_id": "assistant_default",
                        "created_at": "2026-03-18T09:00:00+00:00",
                        "updated_at": "2026-03-18T08:00:00+00:00",
                    },
                    "health_posture": "critical",
                    "activity_posture": "current",
                    "risk_posture": "risky",
                    "risk_score": 3,
                    "last_activity_at": "2026-03-18T08:00:00+00:00",
                    "last_conversation_at": "2026-03-18T08:00:00+00:00",
                    "hours_since_last_activity": 26.0,
                    "conversation_event_count": 2,
                    "operational_event_count": 0,
                    "active_session_count": 0,
                    "open_loop_count": 1,
                    "stale_open_loop_count": 1,
                    "unresolved_contradiction_count": 1,
                    "weak_trust_signal_count": 1,
                    "reasons": ["1 unresolved contradiction case(s).", "1 stale open-loop item(s)."],
                    "recommended_action": "Resolve contradiction cases before trusting this thread for recall or briefing.",
                }
            ],
            "items": [],
            "sources": [
                "threads",
                "thread_sessions",
                "thread_events",
                "continuity_recall",
                "contradiction_cases",
                "trust_signals",
            ],
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_list_memory_revisions_returns_review_payload(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_revision_review_records(store, *, user_id, memory_id, limit):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        captured["limit"] = limit
        return {
            "items": [
                {
                    "id": "revision-123",
                    "memory_id": str(memory_id),
                    "sequence_no": 1,
                    "action": "ADD",
                    "memory_key": "user.preference.coffee",
                    "previous_value": None,
                    "new_value": {"likes": "black"},
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                }
            ],
            "summary": {
                "memory_id": str(memory_id),
                "limit": 5,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["sequence_no_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_revision_review_records",
        fake_list_memory_revision_review_records,
    )

    response = main_module.list_memory_revisions(memory_id=memory_id, user_id=user_id, limit=5)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "revision-123",
                "memory_id": str(memory_id),
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "black"},
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
            }
        ],
        "summary": {
            "memory_id": str(memory_id),
            "limit": 5,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": ["sequence_no_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["memory_id"] == memory_id
    assert captured["limit"] == 5


def test_create_memory_review_label_returns_created_payload(monkeypatch) -> None:
    memory_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_memory_review_label_record(store, *, user_id, memory_id, label, note):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        captured["label"] = label
        captured["note"] = note
        return {
            "label": {
                "id": "label-123",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "correct",
                "note": "Backed by the latest source.",
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 1,
                "counts_by_label": {
                    "correct": 1,
                    "incorrect": 0,
                    "outdated": 0,
                    "insufficient_evidence": 0,
                },
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_memory_review_label_record",
        fake_create_memory_review_label_record,
    )

    response = main_module.create_memory_review_label(
        memory_id,
        main_module.CreateMemoryReviewLabelRequest(
            user_id=user_id,
            label="correct",
            note="Backed by the latest source.",
        ),
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "label": {
            "id": "label-123",
            "memory_id": str(memory_id),
            "reviewer_user_id": str(user_id),
            "label": "correct",
            "note": "Backed by the latest source.",
            "created_at": "2026-03-12T09:00:00+00:00",
        },
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 1,
            "counts_by_label": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 0,
                "insufficient_evidence": 0,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["memory_id"] == memory_id
    assert captured["label"] == "correct"
    assert captured["note"] == "Backed by the latest source."


def test_create_memory_review_label_returns_not_found_for_inaccessible_memory(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_memory_review_label_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryReviewNotFoundError("memory missing")),
    )

    response = main_module.create_memory_review_label(
        uuid4(),
        main_module.CreateMemoryReviewLabelRequest(user_id=uuid4(), label="incorrect"),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "memory missing"}


def test_list_memory_review_labels_returns_deterministic_items_and_summary(monkeypatch) -> None:
    memory_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_label_records(store, *, user_id, memory_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        return {
            "items": [
                {
                    "id": "label-123",
                    "memory_id": str(memory_id),
                    "reviewer_user_id": str(user_id),
                    "label": "incorrect",
                    "note": "Conflicts with the latest event.",
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
                {
                    "id": "label-124",
                    "memory_id": str(memory_id),
                    "reviewer_user_id": str(user_id),
                    "label": "outdated",
                    "note": None,
                    "created_at": "2026-03-12T09:01:00+00:00",
                },
            ],
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 2,
                "counts_by_label": {
                    "correct": 0,
                    "incorrect": 1,
                    "outdated": 1,
                    "insufficient_evidence": 0,
                },
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_review_label_records",
        fake_list_memory_review_label_records,
    )

    response = main_module.list_memory_review_labels(memory_id=memory_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "label-123",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "incorrect",
                "note": "Conflicts with the latest event.",
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            {
                "id": "label-124",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "outdated",
                "note": None,
                "created_at": "2026-03-12T09:01:00+00:00",
            },
        ],
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 2,
            "counts_by_label": {
                "correct": 0,
                "incorrect": 1,
                "outdated": 1,
                "insufficient_evidence": 0,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["memory_id"] == memory_id


def test_list_memory_review_labels_returns_not_found_for_inaccessible_memory(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_review_label_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryReviewNotFoundError("memory hidden")),
    )

    response = main_module.list_memory_review_labels(uuid4(), uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "memory hidden"}


def test_create_embedding_config_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_embedding_config_record(store, *, user_id, config):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["config"] = config
        return {
            "embedding_config": {
                "id": "config-123",
                "provider": "openai",
                "model": "text-embedding-3-large",
                "version": "2026-03-12",
                "dimensions": 3,
                "status": "active",
                "metadata": {"task": "memory_retrieval"},
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_embedding_config_record", fake_create_embedding_config_record)

    response = main_module.create_embedding_config(
        main_module.CreateEmbeddingConfigRequest(
            user_id=user_id,
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3,
            status="active",
            metadata={"task": "memory_retrieval"},
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "embedding_config": {
            "id": "config-123",
            "provider": "openai",
            "model": "text-embedding-3-large",
            "version": "2026-03-12",
            "dimensions": 3,
            "status": "active",
            "metadata": {"task": "memory_retrieval"},
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["config"].provider == "openai"


def test_create_embedding_config_returns_bad_request_for_validation_failure(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_embedding_config_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EmbeddingConfigValidationError(
                "embedding config already exists for provider/model/version under the user scope: "
                "openai/text-embedding-3-large/2026-03-12"
            )
        ),
    )

    response = main_module.create_embedding_config(
        main_module.CreateEmbeddingConfigRequest(
            user_id=uuid4(),
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3,
            status="active",
            metadata={"task": "memory_retrieval"},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": (
            "embedding config already exists for provider/model/version under the user scope: "
            "openai/text-embedding-3-large/2026-03-12"
        )
    }


def test_upsert_memory_embedding_routes_success_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_upsert_memory_embedding_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "embedding": {
                "id": "embedding-123",
                "memory_id": str(memory_id),
                "embedding_config_id": str(config_id),
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-12T10:00:00+00:00",
                "updated_at": "2026-03-12T10:00:00+00:00",
            },
            "write_mode": "created",
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "upsert_memory_embedding_record", fake_upsert_memory_embedding_record)

    response = main_module.upsert_memory_embedding(
        main_module.UpsertMemoryEmbeddingRequest(
            user_id=user_id,
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body)["write_mode"] == "created"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].memory_id == memory_id

    monkeypatch.setattr(
        main_module,
        "upsert_memory_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryEmbeddingValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.upsert_memory_embedding(
        main_module.UpsertMemoryEmbeddingRequest(
            user_id=user_id,
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }


def test_retrieve_semantic_memories_routes_success_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_retrieve_semantic_memory_records(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "items": [
                {
                    "memory_id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "source_event_ids": ["event-123"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                    "updated_at": "2026-03-12T10:00:00+00:00",
                    "score": 0.99,
                }
            ],
            "summary": {
                "embedding_config_id": str(config_id),
                "limit": 5,
                "returned_count": 1,
                "similarity_metric": "cosine_similarity",
                "order": ["score_desc", "created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_semantic_memory_records",
        fake_retrieve_semantic_memory_records,
    )

    response = main_module.retrieve_semantic_memories(
        main_module.RetrieveSemanticMemoriesRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "embedding_config_id": str(config_id),
        "limit": 5,
        "returned_count": 1,
        "similarity_metric": "cosine_similarity",
        "order": ["score_desc", "created_at_asc", "id_asc"],
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].embedding_config_id == config_id
    assert captured["request"].query_vector == (0.1, 0.2, 0.3)

    monkeypatch.setattr(
        main_module,
        "retrieve_semantic_memory_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SemanticMemoryRetrievalValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.retrieve_semantic_memories(
        main_module.RetrieveSemanticMemoriesRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }


def test_memory_embedding_read_routes_return_payload_and_not_found(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    embedding_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_embedding_records",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "id": str(embedding_id),
                    "memory_id": str(memory_id),
                    "embedding_config_id": "config-123",
                    "dimensions": 3,
                    "vector": [0.1, 0.2, 0.3],
                    "created_at": "2026-03-12T10:00:00+00:00",
                    "updated_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        },
    )
    monkeypatch.setattr(
        main_module,
        "get_memory_embedding_record",
        lambda *_args, **_kwargs: {
            "embedding": {
                "id": str(embedding_id),
                "memory_id": str(memory_id),
                "embedding_config_id": "config-123",
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-12T10:00:00+00:00",
                "updated_at": "2026-03-12T10:00:00+00:00",
            }
        },
    )

    list_response = main_module.list_memory_embeddings(memory_id=memory_id, user_id=user_id)
    detail_response = main_module.get_memory_embedding(memory_embedding_id=embedding_id, user_id=user_id)

    assert list_response.status_code == 200
    assert json.loads(list_response.body)["summary"]["memory_id"] == str(memory_id)
    assert detail_response.status_code == 200
    assert json.loads(detail_response.body)["embedding"]["id"] == str(embedding_id)

    monkeypatch.setattr(
        main_module,
        "get_memory_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryEmbeddingNotFoundError(f"memory embedding {embedding_id} was not found")
        ),
    )

    not_found_response = main_module.get_memory_embedding(
        memory_embedding_id=embedding_id,
        user_id=user_id,
    )

    assert not_found_response.status_code == 404
    assert json.loads(not_found_response.body) == {
        "detail": f"memory embedding {embedding_id} was not found"
    }


def test_task_artifact_chunk_embedding_routes_success_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    chunk_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_upsert_task_artifact_chunk_embedding_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "embedding": {
                "id": "artifact-embedding-123",
                "task_artifact_id": "artifact-123",
                "task_artifact_chunk_id": str(chunk_id),
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": str(config_id),
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-14T12:00:00+00:00",
                "updated_at": "2026-03-14T12:00:00+00:00",
            },
            "write_mode": "created",
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "upsert_task_artifact_chunk_embedding_record",
        fake_upsert_task_artifact_chunk_embedding_record,
    )

    response = main_module.upsert_task_artifact_chunk_embedding(
        main_module.UpsertTaskArtifactChunkEmbeddingRequest(
            user_id=user_id,
            task_artifact_chunk_id=chunk_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body)["write_mode"] == "created"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].task_artifact_chunk_id == chunk_id

    monkeypatch.setattr(
        main_module,
        "upsert_task_artifact_chunk_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskArtifactChunkEmbeddingValidationError(
                "task_artifact_chunk_id must reference an existing task artifact chunk owned by the user"
            )
        ),
    )

    error_response = main_module.upsert_task_artifact_chunk_embedding(
        main_module.UpsertTaskArtifactChunkEmbeddingRequest(
            user_id=user_id,
            task_artifact_chunk_id=chunk_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "task_artifact_chunk_id must reference an existing task artifact chunk owned by the user"
    }


def test_task_artifact_chunk_embedding_read_routes_return_payload_and_not_found(monkeypatch) -> None:
    user_id = uuid4()
    artifact_id = uuid4()
    chunk_id = uuid4()
    embedding_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_chunk_embedding_records_for_artifact",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "total_count": 0,
                "order": ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"],
                "scope": {
                    "kind": "artifact",
                    "task_artifact_id": str(artifact_id),
                },
            },
        },
    )
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_chunk_embedding_records_for_chunk",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "total_count": 0,
                "order": ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"],
                "scope": {
                    "kind": "chunk",
                    "task_artifact_id": str(artifact_id),
                    "task_artifact_chunk_id": str(chunk_id),
                },
            },
        },
    )
    monkeypatch.setattr(
        main_module,
        "get_task_artifact_chunk_embedding_record",
        lambda *_args, **_kwargs: {
            "embedding": {
                "id": str(embedding_id),
                "task_artifact_id": str(artifact_id),
                "task_artifact_chunk_id": str(chunk_id),
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": "config-123",
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-14T12:00:00+00:00",
                "updated_at": "2026-03-14T12:00:00+00:00",
            }
        },
    )

    artifact_response = main_module.list_task_artifact_chunk_embeddings_for_artifact(
        task_artifact_id=artifact_id,
        user_id=user_id,
    )
    chunk_response = main_module.list_task_artifact_chunk_embeddings(
        task_artifact_chunk_id=chunk_id,
        user_id=user_id,
    )
    detail_response = main_module.get_task_artifact_chunk_embedding(
        task_artifact_chunk_embedding_id=embedding_id,
        user_id=user_id,
    )

    assert artifact_response.status_code == 200
    assert json.loads(artifact_response.body)["summary"]["scope"]["task_artifact_id"] == str(
        artifact_id
    )
    assert chunk_response.status_code == 200
    assert json.loads(chunk_response.body)["summary"]["scope"]["task_artifact_chunk_id"] == str(
        chunk_id
    )
    assert detail_response.status_code == 200
    assert json.loads(detail_response.body)["embedding"]["id"] == str(embedding_id)

    monkeypatch.setattr(
        main_module,
        "list_task_artifact_chunk_embedding_records_for_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskArtifactNotFoundError(f"task artifact {artifact_id} was not found")
        ),
    )
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_chunk_embedding_records_for_chunk",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskArtifactChunkEmbeddingNotFoundError(
                f"task artifact chunk {chunk_id} was not found"
            )
        ),
    )
    monkeypatch.setattr(
        main_module,
        "get_task_artifact_chunk_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskArtifactChunkEmbeddingNotFoundError(
                f"task artifact chunk embedding {embedding_id} was not found"
            )
        ),
    )

    missing_artifact_response = main_module.list_task_artifact_chunk_embeddings_for_artifact(
        task_artifact_id=artifact_id,
        user_id=user_id,
    )
    missing_chunk_response = main_module.list_task_artifact_chunk_embeddings(
        task_artifact_chunk_id=chunk_id,
        user_id=user_id,
    )
    missing_detail_response = main_module.get_task_artifact_chunk_embedding(
        task_artifact_chunk_embedding_id=embedding_id,
        user_id=user_id,
    )

    assert missing_artifact_response.status_code == 404
    assert json.loads(missing_artifact_response.body) == {
        "detail": f"task artifact {artifact_id} was not found"
    }
    assert missing_chunk_response.status_code == 404
    assert json.loads(missing_chunk_response.body) == {
        "detail": f"task artifact chunk {chunk_id} was not found"
    }
    assert missing_detail_response.status_code == 404
    assert json.loads(missing_detail_response.body) == {
        "detail": f"task artifact chunk embedding {embedding_id} was not found"
    }


def test_create_entity_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    first_memory_id = uuid4()
    second_memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_entity_record(store, *, user_id, entity):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity"] = entity
        return {
            "entity": {
                "id": "entity-123",
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_entity_record", fake_create_entity_record)

    response = main_module.create_entity(
        main_module.CreateEntityRequest(
            user_id=user_id,
            entity_type="project",
            name="AliceBot",
            source_memory_ids=[first_memory_id, second_memory_id],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "entity": {
            "id": "entity-123",
            "entity_type": "project",
            "name": "AliceBot",
            "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity"].entity_type == "project"
    assert captured["entity"].name == "AliceBot"


def test_create_entity_returns_bad_request_when_source_memory_validation_fails(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_entity_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityValidationError("source_memory_ids must all reference existing memories owned by the user")
        ),
    )

    response = main_module.create_entity(
        main_module.CreateEntityRequest(
            user_id=uuid4(),
            entity_type="person",
            name="Alex",
            source_memory_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_memory_ids must all reference existing memories owned by the user",
    }


def test_create_entity_edge_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    from_entity_id = uuid4()
    to_entity_id = uuid4()
    source_memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_entity_edge_record(store, *, user_id, edge):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["edge"] = edge
        return {
            "edge": {
                "id": "edge-123",
                "from_entity_id": str(from_entity_id),
                "to_entity_id": str(to_entity_id),
                "relationship_type": "works_on",
                "valid_from": "2026-03-12T10:00:00+00:00",
                "valid_to": None,
                "source_memory_ids": [str(source_memory_id)],
                "created_at": "2026-03-12T10:01:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_entity_edge_record", fake_create_entity_edge_record)

    response = main_module.create_entity_edge(
        main_module.CreateEntityEdgeRequest(
            user_id=user_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relationship_type="works_on",
            valid_from="2026-03-12T10:00:00+00:00",
            source_memory_ids=[source_memory_id],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "edge": {
            "id": "edge-123",
            "from_entity_id": str(from_entity_id),
            "to_entity_id": str(to_entity_id),
            "relationship_type": "works_on",
            "valid_from": "2026-03-12T10:00:00+00:00",
            "valid_to": None,
            "source_memory_ids": [str(source_memory_id)],
            "created_at": "2026-03-12T10:01:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["edge"].from_entity_id == from_entity_id
    assert captured["edge"].to_entity_id == to_entity_id


def test_create_entity_edge_returns_bad_request_for_validation_failure(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_entity_edge_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityEdgeValidationError("valid_to must be greater than or equal to valid_from")
        ),
    )

    response = main_module.create_entity_edge(
        main_module.CreateEntityEdgeRequest(
            user_id=uuid4(),
            from_entity_id=uuid4(),
            to_entity_id=uuid4(),
            relationship_type="works_on",
            valid_from="2026-03-12T11:00:00+00:00",
            valid_to="2026-03-12T10:00:00+00:00",
            source_memory_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "valid_to must be greater than or equal to valid_from",
    }


def test_list_entities_returns_deterministic_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_entity_records(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "items": [
                {
                    "id": "entity-123",
                    "entity_type": "project",
                    "name": "AliceBot",
                    "source_memory_ids": ["memory-1"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_entity_records", fake_list_entity_records)

    response = main_module.list_entities(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "entity-123",
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        ],
        "summary": {
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_list_entity_edges_returns_deterministic_payload(monkeypatch) -> None:
    user_id = uuid4()
    entity_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_entity_edge_records(store, *, user_id, entity_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity_id"] = entity_id
        return {
            "items": [
                {
                    "id": "edge-123",
                    "from_entity_id": str(entity_id),
                    "to_entity_id": "entity-456",
                    "relationship_type": "works_on",
                    "valid_from": None,
                    "valid_to": None,
                    "source_memory_ids": ["memory-1"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "entity_id": str(entity_id),
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_entity_edge_records", fake_list_entity_edge_records)

    response = main_module.list_entity_edges(entity_id=entity_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "edge-123",
                "from_entity_id": str(entity_id),
                "to_entity_id": "entity-456",
                "relationship_type": "works_on",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        ],
        "summary": {
            "entity_id": str(entity_id),
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity_id"] == entity_id


def test_list_entity_edges_returns_not_found_for_inaccessible_entity(monkeypatch) -> None:
    entity_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_entity_edge_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityNotFoundError(f"entity {entity_id} was not found")
        ),
    )

    response = main_module.list_entity_edges(entity_id=entity_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"entity {entity_id} was not found",
    }


def test_get_entity_returns_detail_payload(monkeypatch) -> None:
    user_id = uuid4()
    entity_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_entity_record(store, *, user_id, entity_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity_id"] = entity_id
        return {
            "entity": {
                "id": str(entity_id),
                "entity_type": "person",
                "name": "Alex",
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_entity_record", fake_get_entity_record)

    response = main_module.get_entity(entity_id=entity_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "entity": {
            "id": str(entity_id),
            "entity_type": "person",
            "name": "Alex",
            "source_memory_ids": ["memory-1"],
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity_id"] == entity_id


def test_get_entity_returns_not_found_for_inaccessible_entity(monkeypatch) -> None:
    entity_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_entity_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityNotFoundError(f"entity {entity_id} was not found")
        ),
    )

    response = main_module.get_entity(entity_id=entity_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"entity {entity_id} was not found",
    }
