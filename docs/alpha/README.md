# Alice vNext Public Alpha

Alice vNext public alpha is a technical, local-first package for design partners who want agent memory and continuity without hosted storage or automatic trusted-memory writes.

Alice is agent-first, not dashboard-first:

1. Install Alice locally.
2. Connect Hermes, OpenClaw, or a custom agent through MCP/API/CLI.
3. Let agents request scoped context packs and submit reviewable outputs.
4. Use `/vnext` to review, govern, audit, configure, and troubleshoot.

Start here:

- [Quickstart](quickstart.md)
- [First-run checklist](first-run.md)
- [Local runtime](local-runtime.md)
- [Doctor](doctor.md)
- [Demo mode](demo-mode.md)
- [Agent integration](agent-integration.md)
- [MCP tools](mcp-tools.md)
- [Hermes skill](hermes-skill.md)
- [OpenClaw skill](openclaw-skill.md)
- [Custom agent guide](custom-agent-guide.md)
- [Context-pack recipes](context-pack-recipes.md)
- [Memory proposal recipes](memory-proposal-recipes.md)
- [Agent output ingestion examples](agent-output-ingestion.md)
- [Dogfooding guide](dogfooding-guide.md)
- [Troubleshooting](troubleshooting.md)
- [Known limitations](known-limitations.md)
- [Security and privacy](security-and-privacy.md)
- [Design partner onboarding](design-partner-onboarding.md)
- [Alpha release notes](release-notes.md)

Current alpha posture:

- local runtime, not hosted SaaS
- technical setup, not consumer install
- review-only source, artifact, and agent memory proposal flows
- no automatic promotion into trusted memory
- supported alpha connectors: local folder, browser clipper MVP, Telegram polling/sync, document payload ingestion, voice transcript payload ingestion, screenshot OCR payload ingestion, and agent output ingestion
- `/vnext` is the operator console, not the main agent interface
