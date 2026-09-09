import type { DocumentStatus } from "@/lib/api";
import { StatusBadge } from "./status-badge";

export function ScanProgress({ scan }: { scan: DocumentStatus }) {
  const isProcessing = scan.status === "QUEUED" || scan.status === "PROCESSING";
  const activeStage = [...scan.stages].reverse().find((stage) => stage.status === "RUNNING");
  const stageCopy: Record<string, { title: string; description: string }> = {
    EXTRACTING: {
      title: "Reading the PDF",
      description: "Extracting text, page structure, and document coordinates.",
    },
    LAYOUT_INSPECTION: {
      title: "Inspecting document layout",
      description: "Checking page continuity, whitespace, navigation, and document control.",
    },
    BUDINSKI_AUDIT: {
      title: "Reviewing technical writing",
      description: "Evaluating report structure, clarity, conclusions, and recommendations.",
    },
    STANDARDS_CHECK: {
      title: "Checking references",
      description: "Reviewing internal references, citations, and traceability signals.",
    },
    LINGUISTIC_CHECK: {
      title: "Checking language",
      description: "Reviewing spelling, grammar, terminology, and ambiguous phrasing.",
    },
    AGGREGATING: {
      title: "Preparing review findings",
      description: "Combining all checks into the Review Workspace and final report.",
    },
  };
  const activity = activeStage
    ? stageCopy[activeStage.name] ?? {
        title: "Processing document",
        description: "Running the document quality checks.",
      }
    : isProcessing
      ? {
          title: "Preparing document",
          description: "The worker is starting the document review pipeline.",
        }
      : {
          title: "Processing complete",
          description: "The document review pipeline has finished.",
        };
  return (
    <section className="panel scan-panel" aria-labelledby="scan-heading">
      <div className="panel-heading">
        <div><p className="eyebrow">Pipeline telemetry</p><h2 id="scan-heading">Document review status</h2></div>
        <StatusBadge status={scan.status} />
      </div>
      <div className={`telemetry-activity ${isProcessing ? "is-processing" : ""}`}>
        {isProcessing ? <span className="telemetry-loader" aria-hidden="true" /> : <span className="telemetry-complete" aria-hidden="true">✓</span>}
        <div>
          <h3>{activity.title}</h3>
          <p>{activity.description}</p>
          {isProcessing && <small>This may take a while for large or complex documents. Please keep this page open.</small>}
        </div>
      </div>
      {activeStage?.error_message && <p className="telemetry-error" role="alert">{activeStage.error_message}</p>}
    </section>
  );
}
