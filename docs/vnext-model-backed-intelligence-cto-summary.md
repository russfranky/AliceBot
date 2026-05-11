# vNext Model-Backed Intelligence CTO Summary

Date: 2026-05-11

## Executive Summary

This phase upgrades Alice vNext from deterministic second-brain scaffolding into a policy-governed, model-backed intelligence layer. Alice can now run its core Brain workflows in either deterministic mode or model-backed mode, compare the outputs side by side, and collect human quality ratings without weakening the trust model.

The result is not "LLM everywhere." The result is a reviewable synthesis system where models help draft better daily briefs, weekly syntheses, connection reports, contradiction reports, open-loop reviews, and project update scans while Core keeps source grounding, policy checks, auditability, and no-auto-promotion guarantees intact.

## What We Built

### 1. Model Provider Abstraction

Alice now has a Brain model provider interface for:

- chat/completion
- summarization
- structured extraction
- classification
- embeddings when needed

The first provider paths are:

- deterministic local provider for tests, local-only runs, and reproducible behavior
- disabled/no-model provider for policy-blocked or unavailable model states
- OpenAI Responses-compatible provider path for cloud-enabled deployments

Model-backed artifacts persist provider metadata: provider, model, temperature/config, prompt hash, input context hash, created time, trace ID, policy mode, and full routing decision.

### 2. Local-First Model Routing Policy

Model generation now runs through routing modes:

- `local_only`
- `cloud_allowed`
- `cloud_requires_approval`
- `model_disabled`

Private, confidential, highly sensitive, sacred, and regulated content defaults to local-only or disabled unless explicitly configured. Public, internal, and professional content can be configured for cloud use. Routing decisions consider workflow type, domain, sensitivity, agent identity, caller configuration, and Brain Charter settings.

### 3. Model-Backed Brain Workflows

The following workflows now support deterministic and model-backed execution:

- Daily Brief
- Weekly Synthesis
- Connection Report
- Contradiction Report
- Open Loop Review
- Project Update Scan

Scheduler workflows can also carry model options, so due scans can run model-backed workflows when policy allows. The Postgres smoke covers a scheduled model-backed workflow end to end.

### 4. Source-Grounded Output Format

Every model-backed artifact uses a structured, reviewable format that separates:

- facts
- inferences
- recommendations
- uncertainties
- source references
- contradictions considered
- open questions

This gives reviewers a way to distinguish evidence from model interpretation and keeps Alice trustworthy rather than merely fluent.

### 5. Trust Model Preservation

The model layer does not silently mutate trusted memory.

Models may:

- generate artifacts
- draft project update candidates
- propose candidate memories or graph edges
- support human review

Models may not:

- auto-promote generated output into trusted memory
- bypass domain or sensitivity filters
- override policy decisions
- execute instructions embedded in imported source content

### 6. Prompt-Injection Hardening

Model prompts mark retrieved/source material as untrusted context. The implementation sanitizes model output and keeps source instructions from becoming tool or policy instructions. The eval suite still reports zero prompt-injection tool writes.

### 7. Human Quality Evaluation Harness

Generated artifacts can now be rated by humans for:

- usefulness
- accuracy
- source grounding
- novel connections
- actionability
- hallucination risk
- verbosity
- missed context
- comments

Ratings are stored in Postgres through a new `artifact_quality_ratings` table and exposed through API, CLI, and the vNext workspace.

### 8. `/vnext` Model Comparison And Review Controls

The `/vnext` workspace now includes:

- generation mode selection
- deterministic vs model-backed comparison for Daily Brief, Connection Report, and Contradiction Report
- visible provider/model metadata on generated artifacts
- quality rating controls for generated artifacts
- workspace quality eval summary data

This gives product and engineering a practical way to prove whether model-backed intelligence improves the user experience before changing defaults.

### 9. API, CLI, MCP, And Scheduler Coverage

Model-backed options are wired across the product surface:

- API artifact generation and quality rating endpoints
- CLI generation flags and quality export/rate commands
- MCP/agent tool generation options with policy checks
- scheduler run-now and due-workflow model options
- Postgres-backed model-backed smoke command

## Why It Matters

Alice already had durable memory, provenance, review state, connectors, context packs, and scheduler machinery. This phase turns that infrastructure into a higher-quality intelligence loop:

- Alice can synthesize instead of only retrieve.
- The team can compare model-backed output against deterministic output.
- Reviewers can score artifacts and create a feedback signal.
- Agents can request richer working context without owning or corrupting Alice memory.
- The system remains local-first, policy-governed, source-grounded, and auditable.

## Validation Evidence

Current validation from this phase:

- Python compile checks passed for the new/modified backend modules.
- Full Python unit suite passed: `1096 passed`.
- Full web test suite passed: `207 passed`.
- Web lint passed.
- Web production build passed and built `/vnext`.
- MCP unit coverage passed: `12 passed`.
- Postgres-backed model-backed smoke passed, including local-only routing, provider metadata, review status, source refs, and grounded sections.
- Eval suite passed: `170/170` cases, zero critical privacy leaks, zero prompt-injection tool writes.

## Explicit Deferrals

Still deferred:

- live Gmail OAuth
- live Calendar OAuth
- live Telegram polling
- browser extension runtime actions
- OCR execution
- voice transcription execution
- hosted cloud deployment
- mobile app
- automatic memory promotion
- major UI redesign

## Bottom Line

This phase moves Alice from "memory infrastructure" toward "trusted second-brain intelligence." The important architectural choice is that model-backed synthesis is added inside the existing trust boundary rather than replacing it: models draft, humans review, Core governs, and every output stays grounded in auditable source evidence.
