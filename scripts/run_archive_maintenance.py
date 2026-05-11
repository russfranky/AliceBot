#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Literal
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
_VENV_REEXEC_ENV = "ALICEBOT_ARCHIVE_MAINTENANCE_REEXEC"


def _maybe_reexec_into_repo_venv() -> None:
    if os.getenv(_VENV_REEXEC_ENV) == "1":
        return

    venv_python = (REPO_ROOT / ".venv" / "bin" / "python").resolve()
    if not venv_python.exists():
        return

    current_python = Path(sys.executable).expanduser().resolve()
    if current_python == venv_python:
        return

    os.environ[_VENV_REEXEC_ENV] = "1"
    os.execv(
        str(venv_python),
        [
            str(venv_python),
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
    )


_maybe_reexec_into_repo_venv()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.db import user_connection
from alicebot_api.retrieval_evaluation import run_phase9_evaluation, write_phase9_evaluation_report
from alicebot_api.store import ContinuityStore
from alicebot_api.trusted_fact_promotions import sync_trusted_fact_promotions

import scripts.verify_phase4_rc_archive as verify_rc_archive


DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
DEFAULT_AUTH_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_REPORT_PATH = REPO_ROOT / "artifacts" / "ops" / "maintenance_status_latest.json"
DEFAULT_HISTORY_DIR = REPO_ROOT / "artifacts" / "ops" / "history"
DEFAULT_ARCHIVE_INDEX_PATH = REPO_ROOT / "artifacts" / "release" / "archive" / "index.json"
DEFAULT_CHECKSUM_MANIFEST_PATH = REPO_ROOT / "artifacts" / "ops" / "archive_checksum_manifest.json"
DEFAULT_STALE_MARKERS_PATH = REPO_ROOT / "artifacts" / "ops" / "stale_fact_markers_latest.json"
DEFAULT_PHASE9_REPORT_PATH = REPO_ROOT / "eval" / "reports" / "phase9_eval_latest.json"
DEFAULT_USER_EMAIL = "maintenance-bot@example.invalid"
DEFAULT_USER_DISPLAY_NAME = "Maintenance Bot"
_MAX_SANITIZED_REPORT_MESSAGE_CHARS = 200
ENSURE_MAINTENANCE_USER_SQL = """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """

JOB_STATUS = Literal["pass", "warn", "fail", "skipped"]


@dataclass(frozen=True, slots=True)
class MaintenanceJobResult:
    job_key: str
    status: JOB_STATUS
    started_at: str
    completed_at: str
    duration_seconds: float
    details: dict[str, object]
    warnings: list[str]
    errors: list[str]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso8601_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _repo_relative(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _resolve_path(path_value: str | Path) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (REPO_ROOT / candidate).resolve()


def _path_within_root(*, path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _allowed_archive_root(index_path: Path) -> Path:
    resolved_index = index_path.expanduser().resolve()
    parent = resolved_index.parent
    # `.../archive/index.json` should allow paths under `.../`.
    return parent.parent if parent.parent != parent else parent


def _sanitize_report_message(message: object, *, fallback: str) -> str:
    if not isinstance(message, str):
        return fallback
    normalized = re.sub(r"\s+", " ", message).strip()
    if normalized == "":
        return fallback
    normalized = re.sub(r"(?:(?:[A-Za-z]:)?[/\\\\][^\s]+)", "[path]", normalized)
    if len(normalized) > _MAX_SANITIZED_REPORT_MESSAGE_CHARS:
        normalized = normalized[:_MAX_SANITIZED_REPORT_MESSAGE_CHARS]
    return normalized


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 64), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _collect_archive_paths(index_path: Path) -> tuple[set[Path], list[str]]:
    paths: set[Path] = {index_path}
    errors: list[str] = []
    allowed_root = _allowed_archive_root(index_path)

    if not index_path.exists():
        return paths, [f"archive index missing: {_repo_relative(index_path)}"]

    try:
        index_payload = _load_json_object(index_path)
    except Exception as exc:  # pragma: no cover - defensive IO guard
        return paths, [f"failed to parse archive index: {exc}"]

    latest_summary = index_payload.get("latest_summary_path")
    if isinstance(latest_summary, str) and latest_summary.strip():
        latest_summary_path = _resolve_path(latest_summary)
        if _path_within_root(path=latest_summary_path, root=allowed_root):
            paths.add(latest_summary_path)
        else:
            errors.append("archive index latest_summary_path points outside allowed archive root")
    else:
        errors.append("archive index latest_summary_path is missing or invalid")

    entries = index_payload.get("entries")
    if not isinstance(entries, list):
        errors.append("archive index entries must be a JSON array")
        return paths, errors

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{idx}] must be a JSON object")
            continue
        archive_artifact_path = entry.get("archive_artifact_path")
        if not isinstance(archive_artifact_path, str) or not archive_artifact_path.strip():
            errors.append(f"entries[{idx}].archive_artifact_path is missing or invalid")
            continue
        archive_artifact = _resolve_path(archive_artifact_path)
        if not _path_within_root(path=archive_artifact, root=allowed_root):
            errors.append(f"entries[{idx}].archive_artifact_path points outside allowed archive root")
            continue
        paths.add(archive_artifact)

    return paths, errors


def _deterministic_embedding_vector(*, text: str, dimensions: int) -> list[float]:
    if dimensions <= 0:
        raise ValueError("dimensions must be greater than zero")

    seed = text.encode("utf-8")
    if not seed:
        seed = b"\x00"

    values: list[float] = []
    nonce = 0
    while len(values) < dimensions:
        hasher = hashlib.sha256()
        hasher.update(seed)
        hasher.update(nonce.to_bytes(4, byteorder="big", signed=False))
        digest = hasher.digest()
        nonce += 1
        for byte_value in digest:
            normalized = (float(byte_value) / 127.5) - 1.0
            values.append(normalized)
            if len(values) == dimensions:
                break

    magnitude = sum(value * value for value in values) ** 0.5
    if magnitude == 0.0:
        # Deterministic fallback to avoid storing zero-magnitude vectors.
        values[0] = 1.0
        magnitude = 1.0

    return [value / magnitude for value in values]


def _run_job(
    *,
    job_key: str,
    operation,
) -> MaintenanceJobResult:
    started = _utc_now()
    started_monotonic = time.monotonic()
    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, object] = {}
    status: JOB_STATUS = "pass"

    try:
        job_payload = operation()
    except Exception as exc:  # pragma: no cover - defensive boundary
        status = "fail"
        errors.append(f"unhandled_exception:{exc.__class__.__name__}")
        job_payload = {}

    if isinstance(job_payload, dict):
        details = dict(job_payload.get("details", {})) if isinstance(job_payload.get("details"), dict) else {}
        payload_warnings = job_payload.get("warnings")
        if isinstance(payload_warnings, list):
            warnings = [
                _sanitize_report_message(item, fallback="maintenance_job_warning")
                for item in payload_warnings
            ]
        payload_errors = job_payload.get("errors")
        if isinstance(payload_errors, list):
            errors.extend(
                _sanitize_report_message(item, fallback="maintenance_job_error")
                for item in payload_errors
            )
        payload_status = job_payload.get("status")
        if payload_status in {"pass", "warn", "fail", "skipped"}:
            status = payload_status

    if errors:
        status = "fail"
    elif status == "pass" and warnings:
        status = "warn"

    completed = _utc_now()
    duration_seconds = round(time.monotonic() - started_monotonic, 6)
    return MaintenanceJobResult(
        job_key=job_key,
        status=status,
        started_at=_iso8601_utc(started),
        completed_at=_iso8601_utc(completed),
        duration_seconds=duration_seconds,
        details=details,
        warnings=warnings,
        errors=errors,
    )


