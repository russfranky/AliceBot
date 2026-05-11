# vNext Contributor Guide

This guide covers contributions to the Alice vNext preview. General repository contribution rules remain in `CONTRIBUTING.md`.

## Contribution Scope

Good first vNext contributions:

- tests for existing deterministic workflows
- docs corrections that match current commands
- fixture-only connector payload examples
- small UI review-state improvements under `/vnext`
- eval cases that strengthen privacy, provenance, or prompt-injection coverage

Avoid in preview PRs unless a maintainer explicitly scopes it:

- live connector OAuth or external polling
- automatic memory promotion
- destructive schema rewrites
- cloud model calls enabled by default
- broad UI redesigns outside the existing vNext workspace

## Required Checks

Run focused checks for touched surfaces, then the release gate if the change is user-facing:

```bash
./.venv/bin/python -m pytest tests/unit -q
pnpm --dir apps/web test
pnpm --dir apps/web build
python3 scripts/check_control_doc_truth.py
git diff --check
```

For connector changes, also run:

```bash
./.venv/bin/python -m pytest tests/unit/test_vnext_connectors.py -q
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["vnext", "connectors", "list"]))'
```

For eval changes, also run:

```bash
./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'
```

## Privacy Rules

- Use synthetic fixtures only.
- Do not add real personal exports, chat histories, emails, calendars, screenshots, voice notes, or customer data.
- Use `example.test`, `example.com`, fake names, and generated identifiers.
- Preserve raw evidence in fixtures only when the fixture itself is synthetic.

## Review Expectations

Every vNext PR should state:

- changed surface
- user-visible behavior
- domain/sensitivity impact
- provenance and event-log impact
- verification commands
- known limitations
