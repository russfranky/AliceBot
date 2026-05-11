"""Add vNext model-backed artifact quality ratings."""

from __future__ import annotations

from alembic import op


revision = "20260511_0069"
down_revision = "20260511_0068"
branch_labels = None
depends_on = None


VERBOSITY_LABELS = ("too_shallow", "right_sized", "too_verbose", "unknown")
_VERBOSITY_LABELS_SQL = ", ".join(f"'{value}'" for value in VERBOSITY_LABELS)
_RATING_CHECK = "CHECK (%(column)s IS NULL OR (%(column)s >= 1 AND %(column)s <= 5))"

_UPGRADE_SCHEMA = f"""
        CREATE TABLE artifact_quality_ratings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          artifact_id uuid NOT NULL,
          reviewer_id text NULL,
          usefulness integer NULL,
          accuracy integer NULL,
          source_grounding integer NULL,
          novel_connections integer NULL,
          actionability integer NULL,
          hallucination_risk integer NULL,
          verbosity text NOT NULL DEFAULT 'unknown',
          missed_context text NULL,
          comments text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT artifact_quality_ratings_artifact_fkey
            FOREIGN KEY (artifact_id, user_id)
            REFERENCES generated_artifacts(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT artifact_quality_ratings_usefulness_check {_RATING_CHECK % {"column": "usefulness"}},
          CONSTRAINT artifact_quality_ratings_accuracy_check {_RATING_CHECK % {"column": "accuracy"}},
          CONSTRAINT artifact_quality_ratings_source_grounding_check {_RATING_CHECK % {"column": "source_grounding"}},
          CONSTRAINT artifact_quality_ratings_novel_connections_check {_RATING_CHECK % {"column": "novel_connections"}},
          CONSTRAINT artifact_quality_ratings_actionability_check {_RATING_CHECK % {"column": "actionability"}},
          CONSTRAINT artifact_quality_ratings_hallucination_risk_check {_RATING_CHECK % {"column": "hallucination_risk"}},
          CONSTRAINT artifact_quality_ratings_verbosity_check
            CHECK (verbosity IN ({_VERBOSITY_LABELS_SQL})),
          CONSTRAINT artifact_quality_ratings_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE INDEX artifact_quality_ratings_user_artifact_created_idx
          ON artifact_quality_ratings (user_id, artifact_id, created_at DESC, id DESC);
        CREATE INDEX artifact_quality_ratings_user_created_idx
          ON artifact_quality_ratings (user_id, created_at DESC, id DESC);
        """

_GRANTS = (
    "GRANT SELECT, INSERT ON artifact_quality_ratings TO alicebot_app",
)

_POLICIES = """
        CREATE POLICY artifact_quality_ratings_is_owner ON artifact_quality_ratings
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE = (
    "DROP TABLE IF EXISTS artifact_quality_ratings",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA)
    _execute_statements(_GRANTS)
    op.execute("ALTER TABLE artifact_quality_ratings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE artifact_quality_ratings FORCE ROW LEVEL SECURITY")
    op.execute(_POLICIES)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE)
