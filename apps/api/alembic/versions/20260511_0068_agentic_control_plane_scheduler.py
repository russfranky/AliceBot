"""Add vNext agent control plane and governed scheduler state."""

from __future__ import annotations

from alembic import op


revision = "20260511_0068"
down_revision = "20260510_0067"
branch_labels = None
depends_on = None


AGENT_TYPES = (
    "personal_assistant",
    "coding_agent",
    "research_agent",
    "workflow_agent",
    "unknown",
)

PERMISSION_PROFILES = (
    "read_only_agent",
    "project_scoped_agent",
    "trusted_local_agent",
    "memory_proposal_agent",
    "admin_agent",
)

WORKFLOW_TYPES = (
    "daily_brief",
    "weekly_synthesis",
    "connection_report",
    "contradiction_report",
    "open_loop_review",
    "project_update_scan",
)

RUN_STATUSES = ("started", "succeeded", "failed")
TRIGGER_TYPES = ("user", "agent", "scheduler", "system")

_AGENT_TYPES_SQL = ", ".join(f"'{value}'" for value in AGENT_TYPES)
_PERMISSION_PROFILES_SQL = ", ".join(f"'{value}'" for value in PERMISSION_PROFILES)
_WORKFLOW_TYPES_SQL = ", ".join(f"'{value}'" for value in WORKFLOW_TYPES)
_RUN_STATUSES_SQL = ", ".join(f"'{value}'" for value in RUN_STATUSES)
_TRIGGER_TYPES_SQL = ", ".join(f"'{value}'" for value in TRIGGER_TYPES)

_RLS_TABLES = ("agent_identities", "scheduler_workflows", "scheduler_runs")


_UPGRADE_SCHEMA = f"""
        CREATE TABLE agent_identities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          agent_id text NOT NULL,
          agent_type text NOT NULL DEFAULT 'unknown',
          permission_profile text NOT NULL DEFAULT 'read_only_agent',
          display_name text NULL,
          project_scope_json jsonb NOT NULL DEFAULT '[]'::jsonb,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, agent_id),
          CONSTRAINT agent_identities_agent_type_check
            CHECK (agent_type IN ({_AGENT_TYPES_SQL})),
          CONSTRAINT agent_identities_permission_profile_check
            CHECK (permission_profile IN ({_PERMISSION_PROFILES_SQL})),
          CONSTRAINT agent_identities_project_scope_json_array_check
            CHECK (jsonb_typeof(project_scope_json) = 'array'),
          CONSTRAINT agent_identities_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE scheduler_workflows (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          workflow_type text NOT NULL,
          enabled boolean NOT NULL DEFAULT false,
          paused boolean NOT NULL DEFAULT false,
          schedule_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          timezone text NOT NULL DEFAULT 'UTC',
          next_run_at timestamptz NULL,
          last_run_id uuid NULL,
          last_run_at timestamptz NULL,
          last_result text NULL,
          last_error text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          UNIQUE (user_id, workflow_type),
          CONSTRAINT scheduler_workflows_type_check
            CHECK (workflow_type IN ({_WORKFLOW_TYPES_SQL})),
          CONSTRAINT scheduler_workflows_schedule_json_object_check
            CHECK (jsonb_typeof(schedule_json) = 'object'),
          CONSTRAINT scheduler_workflows_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE scheduler_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          workflow_id uuid NULL,
          workflow_type text NOT NULL,
          status text NOT NULL DEFAULT 'started',
          triggered_by text NOT NULL DEFAULT 'user',
          trace_id text NOT NULL,
          started_at timestamptz NOT NULL DEFAULT now(),
          finished_at timestamptz NULL,
          artifact_id uuid NULL,
          error_message text NULL,
          policy_decision_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          agent_identity_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT scheduler_runs_workflow_fkey
            FOREIGN KEY (workflow_id, user_id)
            REFERENCES scheduler_workflows(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT scheduler_runs_artifact_fkey
            FOREIGN KEY (artifact_id, user_id)
            REFERENCES generated_artifacts(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT scheduler_runs_type_check
            CHECK (workflow_type IN ({_WORKFLOW_TYPES_SQL})),
          CONSTRAINT scheduler_runs_status_check
            CHECK (status IN ({_RUN_STATUSES_SQL})),
          CONSTRAINT scheduler_runs_triggered_by_check
            CHECK (triggered_by IN ({_TRIGGER_TYPES_SQL})),
          CONSTRAINT scheduler_runs_policy_decision_json_object_check
            CHECK (jsonb_typeof(policy_decision_json) = 'object'),
          CONSTRAINT scheduler_runs_agent_identity_json_object_check
            CHECK (jsonb_typeof(agent_identity_json) = 'object'),
          CONSTRAINT scheduler_runs_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        ALTER TABLE scheduler_workflows
          ADD CONSTRAINT scheduler_workflows_last_run_fkey
          FOREIGN KEY (last_run_id, user_id)
          REFERENCES scheduler_runs(id, user_id)
          ON DELETE SET NULL;

        CREATE INDEX agent_identities_user_profile_idx
          ON agent_identities (user_id, permission_profile, updated_at DESC, id DESC);
        CREATE INDEX scheduler_workflows_user_state_idx
          ON scheduler_workflows (user_id, enabled, paused, next_run_at ASC NULLS LAST, workflow_type);
        CREATE INDEX scheduler_runs_user_workflow_started_idx
          ON scheduler_runs (user_id, workflow_type, started_at DESC, id DESC);
        """

_GRANTS = (
    "GRANT SELECT, INSERT, UPDATE ON agent_identities TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON scheduler_workflows TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON scheduler_runs TO alicebot_app",
)

_POLICIES = """
        CREATE POLICY agent_identities_is_owner ON agent_identities
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY scheduler_workflows_is_owner ON scheduler_workflows
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY scheduler_runs_is_owner ON scheduler_runs
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE = (
    "DROP TABLE IF EXISTS scheduler_runs",
    "DROP TABLE IF EXISTS scheduler_workflows",
    "DROP TABLE IF EXISTS agent_identities",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA)
    _execute_statements(_GRANTS)
    _enable_row_level_security()
    op.execute(_POLICIES)


def downgrade() -> None:
    op.execute("ALTER TABLE scheduler_workflows DROP CONSTRAINT IF EXISTS scheduler_workflows_last_run_fkey")
    _execute_statements(_DOWNGRADE)
