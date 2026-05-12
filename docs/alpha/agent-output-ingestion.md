# Agent Output Ingestion Examples

All examples create reviewable source/artifact evidence. `propose_memory` creates a candidate memory proposal, not trusted memory.

## OpenClaw Sprint Summary

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"openclaw-001","task_id":"public-alpha","project_scope":["Alice"],"title":"OpenClaw sprint summary","content":"Decision: Public alpha packaging uses alpha-check as the first readiness command.","output_type":"sprint_summary","domain":"project","sensitivity":"private","propose_memory":true}
```

## Hermes Daily Planning Summary

```json
{"agent_id":"hermes","agent_type":"personal_assistant","agent_run_id":"hermes-001","task_id":"daily-plan","project_scope":[],"title":"Daily planning summary","content":"The user wants decisions, blockers, and next actions in daily planning.","output_type":"general","domain":"personal","sensitivity":"private","propose_memory":true}
```

## Research Agent Report

```json
{"agent_id":"researcher","agent_type":"research_agent","agent_run_id":"research-001","task_id":"market-map","project_scope":["Alice"],"title":"Research report","content":"Finding: design partners value agent context continuity more than dashboard-first workflows.","output_type":"research_summary","domain":"project","sensitivity":"private","propose_memory":true}
```

## Code Review Findings

```json
{"agent_id":"reviewer","agent_type":"coding_agent","agent_run_id":"review-001","task_id":"pr-205","project_scope":["Alice"],"title":"Code review findings","content":"Finding: source review endpoints preserve review-only behavior.","output_type":"code_review","domain":"project","sensitivity":"private","propose_memory":false}
```

## Meeting Summary

```json
{"agent_id":"meeting-notes","agent_type":"workflow_agent","agent_run_id":"meeting-001","task_id":"alpha-kickoff","project_scope":["Alice"],"title":"Alpha kickoff notes","content":"Decision: first alpha users should run doctor and alpha-check before connecting agents.","output_type":"general","domain":"professional","sensitivity":"private","propose_memory":true}
```

## Architecture Decision

```json
{"agent_id":"architect","agent_type":"coding_agent","agent_run_id":"arch-001","task_id":"agent-memory","project_scope":["Alice"],"title":"Architecture decision","content":"Decision: Agents may propose memory but cannot promote trusted memory directly.","output_type":"decision","domain":"project","sensitivity":"private","propose_memory":true}
```

## Unresolved Risks And Open Loops

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"risk-001","task_id":"alpha-risk","project_scope":["Alice"],"title":"Unresolved alpha risks","content":"TODO: Verify the first design partner can complete setup without hand-holding.","output_type":"project_update","domain":"project","sensitivity":"private","propose_memory":true}
```

Audit behavior:

- source evidence is stored
- reviewable artifact is created
- optional memory proposal appears in review queue
- agent identity and policy decision are logged in the event log
