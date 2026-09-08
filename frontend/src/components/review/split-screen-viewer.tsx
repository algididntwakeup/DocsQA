"use client";

import { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  RotateCw,
  X,
} from "lucide-react";
import type { DocumentItem, IssueItem } from "@/lib/api";
import {
  curateIssue,
  listDocumentIssues,
  getExportUrl,
  getIssueLocation,
} from "@/lib/api";
import { DocumentViewer } from "./document-viewer";
import { IssuePanel } from "./issue-panel";
import { ReportPreviewModal } from "./report-preview-modal";
import { DictionaryModal } from "./dictionary-modal";
import { ExportModal } from "./export-modal";

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
      return loc.page_number ?? 1;
    }
    return 1;
  });

  // Mobile pane switcher: "document" or "findings"
  const [mobilePane, setMobilePane] = useState<"document" | "findings">("document");

  // Modals
  const [isReportModalOpen, setIsReportModalOpen] = useState<boolean>(false);
  const [isDictionaryOpen, setIsDictionaryOpen] = useState<boolean>(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [dictionaryInitialTerm, setDictionaryInitialTerm] = useState<string | undefined>(undefined);

  // Global feedback alert
  const [alertMessage, setAlertMessage] = useState<{
    type: "success" | "error";
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
      const res = await listDocumentIssues(document.id);
      setIssues(res.issues);
      setAlertMessage({ type: "success", message: "Findings successfully refreshed." });
      setTimeout(() => setAlertMessage(null), 3000);
    } catch {
      setAlertMessage({ type: "error", message: "Failed to reload findings list." });
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

  const handleCurateIssue = async (
    issueId: string,
    payload: { included_in_report: boolean; reviewer_note?: string | null }
  ) => {
    try {
      const updated = await curateIssue(issueId, payload);
      setIssues((prev) => prev.map((item) => (item.id === issueId ? updated : item)));
      setAlertMessage({
        type: "success",
        message: `Finding #${issueId.slice(0, 8)} ${
          payload.included_in_report ? "included in" : "excluded from"
        } report.`,
      });
      setTimeout(() => setAlertMessage(null), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update report curation";
      setAlertMessage({ type: "error", message: msg });
    }
  };

  const handleAddToDictionary = (term: string) => {
    setDictionaryInitialTerm(term);
    setIsDictionaryOpen(true);
  };

  // Report statistics
  const includedCount = issues.filter((i) => i.included_in_report).length;
  const blockersCount = issues.filter(
    (i) => i.included_in_report && (i.severity === "CRITICAL" || i.severity === "HIGH")
  ).length;

  return (
    <div className="flex flex-col w-full flex-1 min-h-0 text-ink">
      {/* Above Card Header: Breadcrumbs & Document Info & Status */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 shrink-0">
        {/* Left: Return Link & Document Title */}
        <div className="flex items-center gap-2.5 min-w-0">
          <Link
            href={`/documents/${document.id}`}
            className="button button-secondary btn-sm flex items-center gap-1.5 shrink-0"
            title="Back to inspection status"
          >
            <ArrowLeft size={14} />
            <span>Inspection</span>
          </Link>
          <div className="h-4 w-[1px] bg-line shrink-0 hidden sm:block" />
          <div className="p-1.5 rounded-md bg-panel border border-line shrink-0">
            <FileText size={16} className="text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold truncate text-ink m-0 leading-snug">
              {document.filename}
            </h1>
            <div className="flex items-center gap-2 text-[11px] text-muted leading-tight">
              <span>{document.page_count ?? "—"} pages</span>
              <span>·</span>
              <span>{issues.length} total findings</span>
            </div>
          </div>
        </div>

        {/* Right: Report Summary Pill */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-panel border border-line text-xs shadow-2xs">
            <span className="font-semibold text-ink">{includedCount} Included</span>
            <span className="text-muted">|</span>
            <span className={blockersCount > 0 ? "font-semibold text-red-500" : "text-muted"}>
              {blockersCount} Blockers
            </span>
          </div>
        </div>
      </div>

      {/* Main Review Workspace Card */}
      <div className="panel flex flex-col flex-1 min-h-[520px] w-full overflow-hidden shadow-xs border-line">
        {/* Card Header / Action Toolbar */}
        <header className="h-12 border-b border-line bg-panel flex items-center justify-between px-3 sm:px-4 shrink-0 gap-3">
          {/* Left: Eyebrow label & Mobile Pane Switcher */}
          <div className="flex items-center gap-3">
            <span className="eyebrow text-muted hidden sm:inline text-[10px] tracking-wider m-0">
              Review & Curation
            </span>

            {/* Mobile Pane Switcher */}
            <div className="flex lg:hidden rounded border border-line bg-sunken p-0.5 text-xs">
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-medium transition-colors ${
                  mobilePane === "document"
                    ? "bg-panel text-ink shadow-xs"
                    : "text-muted hover:text-ink"
                }`}
                onClick={() => setMobilePane("document")}
              >
                Document
              </button>
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-medium transition-colors ${
                  mobilePane === "findings"
                    ? "bg-panel text-ink shadow-xs"
                    : "text-muted hover:text-ink"
                }`}
                onClick={() => setMobilePane("findings")}
              >
                Findings ({includedCount})
              </button>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <button
              type="button"
              className="button button-ghost btn-sm p-1.5"
              onClick={refreshIssues}
              disabled={isRefreshing}
              title="Refresh findings"
              aria-label="Refresh findings"
            >
              <RotateCw size={14} className={isRefreshing ? "animate-spin" : ""} />
            </button>

            <button
              type="button"
              className="button button-ghost btn-sm flex items-center gap-1.5"
              onClick={() => {
                setDictionaryInitialTerm(undefined);
                setIsDictionaryOpen(true);
              }}
              title="Custom Dictionary"
            >
              <BookOpen size={14} className="text-amber-500" />
              <span className="hidden md:inline">Dictionary</span>
            </button>

            <button
              type="button"
              className="button button-secondary btn-sm flex items-center gap-1.5"
              onClick={() => setIsReportModalOpen(true)}
            >
              <FileCheck2 size={14} className="text-sky-500" />
              <span className="hidden sm:inline">Report Preview</span>
            </button>

            <button
              type="button"
              className="button button-primary btn-sm flex items-center gap-1.5"
              onClick={() => setIsExportModalOpen(true)}
            >
              <Download size={13} />
              <span>Export</span>
            </button>
          </div>
        </header>

        {/* Global Alert Notification */}
        {alertMessage && (
          <div
            role="alert"
            className={`px-4 py-2 text-xs flex items-center justify-between z-20 shrink-0 ${
              alertMessage.type === "error"
                ? "bg-red-500/15 text-red-700 dark:text-red-300 border-b border-red-500/30"
                : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-b border-emerald-500/30"
            }`}
          >
            <div className="flex items-center gap-2">
              {alertMessage.type === "error" ? (
                <AlertTriangle size={15} />
              ) : (
                <CheckCircle2 size={15} />
              )}
              <span>{alertMessage.message}</span>
            </div>
            <button
              type="button"
              className="text-current opacity-70 hover:opacity-100"
              onClick={() => setAlertMessage(null)}
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Main Workspace Split Layout */}
        <div className="flex-1 flex overflow-hidden relative min-h-0">
          {/* Left / Center: PDF Document Viewer */}
          <main
            className={`flex-1 h-full overflow-hidden min-w-0 ${
              mobilePane === "document" ? "block" : "hidden lg:block"
            }`}
          >
            <DocumentViewer
              documentId={document.id}
              documentTitle={document.filename}
              activeIssue={selectedIssue}
              currentPage={currentPage}
              totalPages={document.page_count ?? 1}
              onPageChange={setCurrentPage}
              onJumpToFinding={(target) => {
                if (target.page_number) setCurrentPage(target.page_number);
              }}
            />
          </main>

          {/* Right Pane: Findings Curation Panel */}
          <section
            className={`w-full lg:w-[380px] xl:w-[420px] h-full shrink-0 overflow-hidden ${
              mobilePane === "findings" ? "block" : "hidden lg:block"
            }`}
          >
            <IssuePanel
              issues={issues}
              selectedIssueId={selectedIssueId}
              onSelectIssue={handleSelectIssue}
              onCurateIssue={handleCurateIssue}
              onJumpToPage={setCurrentPage}
              onAddToDictionary={handleAddToDictionary}
            />
          </section>
        </div>

        {/* Bottom Bar: Report Deliverables Actions */}
        <footer className="min-h-11 border-t border-line bg-panel flex flex-wrap items-center justify-between px-3 sm:px-4 py-2 shrink-0 text-xs gap-2">
          <div className="flex items-center gap-2 text-muted">
            <span className="font-semibold text-ink">{includedCount}</span> findings marked for export
            {blockersCount > 0 && (
              <span className="text-red-500 font-medium">({blockersCount} blockers require correction)</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <a
              href={getExportUrl(document.id, "docx")}
              download
              className="button button-primary btn-sm flex items-center gap-1.5"
            >
              <Download size={13} />
              <span>Export DOCX</span>
            </a>
            <a
              href={getExportUrl(document.id, "pdf")}
              download
              className="button button-secondary btn-sm flex items-center gap-1.5"
            >
              <FileText size={13} />
              <span>Export Annotated PDF</span>
            </a>
          </div>
        </footer>
      </div>

      {/* Modals */}
      <ReportPreviewModal
        documentId={document.id}
        documentFilename={document.filename}
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />

      <DictionaryModal
        isOpen={isDictionaryOpen}
        onClose={() => setIsDictionaryOpen(false)}
        initialTerm={dictionaryInitialTerm}
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
