# vNext Security and Privacy

Alice vNext is built around private, correctable, inspectable continuity. This document describes the public-preview security posture.

## Defaults

- Local-first operation is the default.
- Source evidence is archived with content hashes, connector metadata, domain, sensitivity, and timestamps.
- Sensitive connector defaults are conservative: most new sources default to `private` or stricter.
- Generated artifacts inherit sensitivity from selected inputs.
- Prompt-injection content from sources is data, not policy.
- Model-backed workflows default private, confidential, highly sensitive, sacred, and regulated content to local-only or disabled routing unless an explicit policy configuration allows otherwise.
- Model-backed artifacts remain review-only and do not auto-promote trusted memory.

## Connector Safety

The live capture connector slice is local-first and intentionally narrow. Alice can poll Telegram `getUpdates` with an operator-supplied token reference, scan or poll configured local folders, accept browser clipper captures through the local API, and ingest Hermes/OpenClaw-style agent output. It does not perform managed OAuth, packaged browser extension actions, OCR model execution, transcription model execution, hosted connector polling, or cloud sync.

Connector invariants:

- raw payload or extracted evidence is preserved in source metadata
- default domain and sensitivity are stored with the source
- connector defaults are stored in dedicated connector settings rows, not only in the event log
- sync cursors and counters are stored in dedicated connector state rows
- all connector text is marked as untrusted source material
- sync cursors prevent duplicate ingestion
- local folder scanning is constrained to allowed local roots; by default those are the user home, repo working directory, and system temp directory, with `ALICE_VNEXT_LOCAL_FOLDER_ROOTS` available for operator override
- cursor advancement stops when a failed item could otherwise be skipped
- failed items are logged and not imported as broken memories
- connector payload text cannot trigger tool writes
- live connector captures produce candidate memory/review artifacts only; they do not auto-promote trusted memory

## Secrets

Do not commit secrets, tokens, real personal exports, private chats, production credentials, or unredacted customer data.

Connector secrets are referenced, not returned. Telegram and browser clipper can use `secret_ref` values such as `env:TELEGRAM_BOT_TOKEN` or `telegram.bot_token.default`. Local secret values are stored through the secret provider abstraction, with an encrypted local file fallback for alpha use and an environment-reference provider for operators who prefer env vars.

Secret rules:

- API, CLI, UI, event logs, source metadata, artifact metadata, and health responses must expose only the reference or configured/not-configured status.
- Redaction applies before raw connector payloads are persisted.
- Telegram token tests report whether the reference resolves without printing the token.
- Browser clipper capture tokens are accepted only when configured and are redacted from source/event evidence.
- The future OS keychain or hosted secret-provider implementation should satisfy the same interface without changing connector behavior.

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
- Confirm model-backed artifacts include source references, prompt/context hashes, provider metadata, and source-grounded fact/inference/recommendation/uncertainty sections.
- Confirm `alicebot vnext smoke model-backed` passes for at least one scheduled Postgres-backed model-backed workflow.
- Confirm `alicebot vnext smoke connector-hardening`, `alicebot vnext smoke secret-redaction`, and `alicebot vnext smoke dogfood-doctor` pass against the local Postgres database.
- Confirm docs do not claim live connector behavior that is not shipped.

## Reporting

For a vulnerability in the current public release, use the process in the repository `SECURITY.md`. For vNext preview issues, include the connector name, payload type, reproduction command, and whether the issue affects source archive, memory promotion, retrieval, artifact generation, or external tool writes.
