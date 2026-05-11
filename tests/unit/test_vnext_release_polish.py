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
