import type { DocumentStatus } from "@/lib/api";
import { StatusBadge } from "./status-badge";

const STAGE_COPY: Record<string, { title: string; description: string }> = {
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

const PIPELINE_STAGES: { id: string; label: string }[] = [
  { id: "EXTRACTING", label: "Extracting" },
  { id: "LAYOUT_INSPECTION", label: "Layout" },
  { id: "BUDINSKI_AUDIT", label: "Budinski" },
  { id: "STANDARDS_CHECK", label: "Standards" },
];

export function ScanProgress({ scan }: { scan: DocumentStatus }) {
  const isProcessing = scan.status === "QUEUED" || scan.status === "PROCESSING";
  const activeStage = [...scan.stages].reverse().find((stage) => stage.status === "RUNNING");

  const activity = activeStage
    ? STAGE_COPY[activeStage.name] ?? {
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
    <section
      className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm"
      aria-labelledby="scan-heading"
    >
      <header className="flex items-center justify-between gap-4 border-b border-border/70 px-6 py-5 sm:px-8">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
            Pipeline telemetry
          </p>
          <h2 id="scan-heading" className="mt-1 text-base font-bold text-foreground">
            Document review status
          </h2>
        </div>
        <StatusBadge status={scan.status} />
      </header>

      <div className="p-6 sm:p-8">
        <div
          className={`flex items-start gap-4 rounded-xl border p-5 sm:p-6 ${
            isProcessing
              ? "border-primary/25 bg-gradient-to-br from-accent/70 to-card"
              : "border-emerald-200 bg-emerald-50/60"
          }`}
        >
          {isProcessing ? (
            <span
              aria-hidden="true"
              className="mt-0.5 size-9 shrink-0 animate-spin rounded-full border-[3px] border-primary/25 border-t-primary"
            />
          ) : (
            <span
              aria-hidden="true"
              className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700"
            >
              ✓
            </span>
          )}
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-foreground sm:text-base">{activity.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground sm:text-sm">
              {activity.description}
            </p>
            {isProcessing && (
              <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
                This may take a while for large or complex documents. Please keep this page open.
              </p>
            )}
          </div>
        </div>

        <ol
          className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4"
          aria-label="Inspection pipeline stages"
        >
          {PIPELINE_STAGES.map(({ id, label }, index) => {
            const stage = scan.stages.find((item) => item.name === id);
            const active = stage?.status === "RUNNING";
            const complete =
              stage?.status === "SUCCEEDED" || stage?.status === "SUCCEEDED_WITH_WARNINGS";
            const state = complete ? "Complete" : active ? "Running" : "Queued";

            return (
              <li
                key={id}
                aria-current={active ? "step" : undefined}
                className={`flex flex-col gap-2 rounded-xl border p-4 transition ${
                  active
                    ? "border-primary/35 bg-accent shadow-sm"
                    : complete
                      ? "border-emerald-200 bg-emerald-50"
                      : "border-border/70 bg-muted/40"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`size-2 shrink-0 rounded-full ${
                      active
                        ? "animate-pulse bg-primary"
                        : complete
                          ? "bg-emerald-600"
                          : "bg-slate-300"
                    }`}
                  />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </span>
                <span
                  className={`text-sm font-bold ${
                    active
                      ? "text-accent-foreground"
                      : complete
                        ? "text-emerald-800"
                        : "text-foreground"
                  }`}
                >
                  {label}
                </span>
                <span
                  className={`text-xs font-semibold ${
                    complete
                      ? "text-emerald-700"
                      : active
                        ? "text-accent-foreground"
                        : "text-muted-foreground"
                  }`}
                >
                  {state}
                </span>
              </li>
            );
          })}
        </ol>

        {activeStage?.error_message && (
          <p
            role="alert"
            className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-semibold text-rose-800"
          >
            {activeStage.error_message}
          </p>
        )}
      </div>
    </section>
  );
}
