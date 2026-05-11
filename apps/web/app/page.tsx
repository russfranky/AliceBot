import Link from "next/link";

import { PageHeader } from "../components/page-header";
import { SectionCard } from "../components/section-card";
import { StatusBadge } from "../components/status-badge";

const summaryCards = [
  {
    value: "14",
    label: "Operator views",
    detail:
      "Home, vNext brain workspace, hosted onboarding/settings/admin, request composition, approvals, task inspection, artifact review, Gmail review, Calendar review, memory review, entity review, and explainability are all exposed in one bounded shell.",
  },
  {
    value: "9",
    label: "Governance seams",
    detail:
      "Requests, approvals, tasks, artifact review, Gmail account/ingestion seams, Calendar account/ingestion seams, memory review, vNext brain review, and entity review stay visible instead of being hidden behind a consumer chat wrapper.",
  },
  {
    value: "2",
    label: "Data modes",
    detail: "Pages can read live backend seams when configured and degrade to explicit fixtures when no API contract is present.",
  },
  {
    value: "100%",
    label: "Scoped surface",
    detail: "The shell stays within the sprint packet: no auth expansion, no connector breadth, and no backend contract changes.",
  },
];

const routeCards = [
  {
    href: "/vnext",
    title: "vNext Brain Workspace",
    description:
      "Review memory candidates, ask Alice with provenance, read briefs, inspect generated artifacts, and keep projects, beliefs, loops, graph, and privacy labels visible.",
    status: "preview",
  },
  {
    href: "/onboarding",
    title: "Hosted Onboarding",
    description:
      "Sign in by magic link, create/bootstrap a workspace, and confirm readiness for later Telegram linkage.",
    status: "active",
  },
  {
    href: "/settings",
    title: "Hosted Settings",
    description:
      "Persist Telegram notification posture, quiet hours, daily brief delivery state, and scheduler job visibility.",
    status: "active",
  },
  {
    href: "/admin",
    title: "Hosted Admin",
    description:
      "Inspect hosted workspace posture, delivery receipts, incidents, rollout flags, analytics, and rate-limit evidence.",
    status: "active",
  },
  {
    href: "/chat",
    title: "Governed Requests",
    description: "Compose bounded operator requests, review response history, and keep compilation and response traces visible.",
    status: "active",
  },
  {
    href: "/approvals",
    title: "Approval Inbox",
    description: "Review pending approvals with tool, scope, routing, and rationale all contained in a stable inspector layout.",
    status: "pending_approval",
  },
  {
    href: "/tasks",
    title: "Task Inspection",
    description: "Inspect task lifecycle state, related governed requests, and ordered task-step progress without leaving the shell.",
    status: "approved",
  },
  {
    href: "/artifacts",
    title: "Artifact Review",
    description: "Inspect persisted artifacts, selected detail, linked task workspace metadata, and ordered chunk evidence.",
    status: "ingested",
  },
  {
    href: "/gmail",
    title: "Gmail Review",
    description:
      "Review connected Gmail accounts, inspect one selected account, and explicitly ingest one selected message into a task workspace.",
    status: "active",
  },
  {
    href: "/calendar",
    title: "Calendar Review",
    description:
      "Review connected Calendar accounts, inspect one selected account, and explicitly ingest one selected event into a task workspace.",
    status: "active",
  },
  {
    href: "/memories",
    title: "Memory Review",
    description: "Inspect active memory records, revisions, and review labels through the shipped memory-review seam.",
    status: "requires_review",
  },
  {
    href: "/entities",
    title: "Entity Review",
    description: "Inspect tracked entities, selected entity detail, and related edges through the shipped entity-review seam.",
    status: "active",
  },
  {
    href: "/traces",
    title: "Explain-Why Review",
    description: "Trace context compilation and governed actions through a calm evidence-first review surface.",
    status: "executed",
  },
];

const shellNotes = [
  "Stable navigation with obvious current location and restrained emphasis.",
  "Cards and lists sized for readable density rather than dashboard clutter.",
  "Responsive stacking that protects text containment on tablet and mobile widths.",
  "Clear OSS-versus-hosted boundary: Alice Core remains local-first while Alice Connect beta operations stay explicit.",
];

export default function HomePage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="AliceBot"
        title="Operator shell for governed work"
        description="The first web surface is intentionally narrow: it exposes existing backend seams with calm hierarchy, strong containment, and clear review paths."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Sprint 6V shell</span>
            <span className="subtle-chip">Design-system aligned</span>
          </div>
        }
      />

      <section className="metric-grid" aria-label="Shell summary">
        {summaryCards.map((card) => (
          <SectionCard key={card.label} className="section-card--metric">
            <div className="metric-value">{card.value}</div>
            <div className="metric-label">{card.label}</div>
            <p className="metric-detail">{card.detail}</p>
          </SectionCard>
        ))}
      </section>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Core views"
          title="Primary operator surfaces"
          description="Each route is deliberately narrow, with one clear purpose and predictable visual rhythm."
        >
          <div className="route-grid">
            {routeCards.map((route) => (
              <Link key={route.href} href={route.href} className="nav-card">
                <div className="nav-card__topline">
                  <h3>{route.title}</h3>
                  <StatusBadge status={route.status} />
                </div>
                <p>{route.description}</p>
                <span className="nav-card__cta">Open view</span>
              </Link>
            ))}
          </div>
        </SectionCard>

        <div className="stack">
          <SectionCard
            eyebrow="UI priorities"
            title="What this shell optimizes for"
            description="The interface favors trust, clarity, and reviewability before throughput."
          >
            <ul className="bullet-list">
              {shellNotes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard
            eyebrow="System posture"
            title="Governed by default"
            description="The landing view frames the product around visible control points rather than hidden automation."
          >
            <dl className="key-value-grid">
              <div>
                <dt>Request path</dt>
                <dd>Explicitly labeled as governed and reviewable.</dd>
              </div>
              <div>
                <dt>Consequential actions</dt>
                <dd>Held behind approval and execution review states.</dd>
              </div>
              <div>
                <dt>Explainability</dt>
                <dd>Trace review sits beside operational work, not in a debug-only corner.</dd>
              </div>
            </dl>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
