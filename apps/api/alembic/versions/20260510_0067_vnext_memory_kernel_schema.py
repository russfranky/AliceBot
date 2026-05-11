"""Add vNext memory-kernel schema foundations."""

from __future__ import annotations

from alembic import op


revision = "20260510_0067"
down_revision = "20260416_0066"
branch_labels = None
depends_on = None

DOMAINS = (
    "professional",
    "personal",
    "family",
    "health",
    "spiritual",
    "financial",
    "legal",
    "learning",
    "relationship",
    "project",
    "agent_run",
    "system",
    "unknown",
)

SENSITIVITY_LEVELS = (
    "public",
    "internal",
    "private",
    "confidential",
    "highly_sensitive",
    "sacred",
    "regulated",
    "unknown",
)

LEGACY_MEMORY_TYPES = (
    "preference",
    "identity_fact",
    "relationship_fact",
    "project_fact",
    "decision",
    "commitment",
    "routine",
    "constraint",
    "working_style",
)

VNEXT_MEMORY_TYPES = (
    "episode",
    "semantic",
    "project_state",
    "decision",
    "belief",
    "thesis",
    "person",
    "relationship",
    "open_loop",
    "preference",
    "value",
    "pattern",
    "contradiction",
    "question",
    "answer",
    "artifact_summary",
    "agent_run",
    "system",
)

MEMORY_TYPES = tuple(dict.fromkeys((*LEGACY_MEMORY_TYPES, *VNEXT_MEMORY_TYPES)))

MEMORY_STATUSES = (
    "candidate",
    "active",
    "accepted",
    "rejected",
    "superseded",
    "archived",
    "needs_review",
    "private_only",
)

REVISION_TYPES = (
    "created",
    "edited",
    "corrected",
    "promoted",
    "rejected",
    "superseded",
    "merged",
    "split",
    "archived",
    "restored",
)

EVIDENCE_ROLES = (
    "supports",
    "contradicts",
    "mentions",
    "inferred_from",
    "quoted_from",
    "summarizes",
    "background",
)

EDGE_TYPES = (
    "supports",
    "contradicts",
    "caused_by",
    "influenced_by",
    "similar_to",
    "supersedes",
    "depends_on",
    "mentions",
    "asks",
    "answers",
    "reframes",
    "predicts",
    "invalidates",
    "reopens",
    "same_problem",
    "same_principle",
    "cross_domain_pattern",
    "old_idea_now_relevant",
    "belief_reinforcement",
    "belief_challenge",
    "owned_by",
    "belongs_to_project",
    "related_to_person",
)

ARTIFACT_TYPES = (
    "daily_brief",
    "weekly_synthesis",
    "monthly_distillation",
    "connection_report",
    "contradiction_report",
    "project_update",
    "thesis_report",
    "open_loop_report",
    "queue_result",
    "research_brief",
    "draft",
    "context_pack",
    "agent_resumption_brief",
    "system_report",
)

ARTIFACT_STATUSES = (
    "draft",
    "needs_review",
    "reviewed",
    "accepted",
    "rejected",
    "promoted_to_memory",
    "superseded",
    "archived",
)

TASK_TYPES = (
    "research",
    "synthesize",
    "analyze",
    "compare",
    "draft",
    "summarize",
    "connect",
    "find_contradictions",
    "update_project",
    "create_context_pack",
    "review_memory",
)

TASK_STATUSES = (
    "pending",
    "running",
    "completed",
    "failed",
    "needs_review",
    "cancelled",
)

WRITE_POLICIES = (
    "proposal_only",
    "auto_generate_artifact",
    "requires_review_before_write",
    "admin_only",
)

PROJECT_STATUSES = ("active", "paused", "completed", "archived")
BELIEF_STATUSES = ("emerging", "active", "challenged", "superseded", "retired")
OPEN_LOOP_PRIORITIES = ("low", "normal", "high", "urgent")

