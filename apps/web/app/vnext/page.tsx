import { PageHeader } from "../../components/page-header";
import { VNextBrainWorkspace } from "../../components/vnext-brain-workspace";

export default function VNextPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Alice vNext"
        title="True second-brain workspace"
        description="A fixture-backed UI seed for the vNext memory kernel: review incoming memories, ask Alice with provenance, read briefs, inspect generated artifacts, and keep projects, beliefs, loops, graph, and privacy labels visible."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Sprint 11 connector seed</span>
            <span className="subtle-chip">Fixture-backed</span>
            <span className="subtle-chip">Domain and sensitivity aware</span>
          </div>
        }
      />

      <VNextBrainWorkspace />
    </div>
  );
}
