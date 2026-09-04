import { humanize } from "@/lib/format";

export function StatusBadge({ status }: { status: string }) {
  const tone = status === "FAILED" ? "danger" :
    status === "COMPLETED" ? "success" :
    status === "COMPLETED_WITH_WARNINGS" ? "warning" : "active";
  return <span className={`status-badge status-${tone}`}><i aria-hidden="true" />{humanize(status)}</span>;
}
