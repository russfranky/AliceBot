# Demo Dataset And Demo Mode

The public preview ships a small synthetic vNext dataset in:

```text
fixtures/vnext/demo_dataset.json
```

The dataset demonstrates:

- sources
- candidate memories
- generated artifacts
- open loops
- project updates
- agent activity
- policy block/filter telemetry
- capture-to-brief trace
- quality ratings
- scheduler run output
- connector health

Load it:

```bash
alicebot vnext demo load --reset
```

Reset it:

```bash
alicebot vnext demo reset
```

Safety expectations:

- no private data
- no real email accounts
- no API tokens
- `example.test` URLs only
- synthetic names and identifiers only

After loading, open `/vnext` and inspect Inbox, Memory Review, Generated, Trace, Agent Activity, Doctor, and Connectors.
