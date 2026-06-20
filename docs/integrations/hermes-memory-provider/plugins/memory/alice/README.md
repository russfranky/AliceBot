# Alice Hermes Memory Provider

Hermes external memory provider plugin backed by Alice continuity APIs.

## Provider Features

- `alice_recall` tool for scoped continuity recall.
- `alice_resumption_brief` tool for last-decision and next-action synthesis.
- `alice_open_loops` tool for blocker and waiting-for review.
- prefetch support via Alice resumption brief before each model turn.
- optional turn auto-capture and optional mirror of built-in memory writes.

## Config Location

The provider reads and writes:

- `$HERMES_HOME/alice_memory_provider.json`

## Minimum Config

```json
{
  "base_url": "http://127.0.0.1:8000",
  "user_id": "00000000-0000-0000-0000-000000000001"
}
```

## Optional Keys

- `timeout_seconds` (float, default `8.0`)
- `prefetch_limit` (int, default `5`)
- `max_recent_changes` (int, default `5`)
- `max_open_loops` (int, default `5`)
- `include_non_promotable_facts` (bool, default `false`)
- `sync_turn_capture_enabled` (bool, default `false`; when omitted, an explicit `bridge_mode` of `assist` or `auto` enables turn capture)
- `bridge_mode` (string enum: `manual`, `assist`, `auto`; default `assist`)
- `mirror_memory_writes` (bool, default `false`)

Legacy `auto_capture` and `capture_mode` keys are still accepted. Explicit
`sync_turn_capture_enabled: false` disables turn capture even when `bridge_mode`
is `assist` or `auto`.

## Transport and Identity Safety

- non-loopback `base_url` values must use `https://`
- `http://` is allowed only for loopback development hosts
- provider requests carry user scope in `X-AliceBot-User-Id`

## Activation

```bash
hermes config set memory.provider alice
```

Hermes built-in `MEMORY.md` and `USER.md` stay active. The Alice provider is additive.
