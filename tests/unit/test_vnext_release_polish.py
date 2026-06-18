from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_vnext_public_preview_docs_cover_release_polish_acceptance() -> None:
    readme = _read("README.md")
    overview = _read("docs/vnext/README.md")
    quickstart = _read("docs/vnext/quickstart.md")
    architecture = _read("docs/vnext/architecture.md")
    security = _read("docs/vnext/security-privacy.md")
    contributor = _read("docs/vnext/contributor-guide.md")
    checklist = _read("docs/release/vnext-public-release-checklist.md")

    for marker in (
        "Alice Core",
        "Alice Brain",
        "Alice Agent Memory",
        "docs/vnext/quickstart.md",
        "docs/release/vnext-public-release-checklist.md",
    ):
        assert marker in readme

    assert "first daily brief in under 20 minutes" in overview
    assert "./scripts/dev_up.sh" in quickstart
    assert "daily-brief" in quickstart
    assert "Connector Boundary" in architecture
    assert "Prompt-injection content from sources is data, not policy." in security
    assert "Use synthetic fixtures only." in contributor
    assert "No secrets, private exports, real personal data" in checklist


def test_vnext_demo_dataset_is_synthetic_and_connector_ready() -> None:
    payload = json.loads(_read("fixtures/vnext/demo_dataset.json"))
    serialized = json.dumps(payload, sort_keys=True).casefold()

    assert payload["dataset_id"] == "alice-vnext-demo-2026-05"
    assert "browser_clipper" in payload["connector_payloads"]
    assert "telegram" in payload["connector_payloads"]
    assert payload["agent_outputs"][0]["agent_id"] == "openclaw"
    assert payload["policy_boundary_checks"][0]["expected_decision"] == "blocked"
    assert "example.test" in serialized

    forbidden_markers = (
        "sk-",
        "xoxb-",
        "ghp_",
        "password",
        "access_token",
        "refresh_token",
        "@gmail.com",
    )
    for marker in forbidden_markers:
        assert marker not in serialized


def test_public_alpha_packaging_docs_and_commands_are_discoverable() -> None:
    readme = _read("README.md")
    alpha_readme = _read("docs/alpha/README.md")
    quickstart = _read("docs/alpha/quickstart.md")
    first_run = _read("docs/alpha/first-run.md")
    agent_integration = _read("docs/alpha/agent-integration.md")
    mcp_tools = _read("docs/alpha/mcp-tools.md")
    hermes_skill = _read("docs/alpha/hermes-skill.md")
    openclaw_skill = _read("docs/alpha/openclaw-skill.md")
    custom_agent = _read("docs/alpha/custom-agent-guide.md")
    context_recipes = _read("docs/alpha/context-pack-recipes.md")
    memory_recipes = _read("docs/alpha/memory-proposal-recipes.md")
    output_examples = _read("docs/alpha/agent-output-ingestion.md")
    limitations = _read("docs/alpha/known-limitations.md")
    security = _read("docs/alpha/security-and-privacy.md")
    onboarding = _read("docs/alpha/design-partner-onboarding.md")
    troubleshooting = _read("docs/alpha/troubleshooting.md")
    release_notes = _read("docs/alpha/release-notes.md")
    cto_summary = _read("docs/vnext-public-alpha-packaging-cto-summary.md")
    hermes_copy = _read("agent-skills/hermes/alice-memory-skill.md")
    openclaw_copy = _read("agent-skills/openclaw/alice-project-memory-skill.md")
    makefile = _read("Makefile")
    gitignore = _read(".gitignore")

    for marker in (
        "Alice is a local-first memory and continuity layer for humans and agents.",
        "make setup",
        "alicebot vnext alpha check",
        "alicebot vnext smoke agent-integration-pack",
        "docs/alpha/agent-integration.md",
    ):
        assert marker in readme

    for path_marker in (
        "quickstart.md",
        "first-run.md",
        "agent-integration.md",
        "mcp-tools.md",
        "known-limitations.md",
        "security-and-privacy.md",
    ):
        assert path_marker in alpha_readme

    assert "make setup" in quickstart
    assert "Run doctor" in first_run
    assert "permission_profile" in agent_integration
    assert "alice_vnext_ingest_agent_output" in mcp_tools
    assert "Never directly mutate trusted memory." in hermes_skill
    assert "project_scoped_agent" in openclaw_skill
    assert "Review queues" in custom_agent
    assert context_recipes.count("## ") >= 11
    assert "Do not propose memory for" in memory_recipes
    assert "OpenClaw Sprint Summary" in output_examples
    assert "no hosted cloud" in limitations
    assert "trusted memory is not auto-promoted" in security
    assert "failing command output" in onboarding
    assert "Unable to load live workspace: Load failed" in troubleshooting
    assert "alicebot vnext smoke local-cors" in quickstart
    assert "not hosted SaaS" in release_notes
    assert "Agent Skills v1 Hardening" in cto_summary
    assert "trusted_local_agent" in hermes_copy
    assert "project_scoped_agent" in openclaw_copy
    assert "alpha-check" in makefile


