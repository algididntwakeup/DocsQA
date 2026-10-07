"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, Download, FileText, RotateCw, ShieldCheck, X } from "lucide-react";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getDocument,
  getDocumentStatus,
  getApiBaseUrl,
  getPdfUrl,
  getCurrentUser,
  listDocumentIssues,
  retryDocumentAnalysis,
  subscribeDocumentEvents,
  ApiError,
  type DocumentItem,
  type DocumentStatus,
  type IssueItem,
  type UserRole,
} from "@/lib/api";
import { SplitScreenViewer } from "./split-screen-viewer";
import { ExportModal } from "./export-modal";
import { ProcessingBanner } from "./processing-banner";
import { useLocale } from "@/components/layout/locale-provider";

const isProcessingStatus = (status: string | undefined) =>
  status === "QUEUED" || status === "PROCESSING";
const isTerminalStatus = (status: string | undefined) =>
  status === "COMPLETED" || status === "COMPLETED_WITH_WARNINGS" || status === "FAILED";

async function getAllDocumentIssues(id: string) {
  const pageSize = 50;
  const firstPage = await listDocumentIssues(id, undefined, 1, pageSize);
  const pageCount = Math.ceil(firstPage.pagination.total / pageSize);
  const remainingPages = await Promise.all(
    Array.from({ length: Math.max(0, pageCount - 1) }, (_, index) =>
      listDocumentIssues(id, undefined, index + 2, pageSize)
    )
  );
  return {
    issues: [firstPage.issues, ...remainingPages.map((page) => page.issues)].flat(),
    total: firstPage.pagination.total,
  };
}

export function ReviewWorkspaceView({ id }: { id: string }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
      })
  );
  return (
    <QueryClientProvider client={queryClient}>
      <ReviewWorkspaceContent id={id} />
    </QueryClientProvider>
  );
}

