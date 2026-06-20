#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ControlDocTruthRule:
    relative_path: str
    required_markers: tuple[str, ...]


CONTROL_DOC_TRUTH_RULES: tuple[ControlDocTruthRule, ...] = (
    ControlDocTruthRule(
        relative_path="README.md",
        required_markers=(
            "`v0.5.1` is the current **pre-1.0 public release**.",
            "`v0.5.1-vnext-preview`",
            "## Release Boundary (`v0.5.1`)",
            "Phase 13 adoption surfaces:",
            "Historical planning/control artifacts remain available in:",
            "Phase 14 platform surfaces:",
        ),
    ),
    ControlDocTruthRule(
        relative_path="ROADMAP.md",
        required_markers=(
            "`v0.5.1`: released",
            "Phase 14 is shipped.",
            "Alice vNext public preview release gate is active for `v0.5.1-vnext-preview`.",
        ),
    ),
    ControlDocTruthRule(
        relative_path=".ai/active/SPRINT_PACKET.md",
        required_markers=(
            "Alice vNext Public Preview Release Gate",
            "`v0.5.1-vnext-preview` is the vNext public-preview tag target.",
            "release-gate",
        ),
    ),
    ControlDocTruthRule(
        relative_path="RULES.md",
        required_markers=(
            "While `v0.5.1-vnext-preview` is the active release gate",
            "Continuity semantics must not fork by provider.",
        ),
    ),
    ControlDocTruthRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        required_markers=(
            "`v0.5.1` remains the latest stable public release tag.",
            "Phase 14 is shipped.",
            "Alice vNext public preview release gate is active.",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/archive/planning/2026-04-08-context-compaction/README.md",
        required_markers=("This folder preserves superseded planning and control material removed from the live docs during Context Compaction 01.",),
    ),
)

DISALLOWED_MARKERS: tuple[str, ...] = (
    "through Phase 3 Sprint 9",
    "Active Sprint focus is Phase 4 Sprint 14",
    "Gate ownership is canonicalized to Phase 4 runner scripts",
    "Gate ownership is canonicalized to Phase 4 runner script names",
    "Legacy Compatibility Marker",
    "Legacy Compatibility Markers",
    "Phase 9 Sprint Sequence",
    "No active build sprint is open.",
    "Phase 10 planning docs are not defined yet.",
    "Keep this file as an idle-state pointer, not as a fake active sprint.",
)


def run_control_doc_truth_check(
    *,
    root_dir: Path = ROOT_DIR,
    rules: tuple[ControlDocTruthRule, ...] = CONTROL_DOC_TRUTH_RULES,
    disallowed_markers: tuple[str, ...] = DISALLOWED_MARKERS,
) -> list[str]:
    issues: list[str] = []
    for rule in rules:
        doc_path = root_dir / rule.relative_path
        if not doc_path.exists():
            issues.append(f"{rule.relative_path}: missing file")
            continue

        text = doc_path.read_text(encoding="utf-8")
        for marker in rule.required_markers:
            if marker not in text:
                issues.append(f"{rule.relative_path}: missing required marker '{marker}'")

        lowered_text = text.casefold()
        for marker in disallowed_markers:
            if marker.casefold() in lowered_text:
                issues.append(f"{rule.relative_path}: contains disallowed marker '{marker}'")

    return issues


def main() -> int:
    issues = run_control_doc_truth_check()
    if issues:
        print("Control-doc truth check: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Control-doc truth check: PASS")
    for rule in CONTROL_DOC_TRUTH_RULES:
        print(f" - verified: {rule.relative_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