def test_headless_ubuntu_packaging_is_discoverable_and_safe_by_default() -> None:
    readme = _read("README.md")
    alpha_readme = _read("docs/alpha/README.md")
    install_doc = _read("docs/alpha/headless-ubuntu-install.md")
    hermes_doc = _read("docs/alpha/hermes-dogfood-ubuntu.md")
    release_notes = _read("docs/release/v0.6.0-alpha-rc.2-release-notes.md")
    cto_summary = _read("docs/vnext-headless-ubuntu-cto-summary.md")
    installer = _read("scripts/install-ubuntu.sh")
    uninstaller = _read("scripts/uninstall-ubuntu.sh")
    env_template = _read("packaging/ubuntu/alicebot.env.example")
    web_env_template = _read("apps/web/.env.local.example")
    api_service = _read("packaging/systemd/alice-api.service")
    web_service = _read("packaging/systemd/alice-web.service")
    scheduler_service = _read("packaging/systemd/alice-scheduler.service")
    cli = _read("apps/api/src/alicebot_api/cli.py")

    assert "docs/alpha/headless-ubuntu-install.md" in readme
    assert "headless-ubuntu-install.md" in alpha_readme
    assert "ssh -L 3000:127.0.0.1:3000" in install_doc
    assert "Do not expose `/vnext`" in install_doc
    assert "alicebot vnext alpha check --headless" in install_doc
    assert "agent_id: hermes" in hermes_doc
    assert "trusted_local_agent" in hermes_doc
    assert "policy-boundary test" in hermes_doc
    assert "v0.6.0-alpha-rc.2" in release_notes
    assert "not latest" in release_notes
    assert "Headless Ubuntu" in cto_summary

    for marker in (
        "--tag",
        "--branch",
        "--install-dir",
        "--skip-postgres-install",
        "--non-interactive",
        "--install-systemd",
    ):
        assert marker in installer

    assert "--remove-repo" in uninstaller
    assert "--drop-database" in uninstaller
    assert "Type DELETE to continue" in uninstaller

    for marker in (
        "DATABASE_URL=",
        "APP_ENV=development",
        "ALICE_API_HOST=127.0.0.1",
        "ALICE_WEB_HOST=127.0.0.1",
        "ALICE_SECRET_PROVIDER=",
        "CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000",
        "NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000",
        'ALICE_MCP_COMMAND="',
    ):
        assert marker in env_template
    assert "NEXT_PUBLIC_ALICEBOT_USER_ID=" in web_env_template

    for service in (api_service, web_service, scheduler_service):
        assert "User=__ALICE_USER__" in service
        assert "Restart=on-failure" in service
        assert "EnvironmentFile=__ALICE_ENV_FILE__" in service
        assert "0.0.0.0" not in service
        assert "%h/.alicebot" not in service

    assert "127.0.0.1" in api_service
    assert "127.0.0.1" in web_service
    assert "127.0.0.1" in scheduler_service
    assert "__ALICE_RUNTIME_DIR__" in api_service
    assert "__ALICE_RUNTIME_DIR__/vnext-scheduler" in scheduler_service
    assert "headless-ubuntu" in cli
    assert "--headless" in cli


