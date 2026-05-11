from __future__ import annotations

from dataclasses import dataclass, field


BRAIN_CHARTER_TEMPLATE = """# ALICE.md - Brain Charter

## Owner
Name:
Primary roles:
Current focus areas:
Long-term goals:

## Memory Philosophy
What should Alice remember?
What should Alice ignore?
What should require review?

## Life Domains
Professional:
Personal:
Family:
Health:
Spiritual:
Financial:
Legal:
Learning:

## Active Projects
- Project name: status, goal, next milestone

## Communication Style
How should Alice write to me?
What tone should Alice use?
What should Alice avoid?

## What Matters Most Right Now
Current priorities:
Current constraints:
Current risks:

## Autonomous Operation Rules
- Never delete raw evidence without explicit user instruction.
- Never silently promote generated content into durable memory when confidence/sensitivity requires review.
- Always preserve provenance.
- Always log writes.
- Always distinguish fact, inference, and suggestion.
- Do not mix family/health/spiritual memories into work outputs unless explicitly requested.
- When uncertain, create a review item instead of acting silently.

## Quality Standard
Good Alice output should be:
- specific
- source-grounded
- concise first, expandable second
- honest about uncertainty
- willing to challenge assumptions
- action-oriented when appropriate
"""


@dataclass(frozen=True, slots=True)
class BrainCharter:
    content_markdown: str = BRAIN_CHARTER_TEMPLATE
    owner: dict[str, object] = field(default_factory=dict)
    memory_philosophy: dict[str, object] = field(default_factory=dict)
    life_domains: dict[str, object] = field(default_factory=dict)
    active_projects: list[dict[str, object]] = field(default_factory=list)
    communication_style: dict[str, object] = field(default_factory=dict)
    priorities: dict[str, object] = field(default_factory=dict)
    autonomous_rules: list[str] = field(default_factory=list)
    quality_standard: list[str] = field(default_factory=list)
    sensitivity: str = "private"

    def to_record(self) -> dict[str, object]:
        return {
            "content_markdown": self.content_markdown,
            "owner_json": self.owner,
            "memory_philosophy_json": self.memory_philosophy,
            "life_domains_json": self.life_domains,
            "active_projects_json": self.active_projects,
            "communication_style_json": self.communication_style,
            "priorities_json": self.priorities,
            "autonomous_rules_json": self.autonomous_rules,
            "quality_standard_json": self.quality_standard,
            "sensitivity": self.sensitivity,
        }


def default_brain_charter() -> BrainCharter:
    return BrainCharter(
        autonomous_rules=[
            "Never delete raw evidence without explicit user instruction.",
            "Never silently promote generated content into durable memory when review is required.",
            "Always preserve provenance.",
            "Always log writes.",
        ],
        quality_standard=[
            "specific",
            "source-grounded",
            "honest about uncertainty",
            "action-oriented when appropriate",
        ],
    )


__all__ = ["BRAIN_CHARTER_TEMPLATE", "BrainCharter", "default_brain_charter"]
