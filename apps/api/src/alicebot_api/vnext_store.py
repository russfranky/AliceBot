from __future__ import annotations

from typing import Any, cast

import psycopg
from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_event_log import build_event_log_record
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject


JsonList = list[object]
VNextRow = dict[str, object]


EVENT_LOG_COLUMNS = """
                  id,
                  user_id,
                  event_type,
                  actor_type,
                  actor_id,
                  target_type,
                  target_id,
                  occurred_at,
                  payload_json,
                  trace_id,
                  run_id,
                  integrity_hash
                """

SOURCE_COLUMNS = """
                  id,
                  user_id,
                  source_type,
                  title,
                  author,
                  uri,
                  raw_path,
                  content_hash,
                  captured_at,
                  source_created_at,
                  source_modified_at,
                  connector_name,
                  external_id,
                  domain,
                  sensitivity,
                  metadata_json,
                  deleted_at
                """

SOURCE_CHUNK_COLUMNS = """
                  id,
                  user_id,
                  source_id,
                  chunk_index,
                  text,
                  token_count,
                  metadata_json,
                  created_at
                """

MEMORY_COLUMNS = """
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  title,
                  canonical_text,
                  summary,
                  domain,
                  sensitivity,
                  first_seen_at,
                  last_seen_at,
                  last_reviewed_at,
                  metadata_json,
                  created_at,
                  updated_at,
                  deleted_at
                """

REVISION_COLUMNS = """
                  id,
                  user_id,
                  memory_id,
                  sequence_no,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate,
                  revision_number,
                  revision_type,
                  text_before,
                  text_after,
                  reason,
                  actor_type,
                  actor_id,
                  metadata_json,
                  created_at
                """

PROVENANCE_COLUMNS = """
                  id,
                  user_id,
                  target_type,
                  target_id,
                  source_id,
                  source_chunk_id,
                  quote,
                  evidence_role,
                  confidence,
                  created_at
                """

GRAPH_EDGE_COLUMNS = """
                  id,
                  user_id,
                  from_type,
                  from_id,
                  to_type,
                  to_id,
                  edge_type,
                  confidence,
                  explanation,
                  created_by,
                  created_at,
                  valid_from,
                  valid_to,
                  metadata_json
                """

PROJECT_COLUMNS = """
                  id,
                  user_id,
                  name,
                  slug,
                  status,
                  description,
                  current_state,
                  domain,
                  sensitivity,
                  created_at,
                  updated_at,
                  metadata_json
                """

PERSON_COLUMNS = """
                  id,
                  user_id,
                  name,
                  aliases_json,
                  relationship_type,
                  organization,
                  sensitivity,
                  notes,
                  created_at,
                  updated_at,
                  metadata_json
                """

BELIEF_COLUMNS = """
                  id,
                  user_id,
                  memory_id,
                  claim,
                  status,
                  confidence,
                  first_seen_at,
                  last_reinforced_at,
                  last_challenged_at,
                  superseded_by,
                  metadata_json
                """

OPEN_LOOP_COLUMNS = """
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at,
                  description,
                  priority,
                  project_id,
                  person_id,
                  source_id,
                  closed_at,
                  domain,
                  sensitivity,
                  metadata_json
                """

ARTIFACT_COLUMNS = """
                  id,
                  user_id,
                  artifact_type,
                  title,
                  content_markdown,
                  status,
                  domain,
                  sensitivity,
                  generated_by,
                  prompt_hash,
                  model_info_json,
                  created_at,
                  reviewed_at,
                  promoted_at,
                  metadata_json
                """

TASK_COLUMNS = """
                  id,
                  user_id,
                  title,
                  task_type,
                  instructions,
                  status,
                  requested_by,
                  scope_json,
                  allowed_sources_json,
                  domain,
                  sensitivity,
                  write_policy,
                  scheduled_for,
                  started_at,
                  completed_at,
                  failed_at,
                  error_message,
                  output_artifact_id,
                  created_at,
                  updated_at,
                  metadata_json
                """

BRAIN_CHARTER_COLUMNS = """
                  id,
                  user_id,
                  content_markdown,
                  owner_json,
                  memory_philosophy_json,
                  life_domains_json,
                  active_projects_json,
                  communication_style_json,
                  priorities_json,
                  autonomous_rules_json,
                  quality_standard_json,
                  sensitivity,
                  created_at,
                  updated_at
                """

AGENT_IDENTITY_COLUMNS = """
                  id,
                  user_id,
                  agent_id,
                  agent_type,
                  permission_profile,
                  display_name,
                  project_scope_json,
                  metadata_json,
                  created_at,
                  updated_at
                """

SCHEDULER_WORKFLOW_COLUMNS = """
                  id,
                  user_id,
                  workflow_type,
                  enabled,
                  paused,
                  schedule_json,
                  timezone,
                  next_run_at,
                  last_run_id,
                  last_run_at,
                  last_result,
                  last_error,
                  created_at,
                  updated_at,
                  metadata_json
                """

SCHEDULER_RUN_COLUMNS = """
                  id,
                  user_id,
                  workflow_id,
                  workflow_type,
                  status,
                  triggered_by,
                  trace_id,
                  started_at,
                  finished_at,
                  artifact_id,
                  error_message,
                  policy_decision_json,
                  agent_identity_json,
                  metadata_json
                """


def _json_object(value: object | None) -> Jsonb:
    if value is None:
        value = {}
    return Jsonb(_json_safe(value))


def _json_list(value: object | None) -> Jsonb:
    if value is None:
        value = []
    return Jsonb(_json_safe(value))


def _json_safe(value: object) -> object:
    return json_safe(value)


def _sorted_field_names(record: JsonObject) -> list[str]:
    return sorted(str(key) for key in record)


