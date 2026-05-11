from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import scripts.run_archive_maintenance as maintenance


class _CursorStub:
    def __init__(self, calls: list[tuple[str, tuple[object, ...]]]) -> None:
        self._calls = calls

    def __enter__(self) -> "_CursorStub":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type
        del exc
        del traceback

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        self._calls.append((query, params))


class _ConnectionStub:
    def __init__(self, calls: list[tuple[str, tuple[object, ...]]]) -> None:
        self._calls = calls

    def cursor(self) -> _CursorStub:
        return _CursorStub(self._calls)


class _UserStoreStub:
    def __init__(self, calls: list[tuple[str, tuple[object, ...]]]) -> None:
        self.conn = _ConnectionStub(calls)


def _write_go_summary(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "artifact_version": "phase4_rc_summary.v1",
                "artifact_path": str(path),
                "final_decision": "GO",
                "summary_exit_code": 0,
                "failing_steps": [],
                "ordered_steps": ["phase4_acceptance", "phase4_validation_matrix"],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_archive_index(path: Path, summary_path: Path, latest_path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "archive_dir": str(path.parent),
                "artifact_version": "phase4_rc_archive_index.v1",
                "entries": [
                    {
                        "archive_artifact_path": str(summary_path),
                        "command_mode": "default",
                        "created_at": "2026-03-29T05:49:50Z",
                        "failing_steps": [],
                        "final_decision": "GO",
                        "summary_exit_code": 0,
                    }
                ],
                "latest_summary_path": str(latest_path),
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_verify_archive_checksums_detects_manifest_drift(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True)

    archived_summary_path = archive_dir / "20260329T054950Z_phase4_rc_summary.json"
    latest_summary_path = tmp_path / "phase4_rc_summary.json"
    index_path = archive_dir / "index.json"
    manifest_path = tmp_path / "archive_checksum_manifest.json"

    _write_go_summary(archived_summary_path)
    _write_go_summary(latest_summary_path)
    _write_archive_index(index_path, archived_summary_path, latest_summary_path)

    first = maintenance._verify_archive_checksums(  # type: ignore[attr-defined]
        index_path=index_path,
        checksum_manifest_path=manifest_path,
    )
    assert first["status"] == "pass"
    assert first["errors"] == []

    archived_summary_path.write_text(
        json.dumps(
            {
                "artifact_version": "phase4_rc_summary.v1",
                "artifact_path": str(archived_summary_path),
                "final_decision": "GO",
                "summary_exit_code": 0,
                "failing_steps": [],
                "ordered_steps": ["phase4_acceptance", "phase4_validation_matrix"],
                "revision": "unexpected-change",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    second = maintenance._verify_archive_checksums(  # type: ignore[attr-defined]
        index_path=index_path,
        checksum_manifest_path=manifest_path,
    )
    assert second["status"] == "fail"
    assert second["details"]["manifest_mismatch_count"] == 1
    assert any("archive checksum mismatch" in message for message in second["errors"])


def test_verify_archive_checksums_skips_when_archive_index_is_absent(tmp_path: Path) -> None:
    result = maintenance._verify_archive_checksums(  # type: ignore[attr-defined]
        index_path=tmp_path / "missing" / "index.json",
        checksum_manifest_path=tmp_path / "archive_checksum_manifest.json",
    )

    assert result["status"] == "skipped"
    assert result["errors"] == []
    assert result["details"]["verified_file_count"] == 0
    assert result["details"]["reason"] == "archive index not present; checksum verification skipped"


def test_collect_archive_paths_rejects_outside_allowed_root(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True)
    index_path = archive_dir / "index.json"
    in_scope_summary = archive_dir / "in_scope_summary.json"
    out_of_scope_summary = tmp_path.parent / "outside_summary.json"

    _write_go_summary(in_scope_summary)
    _write_archive_index(index_path, in_scope_summary, out_of_scope_summary)

    paths, errors = maintenance._collect_archive_paths(index_path)  # type: ignore[attr-defined]
    assert any("outside allowed archive root" in message for message in errors)
    assert out_of_scope_summary.resolve() not in paths
    assert in_scope_summary.resolve() in paths


def test_run_job_sanitizes_unhandled_exception_message() -> None:
    def _failing_operation() -> dict[str, object]:
        raise RuntimeError("db password leaked at /private/tmp/secret.txt\nsecond line")

    result = maintenance._run_job(  # type: ignore[attr-defined]
        job_key="sanitization_test",
        operation=_failing_operation,
    )

    assert result.status == "fail"
    assert result.errors == ["unhandled_exception:RuntimeError"]


def test_ensure_user_uses_idempotent_insert() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    maintenance._ensure_user(  # type: ignore[attr-defined]
        _UserStoreStub(calls),  # type: ignore[arg-type]
        user_id=user_id,
        email="maintenance-bot@example.invalid",
        display_name="Maintenance Bot",
    )

    assert len(calls) == 1
    query, params = calls[0]
    assert "ON CONFLICT (id) DO NOTHING" in query
    assert params == (user_id, "maintenance-bot@example.invalid", "Maintenance Bot")


def test_main_commits_maintenance_user_before_stateful_jobs(monkeypatch, tmp_path: Path) -> None:
    events: list[str] = []
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    class _StatefulConnectionContext:
        def __enter__(self) -> object:
            events.append("stateful_connection_opened")
            return object()

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            del exc_type
            del exc
            del traceback
            events.append("stateful_connection_closed")

    monkeypatch.setattr(
        maintenance,
        "_parse_args",
        lambda: SimpleNamespace(
            database_url="postgresql://example",
            user_id=str(user_id),
            schedule="weekly",
            report_path=str(tmp_path / "maintenance_status_latest.json"),
            history_dir=str(tmp_path / "history"),
            archive_index_path=str(tmp_path / "missing" / "index.json"),
            checksum_manifest_path=str(tmp_path / "archive_checksum_manifest.json"),
            stale_markers_path=str(tmp_path / "stale_fact_markers_latest.json"),
            benchmark_report_path=str(tmp_path / "phase9_eval_latest.json"),
            include_benchmark=True,
            user_email="maintenance-bot@example.invalid",
            display_name="Maintenance Bot",
        ),
    )
    monkeypatch.setattr(
        maintenance,
        "_ensure_user_committed",
        lambda **kwargs: events.append("user_bootstrap_committed"),
    )
    monkeypatch.setattr(
        maintenance,
        "user_connection",
        lambda *_args, **_kwargs: _StatefulConnectionContext(),
    )
    monkeypatch.setattr(maintenance, "ContinuityStore", lambda _conn: object())
    monkeypatch.setattr(
        maintenance,
        "_verify_archive_checksums",
        lambda **_kwargs: {"status": "skipped", "details": {}, "errors": []},
    )
    monkeypatch.setattr(
        maintenance,
        "_mark_stale_facts",
        lambda **_kwargs: {"status": "pass", "details": {}},
    )
    monkeypatch.setattr(
        maintenance,
        "_reembed_missing_segments",
        lambda **_kwargs: {"status": "pass", "details": {}},
    )
    monkeypatch.setattr(
        maintenance,
        "_recompute_pattern_candidates",
        lambda **_kwargs: {"status": "pass", "details": {}},
    )
    monkeypatch.setattr(
        maintenance,
        "_regenerate_benchmarks",
        lambda **_kwargs: {"status": "pass", "details": {"benchmark_status": "pass"}},
    )

    assert maintenance.main() == 0
    assert events.index("user_bootstrap_committed") < events.index("stateful_connection_opened")


class _StaleStoreStub:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def count_memories(self, *, status: str | None = None) -> int:
        if status == "active":
            return len(self._rows)
        return len(self._rows)

    def list_review_memories(self, *, status: str | None = None, limit: int | None = None) -> list[dict[str, object]]:
        del status
        del limit
        return list(self._rows)


def test_collect_stale_fact_markers_is_deterministic() -> None:
    stale_id = uuid4()
    contested_id = uuid4()
    fresh_id = uuid4()

    store = _StaleStoreStub(
        [
            {
                "id": stale_id,
                "confirmation_status": "confirmed",
                "valid_to": datetime(2026, 4, 5, 12, 0, tzinfo=UTC),
            },
            {
                "id": contested_id,
                "confirmation_status": "contested",
                "valid_to": None,
            },
            {
                "id": fresh_id,
                "confirmation_status": "confirmed",
                "valid_to": None,
            },
        ]
    )

    stale_ids, contested_count, valid_to_count = maintenance._collect_stale_fact_markers(  # type: ignore[attr-defined]
        store
    )

    assert stale_ids == sorted([str(stale_id), str(contested_id)])
    assert contested_count == 1
    assert valid_to_count == 1


class _EmbeddingStoreStub:
    def __init__(self) -> None:
        self.config_id = UUID("22222222-2222-4222-8222-222222222222")
        self.artifact_id = UUID("33333333-3333-4333-8333-333333333333")
        self.first_chunk_id = UUID("44444444-4444-4444-8444-444444444444")
        self.second_chunk_id = UUID("55555555-5555-4555-8555-555555555555")
        self._created_embeddings: list[dict[str, object]] = []

    def list_embedding_configs(self) -> list[dict[str, object]]:
        return [
            {
                "id": self.config_id,
                "status": "active",
                "dimensions": 8,
            }
        ]

    def list_task_artifacts(self) -> list[dict[str, object]]:
        return [
            {
                "id": self.artifact_id,
                "ingestion_status": "ingested",
            }
        ]

    def list_task_artifact_chunks(self, task_artifact_id: UUID) -> list[dict[str, object]]:
        assert task_artifact_id == self.artifact_id
        return [
            {
                "id": self.first_chunk_id,
                "sequence_no": 1,
                "created_at": datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                "text": "alpha",
            },
            {
                "id": self.second_chunk_id,
                "sequence_no": 2,
                "created_at": datetime(2026, 4, 1, 9, 1, tzinfo=UTC),
                "text": "beta",
            },
        ]

    def list_task_artifact_chunk_embeddings_for_artifact(self, task_artifact_id: UUID) -> list[dict[str, object]]:
        assert task_artifact_id == self.artifact_id
        rows = [
            {
                "task_artifact_chunk_id": self.first_chunk_id,
                "embedding_config_id": self.config_id,
            }
        ]
        rows.extend(
            {
                "task_artifact_chunk_id": embedding["task_artifact_chunk_id"],
                "embedding_config_id": embedding["embedding_config_id"],
            }
            for embedding in self._created_embeddings
        )
        return rows

    def get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
    ) -> dict[str, object] | None:
        for embedding in self._created_embeddings:
            if (
                embedding["task_artifact_chunk_id"] == task_artifact_chunk_id
                and embedding["embedding_config_id"] == embedding_config_id
            ):
                return embedding
        return None

    def create_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> dict[str, object]:
        record = {
            "id": uuid4(),
            "task_artifact_chunk_id": task_artifact_chunk_id,
            "embedding_config_id": embedding_config_id,
            "dimensions": dimensions,
            "vector": vector,
        }
        self._created_embeddings.append(record)
        return record


def test_reembed_missing_segments_backfills_only_uncovered_chunks() -> None:
    store = _EmbeddingStoreStub()

    first = maintenance._reembed_missing_segments(store=store)  # type: ignore[attr-defined]
    assert first["status"] == "pass"
    assert first["details"]["missing_segment_count"] == 1
    assert first["details"]["reembedded_segment_count"] == 1
    assert len(store._created_embeddings) == 1

    second = maintenance._reembed_missing_segments(store=store)  # type: ignore[attr-defined]
    assert second["status"] == "pass"
    assert second["details"]["missing_segment_count"] == 0
    assert second["details"]["reembedded_segment_count"] == 0
    assert len(store._created_embeddings) == 1
