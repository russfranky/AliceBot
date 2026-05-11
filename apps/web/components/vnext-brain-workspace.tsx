"use client";

import { FormEvent, useState } from "react";

import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

export const VNEXT_DOMAIN_OPTIONS = [
  { value: "professional", label: "Work" },
  { value: "personal", label: "Personal" },
  { value: "family", label: "Family" },
  { value: "health", label: "Health" },
  { value: "spiritual", label: "Spiritual" },
  { value: "financial", label: "Financial" },
  { value: "legal", label: "Legal" },
  { value: "learning", label: "Learning" },
  { value: "relationship", label: "Relationship" },
  { value: "project", label: "Project" },
  { value: "agent_run", label: "Agent run" },
  { value: "system", label: "System" },
  { value: "unknown", label: "Unknown" },
] as const;

export const VNEXT_SENSITIVITY_OPTIONS = [
  { value: "public", label: "Public" },
  { value: "internal", label: "Internal" },
  { value: "private", label: "Private" },
  { value: "confidential", label: "Confidential" },
  { value: "highly_sensitive", label: "Highly sensitive" },
  { value: "sacred", label: "Sacred" },
  { value: "regulated", label: "Regulated" },
  { value: "unknown", label: "Unknown" },
] as const;

export const VNEXT_SUPPORTED_CONNECTOR_IDS = [
  "telegram",
  "browser_clipper",
  "pdf_document",
  "docx_document",
  "csv_table",
  "screenshot_ocr",
  "voice_transcription",
] as const;

type Domain = (typeof VNEXT_DOMAIN_OPTIONS)[number]["value"];
type Sensitivity = (typeof VNEXT_SENSITIVITY_OPTIONS)[number]["value"];
type ReviewStatus = "requires_review" | "accepted" | "edited" | "rejected" | "promoted";

type ReviewItem = {
  id: string;
  title: string;
  kind: string;
  status: ReviewStatus;
  note: string;
  domain: Domain;
  sensitivity: Sensitivity;
  project: string;
  updatedAt: string;
  sourceIds: string[];
  provenance: string;
};

type OpenLoopItem = {
  id: string;
  title: string;
  status: string;
  due: string;
  domain: Domain;
  sensitivity: Sensitivity;
  sourceIds: string[];
};

type GeneratedArtifact = {
  id: string;
  title: string;
  type: string;
  status: string;
  summary: string;
  domain: Domain;
  sensitivity: Sensitivity;
  sources: string[];
  provenance: string;
};

type AskAnswer = {
  question: string;
  summary: string;
  memoriesUsed: string[];
  contradictions: string[];
  why: string[];
  sources: string[];
  domain: Domain;
  sensitivity: Sensitivity;
};

type ConnectorSetting = {
  id: string;
  name: string;
  stage: string;
  status: string;
  defaultDomain: Domain;
  defaultSensitivity: Sensitivity;
  cursor: string;
  evidence: string;
  failureMode: string;
};

function optionLabel<T extends string>(
  options: readonly { value: T; label: string }[],
  value: T,
) {
  return options.find((option) => option.value === value)?.label ?? value;
}

function domainLabel(domain: Domain) {
  return optionLabel(VNEXT_DOMAIN_OPTIONS, domain);
}

function sensitivityLabel(sensitivity: Sensitivity) {
  return optionLabel(VNEXT_SENSITIVITY_OPTIONS, sensitivity);
}

const SURFACES = [
  "Home",
  "Inbox",
  "Ask Alice",
  "Daily Brief",
  "Weekly Synthesis",
  "Queue",
  "Generated",
  "Memory Review",
  "Projects",
  "People",
  "Beliefs",
  "Open Loops",
  "Timeline",
  "Graph",
  "Connectors",
  "Settings",
];

const DEFAULT_REVIEW_ITEM: ReviewItem = {
  id: "review-1",
  title: "Launch checklist owner should be confirmed before the product review.",
  kind: "memory_candidate",
  status: "requires_review",
  note: "Promoted from a project meeting capture where the owner was implied but not explicitly confirmed.",
  domain: "project",
  sensitivity: "private",
  project: "Product launch",
  updatedAt: "2026-05-10T08:30:00Z",
  sourceIds: ["capture.launch-review.042", "artifact.product-review-notes"],
  provenance: "Captured from meeting notes and ranked by recency plus project match.",
};

const INITIAL_REVIEW_ITEMS: ReviewItem[] = [
  DEFAULT_REVIEW_ITEM,
  {
    id: "review-2",
    title: "Health lab PDF needs a manual sensitivity check before retrieval.",
    kind: "artifact_memory",
    status: "requires_review",
    note: "File parser extracted a personal health signal, but the document sensitivity is not operator-confirmed.",
    domain: "health",
    sensitivity: "highly_sensitive",
    project: "Personal admin",
    updatedAt: "2026-05-10T07:45:00Z",
    sourceIds: ["artifact.lab-panel.pdf", "capture.health-admin.011"],
    provenance: "Artifact ingestion candidate held for review because the label is sensitive.",
  },
  {
    id: "review-3",
    title: "Vendor legal review is still waiting for Priya.",
    kind: "open_loop_candidate",
    status: "requires_review",
    note: "Waiting-for signal appeared in weekly synthesis and should remain visible until closed.",
    domain: "legal",
    sensitivity: "internal",
    project: "Vendor onboarding",
    updatedAt: "2026-05-09T16:20:00Z",
    sourceIds: ["brief.weekly.2026-W19", "person.priya"],
    provenance: "Derived from unresolved waiting-for items and person graph edges.",
  },
];