_DOMAINS_SQL = ", ".join(f"'{value}'" for value in DOMAINS)
_SENSITIVITY_SQL = ", ".join(f"'{value}'" for value in SENSITIVITY_LEVELS)
_MEMORY_TYPES_SQL = ", ".join(f"'{value}'" for value in MEMORY_TYPES)
_MEMORY_STATUSES_SQL = ", ".join(f"'{value}'" for value in MEMORY_STATUSES)
_REVISION_TYPES_SQL = ", ".join(f"'{value}'" for value in REVISION_TYPES)
_EVIDENCE_ROLES_SQL = ", ".join(f"'{value}'" for value in EVIDENCE_ROLES)
_EDGE_TYPES_SQL = ", ".join(f"'{value}'" for value in EDGE_TYPES)
_ARTIFACT_TYPES_SQL = ", ".join(f"'{value}'" for value in ARTIFACT_TYPES)
_ARTIFACT_STATUSES_SQL = ", ".join(f"'{value}'" for value in ARTIFACT_STATUSES)
_TASK_TYPES_SQL = ", ".join(f"'{value}'" for value in TASK_TYPES)
_TASK_STATUSES_SQL = ", ".join(f"'{value}'" for value in TASK_STATUSES)
_WRITE_POLICIES_SQL = ", ".join(f"'{value}'" for value in WRITE_POLICIES)
_PROJECT_STATUSES_SQL = ", ".join(f"'{value}'" for value in PROJECT_STATUSES)
_BELIEF_STATUSES_SQL = ", ".join(f"'{value}'" for value in BELIEF_STATUSES)
_OPEN_LOOP_PRIORITIES_SQL = ", ".join(f"'{value}'" for value in OPEN_LOOP_PRIORITIES)

_NEW_RLS_TABLES = (
    "sources",
    "source_chunks",
    "provenance_links",
    "graph_edges",
    "projects",
    "people",
    "beliefs",
    "generated_artifacts",
    "task_queue",
    "event_log",
    "brain_charters",
)

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_event_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'event_log is append-only';
        END;
        $$;
        """,
)

_UPGRADE_MEMORY_COMPAT_STATEMENTS = (
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_memory_type_check",
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_memory_type_check
          CHECK (memory_type IN ({_MEMORY_TYPES_SQL}))
        """,
    """
        ALTER TABLE memories
          ADD COLUMN title text NULL,
          ADD COLUMN canonical_text text NOT NULL DEFAULT '',
          ADD COLUMN summary text NULL,
          ADD COLUMN domain text NOT NULL DEFAULT 'unknown',
          ADD COLUMN sensitivity text NOT NULL DEFAULT 'unknown',
          ADD COLUMN first_seen_at timestamptz NOT NULL DEFAULT now(),
          ADD COLUMN last_seen_at timestamptz NOT NULL DEFAULT now(),
          ADD COLUMN last_reviewed_at timestamptz NULL,
          ADD COLUMN metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_domain_check
          CHECK (domain IN ({_DOMAINS_SQL}))
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_sensitivity_check
          CHECK (sensitivity IN ({_SENSITIVITY_SQL}))
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_metadata_json_object_check
          CHECK (jsonb_typeof(metadata_json) = 'object')
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_seen_range_check
          CHECK (last_seen_at >= first_seen_at)
        """,
    """
        CREATE INDEX memories_user_domain_sensitivity_updated_idx
          ON memories (user_id, domain, sensitivity, updated_at DESC, id DESC)
        """,
)

