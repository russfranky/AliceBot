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
  "Model Comparison",
  "Memory Review",
  "Projects",
  "People",
  "Beliefs",
  "Open Loops",
  "Agent Activity",
  "Schedules",
  "Timeline",
  "Trace",
  "Graph",
  "Connectors",
  "Doctor",
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
  "local_folder",
  "agent_output",
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

  async function renderVNextPage() {
    render(await VNextPage({}));
  }

  it("renders the full fixture-backed vNext brain workspace", async () => {
    await renderVNextPage();

    expect(screen.getByRole("heading", { name: "True second-brain workspace" })).toBeInTheDocument();
    expect(screen.getByText("Demo fallback")).toBeInTheDocument();

    for (const surface of EXPECTED_SURFACES) {
      expect(screen.getByRole("link", { name: surface })).toBeInTheDocument();
    }

    expect(screen.getByText("Recent activity")).toBeInTheDocument();
    expect(screen.getByText("Source capture")).toBeInTheDocument();
    expect(screen.getAllByText("Candidate memories").length).toBeGreaterThan(0);
    expect(screen.getByText("Evidence-first answer")).toBeInTheDocument();
    expect(screen.getByText("Artifacts with review actions")).toBeInTheDocument();
    expect(screen.getByText("Belief review")).toBeInTheDocument();
    expect(screen.getByText("Agents and policy posture")).toBeInTheDocument();
    expect(screen.getByText("Governed scheduler")).toBeInTheDocument();
    expect(screen.getByText("Capture-to-brief trace")).toBeInTheDocument();
    expect(screen.getByText("Connection graph")).toBeInTheDocument();
    expect(screen.getByText("Connector settings")).toBeInTheDocument();
    expect(screen.getByText("Readiness checks")).toBeInTheDocument();
    expect(screen.getByText("Brain Charter")).toBeInTheDocument();
    expect(screen.getAllByText("Telegram capture").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Browser clipper").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DOCX processing").length).toBeGreaterThan(0);
    expect(screen.getAllByText("CSV processing").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Screenshot processing").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Domain: Work").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Private").length).toBeGreaterThan(0);
    expect(screen.getByText("Memory sources used")).toBeInTheDocument();
    expect(screen.getAllByText("Contradictions").length).toBeGreaterThan(0);
    expect(screen.getByText("Why this answer")).toBeInTheDocument();
    expect(screen.getByText("OpenClaw")).toBeInTheDocument();
    expect(screen.getByText("Hermes")).toBeInTheDocument();
    expect(screen.getByText("Recent scheduler runs")).toBeInTheDocument();
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

  it("updates review state, labels, project assignment, and open loops from Inbox actions", async () => {
    await renderVNextPage();

    fireEvent.change(screen.getByLabelText("Selected source title"), {
      target: { value: "Reviewed launch source" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save source update" }));
    expect(screen.getAllByText("Demo source action applied: update.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Reviewed launch source").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Mark reviewed" }));
    expect(screen.getAllByText("Demo source action applied: review.").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Edited memory title"), {
      target: { value: "Confirmed launch owner needs explicit review." },
    });
    fireEvent.change(screen.getByLabelText("Edited memory text"), {
      target: { value: "Confirmed launch owner needs explicit review." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save edit" }));
    expect(screen.getAllByText("Confirmed launch owner needs explicit review.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Demo memory review action applied: edit.").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Domain label"), {
      target: { value: "financial" },
    });
    fireEvent.change(screen.getByLabelText("Sensitivity label"), {
      target: { value: "confidential" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save edit" }));
    expect(screen.getAllByText("Demo memory review action applied: edit.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Domain: Financial").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Confidential").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Assign project" }));
    expect(screen.getAllByText("Demo memory review action applied: assign_project.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(screen.getAllByText("Demo memory review action applied: accept.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Promote" }));
    expect(screen.getAllByText("Demo memory review action applied: promote.").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Open-loop title"), {
      target: { value: "Follow up with Sam about launch owner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create open loop from selected memory" }));
    expect(screen.getAllByText("Demo open loop created.").length).toBeGreaterThan(0);
    expect(screen.getByText("Follow up with Sam about launch owner")).toBeInTheDocument();
  }, 10000);

  it("refreshes Ask Alice output and generates reviewable artifacts", async () => {
    await renderVNextPage();

    fireEvent.change(screen.getByLabelText("Ask Alice question"), {
      target: { value: "Where is the launch risk concentrated?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Alice" }));

    expect(
      screen.getByText(
        /For "Where is the launch risk concentrated\?", Alice would focus on launch ownership/i,
      ),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Generate daily brief" }));
    expect(screen.getAllByText("Demo daily artifact generated.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Generate weekly synthesis" }));
    expect(screen.getAllByText("Demo weekly artifact generated.").length).toBeGreaterThan(0);
  });

  it("updates governed scheduler fixture state", async () => {
    await renderVNextPage();

    fireEvent.click(screen.getAllByRole("button", { name: "Enable" })[0]);
    expect(screen.getAllByText("Demo scheduler action applied: enable.").length).toBeGreaterThan(0);

    fireEvent.change(screen.getAllByLabelText("Time of day")[0], {
      target: { value: "07:30" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Edit schedule" })[0]);
    expect(screen.getAllByText("Demo scheduler action applied: update_schedule.").length).toBeGreaterThan(0);
    expect(screen.getByText(/Daily at 07:30 UTC/)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Run now" })[0]);
    expect(screen.getAllByText("Demo scheduler action applied: run_now.").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/scheduler-run-demo-1/).length).toBeGreaterThan(0);
  });

  it("saves Brain Charter settings and keeps connector settings visible", async () => {
    await renderVNextPage();

    fireEvent.change(screen.getByLabelText("Charter sensitivity"), {
      target: { value: "confidential" },
    });
    fireEvent.change(screen.getByLabelText("Brain Charter Markdown"), {
      target: { value: "# ALICE.md\n\nUse provenance-first review." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Brain Charter" }));

    expect(screen.getAllByText("Demo Brain Charter settings saved.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Browser clipper").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Default sensitivity: Private").length).toBeGreaterThan(0);
  });

  it("runs fixture doctor checks from the readiness panel", async () => {
    await renderVNextPage();

    fireEvent.click(screen.getByRole("button", { name: "Run doctor" }));

    expect(screen.getAllByText("Demo doctor check completed.").length).toBeGreaterThan(0);
    expect(screen.getByText("Doctor: pass")).toBeInTheDocument();
  });
});
