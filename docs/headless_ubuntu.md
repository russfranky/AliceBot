
Alice vNext Sprint Prompt: Headless Ubuntu GitHub Installer + Hermes Dogfood Readiness

Sprint Objective

Prepare Alice vNext so it can be installed from GitHub on a headless Ubuntu server or VPS using command-line instructions.

The immediate use case is installing Alice on the same Ubuntu box where Hermes runs, then testing the real agent-first flow:

Hermes -> Alice MCP/API -> context packs / memory proposals / artifacts / open loops -> /vnext review cockpit

Alice already has public alpha packaging, make setup, make dev, make doctor, make vnext, make scheduler, make alpha-check, demo load/reset commands, MCP quickstart, Hermes/OpenClaw skill packs, custom-agent docs, and an agent-integration-pack smoke.

This sprint should make that package practically installable on Ubuntu from GitHub.

---

Target User

Technical alpha user running Alice on:

Ubuntu server
headless box
home lab machine
VPS
agent host running Hermes/OpenClaw/custom agents

The user may not have local desktop access to the machine.

The install path must work over SSH.

---

Product Principle

Alice remains:

agent-first
local-first
review-first
no-auto-promotion
secure-by-default

The default install must not expose /vnext, the API, MCP, or browser clipper endpoint publicly.

Recommended access should be through SSH tunnel first:

ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@server

Do not default-bind services to 0.0.0.0.

---

Core Build Requirements

1. GitHub-Installable Ubuntu Bootstrap Script

Add a script such as:

scripts/install-ubuntu.sh

It should support a clean Ubuntu install path.

The intended command should be something like:

curl -fsSL https://raw.githubusercontent.com/samrusani/AliceBot/v0.6.0-alpha-rc.1/scripts/install-ubuntu.sh -o install-alice.sh
bash install-alice.sh

For safety, docs should recommend downloading and inspecting before running:

curl -fsSL https://raw.githubusercontent.com/samrusani/AliceBot/v0.6.0-alpha-rc.1/scripts/install-ubuntu.sh -o install-alice.sh
less install-alice.sh
bash install-alice.sh

The script should:

detect Ubuntu version
check required packages
install system dependencies
install Python dependencies
install Node/pnpm dependencies
prepare Postgres or verify existing Postgres
clone or update AliceBot repo
checkout requested tag/branch
create local config/env template
run migrations
run doctor
run alpha check
print next-step commands

Support flags:

bash install-alice.sh --tag v0.6.0-alpha-rc.1
bash install-alice.sh --branch main
bash install-alice.sh --install-dir ~/alicebot
bash install-alice.sh --skip-postgres-install
bash install-alice.sh --non-interactive

Acceptance criteria:

Fresh Ubuntu machine can install from GitHub using documented CLI flow.
Installer can target a tag or branch.
Installer is idempotent enough to rerun safely.
Installer does not overwrite existing config without confirmation.
Installer prints clear next steps.
Installer exits non-zero on blocking failures.
Installer never prints secrets.

---

2. Headless Ubuntu Documentation

Add:

docs/alpha/headless-ubuntu-install.md

It should include:

prerequisites
one-command install
safe inspect-before-run install
manual install fallback
environment configuration
Postgres setup
starting services
systemd service setup
SSH tunnel setup
opening /vnext remotely
connecting Hermes
running alpha check
troubleshooting
uninstall/reset notes

Required sections:

Recommended secure access: SSH tunnel
Do not expose /vnext publicly by default
How to bind to localhost
How to verify API/web/scheduler are running
How to run doctor
How to run agent integration smoke
How to connect Hermes through MCP/API

Acceptance criteria:

A technical user can follow the doc over SSH.
Docs do not assume local GUI access.
Docs distinguish RC/dogfood install from public alpha release.
Docs clearly state security defaults.

---

3. Systemd Services for Ubuntu

Create or harden systemd units for:

alice-api
alice-web
alice-scheduler

Possible paths:

packaging/systemd/alice-api.service
packaging/systemd/alice-web.service
packaging/systemd/alice-scheduler.service

The installer should optionally install them.

Commands should be documented:

