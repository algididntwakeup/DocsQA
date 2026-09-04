import type { DocumentStatus } from "@/lib/api";
import { humanize } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function ScanProgress({ scan }: { scan: DocumentStatus }) {
  return (
    <section className="panel scan-panel" aria-labelledby="scan-heading">
      <div className="panel-heading">
        <div><p className="eyebrow">Pipeline telemetry</p><h2 id="scan-heading">Extraction progress</h2></div>
        <StatusBadge status={scan.status} />
      </div>
      <div className="master-progress">
        <div><span>Overall completion</span><strong>{scan.progress_pct}%</strong></div>
        <progress max="100" value={scan.progress_pct}>{scan.progress_pct}%</progress>
      </div>
      {scan.stages.length === 0 ? (
        <p className="empty-inline">Waiting for the extraction worker to start…</p>
      ) : (
        <ol className="stage-list">
          {scan.stages.map((stage) => (
            <li key={stage.id}>
              <div className="stage-index" aria-hidden="true">{String(stage.attempt).padStart(2, "0")}</div>
              <div className="stage-copy">
                <div><strong>{humanize(stage.name)}</strong><span>{stage.progress_pct}%</span></div>
                <progress max="100" value={stage.progress_pct}>{stage.progress_pct}%</progress>
                {stage.error_message && <p role="alert">{stage.error_message}</p>}
              </div>
              <StatusBadge status={stage.status} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
