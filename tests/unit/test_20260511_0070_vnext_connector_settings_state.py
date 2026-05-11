from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260511_0070_vnext_connector_settings_state"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_connector_tables_grants_rls_policies_and_seed(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        module._UPGRADE_SCHEMA,
        *module._GRANTS,
        "ALTER TABLE connector_settings ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE connector_settings FORCE ROW LEVEL SECURITY",
        "ALTER TABLE connector_state ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE connector_state FORCE ROW LEVEL SECURITY",
        module._POLICIES,
        module._SEED_DEFAULTS,
    ]


def test_connector_settings_and_state_schema_tracks_hardening_contract() -> None:
    module = load_migration_module()
    schema = module._UPGRADE_SCHEMA
    seed = module._SEED_DEFAULTS

    assert "CREATE TABLE connector_settings" in schema
    assert "CREATE TABLE connector_state" in schema
    for column in (
        "connector_name",
        "enabled",
        "configured",
        "default_domain",
        "default_sensitivity",
        "sync_mode",
        "poll_interval_seconds",
        "secret_ref",
        "validation_errors_json",
        "metadata_json",
        "last_configured_at",
    ):
        assert column in schema
    for column in (
        "connector_id",
        "cursor_type",
        "cursor_value",
        "last_sync_at",
        "last_success_at",
        "last_failure_at",
        "last_error",
        "items_seen",
        "items_captured",
        "items_deduped",
        "items_failed",
        "average_processing_time_ms",
        "state_json",
    ):
        assert column in schema
    for connector_name, *_defaults in module.CORE_CONNECTOR_DEFAULTS:
        assert f"'{connector_name}'" in seed
    assert "ON CONFLICT (user_id, connector_name) DO NOTHING" in seed
    assert "ON CONFLICT (user_id, connector_name, cursor_type) DO NOTHING" in seed


def test_downgrade_drops_state_before_settings(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        "DROP TABLE IF EXISTS connector_state",
        "DROP TABLE IF EXISTS connector_settings",
    ]
