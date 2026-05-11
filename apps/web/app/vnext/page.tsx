import { PageHeader } from "../../components/page-header";
import { VNextBrainWorkspace } from "../../components/vnext-brain-workspace";
import { getApiConfig, hasLiveApiConfig, pageModeLabel } from "../../lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }
  return value?.trim() ?? "";
}

export default async function VNextPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<string, string | string[] | undefined>;
  const demoMode = normalizeParam(params.mode).toLowerCase() === "demo";
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig) && !demoMode;
  const source = liveModeReady ? "live" : "fixture";
  const modeLabel = liveModeReady ? "Live default" : demoMode ? "Demo mode" : "Demo fallback";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Alice vNext"
        title="True second-brain workspace"
        description="A live-backed local workspace for capturing vNext sources, reviewing candidate memories, asking Alice with provenance, generating briefs, and keeping projects, loops, artifacts, and privacy labels in one loop."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(source)}</span>
            <span className="subtle-chip">{modeLabel}</span>
            <span className="subtle-chip">Domain and sensitivity aware</span>
          </div>
        }
      />

      <VNextBrainWorkspace
        apiBaseUrl={liveModeReady ? apiConfig.apiBaseUrl : undefined}
        userId={liveModeReady ? apiConfig.userId : undefined}
        initialSource={source}
      />
    </div>
  );
}
