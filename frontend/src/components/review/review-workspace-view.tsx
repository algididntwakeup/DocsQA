"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, RotateCw, ShieldCheck } from "lucide-react";
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

export function ReviewWorkspaceView({ id }: { id: string }) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);

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
          body: action === "request-revision" ? JSON.stringify({ workflow_status: "REVIEWED_BY_ENGINEER" }) : undefined,
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
  const canLeadDecide = userRole === "LEAD_ENGINEER" && workflowStatus === "REVIEWED_BY_ENGINEER";

  return (
    <div className="relative">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3" role="status" aria-live="polite">
        <div className="flex items-center gap-2 text-xs text-muted">
          <ShieldCheck size={15} className="text-primary" />
          <span>Workflow status</span>
        </div>
        <span
          className={`status-badge ${workflowStatus === "VERIFIED_BY_LEAD" ? "status-success" : workflowStatus === "REVIEWED_BY_ENGINEER" ? "status-active" : "status-warning"}`}
        >
          <i />{workflowStatus.replaceAll("_", " ")}
        </span>
      </div>

      <SplitScreenViewer document={document} initialIssues={issues} />

      {(canSubmitReview || canLeadDecide || workflowError) && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border border-line bg-panel px-4 py-3 text-xs shadow-sm" role="region" aria-label="Workflow actions">
          <div className="flex items-center gap-2 text-muted">
            <CheckCircle2 size={15} className={workflowError ? "text-danger" : "text-success"} />
            <span>{workflowError ?? "Review disposition"}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {canSubmitReview && (
              <button className="button button-primary btn-sm" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("mark-reviewed")}>
                {workflowBusy ? "Submitting..." : "Tandai Selesai Di-review (Submit to Lead)"}
              </button>
            )}
            {canLeadDecide && (
              <>
                <button className="button button-primary btn-sm" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("verify")}>
                  {workflowBusy ? "Saving..." : "Verifikasi & Approve Laporan"}
                </button>
                <button className="button button-secondary btn-sm" type="button" disabled={workflowBusy} onClick={() => void updateWorkflow("request-revision")}>
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