def _verify_archive_checksums(
    *,
    index_path: Path,
    checksum_manifest_path: Path,
) -> dict[str, object]:
    if not index_path.exists():
        return {
            "status": "skipped",
            "details": {
                "verified_file_count": 0,
                "previous_manifest_file_count": 0,
                "manifest_mismatch_count": 0,
                "checksum_manifest_path": _repo_relative(checksum_manifest_path),
                "archive_index_path": _repo_relative(index_path),
                "reason": "archive index not present; checksum verification skipped",
            },
            "errors": [],
        }

    errors = verify_rc_archive.verify_archive_index(index_path=index_path)
    archive_paths, collection_errors = _collect_archive_paths(index_path)
    errors.extend(collection_errors)

    checksums: dict[str, str] = {}
    for archive_path in sorted(archive_paths):
        if not archive_path.exists():
            errors.append(f"archive file missing: {_repo_relative(archive_path)}")
            continue
        checksums[_repo_relative(archive_path)] = _sha256_for_file(archive_path)

    manifest_mismatch_count = 0
    previous_count = 0
    if checksum_manifest_path.exists():
        try:
            previous_manifest = _load_json_object(checksum_manifest_path)
            previous_checksums = previous_manifest.get("checksums")
            if isinstance(previous_checksums, dict):
                previous_count = len(previous_checksums)
                for relative_path, expected_checksum in sorted(previous_checksums.items()):
                    if not isinstance(relative_path, str) or not isinstance(expected_checksum, str):
                        continue
                    actual_checksum = checksums.get(relative_path)
                    if actual_checksum is None:
                        errors.append(
                            "archive checksum manifest references missing file in current index: "
                            f"{relative_path}"
                        )
                        manifest_mismatch_count += 1
                        continue
                    if actual_checksum != expected_checksum:
                        errors.append(
                            "archive checksum mismatch for "
                            f"{relative_path}: manifest={expected_checksum} current={actual_checksum}"
                        )
                        manifest_mismatch_count += 1
            else:
                errors.append("existing archive checksum manifest is invalid")
        except Exception as exc:  # pragma: no cover - defensive IO guard
            errors.append(f"failed to read checksum manifest: {exc}")

    if not errors:
        checksum_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        checksum_manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "archive_checksum_manifest.v1",
                    "generated_at": _iso8601_utc(_utc_now()),
                    "index_path": _repo_relative(index_path),
                    "entry_count": len(checksums),
                    "checksums": checksums,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    details = {
        "verified_file_count": len(checksums),
        "previous_manifest_file_count": previous_count,
        "manifest_mismatch_count": manifest_mismatch_count,
        "checksum_manifest_path": _repo_relative(checksum_manifest_path),
        "archive_index_path": _repo_relative(index_path),
    }
    return {
        "status": "pass" if not errors else "fail",
        "details": details,
        "errors": errors,
    }


