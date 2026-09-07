"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ExternalLink,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { getPdfUrl, getIssueLocation, type IssueItem } from "@/lib/api";
import { type HighlightBoxItem } from "./highlight-overlay";
import { PdfCanvasViewer } from "./pdf-canvas-viewer";

interface DocumentViewerProps {
  pdfUrl?: string;
  documentId?: string;
  documentTitle?: string;
  currentPage: number;
  totalPages?: number;
  onPageChange: (page: number) => void;
  highlights?: HighlightBoxItem[];
  jumpTargets?: Array<{ page: number; label: string }>;
  activeIssue?: IssueItem | null;
  onJumpToFinding?: (target: { page_number?: number }) => void;
}

export function DocumentViewer({
  pdfUrl,
  documentId,
  documentTitle = "Document",
  currentPage,
  totalPages = 1,
  onPageChange,
  highlights = [],
  jumpTargets = [],
  activeIssue,
  onJumpToFinding,
}: DocumentViewerProps) {
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeTab, setActiveTab] = useState<"interactive" | "embedded">("interactive");

  const effectivePdfUrl = pdfUrl || (documentId ? getPdfUrl(documentId) : "");
  const effectiveTitle = documentTitle || "Document";

  // Derive jump targets if activeIssue is provided and jumpTargets is empty
  const effectiveJumpTargets = [...jumpTargets];
  if (effectiveJumpTargets.length === 0 && activeIssue) {
    const loc = getIssueLocation(activeIssue);
    if (loc.page_number) {
      effectiveJumpTargets.push({
        page: loc.page_number,
        label: "Finding Anchor",
      });
    }
  }

  const effectiveTotalPages = Math.max(totalPages, 1);

  const handlePrev = () => {
    if (currentPage > 1) onPageChange(currentPage - 1);
  };

  const handleNext = () => {
    if (currentPage < effectiveTotalPages) onPageChange(currentPage + 1);
  };

  const handleFirst = () => onPageChange(1);
  const handleLast = () => onPageChange(effectiveTotalPages);

  // Keyboard navigation for fallback embedded mode
  useEffect(() => {
    if (activeTab !== "embedded") return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      if (e.key === "ArrowLeft" && !e.altKey && !e.ctrlKey) {
        if (currentPage > 1) onPageChange(currentPage - 1);
      } else if (e.key === "ArrowRight" && !e.altKey && !e.ctrlKey) {
        if (currentPage < effectiveTotalPages) onPageChange(currentPage + 1);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeTab, currentPage, effectiveTotalPages, onPageChange]);

  return (
    <div className="flex flex-col h-full bg-sunken border-r border-line select-none min-h-0">
      {/* Top Header & Tab Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-panel border-b border-line text-xs text-ink-soft">
        {/* Return Button & Document Info */}
        <div className="flex items-center gap-2 truncate min-w-0 max-w-[calc(100%-250px)]">
          {documentId && (
            <Link
              href={`/documents/${documentId}`}
              className="workspace-back-link shrink-0 py-1 px-2 text-[11px]"
              title="Back to inspection status"
              aria-label="Back to inspection status"
            >
              <ArrowLeft size={13} />
              <span className="hidden sm:inline">Inspection</span>
            </Link>
          )}
          <span className="font-mono text-[10px] text-muted uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-chip text-chip-ink border border-line shrink-0">
            DOC
          </span>
          <span className="font-semibold text-xs text-ink truncate" title={effectiveTitle}>
            {effectiveTitle}
          </span>
        </div>

        {/* View Switcher & External Link */}
        <div className="flex items-center gap-1.5 ml-auto">
          <div className="flex rounded border border-line p-0.5 bg-panel-raised">
            <button
              type="button"
              onClick={() => setActiveTab("interactive")}
              className={`px-2.5 py-1 text-[11px] font-mono font-semibold rounded transition-colors ${
                activeTab === "interactive"
                  ? "bg-primary text-white shadow-xs"
                  : "text-muted hover:text-ink"
              }`}
            >
              Annotated Canvas
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("embedded")}
              className={`px-2.5 py-1 text-[11px] font-mono font-semibold rounded transition-colors ${
                activeTab === "embedded"
                  ? "bg-primary text-white shadow-xs"
                  : "text-muted hover:text-ink"
              }`}
            >
              Native PDF
            </button>
          </div>

          <a
            href={effectivePdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded border border-line bg-panel hover:bg-panel-raised text-muted hover:text-ink transition-colors"
            title="Open canonical PDF in new browser tab"
            aria-label="Open canonical PDF in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Quick Jump Bar for Multi-Location Findings */}
      {effectiveJumpTargets.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 px-3 py-1.5 bg-selected border-b border-line text-xs">
          <span className="font-mono text-accent-soft uppercase text-[10px] font-bold">
            Anchor:
          </span>
          {effectiveJumpTargets.map((t, idx) => (
            <button
              key={`jump-${idx}`}
              type="button"
              onClick={() => {
                onPageChange(t.page);
                if (onJumpToFinding) onJumpToFinding({ page_number: t.page });
              }}
              className={`px-2 py-0.5 rounded text-[11px] font-medium font-mono transition-colors ${
                currentPage === t.page
                  ? "bg-primary text-white font-bold"
                  : "bg-chip text-chip-ink hover:bg-panel-raised border border-line"
              }`}
            >
              {t.label} (p. {t.page})
            </button>
          ))}
        </div>
      )}

      {/* Main Viewport */}
      {activeTab === "interactive" ? (
        documentId ? (
          <PdfCanvasViewer
            documentId={documentId}
            currentPage={currentPage}
            onPageChange={onPageChange}
            totalPages={effectiveTotalPages}
            highlights={highlights}
            activeIssue={activeIssue}
            onJumpToFinding={onJumpToFinding}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center bg-sunken text-muted text-sm">
            No document ID available.
          </div>
        )
      ) : (
        <div className="flex flex-col flex-1 min-h-0">
          {/* Embedded Toolbar for Native PDF */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-panel px-3 py-1.5 text-xs text-ink-soft">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleFirst}
                disabled={currentPage <= 1}
                className="btn btn-secondary btn-sm p-1.5"
                title="First Page"
              >
                <ChevronsLeft className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handlePrev}
                disabled={currentPage <= 1}
                className="btn btn-secondary btn-sm p-1.5"
                title="Previous Page"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-xs px-2 text-ink font-semibold">
                Page {currentPage} of {effectiveTotalPages}
              </span>
              <button
                type="button"
                onClick={handleNext}
                disabled={currentPage >= effectiveTotalPages}
                className="btn btn-secondary btn-sm p-1.5"
                title="Next Page"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleLast}
                disabled={currentPage >= effectiveTotalPages}
                className="btn btn-secondary btn-sm p-1.5"
                title="Last Page"
              >
                <ChevronsRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.max(z - 15, 50))}
                className="btn btn-secondary btn-sm p-1.5"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-xs text-ink-soft w-12 text-center font-semibold">
                {zoomLevel}%
              </span>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.min(z + 15, 200))}
                className="btn btn-secondary btn-sm p-1.5"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel(100)}
                className="btn btn-secondary btn-sm p-1.5"
                title="Reset Zoom"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-hidden p-2 bg-sunken">
            <iframe
              src={`${effectivePdfUrl}#page=${currentPage}`}
              title="Full PDF Rendition"
              className="w-full h-full border-0 rounded bg-white shadow-md"
            />
          </div>
        </div>
      )}
    </div>
  );
}
