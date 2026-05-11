from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260510_0067_vnext_memory_kernel_schema"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    expected_rls = [
        statement
        for table_name in module._NEW_RLS_TABLES
        for statement in (
            f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
            f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        )
    ]
    assert executed == [
        *module._UPGRADE_BOOTSTRAP_STATEMENTS,
        *module._UPGRADE_MEMORY_COMPAT_STATEMENTS,
        *module._UPGRADE_REVISION_COMPAT_STATEMENTS,
        module._UPGRADE_SCHEMA_STATEMENT,
        *module._UPGRADE_OPEN_LOOP_COMPAT_STATEMENTS,
        *module._UPGRADE_TRIGGER_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        *expected_rls,
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        *module._DOWNGRADE_OPEN_LOOP_COMPAT_STATEMENTS,
        *module._DOWNGRADE_TABLE_STATEMENTS,
        *module._DOWNGRADE_REVISION_COMPAT_STATEMENTS,
        *module._DOWNGRADE_MEMORY_COMPAT_STATEMENTS,
    ]


def test_vnext_schema_creates_required_kernel_tables() -> None:
    module = load_migration_module()
    schema_sql = module._UPGRADE_SCHEMA_STATEMENT

    for table_name in (
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
    ):
        assert f"CREATE TABLE {table_name}" in schema_sql


def test_vnext_schema_tracks_domain_sensitivity_and_policy_enums() -> None:
    module = load_migration_module()
    joined_sql = "\n".join(
        (
            *module._UPGRADE_MEMORY_COMPAT_STATEMENTS,
            module._UPGRADE_SCHEMA_STATEMENT,
            *module._UPGRADE_OPEN_LOOP_COMPAT_STATEMENTS,
        )
    )

    for value in module.DOMAINS:
        assert f"'{value}'" in joined_sql
    for value in module.SENSITIVITY_LEVELS:
        assert f"'{value}'" in joined_sql
    for value in ("sources_domain_check", "memories_domain_check", "task_queue_domain_check"):
        assert value in joined_sql
    for value in (
        "generated_artifacts_sensitivity_check",
        "open_loops_sensitivity_check",
        "brain_charters_sensitivity_check",
    ):
        assert value in joined_sql


def test_vnext_schema_keeps_legacy_memory_types_while_adding_vnext_types() -> None:
    module = load_migration_module()
    memory_sql = "\n".join(module._UPGRADE_MEMORY_COMPAT_STATEMENTS)

    for value in module.LEGACY_MEMORY_TYPES:
        assert f"'{value}'" in memory_sql
    for value in module.VNEXT_MEMORY_TYPES:
        assert f"'{value}'" in memory_sql
    for column_name in (
        "canonical_text",
        "first_seen_at",
        "last_seen_at",
        "last_reviewed_at",
        "metadata_json",
    ):
        assert column_name in memory_sql


def test_vnext_event_log_is_append_only_and_rls_scoped() -> None:
    module = load_migration_module()

    assert "CREATE TRIGGER event_log_append_only" in "\n".join(module._UPGRADE_TRIGGER_STATEMENTS)
    assert "event_log_read_own" in module._UPGRADE_POLICY_STATEMENT
    assert "event_log_insert_own" in module._UPGRADE_POLICY_STATEMENT
    assert "GRANT SELECT, INSERT ON event_log TO alicebot_app" in module._UPGRADE_GRANT_STATEMENTS
