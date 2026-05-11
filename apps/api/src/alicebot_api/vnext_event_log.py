from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import cast
from uuid import uuid4

from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import EventStore, JsonObject


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def stable_json_dumps(payload: object) -> str:
    return json.dumps(json_safe(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def integrity_hash_for_event(event: JsonObject) -> str:
    hashable = {key: value for key, value in event.items() if key != "integrity_hash"}
    return hashlib.sha256(stable_json_dumps(hashable).encode("utf-8")).hexdigest()


def build_event_log_record(
    *,
    event_type: str,
    actor_type: str,
    payload: JsonObject | None = None,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    occurred_at: str | None = None,
) -> JsonObject:
    event: JsonObject = {
        "id": str(uuid4()),
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "target_type": target_type,
        "target_id": target_id,
        "occurred_at": occurred_at or _utc_now_iso(),
        "payload_json": json_safe(payload or {}),
        "trace_id": trace_id,
        "run_id": run_id,
    }
    event = cast(JsonObject, json_safe(event))
    event["integrity_hash"] = integrity_hash_for_event(event)
    return event


def append_event(
    event_store: EventStore,
    *,
    event_type: str,
    actor_type: str,
    payload: JsonObject | None = None,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    occurred_at: str | None = None,
) -> JsonObject:
    event = build_event_log_record(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        trace_id=trace_id,
        run_id=run_id,
        occurred_at=occurred_at,
    )
    return event_store.append_event(event)


__all__ = [
    "append_event",
    "build_event_log_record",
    "integrity_hash_for_event",
    "stable_json_dumps",
]
