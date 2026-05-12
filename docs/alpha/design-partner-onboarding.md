# Design Partner Onboarding Guide

This alpha is for technical users who can run a local stack and connect agents through MCP/API/CLI.

## What To Test

- fresh setup from README
- doctor-first onboarding
- one capture connector
- source review
- candidate memory review
- Daily Brief or Connection Report generation
- artifact review/rating
- source-to-artifact trace
- OpenClaw, Hermes, or custom agent integration
- restricted-domain policy boundary

## Install

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
cp .env.example .env
cp .env.lite.example .env.lite
make setup
make migrate
make doctor
make dev
```

## Connect An Agent

Start MCP:

```bash
alicebot-mcp
```

Use [mcp-tools.md](mcp-tools.md), [hermes-skill.md](hermes-skill.md), or [openclaw-skill.md](openclaw-skill.md).

## Configure One Capture Connector

Local folder:

```bash
alicebot vnext connectors local-folder add-path ~/Notes/Alice --extension .md --extension .txt
alicebot vnext connectors local-folder sync
```

Browser clip:

```bash
alicebot vnext connectors browser-clipper capture --url https://example.test/note --selected-text "Fact: demo source" --domain project --sensitivity private
```

## Feedback

Include:

- `alicebot vnext doctor --fix-safe --ci`
- `alicebot vnext alpha check --skip-smokes`
- failing command output
- browser console screenshot only if UI is involved
- expected versus actual behavior

Do not include secrets or private source exports.
