from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260511_0069_model_backed_intelligence_quality"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_quality_rating_table_grants_and_rls(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        module._UPGRADE_SCHEMA,
        *module._GRANTS,
        "ALTER TABLE artifact_quality_ratings ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE artifact_quality_ratings FORCE ROW LEVEL SECURITY",
        module._POLICIES,
    ]


def test_quality_rating_schema_tracks_required_human_eval_fields() -> None:
    module = load_migration_module()
    schema = module._UPGRADE_SCHEMA

    assert "CREATE TABLE artifact_quality_ratings" in schema
    assert "REFERENCES generated_artifacts(id, user_id)" in schema
    for column in (
        "usefulness",
        "accuracy",
        "source_grounding",
        "novel_connections",
        "actionability",
        "hallucination_risk",
        "verbosity",
        "missed_context",
        "comments",
    ):
        assert column in schema
    for value in module.VERBOSITY_LABELS:
        assert f"'{value}'" in schema


def test_downgrade_drops_quality_rating_table(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE)