def test_installation_issue_regressions_are_guarded() -> None:
    makefile = _read("Makefile")
    gitignore = _read(".gitignore")
    web_package = json.loads(_read("apps/web/package.json"))
    installer = _read("scripts/install-ubuntu.sh")
    dev_up = _read("scripts/dev_up.sh")
    api_dev = _read("scripts/api_dev.sh")
    lite_up = _read("scripts/alice_lite_up.sh")
    migrate = _read("scripts/migrate.sh")
    compose = _read("docker-compose.yml")
    compose_lite = _read("docker-compose.lite.yml")
    postgres_init = _read("infra/postgres/init/001_roles.sh")
    install_doc = _read("docs/alpha/headless-ubuntu-install.md")
    troubleshooting = _read("docs/alpha/troubleshooting.md")
    web_env = _read("apps/web/.env.local.example")

    assert "test -f .env || cp .env.example .env" in makefile
    assert "test -f .env.lite || cp .env.lite.example .env.lite" in makefile
    assert "test -f $(WEB_DIR)/.env.local || cp $(WEB_DIR)/.env.local.example $(WEB_DIR)/.env.local" in makefile
    assert "./scripts/validate_env.sh .env .env.lite" in makefile
    assert "./scripts/pnpm_web_install.sh" in makefile
    assert ".env.lite" in gitignore
    assert "apps/web/.env.local" in gitignore

    assert web_package["packageManager"].startswith("pnpm@10.")
    assert web_package["scripts"]["dev:clean"] == "rm -rf .next && next dev"
    assert set(web_package["pnpm"]["onlyBuiltDependencies"]) >= {"esbuild", "sharp", "unrs-resolver"}
    assert "NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000" in web_env

    assert "PNPM_VERSION" in installer
    assert "pnpm@latest" not in installer
    assert "install_pnpm_from_npm" in installer
    assert "command -v npm" in installer
    assert '"${npm_bin}" install -g "pnpm@${PNPM_VERSION}"' in installer
    assert 'sudo "${npm_bin}" install -g "pnpm@${PNPM_VERSION}"' in installer
    assert "postgresql-${pg_major}-pgvector" in installer
    assert "CREATE EXTENSION IF NOT EXISTS vector" in installer
    assert '"${ALICE_RUNTIME_DIR}/vnext-scheduler"' in installer
    assert "run_in_install_dir" in installer
    assert "-c apps/api/alembic.ini" in installer
    assert "write_lite_env_if_missing" in installer
    assert "write_web_env_if_missing" in installer
    assert "validate_env_files" in installer

    for script in (dev_up, api_dev, lite_up, migrate):
        assert "scripts/validate_env.sh" in script
        assert "Missing ${PYTHON_BIN}. Run 'make setup'" in script

    for compose_file in (compose, compose_lite):
        assert "ALICEBOT_COMPOSE_POSTGRES_PASSWORD" in compose_file
        assert "ALICEBOT_COMPOSE_APP_PASSWORD" in compose_file

    assert "ALICEBOT_APP_PASSWORD" in postgres_init
    assert "ALTER ROLE" in postgres_init
    assert 'ALICE_MCP_COMMAND="' in install_doc
    assert "postgresql-16-pgvector" in install_doc
    assert "CREATE EXTENSION IF NOT EXISTS vector" in install_doc
    assert "`~/.alicebot`" in install_doc
    assert "CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000" in install_doc
    assert "docker compose down -v" in install_doc
    assert "Cannot find module './316.js'" in troubleshooting
    assert "pnpm --dir apps/web dev:clean" in troubleshooting


def test_env_validator_rejects_unquoted_values_with_spaces(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                "DATABASE_URL=postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot",
                "DATABASE_ADMIN_URL=postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot",
                "ALICE_MCP_COMMAND=/tmp/alicebot/.venv/bin/python -m alicebot_api.mcp_server",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(ROOT / "scripts" / "validate_env.sh"), str(env_file)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "quote ALICE_MCP_COMMAND" in result.stderr

    env_file.write_text(
        env_file.read_text(encoding="utf-8").replace(
            "ALICE_MCP_COMMAND=/tmp/alicebot/.venv/bin/python -m alicebot_api.mcp_server",
            'ALICE_MCP_COMMAND="/tmp/alicebot/.venv/bin/python -m alicebot_api.mcp_server"',
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(ROOT / "scripts" / "validate_env.sh"), str(env_file)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0

    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=production",
                "DATABASE_URL=postgresql://alicebot_app:custom@localhost:5432/alicebot",
                "DATABASE_ADMIN_URL=postgresql://alicebot_admin:custom@localhost:5432/alicebot",
                'ALICE_MCP_COMMAND="/tmp/alicebot/.venv/bin/python -m alicebot_api.mcp_server"',
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(ROOT / "scripts" / "validate_env.sh"), str(env_file)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "TELEGRAM_WEBHOOK_SECRET is required when APP_ENV=production" in result.stderr