class PostgresVNextStore:
    """SQL-backed vNext repository facade for the second-brain kernel."""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> VNextRow:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return cast(VNextRow, row)

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> VNextRow | None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return cast(VNextRow | None, row)

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[VNextRow]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return cast(list[VNextRow], list(rows))

    def _append_mutation_event(
        self,
        *,
        event_type: str,
        actor_type: str,
        target_type: str,
        target_id: object,
        payload: JsonObject,
        actor_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> VNextRow:
        return self.append_event(
            build_event_log_record(
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                target_type=target_type,
                target_id=str(target_id),
                payload=cast(JsonObject, _json_safe(payload)),
                trace_id=trace_id,
                run_id=run_id,
            )
        )

    def append_event(self, event: JsonObject) -> VNextRow:
        return self._fetch_one(
            "append_event",
            f"""
                INSERT INTO event_log (
                  id,
                  user_id,
                  event_type,
                  actor_type,
                  actor_id,
                  target_type,
                  target_id,
                  occurred_at,
                  payload_json,
                  trace_id,
                  run_id,
                  integrity_hash
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {EVENT_LOG_COLUMNS}
                """,
            (
                event.get("id"),
                event["event_type"],
                event["actor_type"],
                event.get("actor_id"),
                event.get("target_type"),
                event.get("target_id"),
                event.get("occurred_at"),
                _json_object(event.get("payload_json")),
                event.get("trace_id"),
                event.get("run_id"),
                event.get("integrity_hash"),
            ),
        )

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[VNextRow]:
        if target_type is None and target_id is None:
            if limit is not None:
                return self._fetch_all(
                    f"""
                    SELECT {EVENT_LOG_COLUMNS}
                    FROM event_log
                    ORDER BY occurred_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return self._fetch_all(
                f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                ORDER BY occurred_at DESC, id DESC
                """
            )
        if limit is not None:
            return self._fetch_all(
                f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE (%s::text IS NULL OR target_type = %s)
                  AND (%s::text IS NULL OR target_id = %s)
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
                (target_type, target_type, target_id, target_id, limit),
            )
        return self._fetch_all(
            f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE (%s::text IS NULL OR target_type = %s)
                  AND (%s::text IS NULL OR target_id = %s)
                ORDER BY occurred_at DESC, id DESC
            """,
            (target_type, target_type, target_id, target_id),
        )

    def list_sources(
        self,
        *,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 20,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY captured_at DESC, id DESC
                LIMIT %s
                """,
            (domains, domains, sensitivity_allowed, sensitivity_allowed, limit),
        )

    def create_source(self, source: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_source",
            f"""
                INSERT INTO sources (
                  id,
                  user_id,
                  source_type,
                  title,
                  author,
                  uri,
                  raw_path,
                  content_hash,
                  captured_at,
                  source_created_at,
                  source_modified_at,
                  connector_name,
                  external_id,
                  domain,
                  sensitivity,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SOURCE_COLUMNS}
                """,
            (
                source.get("id"),
                source["source_type"],
                source.get("title"),
                source.get("author"),
                source.get("uri"),
                source.get("raw_path"),
                source["content_hash"],
                source.get("captured_at"),
                source.get("source_created_at"),
                source.get("source_modified_at"),
                source.get("connector_name"),
                source.get("external_id"),
                source.get("domain", "unknown"),
                source.get("sensitivity", "unknown"),
                _json_object(source.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="source.created",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(source)},
        )
        return row

    def get_source(self, source_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (source_id,),
        )

    def get_source_by_content_hash(self, content_hash: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE content_hash = %s
                  AND deleted_at IS NULL
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """,
            (content_hash,),
        )

    def update_source(self, *, source_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_source",
            f"""
                UPDATE sources
                SET title = COALESCE(%s, title),
                    author = COALESCE(%s, author),
                    uri = COALESCE(%s, uri),
                    raw_path = COALESCE(%s, raw_path),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json)
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {SOURCE_COLUMNS}
                """,
            (
                patch.get("title"),
                patch.get("author"),
                patch.get("uri"),
                patch.get("raw_path"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                source_id,
            ),
        )
        self._append_mutation_event(
            event_type="source.updated",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def delete_source(self, *, source_id: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "delete_source",
            f"""
                UPDATE sources
                SET deleted_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {SOURCE_COLUMNS}
                """,
            (source_id,),
        )
        self._append_mutation_event(
            event_type="source.deleted",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "delete"},
        )
        return row

    def create_source_chunk(self, chunk: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_source_chunk",
            f"""
                INSERT INTO source_chunks (
                  id,
                  user_id,
                  source_id,
                  chunk_index,
                  text,
                  token_count,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SOURCE_CHUNK_COLUMNS}
                """,
            (
                chunk.get("id"),
                chunk["source_id"],
                chunk["chunk_index"],
                chunk["text"],
                chunk.get("token_count"),
                _json_object(chunk.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="source_chunk.created",
            actor_type=actor_type,
            target_type="source_chunk",
            target_id=row["id"],
            payload={"operation": "create", "source_id": str(row["source_id"])},
        )
        return row

    def list_source_chunks(self, source_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SOURCE_CHUNK_COLUMNS}
                FROM source_chunks
                WHERE source_id = %s::uuid
                ORDER BY chunk_index ASC, id ASC
                """,
            (source_id,),
        )

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_memory",
            f"""
                INSERT INTO memories (
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  title,
                  canonical_text,
                  summary,
                  domain,
                  sensitivity,
                  first_seen_at,
                  last_seen_at,
                  last_reviewed_at,
                  metadata_json,
                  created_at,
                  updated_at
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING {MEMORY_COLUMNS}
                """,
            (
                memory.get("id"),
                memory.get("agent_profile_id", "assistant_default"),
                memory["memory_key"],
                _json_object(memory.get("value")),
                memory.get("status", "candidate"),
                _json_list(memory.get("source_event_ids")),
                memory.get("memory_type", "semantic"),
                memory.get("confidence"),
                memory.get("salience"),
                memory.get("confirmation_status", "unconfirmed"),
                memory.get("trust_class", "deterministic"),
                memory.get("promotion_eligibility", "promotable"),
                memory.get("evidence_count"),
                memory.get("independent_source_count"),
                memory.get("extracted_by_model"),
                memory.get("trust_reason"),
                memory.get("valid_from"),
                memory.get("valid_to"),
                memory.get("last_confirmed_at"),
                memory.get("title"),
                memory.get("canonical_text", ""),
                memory.get("summary"),
                memory.get("domain", "unknown"),
                memory.get("sensitivity", "unknown"),
                memory.get("first_seen_at"),
                memory.get("last_seen_at"),
                memory.get("last_reviewed_at"),
                _json_object(memory.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="memory.created",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(memory)},
        )
        return row

    def get_memory(self, memory_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (memory_id,),
        )

    def list_memories(self, *, status: str | None = None) -> list[VNextRow]:
        if status is None:
            return self._fetch_all(
                f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """
            )
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE status = %s
                  AND deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """,
            (status,),
        )

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        pattern = f"%{query}%"
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (
                    memory_key ILIKE %s
                    OR title ILIKE %s
                    OR canonical_text ILIKE %s
                    OR summary ILIKE %s
                    OR value::text ILIKE %s
                  )
                ORDER BY
                  CASE
                    WHEN canonical_text ILIKE %s THEN 0
                    WHEN title ILIKE %s THEN 1
                    ELSE 2
                  END,
                  updated_at DESC,
                  created_at DESC,
                  id DESC
                LIMIT %s
                """,
            (
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                limit,
            ),
        )

    def update_memory(self, *, memory_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_memory",
            f"""
                UPDATE memories
                SET value = COALESCE(%s, value),
                    status = COALESCE(%s, status),
                    source_event_ids = COALESCE(%s, source_event_ids),
                    memory_type = COALESCE(%s, memory_type),
                    confidence = COALESCE(%s, confidence),
                    salience = COALESCE(%s, salience),
                    confirmation_status = COALESCE(%s, confirmation_status),
                    trust_class = COALESCE(%s, trust_class),
                    promotion_eligibility = COALESCE(%s, promotion_eligibility),
                    evidence_count = COALESCE(%s, evidence_count),
                    independent_source_count = COALESCE(%s, independent_source_count),
                    extracted_by_model = COALESCE(%s, extracted_by_model),
                    trust_reason = COALESCE(%s, trust_reason),
                    valid_from = COALESCE(%s, valid_from),
                    valid_to = COALESCE(%s, valid_to),
                    last_confirmed_at = COALESCE(%s, last_confirmed_at),
                    title = COALESCE(%s, title),
                    canonical_text = COALESCE(%s, canonical_text),
                    summary = COALESCE(%s, summary),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    last_seen_at = COALESCE(%s, last_seen_at),
                    last_reviewed_at = COALESCE(%s, last_reviewed_at),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp(),
                    deleted_at = CASE
                      WHEN %s = 'archived' THEN clock_timestamp()
                      ELSE deleted_at
                    END
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {MEMORY_COLUMNS}
                """,
            (
                _json_object(patch["value"]) if "value" in patch else None,
                patch.get("status"),
                _json_list(patch["source_event_ids"]) if "source_event_ids" in patch else None,
                patch.get("memory_type"),
                patch.get("confidence"),
                patch.get("salience"),
                patch.get("confirmation_status"),
                patch.get("trust_class"),
                patch.get("promotion_eligibility"),
                patch.get("evidence_count"),
                patch.get("independent_source_count"),
                patch.get("extracted_by_model"),
                patch.get("trust_reason"),
                patch.get("valid_from"),
                patch.get("valid_to"),
                patch.get("last_confirmed_at"),
                patch.get("title"),
                patch.get("canonical_text"),
                patch.get("summary"),
                patch.get("domain"),
                patch.get("sensitivity"),
                patch.get("last_seen_at"),
                patch.get("last_reviewed_at"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                patch.get("status"),
                memory_id,
            ),
        )
        self._append_mutation_event(
            event_type="memory.updated",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def append_revision(self, revision: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "append_revision",
            f"""
                WITH next_revision AS (
                  SELECT
                    COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no,
                    COALESCE(MAX(revision_number) + 1, 1) AS revision_number
                  FROM memory_revisions
                  WHERE memory_id = %s::uuid
                    AND user_id = app.current_user_id()
                )
                INSERT INTO memory_revisions (
                  id,
                  user_id,
                  memory_id,
                  sequence_no,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate,
                  revision_number,
                  revision_type,
                  text_before,
                  text_after,
                  reason,
                  actor_type,
                  actor_id,
                  metadata_json
                )
                SELECT
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  COALESCE(%s, next_revision.sequence_no),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, next_revision.revision_number),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                FROM next_revision
                RETURNING {REVISION_COLUMNS}
                """,
            (
                revision["memory_id"],
                revision.get("id"),
                revision["memory_id"],
                revision.get("sequence_no"),
                revision.get("action", "UPDATE"),
                revision["memory_key"],
                _json_object(revision["previous_value"]) if "previous_value" in revision else None,
                _json_object(revision.get("new_value")),
                _json_list(revision.get("source_event_ids")),
                _json_object(revision.get("candidate")),
                revision.get("revision_number"),
                revision.get("revision_type", "edited"),
                revision.get("text_before"),
                revision.get("text_after", ""),
                revision.get("reason"),
                revision.get("actor_type", actor_type),
                revision.get("actor_id"),
                _json_object(revision.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="memory_revision.created",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["memory_id"],
            payload={"operation": "create_revision", "revision_id": str(row["id"])},
        )
        return row

    def list_revisions(self, memory_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {REVISION_COLUMNS}
                FROM memory_revisions
                WHERE memory_id = %s::uuid
                ORDER BY revision_number ASC, sequence_no ASC, id ASC
                """,
            (memory_id,),
        )

    def create_provenance_link(self, link: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_provenance_link",
            f"""
                INSERT INTO provenance_links (
                  id,
                  user_id,
                  target_type,
                  target_id,
                  source_id,
                  source_chunk_id,
                  quote,
                  evidence_role,
                  confidence
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s::uuid,
                  %s::uuid,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PROVENANCE_COLUMNS}
                """,
            (
                link.get("id"),
                link["target_type"],
                link["target_id"],
                link.get("source_id"),
                link.get("source_chunk_id"),
                link.get("quote"),
                link.get("evidence_role", "supports"),
                link.get("confidence", 0.5),
            ),
        )
        self._append_mutation_event(
            event_type="provenance_link.created",
            actor_type=actor_type,
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            payload={"operation": "create", "provenance_link_id": str(row["id"])},
        )
        return row

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {PROVENANCE_COLUMNS}
                FROM provenance_links
                WHERE target_type = %s
                  AND target_id = %s
                ORDER BY created_at DESC, id DESC
                """,
            (target_type, target_id),
        )

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        pattern = f"%{query}%"
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (
                    title ILIKE %s
                    OR author ILIKE %s
                    OR uri ILIKE %s
                    OR raw_path ILIKE %s
                    OR content_hash ILIKE %s
                    OR metadata_json::text ILIKE %s
                  )
                ORDER BY captured_at DESC, id DESC
                LIMIT %s
                """,
            (
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                limit,
            ),
        )

    def create_edge(self, edge: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_edge",
            f"""
                INSERT INTO graph_edges (
                  id,
                  user_id,
                  from_type,
                  from_id,
                  to_type,
                  to_id,
                  edge_type,
                  confidence,
                  explanation,
                  created_by,
                  valid_from,
                  valid_to,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (
                edge.get("id"),
                edge["from_type"],
                edge["from_id"],
                edge["to_type"],
                edge["to_id"],
                edge["edge_type"],
                edge.get("confidence", 0.5),
                edge.get("explanation"),
                edge.get("created_by", actor_type),
                edge.get("valid_from"),
                edge.get("valid_to"),
                _json_object(edge.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="graph_edge.created",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "create", "edge_type": str(row["edge_type"])},
        )
        return row

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {GRAPH_EDGE_COLUMNS}
                FROM graph_edges
                WHERE (%s::text IS NULL OR from_id = %s)
                  AND (%s::text IS NULL OR to_id = %s)
                  AND valid_to IS NULL
                ORDER BY created_at DESC, id DESC
                """,
            (from_id, from_id, to_id, to_id),
        )

    def update_edge_status(self, *, edge_id: str, status: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_edge_status",
            f"""
                UPDATE graph_edges
                SET metadata_json = metadata_json || %s,
                    valid_to = CASE
                      WHEN %s = 'rejected' THEN clock_timestamp()
                      ELSE valid_to
                    END
                WHERE id = %s::uuid
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (_json_object({"status": status, "candidate": status != "accepted"}), status, edge_id),
        )
        self._append_mutation_event(
            event_type="graph_edge.updated",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def expire_edge(self, *, edge_id: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "expire_edge",
            f"""
                UPDATE graph_edges
                SET valid_to = clock_timestamp()
                WHERE id = %s::uuid
                  AND valid_to IS NULL
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (edge_id,),
        )
        self._append_mutation_event(
            event_type="graph_edge.expired",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "expire"},
        )
        return row

    def create_project(self, project: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_project",
            f"""
                INSERT INTO projects (
                  id,
                  user_id,
                  name,
                  slug,
                  status,
                  description,
                  current_state,
                  domain,
                  sensitivity,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PROJECT_COLUMNS}
                """,
            (
                project.get("id"),
                project["name"],
                project["slug"],
                project.get("status", "active"),
                project.get("description"),
                project.get("current_state"),
                project.get("domain", "professional"),
                project.get("sensitivity", "private"),
                _json_object(project.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="project.created",
            actor_type=actor_type,
            target_type="project",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(project)},
        )
        return row

    def get_project(self, project_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {PROJECT_COLUMNS}
                FROM projects
                WHERE id = %s::uuid
                """,
            (project_id,),
        )

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {PROJECT_COLUMNS}
                FROM projects
                WHERE (%s::text IS NULL OR status = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                limit,
            ),
        )

    def update_project(self, *, project_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_project",
            f"""
                UPDATE projects
                SET name = COALESCE(%s, name),
                    status = COALESCE(%s, status),
                    description = COALESCE(%s, description),
                    current_state = COALESCE(%s, current_state),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {PROJECT_COLUMNS}
                """,
            (
                patch.get("name"),
                patch.get("status"),
                patch.get("description"),
                patch.get("current_state"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                project_id,
            ),
        )
        self._append_mutation_event(
            event_type="project.updated",
            actor_type=actor_type,
            target_type="project",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def create_person(self, person: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_person",
            f"""
                INSERT INTO people (
                  id,
                  user_id,
                  name,
                  aliases_json,
                  relationship_type,
                  organization,
                  sensitivity,
                  notes,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PERSON_COLUMNS}
                """,
            (
                person.get("id"),
                person["name"],
                _json_list(person.get("aliases_json")),
                person.get("relationship_type"),
                person.get("organization"),
                person.get("sensitivity", "private"),
                person.get("notes"),
                _json_object(person.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="person.created",
            actor_type=actor_type,
            target_type="person",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(person)},
        )
        return row

    def get_person(self, person_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {PERSON_COLUMNS}
                FROM people
                WHERE id = %s::uuid
            """,
            (person_id,),
        )

    def list_people(
        self,
        *,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {PERSON_COLUMNS}
                FROM people
                WHERE (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (sensitivity_allowed, sensitivity_allowed, limit),
        )

    def update_person(self, *, person_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_person",
            f"""
                UPDATE people
                SET name = COALESCE(%s, name),
                    aliases_json = COALESCE(%s, aliases_json),
                    relationship_type = COALESCE(%s, relationship_type),
                    organization = COALESCE(%s, organization),
                    sensitivity = COALESCE(%s, sensitivity),
                    notes = COALESCE(%s, notes),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {PERSON_COLUMNS}
                """,
            (
                patch.get("name"),
                _json_list(patch["aliases_json"]) if "aliases_json" in patch else None,
                patch.get("relationship_type"),
                patch.get("organization"),
                patch.get("sensitivity"),
                patch.get("notes"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                person_id,
            ),
        )
        self._append_mutation_event(
            event_type="person.updated",
            actor_type=actor_type,
            target_type="person",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def create_belief(self, belief: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_belief",
            f"""
                INSERT INTO beliefs (
                  id,
                  user_id,
                  memory_id,
                  claim,
                  status,
                  confidence,
                  first_seen_at,
                  last_reinforced_at,
                  last_challenged_at,
                  superseded_by,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s::uuid,
                  %s
                )
                RETURNING {BELIEF_COLUMNS}
                """,
            (
                belief.get("id"),
                belief["memory_id"],
                belief["claim"],
                belief.get("status", "active"),
                belief.get("confidence", 0.5),
                belief.get("first_seen_at"),
                belief.get("last_reinforced_at"),
                belief.get("last_challenged_at"),
                belief.get("superseded_by"),
                _json_object(belief.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="belief.created",
            actor_type=actor_type,
            target_type="belief",
            target_id=row["id"],
            payload={"operation": "create", "memory_id": str(row["memory_id"])},
        )
        return row

    def get_belief(self, belief_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {BELIEF_COLUMNS}
                FROM beliefs
                WHERE id = %s::uuid
                """,
            (belief_id,),
        )

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            """
                SELECT
                  b.id,
                  b.user_id,
                  b.memory_id,
                  b.claim,
                  b.status,
                  b.confidence,
                  b.first_seen_at,
                  b.last_reinforced_at,
                  b.last_challenged_at,
                  b.superseded_by,
                  b.metadata_json,
                  m.domain,
                  m.sensitivity,
                  m.memory_type,
                  m.canonical_text AS memory_canonical_text
                FROM beliefs b
                JOIN memories m
                  ON m.id = b.memory_id
                 AND m.user_id = b.user_id
                WHERE (%s::text IS NULL OR b.status = %s)
                  AND m.deleted_at IS NULL
                  AND (%s::text[] IS NULL OR m.domain = ANY(%s::text[]) OR m.domain = 'unknown')
                  AND (%s::text[] IS NULL OR m.sensitivity = ANY(%s::text[]))
                ORDER BY
                  b.last_challenged_at DESC NULLS LAST,
                  b.last_reinforced_at DESC NULLS LAST,
                  b.first_seen_at DESC,
                  b.id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                limit,
            ),
        )

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        row = self._fetch_one(
            "update_belief_status",
            f"""
                UPDATE beliefs
                SET status = %s,
                    confidence = COALESCE(%s, confidence),
                    last_reinforced_at = CASE
                      WHEN %s = 'active' THEN clock_timestamp()
                      ELSE last_reinforced_at
                    END,
                    last_challenged_at = CASE
                      WHEN %s = 'challenged' THEN clock_timestamp()
                      ELSE last_challenged_at
                    END,
                    superseded_by = COALESCE(%s::uuid, superseded_by)
                WHERE id = %s::uuid
                RETURNING {BELIEF_COLUMNS}
                """,
            (status, confidence, status, status, superseded_by, belief_id),
        )
        self._append_mutation_event(
            event_type="belief.updated",
            actor_type=actor_type,
            target_type="belief",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_open_loop(self, loop: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_open_loop",
            f"""
                INSERT INTO open_loops (
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  description,
                  priority,
                  project_id,
                  person_id,
                  source_id,
                  closed_at,
                  domain,
                  sensitivity,
                  metadata_json,
                  created_at,
                  updated_at
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::uuid,
                  %s::uuid,
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (
                loop.get("id"),
                loop.get("memory_id"),
                loop["title"],
                loop.get("status", "open"),
                loop.get("opened_at"),
                loop.get("due_at"),
                loop.get("resolved_at"),
                loop.get("resolution_note"),
                loop.get("description"),
                loop.get("priority", "normal"),
                loop.get("project_id"),
                loop.get("person_id"),
                loop.get("source_id"),
                loop.get("closed_at"),
                loop.get("domain", "unknown"),
                loop.get("sensitivity", "unknown"),
                _json_object(loop.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="open_loop.created",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(loop)},
        )
        return row

    def get_open_loop(self, loop_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE id = %s::uuid
                """,
            (loop_id,),
        )

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE (%s::text IS NULL OR status = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::uuid IS NULL OR project_id = %s::uuid)
                  AND (%s::uuid IS NULL OR person_id = %s::uuid)
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                project_id,
                project_id,
                person_id,
                person_id,
                limit,
            ),
        )

    def update_open_loop(self, *, loop_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_open_loop",
            f"""
                UPDATE open_loops
                SET title = COALESCE(%s, title),
                    description = COALESCE(%s, description),
                    priority = COALESCE(%s, priority),
                    due_at = COALESCE(%s::timestamptz, due_at),
                    project_id = COALESCE(%s::uuid, project_id),
                    person_id = COALESCE(%s::uuid, person_id),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (
                patch.get("title"),
                patch.get("description"),
                patch.get("priority"),
                patch.get("due_at"),
                patch.get("project_id"),
                patch.get("person_id"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                loop_id,
            ),
        )
        self._append_mutation_event(
            event_type="open_loop.updated",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        row = self._fetch_one(
            "update_open_loop_status",
            f"""
                UPDATE open_loops
                SET status = %s,
                    resolved_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE clock_timestamp()
                    END,
                    closed_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE clock_timestamp()
                    END,
                    resolution_note = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE %s
                    END,
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (status, status, status, status, resolution_note, loop_id),
        )
        self._append_mutation_event(
            event_type="open_loop.updated",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_artifact",
            f"""
                INSERT INTO generated_artifacts (
                  id,
                  user_id,
                  artifact_type,
                  title,
                  content_markdown,
                  status,
                  domain,
                  sensitivity,
                  generated_by,
                  prompt_hash,
                  model_info_json,
                  reviewed_at,
                  promoted_at,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::timestamptz,
                  %s
                )
                RETURNING {ARTIFACT_COLUMNS}
                """,
            (
                artifact.get("id"),
                artifact["artifact_type"],
                artifact["title"],
                artifact["content_markdown"],
                artifact.get("status", "draft"),
                artifact.get("domain", "unknown"),
                artifact.get("sensitivity", "unknown"),
                artifact.get("generated_by", actor_type),
                artifact.get("prompt_hash"),
                _json_object(artifact.get("model_info_json")),
                artifact.get("reviewed_at"),
                artifact.get("promoted_at"),
                _json_object(artifact.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="artifact.created",
            actor_type=actor_type,
            target_type="artifact",
            target_id=row["id"],
            payload={"operation": "create", "artifact_type": str(row["artifact_type"])},
        )
        return row

    def get_artifact(self, artifact_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE id = %s::uuid
                """,
            (artifact_id,),
        )

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE (%s::text IS NULL OR artifact_type = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (
                artifact_type,
                artifact_type,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                limit,
            ),
        )

    def update_artifact_status(self, *, artifact_id: str, status: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_artifact_status",
            f"""
                UPDATE generated_artifacts
                SET status = %s,
                    reviewed_at = CASE
                      WHEN %s IN ('reviewed', 'accepted', 'rejected') THEN clock_timestamp()
                      ELSE reviewed_at
                    END,
                    promoted_at = CASE
                      WHEN %s = 'promoted_to_memory' THEN clock_timestamp()
                      ELSE promoted_at
                    END
                WHERE id = %s::uuid
                RETURNING {ARTIFACT_COLUMNS}
                """,
            (status, status, status, artifact_id),
        )
        self._append_mutation_event(
            event_type="artifact.updated",
            actor_type=actor_type,
            target_type="artifact",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_task(self, task: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_task",
            f"""
                INSERT INTO task_queue (
                  id,
                  user_id,
                  title,
                  task_type,
                  instructions,
                  status,
                  requested_by,
                  scope_json,
                  allowed_sources_json,
                  domain,
                  sensitivity,
                  write_policy,
                  scheduled_for,
                  output_artifact_id,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::uuid,
                  %s
                )
                RETURNING {TASK_COLUMNS}
                """,
            (
                task.get("id"),
                task["title"],
                task["task_type"],
                task["instructions"],
                task.get("status", "pending"),
                task.get("requested_by", actor_type),
                _json_object(task.get("scope_json")),
                _json_list(task.get("allowed_sources_json")),
                task.get("domain", "unknown"),
                task.get("sensitivity", "unknown"),
                task.get("write_policy", "proposal_only"),
                task.get("scheduled_for"),
                task.get("output_artifact_id"),
                _json_object(task.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="task.created",
            actor_type=actor_type,
            target_type="task",
            target_id=row["id"],
            payload={"operation": "create", "task_type": str(row["task_type"])},
        )
        return row

    def claim_next_task(self, *, actor_type: str = "system") -> VNextRow | None:
        row = self._fetch_optional_one(
            f"""
                WITH next_task AS (
                  SELECT id
                  FROM task_queue
                  WHERE status = 'pending'
                    AND (scheduled_for IS NULL OR scheduled_for <= clock_timestamp())
                  ORDER BY scheduled_for ASC NULLS FIRST, created_at ASC, id ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE task_queue
                SET status = 'running',
                    started_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                FROM next_task
                WHERE task_queue.id = next_task.id
                RETURNING {TASK_COLUMNS}
                """
        )
        if row is not None:
            self._append_mutation_event(
                event_type="task.claimed",
                actor_type=actor_type,
                target_type="task",
                target_id=row["id"],
                payload={"operation": "claim"},
            )
        return row

    def update_task_status(
        self,
        *,
        task_id: str,
        status: str,
        details: JsonObject | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        details = details or {}
        row = self._fetch_one(
            "update_task_status",
            f"""
                UPDATE task_queue
                SET status = %s,
                    completed_at = CASE
                      WHEN %s = 'completed' THEN clock_timestamp()
                      ELSE completed_at
                    END,
                    failed_at = CASE
                      WHEN %s = 'failed' THEN clock_timestamp()
                      ELSE failed_at
                    END,
                    error_message = COALESCE(%s, error_message),
                    output_artifact_id = COALESCE(%s::uuid, output_artifact_id),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {TASK_COLUMNS}
                """,
            (
                status,
                status,
                status,
                details.get("error_message"),
                details.get("output_artifact_id"),
                _json_object(details["metadata_json"]) if "metadata_json" in details else None,
                task_id,
            ),
        )
        self._append_mutation_event(
            event_type="task.updated",
            actor_type=actor_type,
            target_type="task",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status, "details": details},
        )
        return row

    def list_tasks(self, *, status: str | None = None, limit: int = 8) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {TASK_COLUMNS}
                FROM task_queue
                WHERE (%s::text IS NULL OR status = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (status, status, limit),
        )

    def upsert_brain_charter(self, charter: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "upsert_brain_charter",
            f"""
                INSERT INTO brain_charters (
                  id,
                  user_id,
                  content_markdown,
                  owner_json,
                  memory_philosophy_json,
                  life_domains_json,
                  active_projects_json,
                  communication_style_json,
                  priorities_json,
                  autonomous_rules_json,
                  quality_standard_json,
                  sensitivity
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id)
                DO UPDATE SET
                  content_markdown = EXCLUDED.content_markdown,
                  owner_json = EXCLUDED.owner_json,
                  memory_philosophy_json = EXCLUDED.memory_philosophy_json,
                  life_domains_json = EXCLUDED.life_domains_json,
                  active_projects_json = EXCLUDED.active_projects_json,
                  communication_style_json = EXCLUDED.communication_style_json,
                  priorities_json = EXCLUDED.priorities_json,
                  autonomous_rules_json = EXCLUDED.autonomous_rules_json,
                  quality_standard_json = EXCLUDED.quality_standard_json,
                  sensitivity = EXCLUDED.sensitivity,
                  updated_at = clock_timestamp()
                RETURNING {BRAIN_CHARTER_COLUMNS}
                """,
            (
                charter.get("id"),
                charter["content_markdown"],
                _json_object(charter.get("owner_json")),
                _json_object(charter.get("memory_philosophy_json")),
                _json_object(charter.get("life_domains_json")),
                _json_list(charter.get("active_projects_json")),
                _json_object(charter.get("communication_style_json")),
                _json_object(charter.get("priorities_json")),
                _json_list(charter.get("autonomous_rules_json")),
                _json_list(charter.get("quality_standard_json")),
                charter.get("sensitivity", "private"),
            ),
        )
        self._append_mutation_event(
            event_type="brain_charter.upserted",
            actor_type=actor_type,
            target_type="brain_charter",
            target_id=row["id"],
            payload={"operation": "upsert", "fields": _sorted_field_names(charter)},
        )
        return row

    def get_brain_charter(self) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {BRAIN_CHARTER_COLUMNS}
                FROM brain_charters
                LIMIT 1
                """
        )

    def upsert_agent_identity(self, agent: JsonObject, *, actor_type: str = "agent") -> VNextRow:
        row = self._fetch_one(
            "upsert_agent_identity",
            f"""
                INSERT INTO agent_identities (
                  id,
                  user_id,
                  agent_id,
                  agent_type,
                  permission_profile,
                  display_name,
                  project_scope_json,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, agent_id)
                DO UPDATE SET
                  agent_type = EXCLUDED.agent_type,
                  permission_profile = EXCLUDED.permission_profile,
                  display_name = COALESCE(EXCLUDED.display_name, agent_identities.display_name),
                  project_scope_json = EXCLUDED.project_scope_json,
                  metadata_json = agent_identities.metadata_json || EXCLUDED.metadata_json,
                  updated_at = clock_timestamp()
                RETURNING {AGENT_IDENTITY_COLUMNS}
                """,
            (
                agent.get("id"),
                agent["agent_id"],
                agent.get("agent_type", "unknown"),
                agent.get("permission_profile", "read_only_agent"),
                agent.get("display_name"),
                _json_list(agent.get("project_scope_json") or agent.get("project_scope")),
                _json_object(agent.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="agent.identity_upserted",
            actor_type=actor_type,
            actor_id=str(row["agent_id"]),
            target_type="agent_identity",
            target_id=row["id"],
            payload={"operation": "upsert", "agent_id": str(row["agent_id"])},
        )
        return row

    def list_agent_identities(self, *, limit: int = 20) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {AGENT_IDENTITY_COLUMNS}
                FROM agent_identities
                ORDER BY updated_at DESC, id DESC
                LIMIT %s
                """,
            (limit,),
        )

    def list_agent_events(self, *, agent_id: str | None = None, limit: int = 50) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE actor_type = 'agent'
                  AND (%s::text IS NULL OR actor_id = %s)
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
            (agent_id, agent_id, limit),
        )

    def upsert_scheduler_workflow(self, workflow: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "upsert_scheduler_workflow",
            f"""
                INSERT INTO scheduler_workflows (
                  id,
                  user_id,
                  workflow_type,
                  enabled,
                  paused,
                  schedule_json,
                  timezone,
                  next_run_at,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  COALESCE(%s, false),
                  COALESCE(%s, false),
                  %s,
                  COALESCE(%s, 'UTC'),
                  %s,
                  %s
                )
                ON CONFLICT (user_id, workflow_type)
                DO UPDATE SET
                  enabled = EXCLUDED.enabled,
                  paused = EXCLUDED.paused,
                  schedule_json = EXCLUDED.schedule_json,
                  timezone = EXCLUDED.timezone,
                  next_run_at = EXCLUDED.next_run_at,
                  metadata_json = scheduler_workflows.metadata_json || EXCLUDED.metadata_json,
                  updated_at = clock_timestamp()
                RETURNING {SCHEDULER_WORKFLOW_COLUMNS}
                """,
            (
                workflow.get("id"),
                workflow["workflow_type"],
                workflow.get("enabled"),
                workflow.get("paused"),
                _json_object(workflow.get("schedule_json")),
                workflow.get("timezone"),
                workflow.get("next_run_at"),
                _json_object(workflow.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="scheduler.workflow_upserted",
            actor_type=actor_type,
            target_type="scheduler_workflow",
            target_id=row["id"],
            payload={
                "operation": "upsert",
                "workflow_type": str(row["workflow_type"]),
                "enabled": bool(row["enabled"]),
                "paused": bool(row["paused"]),
            },
        )
        return row

    def update_scheduler_workflow(self, *, workflow_type: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_scheduler_workflow",
            f"""
                UPDATE scheduler_workflows
                SET enabled = COALESCE(%s, enabled),
                    paused = COALESCE(%s, paused),
                    schedule_json = COALESCE(%s, schedule_json),
                    timezone = COALESCE(%s, timezone),
                    next_run_at = CASE
                      WHEN %s THEN %s::timestamptz
                      ELSE next_run_at
                    END,
                    last_run_id = COALESCE(%s::uuid, last_run_id),
                    last_run_at = COALESCE(%s::timestamptz, last_run_at),
                    last_result = COALESCE(%s, last_result),
                    last_error = CASE
                      WHEN %s THEN %s
                      ELSE last_error
                    END,
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE workflow_type = %s
                RETURNING {SCHEDULER_WORKFLOW_COLUMNS}
                """,
            (
                patch.get("enabled"),
                patch.get("paused"),
                _json_object(patch["schedule_json"]) if "schedule_json" in patch else None,
                patch.get("timezone"),
                "next_run_at" in patch,
                patch.get("next_run_at"),
                patch.get("last_run_id"),
                patch.get("last_run_at"),
                patch.get("last_result"),
                "last_error" in patch,
                patch.get("last_error"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                workflow_type,
            ),
        )
        self._append_mutation_event(
            event_type="scheduler.workflow_updated",
            actor_type=actor_type,
            target_type="scheduler_workflow",
            target_id=row["id"],
            payload={"operation": "update", "workflow_type": workflow_type, "changes": patch},
        )
        return row

    def get_scheduler_workflow(self, workflow_type: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                WHERE workflow_type = %s
                """,
            (workflow_type,),
        )

    def list_scheduler_workflows(self) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                ORDER BY workflow_type ASC
                """
        )

    def create_scheduler_run(self, run: JsonObject, *, actor_type: str = "scheduler") -> VNextRow:
        row = self._fetch_one(
            "create_scheduler_run",
            f"""
                INSERT INTO scheduler_runs (
                  id,
                  user_id,
                  workflow_id,
                  workflow_type,
                  status,
                  triggered_by,
                  trace_id,
                  policy_decision_json,
                  agent_identity_json,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  COALESCE(%s, 'started'),
                  COALESCE(%s, 'scheduler'),
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SCHEDULER_RUN_COLUMNS}
                """,
            (
                run.get("id"),
                run.get("workflow_id"),
                run["workflow_type"],
                run.get("status"),
                run.get("triggered_by"),
                run["trace_id"],
                _json_object(run.get("policy_decision_json")),
                _json_object(run.get("agent_identity_json")),
                _json_object(run.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="scheduler.run_started",
            actor_type=actor_type,
            target_type="scheduler_run",
            target_id=row["id"],
            trace_id=str(row["trace_id"]),
            run_id=str(row["id"]),
            payload={"workflow_type": str(row["workflow_type"]), "triggered_by": str(row["triggered_by"])},
        )
        return row

    def update_scheduler_run(self, *, run_id: str, patch: JsonObject, actor_type: str = "scheduler") -> VNextRow:
        row = self._fetch_one(
            "update_scheduler_run",
            f"""
                UPDATE scheduler_runs
                SET status = COALESCE(%s, status),
                    finished_at = CASE
                      WHEN %s IN ('succeeded', 'failed') THEN clock_timestamp()
                      ELSE finished_at
                    END,
                    artifact_id = COALESCE(%s::uuid, artifact_id),
                    error_message = COALESCE(%s, error_message),
                    policy_decision_json = COALESCE(%s, policy_decision_json),
                    agent_identity_json = COALESCE(%s, agent_identity_json),
                    metadata_json = COALESCE(%s, metadata_json)
                WHERE id = %s::uuid
                RETURNING {SCHEDULER_RUN_COLUMNS}
                """,
            (
                patch.get("status"),
                patch.get("status"),
                patch.get("artifact_id"),
                patch.get("error_message"),
                _json_object(patch["policy_decision_json"]) if "policy_decision_json" in patch else None,
                _json_object(patch["agent_identity_json"]) if "agent_identity_json" in patch else None,
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                run_id,
            ),
        )
        event_type = "scheduler.run_succeeded" if row["status"] == "succeeded" else "scheduler.run_failed" if row["status"] == "failed" else "scheduler.run_updated"
        self._append_mutation_event(
            event_type=event_type,
            actor_type=actor_type,
            target_type="scheduler_run",
            target_id=row["id"],
            trace_id=str(row["trace_id"]),
            run_id=str(row["id"]),
            payload={
                "workflow_type": str(row["workflow_type"]),
                "status": str(row["status"]),
                "artifact_id": str(row["artifact_id"]) if row.get("artifact_id") is not None else None,
                "error_message": row.get("error_message"),
            },
        )
        return row

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SCHEDULER_RUN_COLUMNS}
                FROM scheduler_runs
                WHERE (%s::text IS NULL OR workflow_type = %s)
                ORDER BY started_at DESC, id DESC
                LIMIT %s
                """,
            (workflow_type, workflow_type, limit),
        )

    def try_scheduler_workflow_lock(self, workflow_type: str) -> bool:
        row = self._fetch_one(
            "try_scheduler_workflow_lock",
            """
                SELECT pg_try_advisory_xact_lock(hashtextextended(%s::text, 17)) AS acquired
                """,
            (f"vnext_scheduler:{workflow_type}",),
        )
        return bool(row.get("acquired"))


__all__ = [
    "PostgresVNextStore",
    "VNextRow",
]