const INITIAL_OPEN_LOOPS: OpenLoopItem[] = [
  {
    id: "loop-1",
    title: "Confirm launch checklist owner",
    status: "due_soon",
    due: "Today",
    domain: "project",
    sensitivity: "private",
    sourceIds: ["capture.launch-review.042"],
  },
  {
    id: "loop-2",
    title: "Ask Priya for vendor legal review ETA",
    status: "waiting_for",
    due: "Tomorrow",
    domain: "legal",
    sensitivity: "internal",
    sourceIds: ["person.priya", "brief.weekly.2026-W19"],
  },
];

const INITIAL_ARTIFACTS: GeneratedArtifact[] = [
  {
    id: "artifact-1",
    title: "daily-brief-2026-05-10.md",
    type: "Daily Brief",
    status: "ready",
    summary: "Focus on the launch checklist owner, unresolved vendor legal review, and one sensitive health document review.",
    domain: "project",
    sensitivity: "private",
    sources: ["capture.launch-review.042", "open_loop.loop-1", "memory.review-1"],
    provenance: "Generated by daily brief assembly from reviewed memories, open loops, and queue state.",
  },
  {
    id: "artifact-2",
    title: "weekly-synthesis-2026-W19.md",
    type: "Weekly Synthesis",
    status: "ready",
    summary: "Work graph pressure is concentrated around launch ownership, vendor waiting-for items, and project follow-through.",
    domain: "professional",
    sensitivity: "internal",
    sources: ["brief.daily.2026-05-10", "person.priya", "project.vendor-onboarding"],
    provenance: "Generated by weekly synthesis from accepted brief items and graph edges.",
  },
];

const INITIAL_ANSWER: AskAnswer = {
  question: "What should I focus on before the product review?",
  summary:
    "Start by confirming the launch checklist owner, then resolve the vendor legal review waiting-for item before reading lower-priority queue items.",
  memoriesUsed: [
    "Launch checklist owner is unresolved.",
    "Vendor legal review is waiting on Priya.",
    "Daily brief marked the health lab PDF as sensitive and not product-review relevant.",
  ],
  contradictions: [
    "One older note says Morgan owns the checklist; a newer meeting note says ownership was not confirmed.",
  ],
  why: [
    "The selected items are active open loops due soon.",
    "Both items are attached to the Product launch project and have direct source provenance.",
    "Sensitive health evidence is excluded from this work-domain answer.",
  ],
  sources: ["open_loop.loop-1", "memory.review-1", "person.priya", "brief.daily.2026-05-10"],
  domain: "project",
  sensitivity: "private",
};

export const INITIAL_CONNECTORS: ConnectorSetting[] = [
  {
    id: "telegram",
    name: "Telegram capture",
    stage: "Phase 2",
    status: "Webhook payloads",
    defaultDomain: "personal",
    defaultSensitivity: "private",
    cursor: "provider_update_id",
    evidence: "Raw Telegram update JSON",
    failureMode: "Failed items pause cursor advancement.",
  },
  {
    id: "browser_clipper",
    name: "Browser clipper",
    stage: "Phase 2",
    status: "Clip payloads",
    defaultDomain: "learning",
    defaultSensitivity: "private",
    cursor: "captured_at or external id",
    evidence: "URL, selection, page text, and optional HTML",
    failureMode: "Bad clips stay out of memory.",
  },
  {
    id: "pdf_document",
    name: "PDF processing",
    stage: "Phase 2",
    status: "Extracted text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "Extracted PDF text plus file metadata",
    failureMode: "Parser failures leave existing sources unchanged.",
  },
  {
    id: "docx_document",
    name: "DOCX processing",
    stage: "Phase 2",
    status: "Extracted text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "Extracted DOCX text plus file metadata",
    failureMode: "Parser failures leave existing sources unchanged.",
  },
  {
    id: "csv_table",
    name: "CSV processing",
    stage: "Phase 2",
    status: "Normalized rows",
    defaultDomain: "professional",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "CSV text or rows plus file metadata",
    failureMode: "Malformed rows are logged without advancing past the failed item.",
  },
  {
    id: "screenshot_ocr",
    name: "Screenshot processing",
    stage: "Phase 2",
    status: "OCR text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "captured_at or external id",
    evidence: "OCR text plus screenshot metadata",
    failureMode: "OCR extraction failures leave existing sources unchanged.",
  },
  {
    id: "voice_transcription",
    name: "Voice transcription",
    stage: "Phase 2",
    status: "Transcript payloads",
    defaultDomain: "personal",
    defaultSensitivity: "private",
    cursor: "recorded_at or external id",
    evidence: "Transcript text and segment metadata",
    failureMode: "Unusable transcripts are logged for retry.",
  },
];

