"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock3,
  Download,
  FileCheck2,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  RotateCw,
  ShieldCheck,
  X,
} from "lucide-react";
import type { DocumentItem, IssueItem } from "@/lib/api";
import {
  curateIssue,
  listAllDocumentIssues,
  getIssueLocation,
} from "@/lib/api";
import { downloadExport } from "@/lib/download";
import { useLocale } from "@/components/layout/locale-provider";
import { IssuePanel } from "./issue-panel";
import { ReportPreviewModal } from "./report-preview-modal";
import { DictionaryModal } from "./dictionary-modal";
import { ExportModal } from "./export-modal";
import { DocumentViewer } from "./document-viewer";

interface SplitScreenViewerProps {
  document: DocumentItem;
  initialIssues: IssueItem[];
  embedded?: boolean;
}

export function SplitScreenViewer({
  document,
  initialIssues,
  embedded = false,
}: SplitScreenViewerProps) {
  const { locale } = useLocale();
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

  const selectedIssue = useMemo(
    () => issues.find((i) => i.id === selectedIssueId) ?? null,
    [issues, selectedIssueId]
  );

  // Mobile pane switcher: "document" or "findings"
  const [mobilePane, setMobilePane] = useState<"document" | "findings">("document");

  // Modals
  const [isReportModalOpen, setIsReportModalOpen] = useState<boolean>(false);
  const [isDictionaryOpen, setIsDictionaryOpen] = useState<boolean>(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);
  const [dictionaryInitialTerm, setDictionaryInitialTerm] = useState<string | undefined>(undefined);

  // User feedback notification
  const [alertMessage, setAlertMessage] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Sync state if initialIssues change
  useEffect(() => {
    if (initialIssues.length > 0 && !selectedIssueId) {
      setSelectedIssueId(initialIssues[0].id);
    }
  }, [initialIssues, selectedIssueId]);

  const [isRefreshing, setIsRefreshing] = useState(false);
  const handleReloadIssues = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const fresh = await listAllDocumentIssues(document.id);
      setIssues(fresh);
      setAlertMessage({ type: "success", message: "Findings refreshed." });
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
    (i) =>
      i.included_in_report &&
      ["BLOCKER", "CRITICAL", "MAJOR"].includes(i.severity)
  ).length;
  const auditCount = issues.filter(
    (issue) => issue.category === "BUDINSKI" || issue.category === "LAYOUT"
  ).length;
  const isProcessing = document.status === "QUEUED" || document.status === "PROCESSING";
  const statusMessage =
    document.status === "FAILED"
      ? "The review pipeline failed. Findings shown below may be incomplete."
      : document.status === "COMPLETED_WITH_WARNINGS"
        ? "Review completed with warnings. Check the findings before exporting."
        : isProcessing
          ? "The review pipeline is still running. Findings may continue to appear."
           : null;
  const budinskiIssues = issues.filter((issue) => issue.category === "BUDINSKI");
  const baselinePasses = budinskiIssues.filter((issue) => issue.severity !== "BLOCKER" && issue.severity !== "CRITICAL").length;

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden bg-slate-100 text-slate-900">
      {/* Above Card Header: Breadcrumbs & Document Info & Status */}
      <div className={embedded ? "hidden" : "flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5 shrink-0"}>
        {/* Left: Return Link & Document Title */}
        <div className="flex items-center gap-2.5 min-w-0">
          <Link
            href={`/documents/${document.id}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 shrink-0"
            title="Back to inspection status"
          >
            <ArrowLeft size={14} />
            <span>Inspection</span>
          </Link>
          <div className="h-4 w-[1px] bg-slate-200 shrink-0 hidden sm:block" />
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
            <FileText size={16} />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold truncate text-slate-900 m-0 leading-snug">
              {document.filename}
            </h1>
            <div className="flex items-center gap-2 text-[11px] text-slate-500 leading-tight">
              <span>{document.page_count ?? "—"} pages</span>
              <span>·</span>
              <span>{issues.length} total findings</span>
              <span>·</span>
              <span>{auditCount} technical/layout</span>
            </div>
          </div>
        </div>

        {/* Right: Report Summary Pill */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs shadow-2xs">
            <span className="font-semibold text-slate-900">{includedCount} Included</span>
            <span className="text-slate-300">|</span>
            <span className={blockersCount > 0 ? "font-semibold text-rose-600" : "text-slate-400"}>
              {blockersCount} Blockers
            </span>
          </div>
        </div>
      </div>

      {statusMessage && (
        <div
          className={`${embedded ? "hidden" : "flex"} mx-4 my-2 items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
            document.status === "FAILED"
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : document.status === "COMPLETED_WITH_WARNINGS"
                ? "border-amber-200 bg-amber-50 text-amber-800"
                : "border-blue-200 bg-blue-50 text-blue-800"
          }`}
          role="status"
          aria-live="polite"
        >
          {document.status === "FAILED" ? (
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          ) : isProcessing ? (
            <Clock3 size={15} className="mt-0.5 shrink-0" />
          ) : (
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          )}
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Main Review Workspace Card */}
      <div className="flex min-h-0 flex-1 w-full flex-col overflow-hidden">
        {/* Card Header / Action Toolbar */}
        <header className={`${embedded ? "hidden" : "flex"} h-12 border-b border-slate-200 bg-white items-center justify-between px-3 sm:px-4 shrink-0 gap-3`}>
          {/* Left: Eyebrow label & Mobile Pane Switcher */}
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 hidden sm:inline m-0">
              Review & Curation
            </span>

            {/* Mobile Pane Switcher */}
            <div className="flex lg:hidden rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs">
              <button
                type="button"
                className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
                  mobilePane === "document"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
                onClick={() => setMobilePane("document")}
              >
                Document
              </button>
              <button
                type="button"
                className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
                  mobilePane === "findings"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
                onClick={() => setMobilePane("findings")}
              >
                Findings ({issues.length})
              </button>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setIsScorecardOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
            >
              <ShieldCheck size={13} className="text-indigo-600" />
              <span className="hidden sm:inline">Budinski</span> Scorecard
            </button>

            <button
              type="button"
              onClick={() => setIsReportModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
            >
              <FileSpreadsheet size={13} />
              <span>Report Preview</span>
            </button>

            <button
              type="button"
              onClick={() => setIsExportModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1 text-xs font-bold text-white hover:bg-blue-700 shadow-xs"
            >
              <Download size={13} />
              <span>Export</span>
            </button>

            <button
              type="button"
              onClick={() => void handleReloadIssues()}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1.5 text-xs text-slate-600 hover:bg-slate-50 shadow-xs disabled:opacity-50"
              title="Refresh findings list"
            >
              <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
            </button>
          </div>
        </header>

        {/* Global Alert Notification */}
        {alertMessage && (
          <div
            role="alert"
            className={`px-4 py-2 text-xs flex items-center justify-between z-20 shrink-0 border-b ${
              alertMessage.type === "error"
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
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
        <div className="review-workspace-split flex-1 flex overflow-hidden relative min-h-0 min-w-0">
          {/* Left / Center: PDF Document Viewer */}
          <main
            className={`review-document-pane flex-1 h-full min-h-0 overflow-hidden min-w-0 ${
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
            className={`review-findings-pane w-full lg:w-[420px] xl:w-[480px] h-full min-h-0 min-w-0 shrink-0 overflow-hidden ${
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
        <footer className={`${embedded ? "hidden" : "flex"} min-h-11 border-t border-slate-200 bg-white flex-wrap items-center justify-between px-3 sm:px-4 py-2 shrink-0 text-xs gap-2`}>
          <div className="flex items-center gap-2 text-slate-500">
            <span className="font-semibold text-slate-900">{includedCount}</span> findings marked for export
            {blockersCount > 0 && (
              <span className="text-rose-600 font-medium">({blockersCount} blockers require correction)</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void downloadExport(document.id, "docx", false, locale)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 shadow-xs"
            >
              <Download size={13} />
              <span>Export DOCX</span>
            </button>
            <button
              type="button"
              onClick={() => void downloadExport(document.id, "pdf")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <FileText size={13} />
              <span>Export Annotated PDF</span>
            </button>
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

      {isScorecardOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-xs" role="dialog" aria-modal="true" aria-labelledby="scorecard-title" onClick={() => setIsScorecardOpen(false)}>
          <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <header className="flex items-start justify-between border-b border-slate-100 p-5">
              <div>
                <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Technical writing audit</p>
                <h2 id="scorecard-title" className="text-lg font-bold text-slate-900">Budinski Scorecard</h2>
                <p className="mt-1 text-xs text-slate-500">41 Appendix 12 items and 4 baseline measures.</p>
              </div>
              <button type="button" className="text-slate-400 hover:text-slate-600 rounded-lg p-1" aria-label="Close scorecard" onClick={() => setIsScorecardOpen(false)}>
                <X size={18} />
              </button>
            </header>
            <div className="grid grid-cols-3 gap-3 p-5">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-slate-900">{budinskiIssues.length}</strong>
                <span className="text-[11px] font-medium text-slate-500">Items flagged</span>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-emerald-600">{Math.max(0, 41 - budinskiIssues.length)}</strong>
                <span className="text-[11px] font-medium text-slate-500">Items clear</span>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <strong className="block text-2xl font-bold text-blue-600">{baselinePasses}/4</strong>
                <span className="text-[11px] font-medium text-slate-500">Baselines passing</span>
              </div>
            </div>
            <div className="px-5 pb-5">
              <div className="flex justify-between text-xs font-semibold text-slate-600">
                <span>Appendix 12 coverage</span>
                <b className="text-blue-600 font-bold">{Math.round(((41 - budinskiIssues.length) / 41) * 100)}%</b>
              </div>
              <progress className="mt-2 h-2 w-full accent-blue-600 rounded-full" value={Math.max(0, 41 - budinskiIssues.length)} max="41" />
            </div>
            <footer className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-500">
              <span>Detailed values remain in the exported DOCX report.</span>
              <button type="button" className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50" onClick={() => setIsScorecardOpen(false)}>
                Close
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
