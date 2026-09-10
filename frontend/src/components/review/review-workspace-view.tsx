"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, RotateCw } from "lucide-react";
import {
  getDocument,
  getApiBaseUrl,
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
      <div className="panel loading-state" role="status">
        <div className="loading-spinner" />
        <p>Loading document and QA inspection telemetry...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="review-error-container">
        <Link className="back-link" href={`/documents/${id}`}>
          <ArrowLeft size={15} /> Back to inspection status
        </Link>
        <div className="alert alert-error" role="alert">
          <AlertTriangle />
          <div>
            <strong>Unable to initialize review workspace</strong>
            <p>{error ?? "Document not found."}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setIsLoading(true);
              setReloadKey((k) => k + 1);
            }}
          >
            <RotateCw size={14} /> Retry
          </button>
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
             body: action === "request-revision" ? JSON.stringify({ workflow_status: "REVIEWED_BY_ENGINEER", verification_notes: revisionNote.trim() || undefined }) : undefined,
        },
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
  const canLeadDecide = (userRole === "LEAD_ENGINEER" || userRole === "SUPERUSER") && workflowStatus === "REVIEWED_BY_ENGINEER";

  const initials = (document.assigned_to_name ?? document.owner_name ?? "RQ").split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-slate-950 text-slate-100">
      <header className="h-14 shrink-0 flex items-center justify-between gap-4 px-4 border-b border-slate-800 bg-slate-900">
        <div className="rq-review-heading">
          <div className="flex min-w-0 items-center gap-3"><Link href={document.project_id ? `/projects/${document.project_id}` : "/projects"} className="flex shrink-0 items-center gap-1.5 text-xs text-slate-300 hover:text-white"><ArrowLeft size={15} /> Kembali ke Project</Link><span className="h-5 w-px bg-slate-700" /><div className="min-w-0"><h1 className="truncate text-sm font-semibold">{document.filename}</h1><div className="flex items-center gap-2 text-[10px] text-slate-400"><span className="rounded bg-slate-800 px-1.5 py-0.5">{document.project_id?.slice(0, 8) ?? "EQUIPMENT"}</span><span className={`rq-review-status rq-review-status-${workflowStatus.toLowerCase()}`}><i />{workflowStatus.replace("_BY_ENGINEER", "").replace("_BY_LEAD", "")}</span></div></div></div>
        </div>
          <div className="flex shrink-0 items-center gap-2"><button type="button" className="rq-review-action-secondary" onClick={() => setIsScorecardOpen(true)}>Scorecard Budinski</button><button type="button" className="rq-review-action-secondary" onClick={() => setIsExportOpen(true)}>Export DOCX</button><span className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-500 text-xs font-bold text-white" title={document.assigned_to_name ?? document.owner_name ?? "Uploader"}>{initials}</span></div>
      </header>

        <main className="flex-1 min-h-0 flex overflow-hidden"><SplitScreenViewer document={document} initialIssues={issues} /></main>

       <ExportModal documentId={document.id} documentFilename={document.filename} isOpen={isExportOpen} onClose={() => setIsExportOpen(false)} />
       {isScorecardOpen && <div className="rq-scorecard-backdrop" role="dialog" aria-modal="true" aria-labelledby="workspace-scorecard-title" onClick={() => setIsScorecardOpen(false)}><div className="rq-scorecard-modal" onClick={(event) => event.stopPropagation()}><header><div><p className="rq-kicker">Technical writing audit</p><h2 id="workspace-scorecard-title">Budinski Scorecard</h2><p>Inspection summary for this review workspace.</p></div><button type="button" aria-label="Close scorecard" onClick={() => setIsScorecardOpen(false)}>×</button></header><div className="rq-scorecard-kpis"><div><strong>{issues.filter((issue) => issue.category === "BUDINSKI").length}</strong><span>Items flagged</span></div><div><strong>{issues.length}</strong><span>Total findings</span></div><div><strong>{Math.max(0, 41 - issues.filter((issue) => issue.category === "BUDINSKI").length)}</strong><span>Items clear</span></div></div></div></div>}

      {(canSubmitReview || canLeadDecide || workflowError) && (
         <div className="h-14 shrink-0 flex items-center justify-between gap-4 px-6 border-t border-slate-800 bg-slate-900/90" role="region" aria-label="Workflow actions">
           <div className="flex min-w-0 items-center gap-2 text-xs text-slate-400"><CheckCircle2 size={17} className={workflowError ? "text-red-400" : "text-emerald-400"} /><span>{workflowError ?? `PIC Reviewer: ${document.assigned_to_name ?? document.owner_name ?? "Unassigned"}`}<small className="ml-2 text-slate-500">{workflowError ? "Resolve the issue before submitting." : `Review updated ${document.reviewed_at ? new Date(document.reviewed_at).toLocaleString() : "not yet"}`}</small></span></div>
          <div className="rq-signoff-actions">
            {canSubmitReview && (
              <button aria-label="Tandai selesai di-review" className="rq-signoff-primary" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("mark-reviewed")}>
                {workflowBusy ? "Submitting..." : "Selesaikan Review Saya"}
              </button>
            )}
            {canLeadDecide && (
              <>
                <button className="rq-signoff-primary" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("verify")}>
                  {workflowBusy ? "Saving..." : "Verifikasi & Setujui Dokumen"}
                </button>
                <input className="rq-revision-input" value={revisionNote} onChange={(event) => setRevisionNote(event.target.value)} placeholder="Catatan revisi (opsional)" aria-label="Revision note" />
                <button className="rq-signoff-secondary" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("request-revision")}>
                  Minta Revisi
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