const DAILY_BRIEF_ITEMS = [
  {
    title: "Confirm launch checklist owner",
    body: "This is the top unresolved work item and blocks the product review handoff.",
    status: "requires_review",
    sources: ["capture.launch-review.042", "open_loop.loop-1"],
  },
  {
    title: "Review sensitive artifact labels",
    body: "A health lab PDF remains out of work-domain retrieval until the sensitivity label is confirmed.",
    status: "blocked",
    sources: ["artifact.lab-panel.pdf", "memory.review-2"],
  },
];

const WEEKLY_SIGNALS = [
  {
    label: "Decision",
    text: "Keep the launch rollout to one cohort until ownership and vendor legal review are settled.",
    sources: ["brief.weekly.2026-W19", "project.product-launch"],
  },
  {
    label: "Connection",
    text: "Priya is linked to vendor onboarding, legal review, and the launch dependency cluster.",
    sources: ["person.priya", "graph.edge.vendor-legal"],
  },
];

const PROJECTS = [
  {
    name: "Product launch",
    status: "active",
    progress: "3 of 5 loops closed",
    next: "Confirm checklist owner",
    domain: "project" as Domain,
    sensitivity: "private" as Sensitivity,
  },
  {
    name: "Vendor onboarding",
    status: "blocked",
    progress: "Waiting on legal review",
    next: "Ask Priya for ETA",
    domain: "legal" as Domain,
    sensitivity: "internal" as Sensitivity,
  },
];

const PEOPLE = [
  {
    name: "Priya",
    relation: "Vendor legal owner",
    evidence: "Referenced by waiting-for loop and weekly synthesis.",
    sensitivity: "internal" as Sensitivity,
  },
  {
    name: "Morgan",
    relation: "Possible launch checklist owner",
    evidence: "Older note conflicts with newer meeting capture.",
    sensitivity: "private" as Sensitivity,
  },
];

export function getVNextWorkspaceFixtureContract() {
  return {
    domains: [
      ...INITIAL_REVIEW_ITEMS.map((item) => item.domain),
      ...INITIAL_OPEN_LOOPS.map((loop) => loop.domain),
      ...INITIAL_ARTIFACTS.map((artifact) => artifact.domain),
      INITIAL_ANSWER.domain,
      ...PROJECTS.map((project) => project.domain),
      ...INITIAL_CONNECTORS.map((connector) => connector.defaultDomain),
    ],
    sensitivities: [
      ...INITIAL_REVIEW_ITEMS.map((item) => item.sensitivity),
      ...INITIAL_OPEN_LOOPS.map((loop) => loop.sensitivity),
      ...INITIAL_ARTIFACTS.map((artifact) => artifact.sensitivity),
      INITIAL_ANSWER.sensitivity,
      ...PROJECTS.map((project) => project.sensitivity),
      ...PEOPLE.map((person) => person.sensitivity),
      ...INITIAL_CONNECTORS.map((connector) => connector.defaultSensitivity),
    ],
    connectorIds: INITIAL_CONNECTORS.map((connector) => connector.id),
  };
}

const BELIEFS = [
  {
    title: "Launch readiness depends on explicit ownership.",
    confidence: "medium",
    status: "needs_review",
    evidence: ["memory.review-1", "open_loop.loop-1"],
  },
  {
    title: "Sensitive health artifacts should stay outside work retrieval.",
    confidence: "high",
    status: "active",
    evidence: ["artifact.lab-panel.pdf", "policy.domain-isolation"],
  },
];

const TIMELINE = [
  {
    time: "Today 08:30",
    title: "Inbox candidate created",
    detail: "Launch checklist owner memory entered review with work/private labels.",
  },
  {
    time: "Today 07:45",
    title: "Sensitive artifact held",
    detail: "Health PDF memory candidate paused until sensitivity review is complete.",
  },
  {
    time: "Yesterday 16:20",
    title: "Weekly synthesis found waiting-for pressure",
    detail: "Vendor legal review connected Priya to product launch risk.",
  },
];

const GRAPH_NODES = [
  "Product launch",
  "Priya",
  "Vendor legal review",
  "Launch checklist owner",
  "daily-brief-2026-05-10.md",
];

function summarizeSources(sources: string[]) {
  return sources.join(", ");
}

function pushBoundedLog(message: string, previous: string[]) {
  return [message, ...previous].slice(0, 5);
}

