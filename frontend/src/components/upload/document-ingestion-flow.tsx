"use client";

import { useCallback, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, ArrowRight, FileText, FolderKanban, ShieldCheck, Upload } from "lucide-react";
import { ApiError, listProjects, uploadProjectDocument, type ProjectItem } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";
import { Card } from "@/components/ui/card";
import { DropZone } from "./drop-zone";
import { ProjectSelector } from "./project-selector";
import { ProcessingStage } from "./processing-stage";

export type IngestionStep = "SELECT_FILES" | "SELECT_PROJECT" | "PROCESSING";

const stepTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
  transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const },
};

/**
 * Unified document ingestion flow.
 *
 * Replaces the old two-route hand-off (upload -> /documents/[id]) with one
 * local state machine: SELECT_FILES -> SELECT_PROJECT -> PROCESSING. The
 * processing view renders in place, so the browser never performs a hard
 * navigation after the upload starts.
 */
export function DocumentIngestionFlow() {
  const { t } = useLocale();
  const [step, setStep] = useState<IngestionStep>("SELECT_FILES");
  const [files, setFiles] = useState<File[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    try {
      setProjects(await listProjects());
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotLoadProjects"));
    } finally {
      setProjectsLoading(false);
    }
  }, [t]);

  // Fetch on the transition into the project step rather than in an effect:
  // calling setState synchronously inside an effect triggers cascading renders.
  const goToProjectStep = useCallback(() => {
    setStep("SELECT_PROJECT");
    if (projects.length === 0) void loadProjects();
  }, [projects.length, loadProjects]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;

  async function beginInspection() {
    const file = files[0];
    if (!file || !selectedProjectId) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadProjectDocument(selectedProjectId, file);
      setDocumentId(uploaded.id);
      // Local transition: no router.push, so the status view morphs in place.
      setStep("PROCESSING");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("uploadCouldNotComplete"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-10 sm:px-6 lg:py-14">
      <header className="flex flex-col gap-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-accent-foreground">
          {t("controlledIngestion")}
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {t("newDocumentInspection")}
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
          {t("filesStayLocal")}
        </p>
      </header>

      <StepIndicator current={step} />

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <AnimatePresence mode="wait">
        {step === "SELECT_FILES" && (
          <motion.div key="select-files" {...stepTransition}>
            <Card className="p-6 sm:p-8">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
                    Step 01
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-foreground">
                    {t("selectSourceDocuments")}
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    PDF or DOCX, up to 50 MiB each.
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
                  {files.length}/20
                </span>
              </div>

              <DropZone files={files} onChange={setFiles} disabled={uploading} />

              <div className="mt-8 flex flex-col-reverse items-stretch gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
                <p className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                  <ShieldCheck size={15} />
                  Type and archive structure are verified server-side.
                </p>
                <button
                  type="button"
                  disabled={files.length === 0}
                  onClick={goToProjectStep}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Continue
                  <ArrowRight size={16} />
                </button>
              </div>
            </Card>
          </motion.div>
        )}

        {step === "SELECT_PROJECT" && (
          <motion.div key="select-project" {...stepTransition}>
            <Card className="p-6 sm:p-8">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
                    Step 02
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-foreground">
                    Choose a destination project
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    The document is filed into this workspace folder.
                  </p>
                </div>
              </div>

              <div className="mb-6 flex items-center gap-3 rounded-xl border border-border/70 bg-muted/30 px-4 py-3">
                <FileText size={17} className="shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {files[0]?.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {files.length} file{files.length === 1 ? "" : "s"} ready to upload
                  </p>
                </div>
              </div>

              <ProjectSelector
                projects={projects}
                selectedId={selectedProjectId}
                onSelect={setSelectedProjectId}
                loading={projectsLoading}
              />

              <div className="mt-8 flex flex-col-reverse items-stretch gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
                <button
                  type="button"
                  onClick={() => setStep("SELECT_FILES")}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-muted/60"
                >
                  <ArrowLeft size={16} />
                  Back
                </button>
                <button
                  type="button"
                  disabled={!selectedProjectId || uploading}
                  onClick={() => void beginInspection()}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Upload size={16} />
                  {uploading ? "Uploading..." : t("beginInspection")}
                </button>
              </div>
            </Card>
          </motion.div>
        )}

        {step === "PROCESSING" && documentId && (
          <motion.div key="processing" {...stepTransition}>
            <ProcessingStage
              documentId={documentId}
              filename={files[0]?.name ?? "Document"}
              projectName={selectedProject?.name ?? null}
              onStartOver={() => {
                setFiles([]);
                setSelectedProjectId(null);
                setDocumentId(null);
                setStep("SELECT_FILES");
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StepIndicator({ current }: { current: IngestionStep }) {
  const steps: { id: IngestionStep; label: string; icon: typeof FileText }[] = [
    { id: "SELECT_FILES", label: "Select files", icon: FileText },
    { id: "SELECT_PROJECT", label: "Choose project", icon: FolderKanban },
    { id: "PROCESSING", label: "Processing", icon: ShieldCheck },
  ];
  const order: IngestionStep[] = ["SELECT_FILES", "SELECT_PROJECT", "PROCESSING"];
  const currentIndex = order.indexOf(current);

  return (
    <ol className="flex flex-wrap items-center gap-x-3 gap-y-2" aria-label="Ingestion progress">
      {steps.map((item, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        const Icon = item.icon;
        return (
          <li key={item.id} className="flex items-center gap-3">
            <span
              aria-current={active ? "step" : undefined}
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                active
                  ? "border-primary/40 bg-accent text-accent-foreground"
                  : done
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border-border bg-card text-muted-foreground"
              }`}
            >
              <Icon size={14} />
              {item.label}
            </span>
            {index < steps.length - 1 && (
              <span aria-hidden="true" className="h-px w-6 bg-border sm:w-10" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