sudo systemctl enable --now alice-api
sudo systemctl enable --now alice-web
sudo systemctl enable --now alice-scheduler
systemctl status alice-api
systemctl status alice-web
systemctl status alice-scheduler
journalctl -u alice-api -f
journalctl -u alice-web -f
journalctl -u alice-scheduler -f

Requirements:

services run as non-root user
services load env from a local env file
services restart on failure
scheduler uses existing governed scheduler daemon/run-due path
logs are inspectable through journalctl

Acceptance criteria:

Services can be installed on Ubuntu.
Services start after reboot.
Scheduler daemon runs due workflows.
Doctor can detect service posture.
Logs do not expose secrets.

---

4. Local Configuration Layout

Standardize alpha local paths.

Recommended:

Repo:
~/alicebot
Config:
~/.config/alicebot/.env
Data:
~/.local/share/alicebot/
Logs:
~/.local/state/alicebot/logs/
Secrets:
~/.config/alicebot/secrets/

Docs and installer should agree on these paths.

The env template should include:

DATABASE_URL
ALICE_API_HOST=127.0.0.1
ALICE_API_PORT=8000
ALICE_WEB_HOST=127.0.0.1
ALICE_WEB_PORT=3000
ALICE_SECRET_PROVIDER
TELEGRAM_BOT_TOKEN ref example
MODEL_PROVIDER mode
MCP settings if applicable

Acceptance criteria:

Config path is documented.
Installer creates .env from template if missing.
Existing .env is preserved.
Secrets are referenced, not printed.

---

5. GitHub Release / RC Packaging

Prepare an internal RC tag release path.

Recommended immediate tag:

v0.6.0-alpha-rc.1

Do not mark as latest.

Prepare release notes explaining:

RC for Hermes dogfood testing
not public beta
headless Ubuntu install supported
agent integration pack included
known limitations
security defaults

Optional but useful GitHub release assets:

alicebot-v0.6.0-alpha-rc.1-source.tar.gz
SHA256SUMS
install-ubuntu.sh

Acceptance criteria:

GitHub tag can be checked out cleanly.
Installer can target the tag.
Release notes are accurate.
Stable v0.5.1 remains latest.
Alpha RC is marked pre-release if published.

---

6. Hermes Dogfood Setup Guide

Add:

docs/alpha/hermes-dogfood-ubuntu.md

This should explain how to connect Hermes running on the same Ubuntu box.

Include:

Alice API URL
Alice MCP server command/config
agent identity fields for Hermes
recommended permission profile
how Hermes should request context packs
how Hermes should submit outputs
how Hermes should propose memory
how to verify activity in /vnext
how to run the agent integration smoke

Hermes defaults:

agent_id: hermes
agent_type: personal_assistant
permission_profile: trusted_local_agent
project_scope: configurable

Acceptance criteria:

Guide includes copy-paste Hermes config/example.
Guide includes first Hermes test task.
Guide includes expected /vnext evidence.
Guide includes policy-boundary test.

---

7. Headless Alpha Check

Extend or document:

alicebot vnext alpha check

For headless installs, it should verify:

database reachable
migrations current
doctor passing
API reachable
web reachable
scheduler status
MCP available or configured
connector settings/state initialized
demo load/reset works if requested
agent integration smoke available
secret redaction smoke passing
operator console smoke passing

Add a headless-specific smoke if needed:

alicebot vnext smoke headless-ubuntu

Acceptance criteria:

Headless alpha check passes on Ubuntu.
Failures include remediation.
No check requires local browser access.

---

8. Remote /vnext Access Instructions

Document secure access through SSH tunnel.

Example:

ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@ubuntu-box

Then from local browser:

http://127.0.0.1:3000/vnext

Also document CLI-only fallback if the user cannot open the dashboard.

Do not instruct users to expose /vnext publicly without auth.

Acceptance criteria:

Docs show SSH tunnel method.
Docs warn against public bind.
Docs include firewall/security note.
Docs include CLI fallback.

---

9. Clean Uninstall / Reset

Add safe reset instructions.

Document:

make stop
alicebot vnext demo reset
alicebot vnext doctor

