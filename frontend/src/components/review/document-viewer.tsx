"use client";

import { useEffect, useState } from "react";
import {
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
import { HighlightOverlay, type HighlightBoxItem } from "./highlight-overlay";

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

  // Derive highlights if activeIssue is provided and highlights array is empty
  const effectiveHighlights = [...highlights];
  if (effectiveHighlights.length === 0 && activeIssue) {
    const loc = getIssueLocation(activeIssue);
    if (loc.bbox) {
      effectiveHighlights.push({
        box: {
          ...loc.bbox,
          page_index:
            loc.bbox.page_index ??
            (loc.page_number ? loc.page_number - 1 : 0),
        },
        label: activeIssue.type,
        variant: "primary",
      });
    }
    const ev = activeIssue.evidence;
    if (ev && ev.kind === "TABLE_MATH" && Array.isArray(ev.operand_locations)) {
      for (const opBox of ev.operand_locations) {
        effectiveHighlights.push({
          box: opBox,
          label: "Operand",
          variant: "operand",
        });
      }
    } else if (ev && ev.kind === "REFERENCE_DRIFT" && ev.target_location) {
      effectiveHighlights.push({
        box: ev.target_location,
        label: "Target",
        variant: "target",
      });
    } else if (ev && ev.kind === "STANDARD" && ev.bibliography_location) {
      effectiveHighlights.push({
        box: ev.bibliography_location,
        label: "Bibliography",
        variant: "target",
      });
    }
  }

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

  // Keyboard navigation
  useEffect(() => {
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
  }, [currentPage, effectiveTotalPages, onPageChange]);

  return (
    <div className="flex flex-col h-full bg-sunken border-r border-line select-none">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-panel border-b border-line text-sm text-ink-soft">
        {/* Document Info */}
        <div className="flex items-center gap-2 truncate max-w-[280px]">
          <span className="font-mono text-xs text-muted uppercase">DOC</span>
          <span className="font-medium text-xs text-ink truncate" title={effectiveTitle}>
            {effectiveTitle}
          </span>
        </div>

        {/* Page Navigation Controls */}
        <div className="flex items-center gap-1.5 bg-panel px-2 py-1 rounded border border-line">
          <button
            type="button"
            onClick={handleFirst}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-panel-raised disabled:opacity-30 disabled:cursor-not-allowed text-muted"
            title="First Page"
          >
            <ChevronsLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-panel-raised disabled:opacity-30 disabled:cursor-not-allowed text-muted"
            title="Previous Page (Left Arrow)"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="font-mono text-xs px-2 text-ink">
            Page {currentPage} of {effectiveTotalPages}
          </span>

          <button
            type="button"
            onClick={handleNext}
            disabled={currentPage >= effectiveTotalPages}
            className="p-1 rounded hover:bg-panel-raised disabled:opacity-30 disabled:cursor-not-allowed text-muted"
            title="Next Page (Right Arrow)"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleLast}
            disabled={currentPage >= effectiveTotalPages}
            className="p-1 rounded hover:bg-panel-raised disabled:opacity-30 disabled:cursor-not-allowed text-muted"
            title="Last Page"
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        </div>

        {/* Zoom & View Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-panel px-2 py-1 rounded border border-line">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(z - 15, 50))}
              className="p-1 rounded hover:bg-panel-raised text-muted"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] px-1 text-ink-soft">{zoomLevel}%</span>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(z + 15, 200))}
              className="p-1 rounded hover:bg-panel-raised text-muted"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(100)}
              className="p-1 rounded hover:bg-panel-raised text-muted"
              title="Reset Zoom"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex rounded border border-line p-0.5 bg-panel">
            <button
              type="button"
              onClick={() => setActiveTab("interactive")}
              className={`px-2 py-0.5 text-xs font-mono rounded ${
                activeTab === "interactive"
                  ? "bg-primary text-ink"
                  : "text-muted hover:text-ink"
              }`}
            >
              Annotated
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("embedded")}
              className={`px-2 py-0.5 text-xs font-mono rounded ${
                activeTab === "embedded"
                  ? "bg-primary text-ink"
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
            className="p-1.5 rounded hover:bg-panel-raised text-muted hover:text-ink"
            title="Open canonical PDF in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Quick Jump Bar for Multi-Location Findings */}
      {effectiveJumpTargets.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-selected border-b border-primary/40 text-xs">
          <span className="font-mono text-accent-soft uppercase text-[11px] font-semibold">
            Jump to finding anchor:
          </span>
          {effectiveJumpTargets.map((t, idx) => (
            <button
              key={`jump-${idx}`}
              type="button"
              onClick={() => {
                onPageChange(t.page);
                if (onJumpToFinding) onJumpToFinding({ page_number: t.page });
              }}
              className={`px-2.5 py-0.5 rounded text-xs font-medium transition-colors ${
                currentPage === t.page
                  ? "bg-primary text-ink"
                  : "bg-chip text-accent-soft hover:bg-panel-raised"
              }`}
            >
              {t.label} (Page {t.page})
            </button>
          ))}
        </div>
      )}

      {/* Main Document Canvas View */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start bg-sunken">
        {activeTab === "interactive" ? (
          <div
            className="relative bg-white shadow-2xl rounded-sm transition-transform duration-100 origin-top"
            style={{
              width: `${(612 * zoomLevel) / 100}px`,
              minHeight: `${(792 * zoomLevel) / 100}px`,
              aspectRatio: "612 / 792",
            }}
          >
            {/* Native PDF page embed */}
            <iframe
              src={`${effectivePdfUrl}#page=${currentPage}&toolbar=0&navpanes=0`}
              title={`Page ${currentPage}`}
              className="w-full h-full border-0 absolute inset-0 pointer-events-auto"
            />

            {/* Coordinate Highlight Overlay */}
            <HighlightOverlay
              highlights={effectiveHighlights}
              pageIndex={currentPage - 1} // 0-indexed for bounding boxes
            />
          </div>
        ) : (
          <div className="w-full h-full min-h-[600px] rounded border border-line overflow-hidden">
            <iframe
              src={`${effectivePdfUrl}#page=${currentPage}`}
              title="Full PDF Rendition"
              className="w-full h-full min-h-[700px] border-0"
            />
          </div>
        )}
      </div>
    </div>
  );
}