def _collect_stale_fact_markers(store: ContinuityStore) -> tuple[list[str], int, int]:
    active_count = store.count_memories(status="active")
    if active_count == 0:
        return [], 0, 0

    active_memories = store.list_review_memories(status="active", limit=active_count)
    stale_ids: list[str] = []
    contested_count = 0
    valid_to_count = 0

    for memory in active_memories:
        is_contested = memory.get("confirmation_status") == "contested"
        has_valid_to = memory.get("valid_to") is not None
        if is_contested:
            contested_count += 1
        if has_valid_to:
            valid_to_count += 1
        if is_contested or has_valid_to:
            stale_ids.append(str(memory["id"]))

    return sorted(stale_ids), contested_count, valid_to_count


def _mark_stale_facts(
    *,
    store: ContinuityStore,
    stale_markers_path: Path,
) -> dict[str, object]:
    stale_ids, contested_count, valid_to_count = _collect_stale_fact_markers(store)
    stale_markers_path.parent.mkdir(parents=True, exist_ok=True)
    stale_markers_path.write_text(
        json.dumps(
            {
                "schema_version": "stale_fact_markers.v1",
                "generated_at": _iso8601_utc(_utc_now()),
                "stale_fact_count": len(stale_ids),
                "contested_count": contested_count,
                "valid_to_count": valid_to_count,
                "stale_fact_ids": stale_ids,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    warnings: list[str] = []
    if stale_ids:
        warnings.append(
            "stale facts detected; deterministic marker file updated for review queue triage"
        )

    return {
        "status": "warn" if warnings else "pass",
        "details": {
            "stale_fact_count": len(stale_ids),
            "contested_count": contested_count,
            "valid_to_count": valid_to_count,
            "stale_markers_path": _repo_relative(stale_markers_path),
        },
        "warnings": warnings,
    }


def _reembed_missing_segments(
    *,
    store: ContinuityStore,
) -> dict[str, object]:
    configs = store.list_embedding_configs()
    if not configs:
        return {
            "status": "warn",
            "details": {
                "artifact_count": 0,
                "chunk_count": 0,
                "missing_segment_count": 0,
                "reembedded_segment_count": 0,
                "embedding_config_id": None,
            },
            "warnings": ["no embedding configs exist; re-embedding skipped"],
        }

    target_config = next((config for config in configs if config["status"] == "active"), configs[0])
    target_config_id = target_config["id"]
    target_dimensions = int(target_config["dimensions"])

    artifacts = [
        artifact
        for artifact in store.list_task_artifacts()
        if artifact["ingestion_status"] == "ingested"
    ]

    total_chunks = 0
    missing_chunks = 0
    reembedded_chunks = 0

    for artifact in artifacts:
        artifact_id = artifact["id"]
        chunks = store.list_task_artifact_chunks(artifact_id)
        total_chunks += len(chunks)

        embeddings = store.list_task_artifact_chunk_embeddings_for_artifact(artifact_id)
        embedded_chunk_ids = {
            embedding["task_artifact_chunk_id"]
            for embedding in embeddings
            if embedding["embedding_config_id"] == target_config_id
        }

        ordered_chunks = sorted(
            chunks,
            key=lambda chunk: (chunk["sequence_no"], chunk["created_at"], chunk["id"]),
        )

        for chunk in ordered_chunks:
            if chunk["id"] in embedded_chunk_ids:
                continue

            missing_chunks += 1
            existing = store.get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
                task_artifact_chunk_id=chunk["id"],
                embedding_config_id=target_config_id,
            )
            if existing is not None:
                continue

            vector = _deterministic_embedding_vector(
                text=str(chunk["text"]),
                dimensions=target_dimensions,
            )
            store.create_task_artifact_chunk_embedding(
                task_artifact_chunk_id=chunk["id"],
                embedding_config_id=target_config_id,
                dimensions=target_dimensions,
                vector=vector,
            )
            reembedded_chunks += 1

    return {
        "status": "pass",
        "details": {
            "artifact_count": len(artifacts),
            "chunk_count": total_chunks,
            "missing_segment_count": missing_chunks,
            "reembedded_segment_count": reembedded_chunks,
            "embedding_config_id": str(target_config_id),
            "embedding_dimensions": target_dimensions,
            "embedding_source": "deterministic_hash_vector",
        },
    }


def _recompute_pattern_candidates(
    *,
    store: ContinuityStore,
    user_id: UUID,
) -> dict[str, object]:
    sync_trusted_fact_promotions(store, user_id=user_id)
    pattern_count = store.count_fact_patterns()
    playbook_count = store.count_fact_playbooks()

    return {
        "status": "pass",
        "details": {
            "pattern_candidate_count": pattern_count,
            "playbook_count": playbook_count,
        },
    }


def _regenerate_benchmarks(
    *,
    store: ContinuityStore,
    user_id: UUID,
    include_benchmark: bool,
    benchmark_report_path: Path,
) -> dict[str, object]:
    if not include_benchmark:
        return {
            "status": "skipped",
            "details": {
                "benchmark_status": "skipped",
                "benchmark_report_path": _repo_relative(benchmark_report_path),
                "reason": "benchmark regeneration is scheduled weekly or via explicit opt-in",
            },
        }

    report = run_phase9_evaluation(store, user_id=user_id)
    output_path = write_phase9_evaluation_report(
        report=report,
        report_path=benchmark_report_path,
    )

    summary = report.get("summary", {})
    benchmark_status = summary.get("status", "unknown")
    warnings: list[str] = []
    status: JOB_STATUS = "pass"
    if benchmark_status != "pass":
        warnings.append(f"benchmark summary status is {benchmark_status}")
        status = "warn"

    return {
        "status": status,
        "details": {
            "benchmark_status": benchmark_status,
            "benchmark_report_path": _repo_relative(output_path),
            "benchmark_summary": summary,
        },
        "warnings": warnings,
    }


def _ensure_user(store: ContinuityStore, *, user_id: UUID, email: str, display_name: str) -> None:
    with store.conn.cursor() as cur:
        cur.execute(ENSURE_MAINTENANCE_USER_SQL, (user_id, email, display_name))


def _ensure_user_committed(
    *,
    database_url: str,
    user_id: UUID,
    email: str,
    display_name: str,
) -> None:
    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        _ensure_user(
            store,
            user_id=user_id,
            email=email,
            display_name=display_name,
        )


def _serialize_job(job: MaintenanceJobResult) -> dict[str, object]:
    return {
        "job_key": job.job_key,
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "duration_seconds": job.duration_seconds,
        "details": job.details,
        "warnings": job.warnings,
        "errors": job.errors,
    }


def _write_maintenance_report(
    *,
    report_path: Path,
    history_dir: Path,
    schedule: str,
    run_started_at: str,
    run_completed_at: str,
    jobs: list[MaintenanceJobResult],
) -> tuple[Path, Path, dict[str, object]]:
    failures = [job for job in jobs if job.status == "fail"]
    warnings = [job for job in jobs if job.status == "warn"]

    if failures:
        overall_status: JOB_STATUS = "fail"
    elif warnings:
        overall_status = "warn"
    else:
        overall_status = "pass"

    summary = {
        "status": overall_status,
        "schedule": schedule,
        "run_started_at": run_started_at,
        "run_completed_at": run_completed_at,
        "job_count": len(jobs),
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }

    payload = {
        "schema_version": "archive_maintenance_report.v1",
        "generated_at": run_completed_at,
        "summary": summary,
        "jobs": [_serialize_job(job) for job in jobs],
        "alerts": [
            {
                "severity": "error",
                "job_key": job.job_key,
                "message": message,
            }
            for job in failures
            for message in (job.errors or ["job failed without error detail"])
        ]
        + [
            {
                "severity": "warning",
                "job_key": job.job_key,
                "message": message,
            }
            for job in warnings
            for message in (job.warnings or ["job reported warning"])
        ],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = run_completed_at.replace(":", "").replace("-", "").replace(".", "")
    history_path = history_dir / f"maintenance_status_{timestamp_slug}.json"
    history_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return report_path, history_path, summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic archive maintenance jobs (checksum verification, stale fact surfacing, "
            "segment re-embedding, pattern recompute, and benchmark regeneration)."
        )
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL used for maintenance jobs that require continuity state.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_AUTH_USER_ID),
        help="User ID used for maintenance state reads/writes.",
    )
    parser.add_argument(
        "--schedule",
        choices=("nightly", "weekly", "manual"),
        default="manual",
        help="Schedule slot metadata for ops status reporting.",
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Path for the latest maintenance report JSON output.",
    )
    parser.add_argument(
        "--history-dir",
        default=str(DEFAULT_HISTORY_DIR),
        help="Directory for timestamped maintenance report history files.",
    )
    parser.add_argument(
        "--archive-index-path",
        default=str(DEFAULT_ARCHIVE_INDEX_PATH),
        help="Path to the archive index file used for integrity verification.",
    )
    parser.add_argument(
        "--checksum-manifest-path",
        default=str(DEFAULT_CHECKSUM_MANIFEST_PATH),
        help="Path to the archive checksum baseline manifest.",
    )
    parser.add_argument(
        "--stale-markers-path",
        default=str(DEFAULT_STALE_MARKERS_PATH),
        help="Path to write deterministic stale fact markers.",
    )
    parser.add_argument(
        "--benchmark-report-path",
        default=str(DEFAULT_PHASE9_REPORT_PATH),
        help="Path for regenerated benchmark output.",
    )
    parser.add_argument(
        "--include-benchmark",
        action="store_true",
        help="Run benchmark regeneration during this maintenance invocation.",
    )
    parser.add_argument(
        "--user-email",
        default=DEFAULT_USER_EMAIL,
        help="Email for auto-created maintenance user when --user-id does not exist.",
    )
    parser.add_argument(
        "--display-name",
        default=DEFAULT_USER_DISPLAY_NAME,
        help="Display name for auto-created maintenance user when --user-id does not exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    user_id = UUID(str(args.user_id))

    report_path = _resolve_path(str(args.report_path))
    history_dir = _resolve_path(str(args.history_dir))
    archive_index_path = _resolve_path(str(args.archive_index_path))
    checksum_manifest_path = _resolve_path(str(args.checksum_manifest_path))
    stale_markers_path = _resolve_path(str(args.stale_markers_path))
    benchmark_report_path = _resolve_path(str(args.benchmark_report_path))

    run_started = _iso8601_utc(_utc_now())
    jobs: list[MaintenanceJobResult] = []

    _ensure_user_committed(
        database_url=str(args.database_url),
        user_id=user_id,
        email=str(args.user_email),
        display_name=str(args.display_name),
    )

    jobs.append(
        _run_job(
            job_key="checksum_verification",
            operation=lambda: _verify_archive_checksums(
                index_path=archive_index_path,
                checksum_manifest_path=checksum_manifest_path,
            ),
        )
    )

    with user_connection(str(args.database_url), user_id) as conn:
        store = ContinuityStore(conn)

        jobs.append(
            _run_job(
                job_key="stale_fact_marking",
                operation=lambda: _mark_stale_facts(
                    store=store,
                    stale_markers_path=stale_markers_path,
                ),
            )
        )
        jobs.append(
            _run_job(
                job_key="reembed_missing_segments",
                operation=lambda: _reembed_missing_segments(store=store),
            )
        )
        jobs.append(
            _run_job(
                job_key="pattern_candidate_recompute",
                operation=lambda: _recompute_pattern_candidates(store=store, user_id=user_id),
            )
        )
        jobs.append(
            _run_job(
                job_key="benchmark_regeneration",
                operation=lambda: _regenerate_benchmarks(
                    store=store,
                    user_id=user_id,
                    include_benchmark=bool(args.include_benchmark),
                    benchmark_report_path=benchmark_report_path,
                ),
            )
        )

    run_completed = _iso8601_utc(_utc_now())
    latest_report_path, history_report_path, summary = _write_maintenance_report(
        report_path=report_path,
        history_dir=history_dir,
        schedule=str(args.schedule),
        run_started_at=run_started,
        run_completed_at=run_completed,
        jobs=jobs,
    )

    output = {
        "status": summary["status"],
        "schedule": summary["schedule"],
        "failure_count": summary["failure_count"],
        "warning_count": summary["warning_count"],
        "latest_report_path": _repo_relative(latest_report_path),
        "history_report_path": _repo_relative(history_report_path),
    }
    print(json.dumps(output, indent=2, sort_keys=True))

    if summary["status"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
