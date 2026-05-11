import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  VNEXT_DOMAIN_OPTIONS,
  VNEXT_SENSITIVITY_OPTIONS,
  VNEXT_SUPPORTED_CONNECTOR_IDS,
  getVNextWorkspaceFixtureContract,
} from "../../components/vnext-brain-workspace";
import VNextPage from "./page";

const EXPECTED_SURFACES = [
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

const EXPECTED_VNEXT_DOMAINS = [
  "professional",
  "personal",
  "family",
  "health",
  "spiritual",
  "financial",
  "legal",
  "learning",
  "relationship",
  "project",
  "agent_run",
  "system",
  "unknown",
];

const EXPECTED_VNEXT_SENSITIVITIES = [
  "public",
  "internal",
  "private",
  "confidential",
  "highly_sensitive",
  "sacred",
  "regulated",
  "unknown",
];

const EXPECTED_SPRINT_11_CONNECTORS = [
  "telegram",
  "browser_clipper",
  "pdf_document",
  "docx_document",
  "csv_table",
  "screenshot_ocr",
  "voice_transcription",
];

describe("VNextPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders the full fixture-backed vNext brain workspace", () => {
    render(<VNextPage />);

    expect(screen.getByRole("heading", { name: "True second-brain workspace" })).toBeInTheDocument();
    expect(screen.getByText("Sprint 11 connector seed")).toBeInTheDocument();

    for (const surface of EXPECTED_SURFACES) {
      expect(screen.getByRole("link", { name: surface })).toBeInTheDocument();
    }

    expect(screen.getByText("Today at a glance")).toBeInTheDocument();
    expect(screen.getByText("Review queue")).toBeInTheDocument();
    expect(screen.getByText("Evidence-first answer")).toBeInTheDocument();
    expect(screen.getByText("Artifacts with provenance")).toBeInTheDocument();
    expect(screen.getByText("Belief review")).toBeInTheDocument();
    expect(screen.getByText("Connection graph")).toBeInTheDocument();
    expect(screen.getByText("Connector settings")).toBeInTheDocument();
    expect(screen.getAllByText("Telegram capture").length).toBeGreaterThan(0);
    expect(screen.getByText("Browser clipper")).toBeInTheDocument();
    expect(screen.getByText("DOCX processing")).toBeInTheDocument();
    expect(screen.getByText("CSV processing")).toBeInTheDocument();
    expect(screen.getByText("Screenshot processing")).toBeInTheDocument();
    expect(screen.getAllByText("Domain: Work").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Private").length).toBeGreaterThan(0);
    expect(screen.getByText("Memory sources used")).toBeInTheDocument();
    expect(screen.getAllByText("Contradictions").length).toBeGreaterThan(0);
    expect(screen.getByText("Why this answer")).toBeInTheDocument();
  });

  it("keeps fixture labels aligned to vNext schema values and connector contracts", () => {
    const fixture = getVNextWorkspaceFixtureContract();
    const domainValues = VNEXT_DOMAIN_OPTIONS.map((option) => option.value);
    const sensitivityValues = VNEXT_SENSITIVITY_OPTIONS.map((option) => option.value);

    expect(domainValues).toEqual(EXPECTED_VNEXT_DOMAINS);
    expect(sensitivityValues).toEqual(EXPECTED_VNEXT_SENSITIVITIES);
    expect([...VNEXT_SUPPORTED_CONNECTOR_IDS]).toEqual(EXPECTED_SPRINT_11_CONNECTORS);
    expect(fixture.connectorIds).toEqual(EXPECTED_SPRINT_11_CONNECTORS);
    expect(fixture.domains.every((domain) => EXPECTED_VNEXT_DOMAINS.includes(domain))).toBe(true);
    expect(
      fixture.sensitivities.every((sensitivity) =>
        EXPECTED_VNEXT_SENSITIVITIES.includes(sensitivity),
      ),
    ).toBe(true);
  });

  it("updates review state, labels, project assignment, and open loops from Inbox actions", () => {
    render(<VNextPage />);

    fireEvent.change(screen.getByLabelText("Edited memory title"), {
      target: { value: "Confirmed launch owner needs explicit review." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save selected edit" }));
    expect(screen.getAllByText("Confirmed launch owner needs explicit review.").length).toBeGreaterThan(0);
    expect(screen.getByText("Saved edited memory text with review provenance intact.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Domain label"), {
      target: { value: "financial" },
    });
    fireEvent.change(screen.getByLabelText("Sensitivity label"), {
      target: { value: "confidential" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply domain and sensitivity labels" }));
    expect(screen.getByText("Applied labels: Financial / Confidential.")).toBeInTheDocument();
    expect(screen.getAllByText("Domain: Financial").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Confidential").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Assigned project"), {
      target: { value: "Launch command center" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Assign project" }));
    expect(screen.getByText("Assigned selected memory to Launch command center.")).toBeInTheDocument();
    expect(screen.getAllByText("Project: Launch command center").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Accept selected memory" }));
    expect(screen.getByText("Accepted candidate from Inbox review.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Promote to belief" }));
    expect(screen.getByText("Promoted selected memory candidate to belief review.")).toBeInTheDocument();
    expect(screen.getAllByText("Promoted").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Open-loop title"), {
      target: { value: "Follow up with Sam about launch owner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create open loop from selected memory" }));
    expect(screen.getByText("Created open loop from selected memory candidate.")).toBeInTheDocument();
    expect(screen.getByText("Follow up with Sam about launch owner")).toBeInTheDocument();
  });

  it("refreshes Ask Alice output and saves the answer as a generated artifact with provenance", () => {
    render(<VNextPage />);

    fireEvent.change(screen.getByLabelText("Ask Alice question"), {
      target: { value: "Where is the launch risk concentrated?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Alice" }));

    expect(
      screen.getByText(
        /For "Where is the launch risk concentrated\?", Alice would focus on the launch owner/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/open_loop\.loop-1/).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Save answer as artifact" }));
    expect(screen.getByText("ask-alice-answer-3.md")).toBeInTheDocument();
    expect(screen.getByText("Saved ask-alice-answer-3.md with provenance.")).toBeInTheDocument();
    expect(screen.getAllByText(/Provenance:/).length).toBeGreaterThan(0);
  });

  it("updates connector defaults from the settings surface", () => {
    render(<VNextPage />);

    fireEvent.click(screen.getByRole("button", { name: /Browser clipper/i }));
    fireEvent.change(screen.getByLabelText("Connector domain default"), {
      target: { value: "project" },
    });
    fireEvent.change(screen.getByLabelText("Connector sensitivity default"), {
      target: { value: "confidential" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save connector defaults" }));

    expect(screen.getByText("Saved Browser clipper defaults: Project / Confidential.")).toBeInTheDocument();
    expect(screen.getAllByText("Default domain: Project").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Default sensitivity: Confidential").length).toBeGreaterThan(0);
  });
});
