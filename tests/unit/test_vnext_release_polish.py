from __future__ import annotations

import json
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
    assert "docker compose up -d" in quickstart
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
    release_notes = _read("docs/alpha/release-notes.md")
    cto_summary = _read("docs/vnext-public-alpha-packaging-cto-summary.md")
    hermes_copy = _read("agent-skills/hermes/alice-memory-skill.md")
    openclaw_copy = _read("agent-skills/openclaw/alice-project-memory-skill.md")
    makefile = _read("Makefile")

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
    assert "not hosted SaaS" in release_notes
    assert "Agent Skills v1 Hardening" in cto_summary
    assert "trusted_local_agent" in hermes_copy
    assert "project_scoped_agent" in openclaw_copy
    assert "alpha-check" in makefile