If appropriate, add:

scripts/uninstall-ubuntu.sh

or document manual cleanup:

disable systemd services
remove repo directory
preserve or delete config
preserve or delete database
preserve or delete local secrets

Acceptance criteria:

User can reset demo data.
User can stop services.
User can understand what data will be deleted before deleting it.
No destructive reset runs without confirmation.

---

Required End-to-End Flow

Flow 1: Fresh Ubuntu install from GitHub

SSH into Ubuntu box.
Download installer from GitHub tag.
Run installer.
Installer installs dependencies and repo.
Installer creates config template.
Installer runs migrations.
Installer runs doctor.
Installer runs alpha check.
User starts services.

Flow 2: Remote /vnext access

User creates SSH tunnel.
User opens /vnext from local browser.
Doctor/readiness is visible.
Demo data or live data loads.

Flow 3: Hermes connection

Hermes connects through Alice MCP/API.
Hermes identifies as hermes.
Hermes requests scoped context pack.
Hermes submits output.
Hermes proposes memory.
Memory proposal appears in /vnext.
No trusted memory is auto-promoted.

Flow 4: Scheduler works headlessly

alice-scheduler service runs.
Due workflow executes.
Generated artifact appears.
Scheduler run history records lifecycle.

Flow 5: Security defaults

API/web bind to localhost by default.
Secrets are not printed.
Doctor/alpha check do not expose secrets.
Public network exposure is not enabled by default.

---

Explicit Deferrals

Do not build:

hosted cloud deployment
public SaaS auth
team accounts
billing
Gmail OAuth
Calendar OAuth
voice transcription
OCR
mobile app
automatic memory promotion
major UI redesign

This sprint is installation, packaging, and Hermes dogfood readiness.

---

Acceptance Criteria

The sprint is complete when:

Ubuntu installer exists.
Installer supports tag/branch/install-dir flags.
Installer works on a clean Ubuntu server or documented test environment.
Systemd service templates exist for API, web, and scheduler.
Headless Ubuntu install docs exist.
Remote /vnext SSH tunnel docs exist.
Hermes dogfood guide exists.
Alpha check works in headless mode.
Optional headless-ubuntu smoke exists and passes, or equivalent documented validation exists.
GitHub RC tag/release instructions exist.
Release notes for v0.6.0-alpha-rc.1 exist.
Stable v0.5.1 remains latest.
Secrets are never printed in install logs.
Services bind to localhost by default.
Hermes integration flow is documented and tested.
Agent integration smoke still passes.
Operator console smoke still passes.
Connector hardening smoke still passes.
Secret redaction smoke still passes.
Dogfood doctor smoke still passes.
Capture-to-brief smoke still passes.
Agentic scheduler smoke still passes.
Eval suite passes with 0 critical privacy leaks and 0 prompt-injection tool writes.
Python unit tests pass.
Python integration tests pass.
Web tests pass.
Web lint/build pass.
git diff --check passes.

---

Validation Commands

Run:

pytest tests/unit -q
pytest tests/integration -q
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
alicebot eval run --suite all
git diff --check

Run:

alicebot vnext alpha check
alicebot vnext smoke agent-integration-pack
alicebot vnext smoke operator-console
alicebot vnext smoke connector-hardening
alicebot vnext smoke secret-redaction
alicebot vnext smoke dogfood-doctor
alicebot vnext smoke live-capture-connectors
alicebot vnext smoke capture-to-brief
alicebot vnext smoke agentic-scheduler

Add if practical:

alicebot vnext smoke headless-ubuntu

---

Final Deliverable

Provide a CTO summary with:

what was built
installer command
supported Ubuntu assumptions
systemd service behavior
config/secrets layout
remote access instructions
Hermes dogfood guide
GitHub RC tag/release status
validation results
known limitations
recommended next phase
PR number
merge commit

---

My recommendation on tagging

Prep the repo for:

v0.6.0-alpha-rc.1

Then install that exact tag on your Ubuntu/Hermes box.

After your Hermes dogfood test passes, publish:

v0.6.0-alpha.1

as a GitHub pre-release, not latest.