_UPGRADE_REVISION_COMPAT_STATEMENTS = (
    """
        ALTER TABLE memory_revisions
          ADD COLUMN revision_number bigint NULL,
          ADD COLUMN revision_type text NULL,
          ADD COLUMN text_before text NULL,
          ADD COLUMN text_after text NULL,
          ADD COLUMN reason text NULL,
          ADD COLUMN actor_type text NOT NULL DEFAULT 'system',
          ADD COLUMN actor_id text NULL,
          ADD COLUMN metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    """
        UPDATE memory_revisions
        SET
          revision_number = sequence_no,
          revision_type = CASE action
            WHEN 'ADD' THEN 'created'
            WHEN 'UPDATE' THEN 'edited'
            WHEN 'DELETE' THEN 'archived'
            ELSE 'edited'
          END,
          text_before = CASE
            WHEN previous_value IS NULL THEN NULL
            ELSE previous_value::text
          END,
          text_after = COALESCE(new_value::text, '{}')
        WHERE revision_number IS NULL
        """,
    """
        ALTER TABLE memory_revisions
          ALTER COLUMN revision_number SET NOT NULL,
          ALTER COLUMN revision_type SET NOT NULL,
          ALTER COLUMN text_after SET NOT NULL
        """,
    f"""
        ALTER TABLE memory_revisions
          ADD CONSTRAINT memory_revisions_revision_type_check
          CHECK (revision_type IN ({_REVISION_TYPES_SQL}))
        """,
    """
        ALTER TABLE memory_revisions
          ADD CONSTRAINT memory_revisions_revision_number_positive_check
          CHECK (revision_number >= 1)
        """,
    """
        ALTER TABLE memory_revisions
          ADD CONSTRAINT memory_revisions_metadata_json_object_check
          CHECK (jsonb_typeof(metadata_json) = 'object')
        """,
)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE sources (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_type text NOT NULL,
          title text NULL,
          author text NULL,
          uri text NULL,
          raw_path text NULL,
          content_hash text NOT NULL,
          captured_at timestamptz NOT NULL DEFAULT now(),
          source_created_at timestamptz NULL,
          source_modified_at timestamptz NULL,
          connector_name text NULL,
          external_id text NULL,
          domain text NOT NULL DEFAULT 'unknown',
          sensitivity text NOT NULL DEFAULT 'unknown',
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          deleted_at timestamptz NULL,
          UNIQUE (id, user_id),
          CONSTRAINT sources_source_type_length_check
            CHECK (char_length(source_type) BETWEEN 1 AND 120),
          CONSTRAINT sources_content_hash_length_check
            CHECK (char_length(content_hash) BETWEEN 1 AND 200),
          CONSTRAINT sources_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT sources_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT sources_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE source_chunks (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_id uuid NOT NULL,
          chunk_index integer NOT NULL,
          text text NOT NULL,
          token_count integer NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, source_id, chunk_index),
          CONSTRAINT source_chunks_source_fkey
            FOREIGN KEY (source_id, user_id)
            REFERENCES sources(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT source_chunks_chunk_index_check
            CHECK (chunk_index >= 0),
          CONSTRAINT source_chunks_token_count_check
            CHECK (token_count IS NULL OR token_count >= 0),
          CONSTRAINT source_chunks_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE provenance_links (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          target_type text NOT NULL,
          target_id text NOT NULL,
          source_id uuid NULL,
          source_chunk_id uuid NULL,
          quote text NULL,
          evidence_role text NOT NULL,
          confidence double precision NOT NULL DEFAULT 0.5,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT provenance_links_source_fkey
            FOREIGN KEY (source_id, user_id)
            REFERENCES sources(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT provenance_links_source_chunk_fkey
            FOREIGN KEY (source_chunk_id, user_id)
            REFERENCES source_chunks(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT provenance_links_evidence_role_check
            CHECK (evidence_role IN ({_EVIDENCE_ROLES_SQL})),
          CONSTRAINT provenance_links_confidence_range_check
            CHECK (confidence >= 0.0 AND confidence <= 1.0)
        );

        CREATE TABLE graph_edges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          from_type text NOT NULL,
          from_id text NOT NULL,
          to_type text NOT NULL,
          to_id text NOT NULL,
          edge_type text NOT NULL,
          confidence double precision NOT NULL DEFAULT 0.5,
          explanation text NULL,
          created_by text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          valid_from timestamptz NULL,
          valid_to timestamptz NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT graph_edges_edge_type_check
            CHECK (edge_type IN ({_EDGE_TYPES_SQL})),
          CONSTRAINT graph_edges_confidence_range_check
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
          CONSTRAINT graph_edges_valid_range_check
            CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from),
          CONSTRAINT graph_edges_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE projects (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name text NOT NULL,
          slug text NOT NULL,
          status text NOT NULL DEFAULT 'active',
          description text NULL,
          current_state text NULL,
          domain text NOT NULL DEFAULT 'professional',
          sensitivity text NOT NULL DEFAULT 'private',
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          UNIQUE (user_id, slug),
          CONSTRAINT projects_status_check
            CHECK (status IN ({_PROJECT_STATUSES_SQL})),
          CONSTRAINT projects_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT projects_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT projects_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE people (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name text NOT NULL,
          aliases_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          relationship_type text NULL,
          organization text NULL,
          sensitivity text NOT NULL DEFAULT 'private',
          notes text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT people_aliases_json_array_check
            CHECK (jsonb_typeof(aliases_json) = 'array'),
          CONSTRAINT people_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT people_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE beliefs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          memory_id uuid NOT NULL,
          claim text NOT NULL,
          status text NOT NULL DEFAULT 'active',
          confidence double precision NOT NULL DEFAULT 0.5,
          first_seen_at timestamptz NOT NULL DEFAULT now(),
          last_reinforced_at timestamptz NULL,
          last_challenged_at timestamptz NULL,
          superseded_by uuid NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT beliefs_memory_fkey
            FOREIGN KEY (memory_id, user_id)
            REFERENCES memories(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT beliefs_superseded_by_fkey
            FOREIGN KEY (superseded_by, user_id)
            REFERENCES beliefs(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT beliefs_status_check
            CHECK (status IN ({_BELIEF_STATUSES_SQL})),
          CONSTRAINT beliefs_confidence_range_check
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
          CONSTRAINT beliefs_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE generated_artifacts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          artifact_type text NOT NULL,
          title text NOT NULL,
          content_markdown text NOT NULL,
          status text NOT NULL DEFAULT 'draft',
          domain text NOT NULL DEFAULT 'unknown',
          sensitivity text NOT NULL DEFAULT 'unknown',
          generated_by text NOT NULL,
          prompt_hash text NULL,
          model_info_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          reviewed_at timestamptz NULL,
          promoted_at timestamptz NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT generated_artifacts_type_check
            CHECK (artifact_type IN ({_ARTIFACT_TYPES_SQL})),
          CONSTRAINT generated_artifacts_status_check
            CHECK (status IN ({_ARTIFACT_STATUSES_SQL})),
          CONSTRAINT generated_artifacts_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT generated_artifacts_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT generated_artifacts_model_info_json_object_check
            CHECK (jsonb_typeof(model_info_json) = 'object'),
          CONSTRAINT generated_artifacts_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE task_queue (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title text NOT NULL,
          task_type text NOT NULL,
          instructions text NOT NULL,
          status text NOT NULL DEFAULT 'pending',
          requested_by text NOT NULL,
          scope_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          allowed_sources_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          domain text NOT NULL DEFAULT 'unknown',
          sensitivity text NOT NULL DEFAULT 'unknown',
          write_policy text NOT NULL DEFAULT 'proposal_only',
          scheduled_for timestamptz NULL,
          started_at timestamptz NULL,
          completed_at timestamptz NULL,
          failed_at timestamptz NULL,
          error_message text NULL,
          output_artifact_id uuid NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT task_queue_artifact_fkey
            FOREIGN KEY (output_artifact_id, user_id)
            REFERENCES generated_artifacts(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT task_queue_task_type_check
            CHECK (task_type IN ({_TASK_TYPES_SQL})),
          CONSTRAINT task_queue_status_check
            CHECK (status IN ({_TASK_STATUSES_SQL})),
          CONSTRAINT task_queue_write_policy_check
            CHECK (write_policy IN ({_WRITE_POLICIES_SQL})),
          CONSTRAINT task_queue_scope_json_object_check
            CHECK (jsonb_typeof(scope_json) = 'object'),
          CONSTRAINT task_queue_allowed_sources_json_array_check
            CHECK (jsonb_typeof(allowed_sources_json) = 'array'),
          CONSTRAINT task_queue_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT task_queue_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT task_queue_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE event_log (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          event_type text NOT NULL,
          actor_type text NOT NULL,
          actor_id text NULL,
          target_type text NULL,
          target_id text NULL,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          payload_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          trace_id text NULL,
          run_id text NULL,
          integrity_hash text NULL,
          UNIQUE (id, user_id),
          CONSTRAINT event_log_event_type_length_check
            CHECK (char_length(event_type) BETWEEN 1 AND 160),
          CONSTRAINT event_log_actor_type_length_check
            CHECK (char_length(actor_type) BETWEEN 1 AND 80),
          CONSTRAINT event_log_payload_json_object_check
            CHECK (jsonb_typeof(payload_json) = 'object')
        );

        CREATE TABLE brain_charters (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          content_markdown text NOT NULL,
          owner_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          memory_philosophy_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          life_domains_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          active_projects_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          communication_style_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          priorities_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          autonomous_rules_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          quality_standard_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          sensitivity text NOT NULL DEFAULT 'private',
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id),
          CONSTRAINT brain_charters_owner_json_object_check
            CHECK (jsonb_typeof(owner_json) = 'object'),
          CONSTRAINT brain_charters_memory_philosophy_json_object_check
            CHECK (jsonb_typeof(memory_philosophy_json) = 'object'),
          CONSTRAINT brain_charters_life_domains_json_object_check
            CHECK (jsonb_typeof(life_domains_json) = 'object'),
          CONSTRAINT brain_charters_active_projects_json_array_check
            CHECK (jsonb_typeof(active_projects_json) = 'array'),
          CONSTRAINT brain_charters_communication_style_json_object_check
            CHECK (jsonb_typeof(communication_style_json) = 'object'),
          CONSTRAINT brain_charters_priorities_json_object_check
            CHECK (jsonb_typeof(priorities_json) = 'object'),
          CONSTRAINT brain_charters_autonomous_rules_json_array_check
            CHECK (jsonb_typeof(autonomous_rules_json) = 'array'),
          CONSTRAINT brain_charters_quality_standard_json_array_check
            CHECK (jsonb_typeof(quality_standard_json) = 'array'),
          CONSTRAINT brain_charters_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL}))
        );

        CREATE INDEX sources_user_connector_captured_idx
          ON sources (user_id, connector_name, captured_at DESC, id DESC);
        CREATE INDEX source_chunks_source_index_idx
          ON source_chunks (source_id, chunk_index);
        CREATE INDEX provenance_links_target_idx
          ON provenance_links (user_id, target_type, target_id, created_at DESC, id DESC);
        CREATE INDEX graph_edges_user_edge_idx
          ON graph_edges (user_id, edge_type, created_at DESC, id DESC);
        CREATE INDEX projects_user_status_updated_idx
          ON projects (user_id, status, updated_at DESC, id DESC);
        CREATE INDEX people_user_name_idx
          ON people (user_id, name);
        CREATE INDEX beliefs_user_status_seen_idx
          ON beliefs (user_id, status, first_seen_at DESC, id DESC);
        CREATE INDEX generated_artifacts_user_type_status_idx
          ON generated_artifacts (user_id, artifact_type, status, created_at DESC, id DESC);
        CREATE INDEX task_queue_user_status_scheduled_idx
          ON task_queue (user_id, status, scheduled_for ASC NULLS LAST, created_at DESC, id DESC);
        CREATE INDEX event_log_user_type_occurred_idx
          ON event_log (user_id, event_type, occurred_at DESC, id DESC);
        """

_UPGRADE_OPEN_LOOP_COMPAT_STATEMENTS = (
    """
        ALTER TABLE open_loops
          ADD COLUMN description text NULL,
          ADD COLUMN priority text NOT NULL DEFAULT 'normal',
          ADD COLUMN project_id uuid NULL,
          ADD COLUMN person_id uuid NULL,
          ADD COLUMN source_id uuid NULL,
          ADD COLUMN closed_at timestamptz NULL,
          ADD COLUMN domain text NOT NULL DEFAULT 'unknown',
          ADD COLUMN sensitivity text NOT NULL DEFAULT 'unknown',
          ADD COLUMN metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    f"""
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_priority_check
          CHECK (priority IN ({_OPEN_LOOP_PRIORITIES_SQL}))
        """,
    f"""
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_domain_check
          CHECK (domain IN ({_DOMAINS_SQL}))
        """,
    f"""
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_sensitivity_check
          CHECK (sensitivity IN ({_SENSITIVITY_SQL}))
        """,
    """
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_metadata_json_object_check
          CHECK (jsonb_typeof(metadata_json) = 'object')
        """,
    """
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_project_fkey
          FOREIGN KEY (project_id, user_id)
          REFERENCES projects(id, user_id)
          ON DELETE SET NULL
        """,
    """
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_person_fkey
          FOREIGN KEY (person_id, user_id)
          REFERENCES people(id, user_id)
          ON DELETE SET NULL
        """,
    """
        ALTER TABLE open_loops
          ADD CONSTRAINT open_loops_source_fkey
          FOREIGN KEY (source_id, user_id)
          REFERENCES sources(id, user_id)
          ON DELETE SET NULL
        """,
    """
        CREATE INDEX open_loops_user_project_status_idx
          ON open_loops (user_id, project_id, status, due_at ASC NULLS LAST, id DESC)
        """,
)

_UPGRADE_TRIGGER_STATEMENTS = (
    """
        CREATE TRIGGER event_log_append_only
        BEFORE UPDATE OR DELETE ON event_log
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_event_log_mutation();
        """,
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON sources TO alicebot_app",
    "GRANT SELECT, INSERT ON source_chunks TO alicebot_app",
    "GRANT SELECT, INSERT ON provenance_links TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON graph_edges TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON projects TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON people TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON beliefs TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON generated_artifacts TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON task_queue TO alicebot_app",
    "GRANT SELECT, INSERT ON event_log TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON brain_charters TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY sources_is_owner ON sources
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY source_chunks_is_owner ON source_chunks
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY provenance_links_is_owner ON provenance_links
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY graph_edges_is_owner ON graph_edges
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY projects_is_owner ON projects
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY people_is_owner ON people
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY beliefs_is_owner ON beliefs
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY generated_artifacts_is_owner ON generated_artifacts
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY task_queue_is_owner ON task_queue
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY event_log_read_own ON event_log
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY event_log_insert_own ON event_log
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY brain_charters_is_owner ON brain_charters
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_OPEN_LOOP_COMPAT_STATEMENTS = (
    "DROP INDEX IF EXISTS open_loops_user_project_status_idx",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_source_fkey",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_person_fkey",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_project_fkey",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_metadata_json_object_check",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_sensitivity_check",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_domain_check",
    "ALTER TABLE open_loops DROP CONSTRAINT IF EXISTS open_loops_priority_check",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS metadata_json",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS sensitivity",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS domain",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS closed_at",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS source_id",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS person_id",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS project_id",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS priority",
    "ALTER TABLE open_loops DROP COLUMN IF EXISTS description",
)

_DOWNGRADE_TABLE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS event_log_append_only ON event_log",
    "DROP TABLE IF EXISTS brain_charters",
    "DROP TABLE IF EXISTS event_log",
    "DROP TABLE IF EXISTS task_queue",
    "DROP TABLE IF EXISTS generated_artifacts",
    "DROP TABLE IF EXISTS beliefs",
    "DROP TABLE IF EXISTS people",
    "DROP TABLE IF EXISTS projects",
    "DROP TABLE IF EXISTS graph_edges",
    "DROP TABLE IF EXISTS provenance_links",
    "DROP TABLE IF EXISTS source_chunks",
    "DROP TABLE IF EXISTS sources",
    "DROP FUNCTION IF EXISTS app.reject_event_log_mutation()",
)

_DOWNGRADE_REVISION_COMPAT_STATEMENTS = (
    "ALTER TABLE memory_revisions DROP CONSTRAINT IF EXISTS memory_revisions_metadata_json_object_check",
    "ALTER TABLE memory_revisions DROP CONSTRAINT IF EXISTS memory_revisions_revision_number_positive_check",
    "ALTER TABLE memory_revisions DROP CONSTRAINT IF EXISTS memory_revisions_revision_type_check",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS metadata_json",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS actor_id",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS actor_type",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS reason",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS text_after",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS text_before",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS revision_type",
    "ALTER TABLE memory_revisions DROP COLUMN IF EXISTS revision_number",
)

_DOWNGRADE_MEMORY_COMPAT_STATEMENTS = (
    "DROP INDEX IF EXISTS memories_user_domain_sensitivity_updated_idx",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_seen_range_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_metadata_json_object_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_sensitivity_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_domain_check",
    "ALTER TABLE memories DROP COLUMN IF EXISTS metadata_json",
    "ALTER TABLE memories DROP COLUMN IF EXISTS last_reviewed_at",
    "ALTER TABLE memories DROP COLUMN IF EXISTS last_seen_at",
    "ALTER TABLE memories DROP COLUMN IF EXISTS first_seen_at",
    "ALTER TABLE memories DROP COLUMN IF EXISTS sensitivity",
    "ALTER TABLE memories DROP COLUMN IF EXISTS domain",
    "ALTER TABLE memories DROP COLUMN IF EXISTS summary",
    "ALTER TABLE memories DROP COLUMN IF EXISTS canonical_text",
    "ALTER TABLE memories DROP COLUMN IF EXISTS title",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_memory_type_check",
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_memory_type_check
          CHECK (memory_type IN ({", ".join(f"'{value}'" for value in LEGACY_MEMORY_TYPES)}))
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _NEW_RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    _execute_statements(_UPGRADE_MEMORY_COMPAT_STATEMENTS)
    _execute_statements(_UPGRADE_REVISION_COMPAT_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_OPEN_LOOP_COMPAT_STATEMENTS)
    _execute_statements(_UPGRADE_TRIGGER_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_OPEN_LOOP_COMPAT_STATEMENTS)
    _execute_statements(_DOWNGRADE_TABLE_STATEMENTS)
    _execute_statements(_DOWNGRADE_REVISION_COMPAT_STATEMENTS)
    _execute_statements(_DOWNGRADE_MEMORY_COMPAT_STATEMENTS)
