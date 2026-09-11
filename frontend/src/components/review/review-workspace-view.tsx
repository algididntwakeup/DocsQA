"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, Download, FileText, RotateCw, ShieldCheck, X } from "lucide-react";
import {
  getDocument,
  getApiBaseUrl,
  getPdfUrl,
  getCurrentUser,
  listAllDocumentIssues,
  subscribeDocumentEvents,
  ApiError,
  type DocumentItem,
  type IssueItem,
  type UserRole,
} from "@/lib/api";
import { SplitScreenViewer } from "./split-screen-viewer";
import { ExportModal } from "./export-modal";

export function ReviewWorkspaceView({ id }: { id: string }) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [revisionNote, setRevisionNote] = useState("");
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        const [docData, issuesData, userData] = await Promise.all([
          getDocument(id),
          listAllDocumentIssues(id),
          getCurrentUser(),
        ]);
        if (active) {
          setDocument(docData);
          setIssues(issuesData);
          setUserRole(userData.role);
          setError(null);
          setIsLoading(false);

          // Findings are written asynchronously. Keep the workspace in sync when
          // it was opened before the worker finished its audit stages.
          if (docData.status === "QUEUED" || docData.status === "PROCESSING") {
            const unsubscribe = subscribeDocumentEvents(id, (event) => {
              if (
                event.status === "COMPLETED" ||
                event.status === "COMPLETED_WITH_WARNINGS" ||
                event.status === "FAILED"
              ) {
                unsubscribe();
                if (event.status !== "FAILED") {
                  void fetchData();
                }
              }
            });
            return unsubscribe;
          }
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

    let cleanup: (() => void) | undefined;
    void fetchData().then((result) => {
      cleanup = typeof result === "function" ? result : undefined;
    });

    return () => {
      active = false;
      cleanup?.();
    };
  }, [id, reloadKey]);

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex h-screen w-screen flex-col items-center justify-center bg-slate-50 text-slate-600 gap-3" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-blue-600 border-t-transparent" />
        <p className="text-xs font-semibold text-slate-700">Loading document inspection & telemetry...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="fixed inset-0 flex h-screen w-screen flex-col items-center justify-center bg-slate-50 px-6 text-slate-800">
        <div className="w-full max-w-lg rounded-2xl border border-rose-200 bg-white p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-3 text-rose-600">
            <AlertTriangle size={24} />
            <h2 className="text-base font-bold text-slate-900">Unable to initialize review workspace</h2>
          </div>
          <p className="text-xs text-slate-600">{error ?? "Document not found."}</p>
          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <Link
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:underline"
              href={`/documents/${id}`}
            >
              <ArrowLeft size={14} /> Kembali ke Dokumen
            </Link>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              onClick={() => {
                setIsLoading(true);
                setReloadKey((k) => k + 1);
              }}
            >
              <RotateCw size={13} /> Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const loadedDocument = document;

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

  const workflowStatus = document.workflow_status ?? "ANALYZING";
  const canSubmitReview = userRole === "ENGINEER" && workflowStatus === "ANALYZING";
  const canLeadDecide =
    (userRole === "LEAD_ENGINEER" || userRole === "SUPERUSER") &&
    workflowStatus === "REVIEWED_BY_ENGINEER";

  return (
    <div className="fixed inset-0 h-screen w-screen overflow-hidden flex flex-col bg-slate-100 text-slate-900 font-sans">
      {/* Zone 1 – Top Navigation Bar */}
      <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 shadow-2xs z-30">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href={document.project_id ? `/projects/${document.project_id}` : "/projects"}
            className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft size={14} /> Kembali
          </Link>
          <span className="text-slate-300">|</span>
          <h1 className="min-w-0 truncate text-xs sm:text-sm font-bold text-slate-900" title={document.filename}>
            {document.filename}
          </h1>
          <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 ring-1 ring-blue-700/10">
            {workflowStatus.replace("_BY_ENGINEER", "").replace("_BY_LEAD", "")}
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition"
            onClick={() => setIsScorecardOpen(true)}
          >
            <ShieldCheck size={14} className="text-indigo-600" /> Budinski Scorecard
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 shadow-xs transition"
            onClick={() => setIsExportOpen(true)}
          >
            <Download size={14} /> Export DOCX
          </button>
          <a
            className="hidden lg:inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition"
            href={getPdfUrl(document.id)}
            download
          >
            <FileText size={14} /> PDF
          </a>
        </div>
      </header>

      {/* Zone 2 – Split Screen Viewer */}
      <main className="flex-1 min-h-0 flex overflow-hidden">
        <SplitScreenViewer document={document} initialIssues={issues} embedded />
      </main>

      <ExportModal
        documentId={document.id}
        documentFilename={document.filename}
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
            className="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="flex items-start justify-between border-b border-slate-100 p-5">
              <div>
                <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Technical writing audit
                </p>
                <h2 id="workspace-scorecard-title" className="text-lg font-bold text-slate-900">
                  Budinski Scorecard
                </h2>
                <p className="mt-1 text-xs text-slate-500">Inspection summary for this review workspace.</p>
              </div>
              <button
                type="button"
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Close scorecard"
                onClick={() => setIsScorecardOpen(false)}
              >
                <X size={18} />
              </button>
            </header>
            <div className="grid grid-cols-3 gap-3 p-5">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-slate-900">
                  {issues.filter((issue) => issue.category === "BUDINSKI").length}
                </strong>
                <span className="text-[11px] font-medium text-slate-500">Items flagged</span>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-slate-900">{issues.length}</strong>
                <span className="text-[11px] font-medium text-slate-500">Total findings</span>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-emerald-600">
                  {Math.max(0, 41 - issues.filter((issue) => issue.category === "BUDINSKI").length)}
                </strong>
                <span className="text-[11px] font-medium text-slate-500">Items clear</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Zone 3 – Bottom Workflow Action Footer */}
      <footer
        className="flex h-12 shrink-0 items-center justify-between gap-4 border-t border-slate-200 bg-white px-4 shadow-2xs z-30"
        role="region"
        aria-label="Workflow actions"
      >
        <div className="flex min-w-0 items-center gap-2 text-xs text-slate-600">
          <CheckCircle2 size={16} className={workflowError ? "text-rose-500" : "text-emerald-600"} />
          <span className="truncate font-medium">
            {workflowError ?? `PIC Reviewer: ${document.assigned_to_name ?? document.owner_name ?? "Unassigned"}`}
            <small className="ml-2 text-slate-400">
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
              className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50 transition"
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
                className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50 transition"
                type="button"
                disabled={workflowBusy}
                onClick={() => void updateWorkflow("verify")}
              >
                {workflowBusy ? "Saving..." : "Verifikasi & Setujui Dokumen"}
              </button>
              <input
                className="hidden sm:block w-44 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-900 placeholder:text-slate-400 focus:border-amber-500 focus:outline-none"
                value={revisionNote}
                onChange={(event) => setRevisionNote(event.target.value)}
                placeholder="Catatan revisi..."
                aria-label="Revision note"
              />
              <button
                className="rounded-lg bg-amber-600 px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-amber-700 disabled:opacity-50 transition"
                type="button"
                disabled={workflowBusy}
                onClick={() => void updateWorkflow("request-revision")}
              >
                Minta Revisi
              </button>
            </>
          )}
        </div>
      </footer>
    </div>
  );
}