export function VNextBrainWorkspace() {
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>(INITIAL_REVIEW_ITEMS);
  const [selectedReviewId, setSelectedReviewId] = useState(DEFAULT_REVIEW_ITEM.id);
  const [draftTitle, setDraftTitle] = useState(DEFAULT_REVIEW_ITEM.title);
  const [draftNote, setDraftNote] = useState(DEFAULT_REVIEW_ITEM.note);
  const [draftDomain, setDraftDomain] = useState<Domain>(DEFAULT_REVIEW_ITEM.domain);
  const [draftSensitivity, setDraftSensitivity] = useState<Sensitivity>(
    DEFAULT_REVIEW_ITEM.sensitivity,
  );
  const [draftProject, setDraftProject] = useState(DEFAULT_REVIEW_ITEM.project);
  const [openLoopTitle, setOpenLoopTitle] = useState(DEFAULT_REVIEW_ITEM.title);
  const [openLoops, setOpenLoops] = useState<OpenLoopItem[]>(INITIAL_OPEN_LOOPS);
  const [artifacts, setArtifacts] = useState<GeneratedArtifact[]>(INITIAL_ARTIFACTS);
  const [connectors, setConnectors] = useState<ConnectorSetting[]>(INITIAL_CONNECTORS);
  const [selectedConnectorId, setSelectedConnectorId] = useState(INITIAL_CONNECTORS[0].id);
  const [connectorDomain, setConnectorDomain] = useState<Domain>(INITIAL_CONNECTORS[0].defaultDomain);
  const [connectorSensitivity, setConnectorSensitivity] = useState<Sensitivity>(
    INITIAL_CONNECTORS[0].defaultSensitivity,
  );
  const [question, setQuestion] = useState(INITIAL_ANSWER.question);
  const [answer, setAnswer] = useState<AskAnswer>(INITIAL_ANSWER);
  const [actionLog, setActionLog] = useState<string[]>([
    "Select a candidate, adjust labels, then accept, reject, promote, assign, or create a loop.",
  ]);

  const selectedReview =
    reviewItems.find((item) => item.id === selectedReviewId) ?? DEFAULT_REVIEW_ITEM;
  const selectedConnector =
    connectors.find((connector) => connector.id === selectedConnectorId) ?? INITIAL_CONNECTORS[0];
  const activeReviewCount = reviewItems.filter((item) => item.status === "requires_review").length;
  const promotedCount = reviewItems.filter((item) => item.status === "promoted").length;

  function logAction(message: string) {
    setActionLog((previous) => pushBoundedLog(message, previous));
  }

  function selectReview(item: ReviewItem) {
    setSelectedReviewId(item.id);
    setDraftTitle(item.title);
    setDraftNote(item.note);
    setDraftDomain(item.domain);
    setDraftSensitivity(item.sensitivity);
    setDraftProject(item.project);
    setOpenLoopTitle(item.title);
    logAction(`Selected ${item.id} for review.`);
  }

  function updateSelectedReview(patch: Partial<ReviewItem>) {
    setReviewItems((items) =>
      items.map((item) =>
        item.id === selectedReview.id
          ? {
              ...item,
              ...patch,
              updatedAt: "Now",
            }
          : item,
      ),
    );
  }

  function acceptSelectedReview() {
    updateSelectedReview({ status: "accepted" });
    logAction("Accepted candidate from Inbox review.");
  }

  function rejectSelectedReview() {
    updateSelectedReview({ status: "rejected" });
    logAction("Rejected candidate and kept source provenance for audit.");
  }

  function saveSelectedEdit() {
    const normalizedTitle = draftTitle.trim();
    const normalizedNote = draftNote.trim();
    if (!normalizedTitle) {
      logAction("Edit was not saved because the title is empty.");
      return;
    }

    updateSelectedReview({
      title: normalizedTitle,
      note: normalizedNote || selectedReview.note,
      status: "edited",
    });
    logAction("Saved edited memory text with review provenance intact.");
  }

  function promoteSelectedReview() {
    updateSelectedReview({ status: "promoted" });
    logAction("Promoted selected memory candidate to belief review.");
  }

  function applyLabels() {
    updateSelectedReview({
      domain: draftDomain,
      sensitivity: draftSensitivity,
    });
    logAction(`Applied labels: ${domainLabel(draftDomain)} / ${sensitivityLabel(draftSensitivity)}.`);
  }

  function assignProject() {
    const normalizedProject = draftProject.trim();
    if (!normalizedProject) {
      logAction("Project assignment needs a project name.");
      return;
    }

    updateSelectedReview({ project: normalizedProject });
    logAction(`Assigned selected memory to ${normalizedProject}.`);
  }

  function createOpenLoop() {
    const normalizedTitle = openLoopTitle.trim();
    if (!normalizedTitle) {
      logAction("Open-loop creation needs a title.");
      return;
    }

    const nextLoop: OpenLoopItem = {
      id: `loop-ui-${openLoops.length + 1}`,
      title: normalizedTitle,
      status: "open",
      due: "Unscheduled",
      domain: selectedReview.domain,
      sensitivity: selectedReview.sensitivity,
      sourceIds: selectedReview.sourceIds,
    };
    setOpenLoops((items) => [nextLoop, ...items]);
    logAction("Created open loop from selected memory candidate.");
  }

  function selectConnector(connector: ConnectorSetting) {
    setSelectedConnectorId(connector.id);
    setConnectorDomain(connector.defaultDomain);
    setConnectorSensitivity(connector.defaultSensitivity);
    logAction(`Selected ${connector.name} connector settings.`);
  }

  function applyConnectorDefaults() {
    setConnectors((items) =>
      items.map((connector) =>
        connector.id === selectedConnector.id
          ? {
              ...connector,
              defaultDomain: connectorDomain,
              defaultSensitivity: connectorSensitivity,
            }
          : connector,
      ),
    );
    logAction(
      `Saved ${selectedConnector.name} defaults: ${domainLabel(connectorDomain)} / ${sensitivityLabel(connectorSensitivity)}.`,
    );
  }

  function askAlice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) {
      logAction("Ask Alice needs a question before retrieval can run.");
      return;
    }

    setAnswer({
      ...INITIAL_ANSWER,
      question: normalizedQuestion,
      summary: `For "${normalizedQuestion}", Alice would focus on the launch owner and vendor legal waiting-for item, while excluding sensitive health evidence from the work-domain answer.`,
    });
    logAction("Ask Alice refreshed the answer with sources, memories, contradictions, and why explanation.");
  }

  function saveAnswerAsArtifact() {
    const nextIndex = artifacts.length + 1;
    const artifact: GeneratedArtifact = {
      id: `artifact-ui-${nextIndex}`,
      title: `ask-alice-answer-${nextIndex}.md`,
      type: "Ask Alice Answer",
      status: "registered",
      summary: answer.summary,
      domain: answer.domain,
      sensitivity: answer.sensitivity,
      sources: answer.sources,
      provenance: "Saved from Ask Alice answer with retrieval context, memory use, contradictions, and why explanation.",
    };
    setArtifacts((items) => [artifact, ...items]);
    logAction(`Saved ${artifact.title} with provenance.`);
  }

  return (
    <div className="page-stack">
      <nav className="vnext-surface-nav" aria-label="Alice vNext surfaces">
        {SURFACES.map((surface) => (
          <a
            key={surface}
            className="vnext-surface-nav__item"
            href={`#vnext-${surface.toLowerCase().replace(/\s+/g, "-")}`}
          >
            {surface}
          </a>
        ))}
      </nav>

      <section id="vnext-home" className="metric-grid" aria-label="vNext home dashboard">
        <SectionCard className="section-card--metric">
          <div className="metric-value">{activeReviewCount}</div>
          <div className="metric-label">Review items</div>
          <p className="metric-detail">Inbox candidates awaiting accept, edit, reject, or promotion.</p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">{openLoops.length}</div>
          <div className="metric-label">Open loops</div>
          <p className="metric-detail">Due-soon and waiting-for items stay visible from the first screen.</p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">{PROJECTS.length}</div>
          <div className="metric-label">Active projects</div>
          <p className="metric-detail">Project state includes next action, blockers, domain, and sensitivity.</p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">{promotedCount}</div>
          <div className="metric-label">Promoted beliefs</div>
          <p className="metric-detail">Belief promotion is explicit and remains traceable to the reviewed source.</p>
        </SectionCard>
      </section>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Home"
          title="Today at a glance"
          description="Brief, review pressure, open loops, active project status, connections, contradictions, and queue posture are visible before the operator asks anything."
        >
          <div className="detail-stack">
            <div className="governance-banner">
              <strong>Today&apos;s brief summary</strong>
              <span>
                Confirm launch ownership, clear one waiting-for item, and keep sensitive health evidence
                out of work-domain retrieval until review is complete.
              </span>
            </div>
            <div className="key-value-grid">
              <div>
                <dt>Recent connection</dt>
                <dd>Priya connects vendor legal review to the product launch blocker cluster.</dd>
              </div>
              <div>
                <dt>Contradiction</dt>
                <dd>Older notes name Morgan as owner; the latest capture says owner is not confirmed.</dd>
              </div>
              <div>
                <dt>Queue status</dt>
                <dd>Memory review has {activeReviewCount} candidates and one sensitive label gate.</dd>
              </div>
              <div>
                <dt>Active project</dt>
                <dd>Product launch is active with ownership still unresolved.</dd>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Settings"
          title="Privacy and retrieval posture"
          description="Domain and sensitivity labels are visible on review items, generated artifacts, questions, and open loops."
        >
          <div id="vnext-settings" className="detail-stack">
            <div className="cluster">
              <StatusBadge status="active" label="Local-first" />
              <StatusBadge status="requires_review" label="Sensitive items held" />
              <span className="meta-pill">Default domain: {domainLabel("professional")}</span>
              <span className="meta-pill">Default sensitivity: {sensitivityLabel("private")}</span>
            </div>
            <p className="muted-copy">
              Retrieval should use reviewed evidence first, suppress sensitive cross-domain evidence, and show
              exactly which memories and artifacts influenced the answer.
            </p>
          </div>
        </SectionCard>
      </div>

      <div id="vnext-inbox" className="vnext-review-layout">
        <SectionCard
          eyebrow="Inbox"
          title="Review queue"
          description="Candidates are fixture-backed here, but the controls exercise the intended accept, edit, reject, promote, assign, label, and open-loop flow end to end."
        >
          <div className="list-rows">
            {reviewItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`list-row vnext-review-button${
                  item.id === selectedReview.id ? " is-selected" : ""
                }`}
                onClick={() => selectReview(item)}
              >
                <span className="list-row__topline">
                  <span className="detail-stack">
                    <span className="list-row__eyebrow mono">{item.kind}</span>
                    <span className="list-row__title">{item.title}</span>
                  </span>
                  <StatusBadge status={item.status} />
                </span>
                <span className="list-row__meta">
                  <span className="meta-pill">Domain: {domainLabel(item.domain)}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(item.sensitivity)}</span>
                  <span className="meta-pill">Project: {item.project}</span>
                </span>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Review actions"
          title="Selected memory candidate"
          description="The selected item keeps provenance, project assignment, and labels attached while review actions update visible state."
        >
          <div className="detail-stack">
            <div className="cluster">
              <StatusBadge status={selectedReview.status} />
              <span className="meta-pill">Domain: {domainLabel(selectedReview.domain)}</span>
              <span className="meta-pill">Sensitivity: {sensitivityLabel(selectedReview.sensitivity)}</span>
              <span className="meta-pill">Project: {selectedReview.project}</span>
            </div>

            <div className="detail-group detail-group--muted">
              <h3>Provenance</h3>
              <p className="muted-copy">{selectedReview.provenance}</p>
              <div className="cluster">
                {selectedReview.sourceIds.map((source) => (
                  <span key={source} className="meta-pill">
                    {source}
                  </span>
                ))}
              </div>
            </div>

            <div className="form-field-group">
              <div className="form-field">
                <label htmlFor="vnext-review-title">Edited memory title</label>
                <textarea
                  id="vnext-review-title"
                  value={draftTitle}
                  onChange={(event) => setDraftTitle(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="vnext-review-note">Reviewer note</label>
                <textarea
                  id="vnext-review-note"
                  value={draftNote}
                  onChange={(event) => setDraftNote(event.target.value)}
                />
              </div>
            </div>

            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-domain">Domain label</label>
                <select
                  id="vnext-domain"
                  value={draftDomain}
                  onChange={(event) => setDraftDomain(event.target.value as Domain)}
                >
                  {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                    <option key={domain.value} value={domain.value}>
                      {domain.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-sensitivity">Sensitivity label</label>
                <select
                  id="vnext-sensitivity"
                  value={draftSensitivity}
                  onChange={(event) => setDraftSensitivity(event.target.value as Sensitivity)}
                >
                  {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                    <option key={sensitivity.value} value={sensitivity.value}>
                      {sensitivity.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-project">Assigned project</label>
                <input
                  id="vnext-project"
                  value={draftProject}
                  onChange={(event) => setDraftProject(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="vnext-open-loop">Open-loop title</label>
                <input
                  id="vnext-open-loop"
                  value={openLoopTitle}
                  onChange={(event) => setOpenLoopTitle(event.target.value)}
                />
              </div>
            </div>

            <div className="vnext-review-actions">
              <button type="button" className="button" onClick={acceptSelectedReview}>
                Accept selected memory
              </button>
              <button type="button" className="button-secondary" onClick={saveSelectedEdit}>
                Save selected edit
              </button>
              <button type="button" className="button-secondary" onClick={promoteSelectedReview}>
                Promote to belief
              </button>
              <button type="button" className="button-secondary" onClick={assignProject}>
                Assign project
              </button>
              <button type="button" className="button-secondary" onClick={applyLabels}>
                Apply domain and sensitivity labels
              </button>
              <button type="button" className="button-secondary" onClick={createOpenLoop}>
                Create open loop from selected memory
              </button>
              <button type="button" className="button-secondary button-secondary--danger" onClick={rejectSelectedReview}>
                Reject selected memory
              </button>
            </div>

            <div className="composer-status" aria-live="polite">
              <StatusBadge status={selectedReview.status} label="Latest action" />
              <span>{actionLog[0]}</span>
            </div>
          </div>
        </SectionCard>
      </div>

      <div id="vnext-ask-alice" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Ask Alice"
          title="Evidence-first answer"
          description="Answers show direct sources, memories used, contradictions, why explanation, and a generated-artifact save action."
        >
          <form className="detail-stack" onSubmit={askAlice}>
            <div className="form-field">
              <label htmlFor="vnext-ask-question">Ask Alice question</label>
              <textarea
                id="vnext-ask-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
            </div>
            <div className="composer-actions">
              <button type="submit" className="button">
                Ask Alice
              </button>
              <button type="button" className="button-secondary" onClick={saveAnswerAsArtifact}>
                Save answer as artifact
              </button>
            </div>
          </form>

          <div className="transcript-entry transcript-entry--assistant" aria-live="polite">
            <div className="transcript-entry__heading">
              <span className="transcript-entry__role transcript-entry__role--assistant">
                Alice answer
              </span>
              <span className="meta-pill">Domain: {domainLabel(answer.domain)}</span>
              <span className="meta-pill">Sensitivity: {sensitivityLabel(answer.sensitivity)}</span>
            </div>
            <p className="response-copy">{answer.summary}</p>
            <div className="key-value-grid">
              <div>
                <dt>Memory sources used</dt>
                <dd>{answer.memoriesUsed.join(" ")}</dd>
              </div>
              <div>
                <dt>Contradictions</dt>
                <dd>{answer.contradictions.join(" ")}</dd>
              </div>
              <div>
                <dt>Why this answer</dt>
                <dd>{answer.why.join(" ")}</dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>{summarizeSources(answer.sources)}</dd>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Generated"
          title="Artifacts with provenance"
          description="Every generated item displays status, source IDs, provenance, domain, and sensitivity before it can be trusted."
        >
          <div id="vnext-generated" className="list-rows">
            {artifacts.map((artifact) => (
              <article key={artifact.id} className="list-row">
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow mono">{artifact.type}</span>
                    <h3 className="list-row__title">{artifact.title}</h3>
                  </div>
                  <StatusBadge status={artifact.status} />
                </div>
                <p>{artifact.summary}</p>
                <div className="list-row__meta">
                  <span className="meta-pill">Domain: {domainLabel(artifact.domain)}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(artifact.sensitivity)}</span>
                  <span className="meta-pill">Sources: {summarizeSources(artifact.sources)}</span>
                </div>
                <p className="responsive-note">Provenance: {artifact.provenance}</p>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Daily Brief"
          title="Daily brief review"
          description="A non-technical operator can read the day, see why items were selected, and inspect source provenance."
        >
          <div id="vnext-daily-brief" className="list-rows">
            {DAILY_BRIEF_ITEMS.map((item) => (
              <article key={item.title} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{item.title}</h3>
                  <StatusBadge status={item.status} />
                </div>
                <p>{item.body}</p>
                <span className="meta-pill">Sources: {summarizeSources(item.sources)}</span>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Weekly Synthesis"
          title="Synthesis signals"
          description="Weekly synthesis turns reviewed memories, project edges, and open loops into explainable planning signals."
        >
          <div id="vnext-weekly-synthesis" className="list-rows">
            {WEEKLY_SIGNALS.map((signal) => (
              <article key={signal.text} className="list-row">
                <span className="list-row__eyebrow mono">{signal.label}</span>
                <p>{signal.text}</p>
                <span className="meta-pill">Sources: {summarizeSources(signal.sources)}</span>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Queue"
          title="Work queue"
          description="Queue state is visible as a first-class operational surface, not hidden behind chat."
        >
          <div id="vnext-queue" className="key-value-grid">
            <div>
              <dt>Memory review</dt>
              <dd>{activeReviewCount} candidates waiting for review.</dd>
            </div>
            <div>
              <dt>Artifact generation</dt>
              <dd>{artifacts.length} generated artifacts are available for inspection.</dd>
            </div>
            <div>
              <dt>Contradictions</dt>
              <dd>One ownership contradiction is unresolved.</dd>
            </div>
            <div>
              <dt>Sensitive gates</dt>
              <dd>One Health / Highly sensitive artifact is withheld from work retrieval.</dd>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Memory Review"
          title="Review candidates"
          description="Memory review shows candidate type, review state, source IDs, and labels before anything becomes trusted."
        >
          <div id="vnext-memory-review" className="list-rows">
            {reviewItems.map((item) => (
              <article key={`memory-${item.id}`} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{item.title}</h3>
                  <StatusBadge status={item.status} />
                </div>
                <p>{item.note}</p>
                <div className="list-row__meta">
                  <span className="meta-pill">Domain: {domainLabel(item.domain)}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(item.sensitivity)}</span>
                  <span className="meta-pill">Sources: {summarizeSources(item.sourceIds)}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div id="vnext-projects" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Projects"
          title="Project state"
          description="Projects expose status, next action, connected loops, and labels."
        >
          <div className="list-rows">
            {PROJECTS.map((project) => (
              <article key={project.name} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{project.name}</h3>
                  <StatusBadge status={project.status} />
                </div>
                <p>{project.progress}</p>
                <div className="list-row__meta">
                  <span className="meta-pill">Next: {project.next}</span>
                  <span className="meta-pill">Domain: {domainLabel(project.domain)}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(project.sensitivity)}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="People"
          title="People graph"
          description="People records show the relationship and evidence path that placed them in the current context."
        >
          <div id="vnext-people" className="list-rows">
            {PEOPLE.map((person) => (
              <article key={person.name} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{person.name}</h3>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(person.sensitivity)}</span>
                </div>
                <p>{person.relation}</p>
                <p className="responsive-note">Evidence: {person.evidence}</p>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Beliefs"
          title="Belief review"
          description="Beliefs keep confidence, review state, and evidence attached so Alice can explain what she thinks she knows."
        >
          <div id="vnext-beliefs" className="list-rows">
            {BELIEFS.map((belief) => (
              <article key={belief.title} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{belief.title}</h3>
                  <StatusBadge status={belief.status} />
                </div>
                <div className="list-row__meta">
                  <span className="meta-pill">Confidence: {belief.confidence}</span>
                  <span className="meta-pill">Evidence: {summarizeSources(belief.evidence)}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Open Loops"
          title="Due and waiting items"
          description="Open loops remain editable and source-backed from review, daily brief, and project views."
        >
          <div id="vnext-open-loops" className="list-rows">
            {openLoops.map((loop) => (
              <article key={loop.id} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{loop.title}</h3>
                  <StatusBadge status={loop.status} />
                </div>
                <div className="list-row__meta">
                  <span className="meta-pill">Due: {loop.due}</span>
                  <span className="meta-pill">Domain: {domainLabel(loop.domain)}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(loop.sensitivity)}</span>
                  <span className="meta-pill">Sources: {summarizeSources(loop.sourceIds)}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Timeline"
          title="Brain timeline"
          description="Timeline entries make capture, review, synthesis, and contradiction events inspectable in one chronological stream."
        >
          <div id="vnext-timeline" className="timeline-list">
            {TIMELINE.map((item) => (
              <article key={`${item.time}-${item.title}`} className="timeline-item">
                <div className="timeline-item__topline">
                  <span className="list-row__eyebrow mono">{item.time}</span>
                  <h3 className="list-row__title">{item.title}</h3>
                </div>
                <p>{item.detail}</p>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Graph"
          title="Connection graph"
          description="The first graph surface exposes nodes, edges, filters, and evidence labels without requiring a 3D visualization."
        >
          <div id="vnext-graph" className="vnext-graph-grid">
            <div className="vnext-graph-canvas" aria-label="Graph preview">
              {GRAPH_NODES.map((node, index) => (
                <span key={node} className={`vnext-graph-node vnext-graph-node--${index + 1}`}>
                  {node}
                </span>
              ))}
            </div>
            <div className="detail-stack">
              <div className="cluster">
                <span className="meta-pill">Filter: Work</span>
                <span className="meta-pill">Sensitivity: Private + Internal</span>
                <span className="meta-pill">Edges: project, person, source</span>
              </div>
              <p className="muted-copy">
                Selected path: Product launch to Vendor legal review to Priya to weekly synthesis.
              </p>
            </div>
          </div>
        </SectionCard>
      </div>

      <div id="vnext-connectors" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Connectors"
          title="Connector settings"
          description="Connector defaults stay explicit before Telegram, browser clips, documents, screenshots, and voice transcripts enter memory."
        >
          <div className="list-rows">
            {connectors.map((connector) => (
              <button
                key={connector.id}
                type="button"
                className={`list-row vnext-review-button${
                  connector.id === selectedConnector.id ? " vnext-review-button--active" : ""
                }`}
                onClick={() => selectConnector(connector)}
              >
                <span className="list-row__topline">
                  <span className="list-row__title">{connector.name}</span>
                  <StatusBadge status={connector.status} />
                </span>
                <span className="list-row__meta">
                  <span className="meta-pill">{connector.stage}</span>
                  <span className="meta-pill">Default domain: {domainLabel(connector.defaultDomain)}</span>
                  <span className="meta-pill">
                    Default sensitivity: {sensitivityLabel(connector.defaultSensitivity)}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected Connector"
          title={selectedConnector.name}
          description="Defaults, cursor posture, and raw evidence handling remain visible before sync runs."
        >
          <div className="detail-stack">
            <div className="key-value-grid key-value-grid--compact">
              <div>
                <dt>Cursor</dt>
                <dd>{selectedConnector.cursor}</dd>
              </div>
              <div>
                <dt>Raw evidence</dt>
                <dd>{selectedConnector.evidence}</dd>
              </div>
              <div>
                <dt>Failure posture</dt>
                <dd>{selectedConnector.failureMode}</dd>
              </div>
              <div>
                <dt>Sync state</dt>
                <dd>{selectedConnector.status}</dd>
              </div>
            </div>

            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-connector-domain">Connector domain default</label>
                <select
                  id="vnext-connector-domain"
                  value={connectorDomain}
                  onChange={(event) => setConnectorDomain(event.target.value as Domain)}
                >
                  {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                    <option key={domain.value} value={domain.value}>
                      {domain.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-connector-sensitivity">Connector sensitivity default</label>
                <select
                  id="vnext-connector-sensitivity"
                  value={connectorSensitivity}
                  onChange={(event) => setConnectorSensitivity(event.target.value as Sensitivity)}
                >
                  {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                    <option key={sensitivity.value} value={sensitivity.value}>
                      {sensitivity.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button type="button" className="button button--primary" onClick={applyConnectorDefaults}>
              Save connector defaults
            </button>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
