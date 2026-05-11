

Next Sprint Scope: Model-Backed Intelligence + Quality Evals

Objective

Upgrade Alice Brain workflows from deterministic/local scaffolds into model-backed, policy-governed synthesis workflows that produce genuinely useful, source-grounded, reviewable outputs for humans and agents.

The goal is not “make it use an LLM everywhere.”

The goal is:

better context packs
better daily briefs
better weekly synthesis
better connection discovery
better contradiction detection
better project updates
better open-loop reasoning
measurable quality improvement

All model-backed outputs must remain:

reviewable
source-grounded
policy-checked
auditable
non-auto-promoted
safe against prompt injection

⸻

Core deliverables

1. Model provider abstraction for Alice Brain workflows
2. Local-first model routing policy
3. Model-backed Daily Brief
4. Model-backed Weekly Synthesis
5. Model-backed Connection Report
6. Model-backed Contradiction Report
7. Model-backed Open Loop Review
8. Model-backed Project Update Scan
9. Human-rated eval harness
10. Side-by-side deterministic vs model-backed comparison mode
11. Prompt-injection hardening for model-backed workflows
12. /vnext quality review controls

⸻

Key product rule

Model-backed generation must not weaken Alice’s trust model.

The rule remains:

Models may generate artifacts and proposals.
Models may not silently create trusted memory.
Models may not override policy.
Models may not bypass sensitivity/domain restrictions.
Models may not execute instructions found inside imported source content.

⸻

Build requirements

1. Model provider abstraction

Add or extend a provider interface for:

chat/completion
structured extraction
summarization
classification
embedding if needed

The interface should support:

local model provider
cloud model provider
mock/deterministic provider for tests
disabled/no-model mode

Provider metadata must be stored on artifacts:

provider
model
temperature/config
prompt_hash
input_context_hash
created_at
trace_id
policy_mode

⸻

2. Model routing policy

Add model-routing rules based on:

domain
sensitivity
agent identity
workflow type
user configuration
Brain Charter settings

Initial routing modes:

local_only
cloud_allowed
cloud_requires_approval
model_disabled

Default:

private/confidential/highly_sensitive/sacred/regulated = local_only or disabled unless explicitly configured
public/internal/professional = configurable

This is crucial for Alice’s positioning.

⸻

3. Model-backed workflow upgrade

Upgrade all six workflows:

daily_brief
weekly_synthesis
connection_report
contradiction_report
open_loop_review
project_update_scan

Each workflow should have two modes:

deterministic
model_backed

The system should be able to run both and compare outputs.

⸻

4. Source-grounded output format

Every model-backed artifact must separate:

facts
inferences
recommendations
uncertainties
source references
contradictions considered
open questions

This matters because Alice must be trusted, not just eloquent.

⸻

5. Human-rated evals

Add a human-reviewable eval layer.

For generated artifacts, allow ratings on:

usefulness
accuracy
source grounding
novel connections
actionability
missed context
hallucination risk
too verbose / too shallow

Store ratings and comments.

Add CLI/API/UI support for eval review.

⸻

6. Side-by-side comparison

In /vnext, allow comparing:

deterministic daily brief vs model-backed daily brief
deterministic connection report vs model-backed connection report
deterministic contradiction report vs model-backed contradiction report

This is important for proving the model layer actually improves the product.

⸻

Acceptance criteria

Model provider abstraction exists and supports deterministic/mock and at least one real provider path.
Model routing policy exists and respects domain/sensitivity settings.
Private/highly sensitive content does not leave local mode unless explicitly configured.
Daily Brief can run in deterministic and model-backed mode.
Weekly Synthesis can run in deterministic and model-backed mode.
Connection Report can run in deterministic and model-backed mode.
Contradiction Report can run in deterministic and model-backed mode.
Open Loop Review can run in deterministic and model-backed mode.
Project Update Scan can run in deterministic and model-backed mode.
All model-backed artifacts include provider/model/prompt/context metadata.
All model-backed artifacts include source references.
All model-backed artifacts distinguish fact, inference, recommendation, uncertainty.
No model-backed artifact auto-promotes into trusted memory.
Prompt-injection evals still pass with model-backed workflows enabled.
Privacy leakage evals still pass.
Human rating model exists for generated artifacts.
UI supports rating generated artifacts.
CLI/API can export quality eval results.
Side-by-side deterministic vs model-backed comparison exists for at least Daily Brief, Connection Report, and Contradiction Report.
Scheduler can run model-backed workflows if enabled by policy.
Agent-triggered model-backed workflows are policy-checked.
Postgres-backed smoke covers at least one scheduled model-backed workflow.
Existing tests pass.
Web tests pass.
Web lint/build pass.
Eval suite passes.
git diff --check passes.

⸻

Explicit deferrals

Still defer:

live Gmail OAuth
live Calendar OAuth
live Telegram polling
browser extension runtime actions
OCR execution
voice transcription execution
hosted cloud deployment
mobile app
automatic memory promotion
major UI redesign

The goal is quality of intelligence, not more inputs yet.

⸻

Why this should be next

Alice now has the machinery. But the product will only become magical when the outputs are genuinely good.

The next sprint should answer:

Can Alice find a non-obvious connection I missed?
Can Alice surface a real contradiction in my thinking?
Can Alice generate a daily brief I would actually read?
Can Alice give Hermes/OpenClaw better working context than a normal RAG system?
Can Alice improve with human feedback?

That is the difference between infrastructure and product-market pull.

⸻

Bottom line

This phase successfully made Alice operational.

The next phase should make Alice intelligent enough to matter.

My recommended sprint title:

Alice vNext: Model-Backed Intelligence + Quality Evals

Once that is strong, then connectors become much more valuable because Alice will know what to do with the information it captures.