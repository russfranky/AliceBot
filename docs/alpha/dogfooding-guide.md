# Dogfooding Guide

Daily public alpha dogfood loop:

```bash
alicebot vnext doctor --fix-safe --ci
alicebot vnext alpha check
alicebot vnext dogfooding dashboard
```

Then use `/vnext`:

1. Review new sources in Inbox.
2. Accept, edit, or reject candidate memories.
3. Review generated artifacts.
4. Rate useful artifacts.
5. Inspect Trace for source-to-artifact provenance.
6. Check Agent Activity for policy blocks and proposals.
7. Check Doctor before reporting bugs.

Include these with bug reports:

- output from `alicebot vnext doctor --fix-safe --ci`
- output from `alicebot vnext alpha check --skip-smokes`
- failing smoke command and error
- `/vnext` page and action that failed
- redacted connector config, never secret values
