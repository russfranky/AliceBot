from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dev_up_waits_for_postgres_and_role_bootstrap() -> None:
    script = (REPO_ROOT / "scripts" / "dev_up.sh").read_text()

    assert "Timed out waiting for Postgres readiness and alicebot_app bootstrap" in script
    assert "SELECT 1 FROM pg_roles WHERE rolname = %s" in script


def test_runtime_role_init_only_grants_connect_on_alicebot_database() -> None:
    init_sql = (REPO_ROOT / "infra" / "postgres" / "init" / "001_roles.sh").read_text()

    assert "GRANT CONNECT ON DATABASE %I TO %I" in init_sql
    assert "current_database()" in init_sql
    assert "GRANT CONNECT ON DATABASE postgres TO alicebot_app;" not in init_sql


def test_archive_maintenance_workflow_uses_current_postgres_bootstrap() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "archive-maintenance.yml").read_text()

    assert "infra/postgres/init/001_roles.sh" in workflow
    assert "infra/postgres/init/001_roles.sql" not in workflow
    assert "DATABASE_ADMIN_URL: postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot" in workflow
    assert "DATABASE_URL: postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot" in workflow
