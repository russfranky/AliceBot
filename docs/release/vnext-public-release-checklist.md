# vNext Public Release Checklist

Use this checklist before cutting a vNext preview tag or public announcement. Do not publish until every required item is checked with current evidence.

## Docs

- [ ] README links the vNext preview, quickstart, architecture, security/privacy, demo script, and release checklist.
- [ ] Quickstart includes local install, Docker/local stack, first source capture, and first daily brief.
- [ ] Docs explain Alice Core vs Alice Brain vs Alice Agent Memory.
- [ ] Example `ALICE.md` is included and uses only synthetic content.
- [ ] Demo video script is current.
- [ ] Contributor guide explains how to work on vNext safely.
- [ ] Security/privacy docs describe connector boundaries and secret handling.

## Product Gate

- [ ] New user can install locally and generate a first daily brief in under 20 minutes.
- [ ] `/vnext` renders the fixture-backed workspace.
- [ ] Connector settings are visible in the UI.
- [ ] Connector payload ingestion preserves raw evidence, default domain/sensitivity, and cursor posture.
- [ ] Generated artifacts remain reviewable and are not auto-promoted to trusted memory.

## Verification

- [ ] `./.venv/bin/python -m pytest tests/unit -q`
- [ ] `pnpm --dir apps/web test`
- [ ] `pnpm --dir apps/web build`
- [ ] `python3 scripts/check_control_doc_truth.py`
- [ ] `git diff --check`
- [ ] `./.venv/bin/python -c 'from alicebot_api.cli import main; raise SystemExit(main(["eval", "run", "--suite", "all"]))'`

## Security and Privacy

- [ ] No secrets, private exports, real personal data, or production credentials are committed.
- [ ] Demo dataset contains only synthetic people, projects, notes, and connector payloads.
- [ ] Prompt-injection evals show zero tool writes.
- [ ] Critical privacy leakage evals show zero critical leaks.
- [ ] New connector/write paths have security review notes.

## Release Operations

- [ ] Changelog entry prepared.
- [ ] Tag plan prepared.
- [ ] Rollback path documented.
- [ ] Known limitations documented: no live connector OAuth/polling, no hosted SLA, no automatic memory promotion, no production scheduler.
- [ ] Release owner signs off.