function ReviewWorkspaceContent({ id }: { id: string }) {
  const { t } = useLocale();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const [issuePage, setIssuePage] = useState(1);
  const [issueRevision, setIssueRevision] = useState(0);
  const [issueTotal, setIssueTotal] = useState(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [revisionNote, setRevisionNote] = useState("");
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);
  const previousStatusRef = useRef<string | undefined>(undefined);
  const queryClient = useQueryClient();
  const statusQueryKey = ["document-status", id] as const;
  const statusQuery = useQuery({
    queryKey: statusQueryKey,
    queryFn: () => getDocumentStatus(id),
    enabled: document !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === undefined || isProcessingStatus(status) ? 2500 : false;
    },
    refetchIntervalInBackground: true,
  });
  const { data: statusData, refetch: refetchStatus } = statusQuery;
  const effectiveStatus = statusData?.status ?? document?.status;
  const isProcessing = isProcessingStatus(effectiveStatus);
  const isFailed = effectiveStatus === "FAILED";
  const currentStage = statusData?.current_stage ?? "Preparing document analysis";
  const progressPct = Math.max(document?.progress_pct ?? 0, statusData?.progress_pct ?? 0);
  const retryMutation = useMutation({
    mutationFn: () => retryDocumentAnalysis(id),
    onSuccess: (retriedDocument) => {
      previousStatusRef.current = retriedDocument.status;
      setDocument(retriedDocument);
      queryClient.setQueryData<DocumentStatus>(statusQueryKey, (previous) => ({
        ...(previous ?? {
          id: retriedDocument.id,
          stages: [],
          updated_at: retriedDocument.updated_at,
        }),
        id: retriedDocument.id,
        status: retriedDocument.status,
        progress_pct: 0,
        current_stage: "Queued for processing",
        error_message: null,
        updated_at: retriedDocument.updated_at,
      }));
    },
  });

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        const [docData, loadedIssues, userData] = await Promise.all([
          getDocument(id),
          getAllDocumentIssues(id),
          getCurrentUser(),
        ]);
        if (active) {
          previousStatusRef.current = docData.status;
          setDocument(docData);
          setIssues(loadedIssues.issues);
          setIssueRevision((revision) => revision + 1);
          setIssuePage(Math.max(1, Math.ceil(loadedIssues.issues.length / 50)));
          setIssueTotal(loadedIssues.total);
          setUserRole(userData.role);
          setError(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : err instanceof Error
              ? err.message
              : "Could not load review workspace."
          );
          setIsLoading(false);
        }
      }
    };

    void fetchData();

    return () => {
      active = false;
    };
  }, [id, reloadKey]);

  useEffect(() => {
    if (!isProcessing || typeof window === "undefined" || !("EventSource" in window)) return;
    try {
      return subscribeDocumentEvents(
        id,
        () => void refetchStatus(),
        () => void refetchStatus(),
        () => void refetchStatus()
      );
    } catch {
      // TanStack Query polling remains active if EventSource is unavailable.
      return;
    }
  }, [id, isProcessing, refetchStatus]);

  useEffect(() => {
    const status = statusData?.status;
    if (!status) return;
    const previousStatus = previousStatusRef.current;
    previousStatusRef.current = status;

    if (
      isProcessingStatus(previousStatus) &&
      isTerminalStatus(status) &&
      status !== "FAILED"
    ) {
      void (async () => {
        try {
          const [freshDocument, loadedIssues] = await Promise.all([
            getDocument(id),
            getAllDocumentIssues(id),
          ]);
          setDocument(freshDocument);
          setIssues(loadedIssues.issues);
          setIssueRevision((revision) => revision + 1);
          setIssuePage(Math.max(1, Math.ceil(loadedIssues.issues.length / 50)));
          setIssueTotal(loadedIssues.total);
        } catch (caught: unknown) {
          setError(
            caught instanceof ApiError
              ? caught.message
              : caught instanceof Error
                ? caught.message
                : "Could not refresh completed findings."
          );
        }
      })();
    }
  }, [id, statusData]);

  if (isLoading) {
    return (
      <div className="flex h-[calc(100dvh-4rem)] w-full flex-col items-center justify-center gap-3 bg-muted/20 text-muted-foreground" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
        <p className="text-xs font-semibold text-foreground">{t("loadingRegister")}</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex h-[calc(100dvh-4rem)] w-full flex-col items-center justify-center bg-muted/20 px-6 text-foreground">
        <div className="w-full max-w-lg space-y-4 rounded-xl border border-destructive/30 bg-card p-6 shadow-xl">
          <div className="flex items-center gap-3 text-destructive">
            <AlertTriangle size={24} />
            <h2 className="text-base font-bold text-foreground">{t("couldNotLoadWorkspace")}</h2>
          </div>
          <p className="text-xs text-muted-foreground">{error ?? "Document not found."}</p>
          <div className="flex items-center justify-between border-t border-border pt-2">
            <Link
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
              href={`/documents/${id}`}
            >
               <ArrowLeft size={14} /> {t("document")}
            </Link>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-muted"
              onClick={() => {
                setIsLoading(true);
                setReloadKey((k) => k + 1);
              }}
            >
               <RotateCw size={13} /> {t("retry")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const loadedDocument = document;
  const workspaceDocument = {
    ...loadedDocument,
    status: effectiveStatus ?? loadedDocument.status,
    progress_pct: progressPct,
  };
  const failureMessage =
    statusData?.error_message ?? "Document analysis failed. Retry the analysis or contact support.";

  async function updateWorkflow(action: "mark-reviewed" | "verify" | "request-revision") {
    setWorkflowBusy(true);
    setWorkflowError(null);
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/documents/${encodeURIComponent(loadedDocument.id)}/${action}`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            Accept: "application/json",
            ...(action === "request-revision" ? { "Content-Type": "application/json" } : {}),
          },
          body:
            action === "request-revision"
              ? JSON.stringify({
                  workflow_status: "REVIEWED_BY_ENGINEER",
                  verification_notes: revisionNote.trim() || undefined,
                })
              : undefined,
        }
      );
      if (!response.ok) {
        if (response.status === 401) window.location.pathname = "/login";
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? `Workflow update failed (${response.status}).`);
      }
      setDocument((await response.json()) as DocumentItem);
    } catch (caught) {
      setWorkflowError(caught instanceof Error ? caught.message : "Workflow update failed.");
    } finally {
      setWorkflowBusy(false);
    }
  }
  async function loadMoreIssues() {
    const nextPage = issuePage + 1;
    const response = await listDocumentIssues(id, undefined, nextPage, 50);
    setIssues((current) => [...current, ...response.issues]);
    setIssuePage(nextPage);
    setIssueTotal(response.pagination.total);
    setIssueRevision((revision) => revision + 1);
  }


  const projectFinished = Boolean(document.project_finished);
  const workflowStatus = document.workflow_status ?? "ANALYZING";
  const canSubmitReview =
    !isProcessing && !isFailed && !projectFinished && userRole === "ENGINEER" && workflowStatus === "ANALYZING";
  const canLeadDecide =
    !isProcessing &&
    !isFailed &&
    !projectFinished &&
    (userRole === "LEAD_ENGINEER" || userRole === "SUPERUSER") &&
    workflowStatus === "REVIEWED_BY_ENGINEER";
  const isLeadReviewer = userRole === "LEAD_ENGINEER" || userRole === "SUPERUSER";

  return (
    <div className="flex h-[calc(100dvh-4rem)] w-full flex-col gap-4 overflow-hidden bg-muted/20 p-4 font-sans text-foreground">
      {/* Zone 1 – Top Navigation Bar */}
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 rounded-xl border border-border/60 bg-card px-4 shadow-sm">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href={document.project_id ? `/projects/${document.project_id}` : "/projects"}
            className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={14} /> Kembali
          </Link>
          <span className="text-border">|</span>
          <h1 className="min-w-0 truncate text-xs sm:text-sm font-bold text-foreground" title={document.filename}>
            {document.filename}
          </h1>
          <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent-foreground ring-1 ring-primary/10">
            {workflowStatus.replace("_BY_ENGINEER", "").replace("_BY_LEAD", "")}
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled={isProcessing}
            title={isProcessing ? "Scorecard dan temuan sedang dikompilasi..." : undefined}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground shadow-sm transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => setIsScorecardOpen(true)}
          >
            <ShieldCheck size={14} className="text-indigo-600" /> Budinski Scorecard
          </button>
          <button
            type="button"
            disabled={isProcessing}
            title={isProcessing ? "Fitur ekspor aktif setelah analisis selesai." : undefined}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => setIsExportOpen(true)}
          >
            <Download size={14} /> Export DOCX
          </button>
          <a
            aria-disabled={isProcessing}
            tabIndex={isProcessing ? -1 : undefined}
            title={isProcessing ? "Fitur ekspor aktif setelah analisis selesai." : undefined}
            className={`hidden lg:inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground shadow-sm transition hover:bg-muted ${isProcessing ? "pointer-events-none opacity-50" : ""}`}
            href={getPdfUrl(document.id)}
            download
            onClick={(event) => {
              if (isProcessing) event.preventDefault();
            }}
          >
            <FileText size={14} /> PDF
          </a>
        </div>
      </header>
      {isProcessing && (
        <ProcessingBanner progressPct={progressPct} currentStage={currentStage} />
      )}
      {isFailed && (
        <div
          className="flex shrink-0 flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-destructive"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex min-w-0 items-start gap-2">
            <AlertTriangle size={17} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs font-bold">Analysis failed</p>
              <p className="break-words text-xs">{failureMessage}</p>
              {retryMutation.isError && (
                <p className="mt-1 text-xs font-semibold">
                  {retryMutation.error instanceof Error
                    ? retryMutation.error.message
                    : "Could not retry analysis."}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-destructive px-3 py-1.5 text-xs font-bold text-destructive-foreground shadow-sm disabled:cursor-wait disabled:opacity-60"
            disabled={retryMutation.isPending}
            onClick={() => retryMutation.mutate()}
          >
            <RotateCw size={13} className={retryMutation.isPending ? "animate-spin" : ""} />
            {retryMutation.isPending ? "Retrying..." : "Retry Analysis"}
          </button>
        </div>
      )}
      {isLeadReviewer && (
        <div className="shrink-0 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-900" role="status">
          Anda sedang meninjau dokumen ini sebagai Lead Engineer / Superuser
        </div>
      )}
      {projectFinished && (
        <div className="shrink-0 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-semibold text-emerald-800" role="status">
          Project finished. Review actions are disabled; exports remain available.
        </div>
      )}
      {issues.length < issueTotal && (
        <div className="flex shrink-0 justify-center border-x border-border/60 bg-card py-2">
          <button
            type="button"
            disabled={isProcessing}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => void loadMoreIssues()}
          >
            Load more findings ({issues.length} of {issueTotal})
          </button>
        </div>
      )}
      <main className="flex min-h-0 flex-1 overflow-hidden rounded-xl border border-border/60 bg-card p-4 shadow-sm">
        <SplitScreenViewer key={issueRevision} document={workspaceDocument} initialIssues={issues} embedded readOnly={projectFinished} />
      </main>

      <ExportModal
        documentId={document.id}
        documentFilename={document.filename}
        projectId={document.project_id}
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
      />

      {/* Budinski Scorecard Modal */}
      {isScorecardOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
          aria-labelledby="workspace-scorecard-title"
          onClick={() => setIsScorecardOpen(false)}
        >
          <div
            className="w-full max-w-xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="flex items-start justify-between border-b border-border p-5">
              <div>
                <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Technical writing audit
                </p>
                <h2 id="workspace-scorecard-title" className="text-lg font-bold text-foreground">
                  Budinski Scorecard
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">Inspection summary for this review workspace.</p>
              </div>
              <button
                type="button"
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="Close scorecard"
                onClick={() => setIsScorecardOpen(false)}
              >
                <X size={18} />
              </button>
            </header>
            {isProcessing ? (
              <div className="flex flex-col items-center gap-4 p-8 text-center" aria-live="polite">
                <div className="w-full max-w-sm space-y-3" aria-hidden="true">
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                </div>
                <p className="text-sm font-semibold text-muted-foreground">
                  Scorecard dan temuan sedang dikompilasi...
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3 p-5">
                <div className="rounded-xl border border-border bg-muted/40 p-4 text-center">
                  <strong className="block text-2xl font-bold text-foreground">
                    {issues.filter((issue) => issue.category === "BUDINSKI").length}
                  </strong>
                  <span className="text-[11px] font-medium text-muted-foreground">Items flagged</span>
                </div>
                <div className="rounded-xl border border-border bg-muted/40 p-4 text-center">
                  <strong className="block text-2xl font-bold text-foreground">{issues.length}</strong>
                  <span className="text-[11px] font-medium text-muted-foreground">Total findings</span>
                </div>
                <div className="rounded-xl border border-border bg-muted/40 p-4 text-center">
                  <strong className="block text-2xl font-bold text-emerald-600">
                    {Math.max(0, 41 - issues.filter((issue) => issue.category === "BUDINSKI").length)}
                  </strong>
                  <span className="text-[11px] font-medium text-muted-foreground">Items clear</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Zone 3 – Bottom Workflow Action Footer */}
      <footer
        className="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-4 rounded-xl border border-border/60 bg-card px-4 py-2 shadow-sm"
        role="region"
        aria-label="Workflow actions"
      >
        <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle2 size={16} className={workflowError ? "text-rose-500" : "text-emerald-600"} />
          <span className="truncate font-medium">
            {workflowError ?? `PIC Reviewer: ${document.assigned_to_name ?? document.owner_name ?? "Unassigned"}`}
            <small className="ml-2 text-muted-foreground/70">
              {workflowError
                ? "Resolve the issue before submitting."
                : `Updated ${document.reviewed_at ? new Date(document.reviewed_at).toLocaleTimeString() : "not yet"}`}
            </small>
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {canSubmitReview && (
            <button
              aria-label="Tandai selesai di-review"
              className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
              type="button"
              disabled={workflowBusy}
              onClick={() => void updateWorkflow("mark-reviewed")}
            >
              {workflowBusy ? "Submitting..." : "Selesaikan Review Saya"}
            </button>
          )}

          {canLeadDecide && (
            <>
              <button
                className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                type="button"
                disabled={workflowBusy}
                onClick={() => void updateWorkflow("verify")}
              >
                {workflowBusy ? "Saving..." : "Verifikasi & Setujui Dokumen"}
              </button>
              <input
                className="hidden w-44 rounded-lg border border-input bg-card px-2.5 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:border-amber-500 focus:outline-none sm:block"
                value={revisionNote}
                onChange={(event) => setRevisionNote(event.target.value)}
                placeholder="Catatan revisi..."
                aria-label="Revision note"
              />
              <button
                className="rounded-lg bg-amber-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-amber-700 disabled:opacity-50"
                type="button"
                disabled={workflowBusy}
                onClick={() => void updateWorkflow("request-revision")}
              >
                Minta Revisi
              </button>
            </>
          )}

          {isLeadReviewer && workflowStatus === "ANALYZING" && (
            <span className="rounded-lg border border-primary/20 bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground">
              Analisis masih berjalan. Pemantauan aktif.
            </span>
          )}
        </div>
      </footer>
    </div>
  );
}
