"use client";

import { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  FileText,
  History,
  RotateCw,
  ShieldCheck,
  AlertTriangle,
  X,
  Download,
} from "lucide-react";
import type { DocumentItem, IssueItem, IssueDecision, IssueDisposition } from "@/lib/api";
import {
  decideIssue,
  disposeIssue,
  bulkDecideIssues,
  setDocumentDisposition,
  listDocumentIssues,
  getIssueLocation,
  ApiError,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import { DocumentViewer } from "./document-viewer";
import { IssuePanel } from "./issue-panel";
import { AuditTrailModal } from "./audit-trail-modal";
import { TraceabilitySummaryModal } from "./traceability-summary-modal";
import { DictionaryModal } from "./dictionary-modal";
import { ExportModal } from "./export-modal";
import { ThemeToggle } from "../layout/theme-toggle";

interface SplitScreenViewerProps {
  document: DocumentItem;
  initialIssues: IssueItem[];
}

export function SplitScreenViewer({ document, initialIssues }: SplitScreenViewerProps) {
  const [issues, setIssues] = useState<IssueItem[]>(initialIssues);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(
    initialIssues.length > 0 ? initialIssues[0].id : null
  );
  const [currentPage, setCurrentPage] = useState<number>(() => {
    if (initialIssues.length > 0) {
      const loc = getIssueLocation(initialIssues[0]);
      if (loc.page_number) return loc.page_number;
    }
    return 1;
  });

  // Modals
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState<boolean>(false);
  const [isDictionaryOpen, setIsDictionaryOpen] = useState<boolean>(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [dictionaryInitialTerm, setDictionaryInitialTerm] = useState<string | undefined>(undefined);

  // Document Disposition State
  const [documentDisposition, setDocumentDispositionState] = useState<string | null>(null);
  const [pendingDispositionType, setPendingDispositionType] = useState<
    "APPROVED" | "REVISION_REQUIRED" | null
  >(null);
  const [dispositionJustification, setDispositionJustification] = useState<string>("");
  const [isSubmittingDisposition, setIsSubmittingDisposition] = useState<boolean>(false);

  // Global feedback / conflict alert
  const [alertMessage, setAlertMessage] = useState<{
    type: "error" | "success" | "conflict";
    message: string;
  } | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const selectedIssue = useMemo(
    () => issues.find((i) => i.id === selectedIssueId) ?? null,
    [issues, selectedIssueId]
  );

  const refreshIssues = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const response = await listDocumentIssues(document.id);
      setIssues(response.issues);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to refresh issues";
      setAlertMessage({ type: "error", message: msg });
    } finally {
      setIsRefreshing(false);
    }
  }, [document.id]);

  const handleSelectIssue = (issueId: string) => {
    setSelectedIssueId(issueId);
    const iss = issues.find((i) => i.id === issueId);
    if (iss) {
      const loc = getIssueLocation(iss);
      if (loc.page_number) {
        setCurrentPage(loc.page_number);
      }
    }
  };

  const handleDecideIssue = async (issueId: string, payload: IssueDecision) => {
    try {
      const updated = await decideIssue(issueId, payload);
      setIssues((prev) => prev.map((item) => (item.id === issueId ? updated : item)));
      setAlertMessage({
        type: "success",
        message: `Issue #${issueId.slice(0, 8)} marked as ${payload.decision}.`,
      });
      setTimeout(() => setAlertMessage(null), 3000);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setAlertMessage({
          type: "conflict",
          message:
            "Concurrency conflict (409): Another reviewer updated this issue. Refreshing latest state...",
        });
        await refreshIssues();
      } else {
        const msg = err instanceof Error ? err.message : "Failed to record decision.";
        setAlertMessage({ type: "error", message: msg });
      }
      throw err;
    }
  };

  const handleDisposeIssue = async (issueId: string, payload: IssueDisposition) => {
    try {
      const updated = await disposeIssue(issueId, payload);
      setIssues((prev) => prev.map((item) => (item.id === issueId ? updated : item)));
      setAlertMessage({
        type: "success",
        message: `Lead disposition recorded: ${payload.disposition}.`,
      });
      setTimeout(() => setAlertMessage(null), 3000);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setAlertMessage({
          type: "conflict",
          message:
            "Concurrency conflict (409): Another reviewer updated this issue. Refreshing latest state...",
        });
        await refreshIssues();
      } else {
        const msg = err instanceof Error ? err.message : "Failed to record disposition.";
        setAlertMessage({ type: "error", message: msg });
      }
      throw err;
    }
  };

  const handleBulkDecideLanguage = async () => {
    try {
      const eligible = issues.filter(
        (i) => i.category === "LINGUISTIC" && !i.decision
      );
      if (eligible.length === 0) {
        setAlertMessage({
          type: "error",
          message: "No pending linguistic findings available for bulk acceptance.",
        });
        return;
      }
      const result = await bulkDecideIssues({
        issue_ids: eligible.map((i) => i.id),
        decision: "ACCEPTED",
        actor_id: "reviewer@local",
        actor_role: "QA_ENGINEER",
        comment: "Bulk accepted high-confidence linguistic findings",
      });
      setAlertMessage({
        type: "success",
        message: `Successfully bulk-accepted ${result.updated_count} linguistic findings.`,
      });
      await refreshIssues();
      setTimeout(() => setAlertMessage(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Bulk action failed";
      setAlertMessage({ type: "error", message: msg });
      throw err;
    }
  };

  const handleConfirmDocumentDisposition = async () => {
    if (!pendingDispositionType) return;
    if (!dispositionJustification.trim()) {
      setAlertMessage({
        type: "error",
        message: "A justification note is required for document-level disposition.",
      });
      return;
    }

    setIsSubmittingDisposition(true);
    try {
      await setDocumentDisposition(document.id, {
        disposition: pendingDispositionType,
        justification: dispositionJustification.trim(),
        actor_id: "lead_reviewer@local",
        actor_role: "LEAD_REVIEWER",
      });
      setDocumentDispositionState(pendingDispositionType);
      setAlertMessage({
        type: "success",
        message: `Document disposition recorded: ${pendingDispositionType}.`,
      });
      setPendingDispositionType(null);
      setDispositionJustification("");
      setTimeout(() => setAlertMessage(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to set document disposition";
      setAlertMessage({ type: "error", message: msg });
    } finally {
      setIsSubmittingDisposition(false);
    }
  };

  return (
    <div className="split-screen-workspace">
      {/* Top Navigation & Metadata Bar */}
      <header className="workspace-header">
        <div className="header-left">
          <Link href={`/documents/${document.id}`} className="workspace-back-link">
            <ArrowLeft size={16} />
            <span>Inspection</span>
          </Link>

          <div className="workspace-doc-meta">
            <FileText size={18} className="doc-icon" />
            <div>
              <h1 className="doc-title">{document.filename}</h1>
              <p className="doc-subtitle">
                Uploaded {formatDate(document.created_at)} · {document.page_count ?? 1} pages ·{" "}
                {issues.length} total findings
              </p>
            </div>
          </div>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setIsSummaryModalOpen(true)}
            title="View Traceability Audit Summary"
          >
            <ShieldCheck size={14} />
            <span>Traceability Audit</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setDictionaryInitialTerm(undefined);
              setIsDictionaryOpen(true);
            }}
            title="View Governed Engineering Dictionary"
          >
            <BookOpen size={14} />
            <span>Dictionary</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setIsAuditModalOpen(true)}
            title="View Document Audit Trail"
          >
            <History size={14} />
            <span>Audit Trail</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setIsExportModalOpen(true)}
            title="Export Findings and Verification Artifacts"
            data-testid="open-export-modal-btn"
          >
            <Download size={14} />
            <span>Export</span>
          </button>

          <ThemeToggle />

          <button
            type="button"
            className="icon-button"
            onClick={() => void refreshIssues()}
            disabled={isRefreshing}
            aria-label="Refresh issues"
          >
            <RotateCw size={15} className={isRefreshing ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      {/* Global Alert / Conflict Notification */}
      {alertMessage && (
        <div
          className={`workspace-alert ${
            alertMessage.type === "conflict"
              ? "alert-conflict"
              : alertMessage.type === "error"
              ? "alert-error"
              : "alert-success"
          }`}
          role="alert"
        >
          {alertMessage.type === "conflict" || alertMessage.type === "error" ? (
            <AlertTriangle size={16} />
          ) : (
            <CheckCircle2 size={16} />
          )}
          <span>{alertMessage.message}</span>
          <button
            type="button"
            onClick={() => setAlertMessage(null)}
            className="alert-close-btn"
            aria-label="Dismiss alert"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Split Workspace Body */}
      <main className="workspace-split-body">
        {/* Left Pane: Canonical PDF Document Viewer */}
        <div className="workspace-left-pane">
          <DocumentViewer
            documentId={document.id}
            totalPages={document.page_count ?? 1}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
            activeIssue={selectedIssue}
            onJumpToFinding={(target) => {
              if (target.page_number) {
                setCurrentPage(target.page_number);
              }
            }}
          />
        </div>

        {/* Right Pane: Issue Triage & Decision Panel */}
        <div className="workspace-right-pane">
          <IssuePanel
            issues={issues}
            selectedIssueId={selectedIssueId}
            onSelectIssue={handleSelectIssue}
            onDecideIssue={handleDecideIssue}
            onDisposeIssue={handleDisposeIssue}
            onBulkDecideLanguage={handleBulkDecideLanguage}
            onJumpToPage={(p) => setCurrentPage(p)}
            onAddToDictionary={(term) => {
              setDictionaryInitialTerm(term);
              setIsDictionaryOpen(true);
            }}
          />
        </div>
      </main>

      {/* Bottom Lead Reviewer Disposition Bar */}
      <footer className="workspace-disposition-footer">
        <div className="footer-status-label">
          <span className="lead-role-pill">Lead Reviewer</span>
          {documentDisposition ? (
            <span className="doc-disposition-badge">
              Document Disposition: <strong>{documentDisposition}</strong>
            </span>
          ) : (
            <span className="doc-disposition-pending">
              Document Disposition: <em>Pending Review</em>
            </span>
          )}
        </div>

        <div className="footer-actions">
          <button
            type="button"
            className="btn btn-danger-action"
            onClick={() => setPendingDispositionType("REVISION_REQUIRED")}
          >
            Request Revisions
          </button>
          <button
            type="button"
            className="btn btn-success-action"
            onClick={() => setPendingDispositionType("APPROVED")}
          >
            Approve Document
          </button>
        </div>
      </footer>

      {/* Lead Reviewer Document Disposition Confirmation Modal */}
      {pendingDispositionType && (
        <div
          className="modal-backdrop"
          onClick={() => setPendingDispositionType(null)}
          role="dialog"
          aria-modal="true"
        >
          <div className="modal-container disposition-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                {pendingDispositionType === "APPROVED"
                  ? "Approve Document Sign-Off"
                  : "Request Document Revisions"}
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setPendingDispositionType(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-desc">
                {pendingDispositionType === "APPROVED"
                  ? "Confirming this disposition signifies that all critical issues and traceability findings have been satisfactorily verified or justified."
                  : "Requesting revisions will return this document to the authoring team with open QA findings and required remediation."}
              </p>

              <div className="form-group">
                <label htmlFor="lead-disposition-notes" className="form-label">
                  Justification / Audit Notes (Required)
                </label>
                <textarea
                  id="lead-disposition-notes"
                  rows={3}
                  className="form-textarea"
                  placeholder="Enter regulatory justification, engineering rationale, or required corrections..."
                  value={dispositionJustification}
                  onChange={(e) => setDispositionJustification(e.target.value)}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setPendingDispositionType(null)}
                disabled={isSubmittingDisposition}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`btn ${
                  pendingDispositionType === "APPROVED"
                    ? "btn-success-action"
                    : "btn-danger-action"
                }`}
                onClick={() => void handleConfirmDocumentDisposition()}
                disabled={isSubmittingDisposition || !dispositionJustification.trim()}
              >
                {isSubmittingDisposition
                  ? "Recording..."
                  : pendingDispositionType === "APPROVED"
                  ? "Confirm Approval"
                  : "Confirm Revision Request"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <AuditTrailModal
        documentId={document.id}
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />

      <TraceabilitySummaryModal
        documentId={document.id}
        isOpen={isSummaryModalOpen}
        onClose={() => setIsSummaryModalOpen(false)}
      />

      <DictionaryModal
        isOpen={isDictionaryOpen}
        initialTerm={dictionaryInitialTerm}
        onClose={() => {
          setIsDictionaryOpen(false);
          setDictionaryInitialTerm(undefined);
        }}
        onTermCreated={() => void refreshIssues()}
      />

      <ExportModal
        documentId={document.id}
        documentFilename={document.filename}
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
      />
    </div>
  );
}
