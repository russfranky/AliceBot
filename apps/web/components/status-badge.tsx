type StatusBadgeProps = {
  status: string;
  label?: string;
};

function normalizeStatus(status: string) {
  return status.trim().toLowerCase().replace(/\s+/g, "_");
}

function toneForStatus(status: string) {
  const normalized = normalizeStatus(status);

  if (
    [
      "approved",
      "executed",
      "completed",
      "active",
      "ready",
      "success",
      "ingested",
      "accepted",
      "promoted",
    ].includes(normalized)
  ) {
    return "success";
  }

  if (normalized === "correct") {
    return "success";
  }

  if (
    [
      "pending",
      "pending_approval",
      "requires_review",
      "created",
      "blocked",
      "approval_required",
      "executing",
      "outdated",
      "insufficient_evidence",
      "edited",
    ].includes(normalized)
  ) {
    return normalized === "blocked" ? "danger" : "warning";
  }

  if (
    [
      "denied",
      "rejected",
      "inactive",
      "superseded",
      "error",
      "failed",
      "incorrect",
      "deleted",
    ].includes(normalized)
  ) {
    return "danger";
  }

  if (["info", "live", "loading", "submitting", "registered"].includes(normalized)) {
    return "info";
  }

  if (["fixture", "preview", "draft", "unavailable"].includes(normalized)) {
    return "neutral";
  }

  return "neutral";
}

function formatLabel(status: string) {
  return status
    .replace(/_/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const tone = toneForStatus(status);

  return <span className={`status-badge status-badge--${tone}`}>{label ?? formatLabel(status)}</span>;
}
