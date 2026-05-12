# Alice vNext Headless Ubuntu Packaging: CTO Summary

Date: 2026-05-12
Audience: CTO / technical leadership
Sprint artifact: `codex/headless-ubuntu-installer`

## Executive Summary

This phase makes Alice vNext practically installable from GitHub on a headless Ubuntu box for Hermes dogfood testing. It keeps the product local-first, agent-first, review-first, and secure-by-default: Alice binds to localhost, `/vnext` is reached through SSH tunneling, and Hermes connects through MCP/API without direct trusted-memory writes.

## What Was Built

- `scripts/install-ubuntu.sh` for tag/branch/install-dir based GitHub installs
- `scripts/uninstall-ubuntu.sh` for safe service stop/reset and opt-in destructive cleanup
- systemd templates for `alice-api`, `alice-web`, and `alice-scheduler`
- `packaging/ubuntu/alicebot.env.example` for agreed headless config paths
- `docs/alpha/headless-ubuntu-install.md`
- `docs/alpha/hermes-dogfood-ubuntu.md`
- `docs/release/v0.6.0-alpha-rc.1-release-notes.md`
- `alicebot vnext smoke headless-ubuntu`
- `alicebot vnext alpha check --headless`

## Installer Command

```bash
curl -fsSL https://raw.githubusercontent.com/samrusani/AliceBot/v0.6.0-alpha-rc.1/scripts/install-ubuntu.sh -o install-alice.sh
less install-alice.sh
bash install-alice.sh --tag v0.6.0-alpha-rc.1
```

Supported assumptions: Ubuntu 22.04 or 24.04, SSH access, local or existing Postgres, Node 20, Python venv, and local-only service binding.

## Systemd Behavior

The templates run as the installing non-root user, load `~/.config/alicebot/.env`, restart on failure, and log through `journalctl`. API binds to `127.0.0.1:8000`, web binds to `127.0.0.1:3000`, and scheduler uses the governed `alicebot vnext scheduler daemon start --foreground` path.

## Config And Secrets Layout

- repo: `~/alicebot`
- config: `~/.config/alicebot/.env`
- data: `~/.local/share/alicebot/`
- logs/state: `~/.local/state/alicebot/logs/`
- local secret references: `~/.config/alicebot/secrets/`

Existing config is preserved. The installer does not print generated local database passwords or connector secrets.

## Remote Access

Recommended access is an SSH tunnel:

```bash
ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 user@ubuntu-box
```

Then open `http://127.0.0.1:3000/vnext` locally.

## Hermes Dogfood

Hermes should identify as `agent_id=hermes`, `agent_type=personal_assistant`, `permission_profile=trusted_local_agent`, and request project-scoped context through Alice MCP/API. Outputs become reviewable source/artifact evidence. Durable facts become candidate memory proposals only.

## RC Tag / Release Status

The repo is prepared for `v0.6.0-alpha-rc.1`. Stable `v0.5.1` remains latest. If published, the RC should be a GitHub pre-release with `--latest=false`.

## Known Limitations

This does not add hosted cloud deployment, public SaaS auth, team accounts, billing, Gmail OAuth, Calendar OAuth, OCR execution, voice transcription, mobile app, or automatic memory promotion.

## Recommended Next Phase

Run the exact `v0.6.0-alpha-rc.1` installer on the Ubuntu/Hermes dogfood host, record the real install transcript, then publish `v0.6.0-alpha.1` as a pre-release only after Hermes completes the first context-pack/output/proposal loop.
