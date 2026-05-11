# vNext Security and Privacy

Alice vNext is built around private, correctable, inspectable continuity. This document describes the public-preview security posture.

## Defaults

- Local-first operation is the default.
- Source evidence is archived with content hashes, connector metadata, domain, sensitivity, and timestamps.
- Sensitive connector defaults are conservative: most new sources default to `private` or stricter.
- Generated artifacts inherit sensitivity from selected inputs.
- Prompt-injection content from sources is data, not policy.

## Connector Safety

Sprint 11 connectors are deterministic payload ingestion paths. They do not perform live OAuth, polling, remote fetches, browser extension actions, OCR model execution, or transcription model execution.

Connector invariants:

- raw payload or extracted evidence is preserved in source metadata
- default domain and sensitivity are stored with the source
- sync cursors prevent duplicate ingestion
- cursor advancement stops when a failed item could otherwise be skipped
- failed items are logged and not imported as broken memories
- connector payload text cannot trigger tool writes

## Secrets

Do not commit secrets, tokens, real personal exports, private chats, production credentials, or unredacted customer data.

Allowed public demo material:

- synthetic people and projects
- fake URLs under `example.test` or `example.com`
- synthetic source text
- redacted or generated screenshots
- fixture payloads with no real account identifiers

Disallowed public demo material:

- real OAuth tokens
- Telegram chat IDs tied to real users
- real health, legal, financial, family, or customer records
- real browser history
- real voice transcripts
- real email/calendar payloads unless fully synthetic

## Security Review Checklist

- Run unit tests, web tests, build, control-doc truth, and `git diff --check`.
- Run vNext evals and confirm critical privacy leaks are zero.
- Inspect new fixtures for secrets and personal data.
- Inspect new connector write paths for raw-evidence preservation and failure isolation.
- Confirm no generated artifacts are auto-promoted to trusted memory.
- Confirm docs do not claim live connector behavior that is not shipped.

## Reporting

For a vulnerability in the current public release, use the process in the repository `SECURITY.md`. For vNext preview issues, include the connector name, payload type, reproduction command, and whether the issue affects source archive, memory promotion, retrieval, artifact generation, or external tool writes.
