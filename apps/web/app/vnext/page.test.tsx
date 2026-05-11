import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

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
    expect(screen.getAllByText("Domain: Work").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Private").length).toBeGreaterThan(0);
    expect(screen.getByText("Memory sources used")).toBeInTheDocument();
    expect(screen.getAllByText("Contradictions").length).toBeGreaterThan(0);
    expect(screen.getByText("Why this answer")).toBeInTheDocument();
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
      target: { value: "Operations" },
    });
    fireEvent.change(screen.getByLabelText("Sensitivity label"), {
      target: { value: "Internal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply domain and sensitivity labels" }));
    expect(screen.getByText("Applied labels: Operations / Internal.")).toBeInTheDocument();
    expect(screen.getAllByText("Domain: Operations").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sensitivity: Internal").length).toBeGreaterThan(0);

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
      target: { value: "Operations" },
    });
    fireEvent.change(screen.getByLabelText("Connector sensitivity default"), {
      target: { value: "Internal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save connector defaults" }));

    expect(screen.getByText("Saved Browser clipper defaults: Operations / Internal.")).toBeInTheDocument();
    expect(screen.getAllByText("Default domain: Operations").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Default sensitivity: Internal").length).toBeGreaterThan(0);
  });
});
