# Public Alpha Security And Privacy

Alice public preview is local-first.

Security posture:

- source evidence is review-only
- generated artifacts are review-only
- agent memory proposals are review-only
- trusted memory is not auto-promoted
- connector secrets should be stored as secret refs
- CLI/API/UI/event/source/artifact output should not print secret values
- prompt-injection source text is data, not policy
- agents are policy-checked by identity, permission profile, domain, sensitivity, and action

Recommended alpha defaults:

```bash
alicebot vnext doctor --fix-safe --ci
alicebot vnext smoke secret-redaction
alicebot eval run --suite all
```

Sensitive domain guidance:

- project-scoped agents should avoid personal, family, health, spiritual, legal, financial, and regulated domains
- trusted local assistants should request sensitive domains only when necessary
- blocked or filtered policy decisions should be surfaced in `/vnext` Agent Activity

Reporting issues:

- include command output with secrets redacted
- include failing smoke names
- do not include private exports, real Telegram payloads, API tokens, or personal datasets
