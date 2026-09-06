"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { getIssueLocation, getPdfUrl, type IssueItem } from "@/lib/api";
import { HighlightOverlay, type HighlightBoxItem } from "./highlight-overlay";

if (typeof window !== "undefined" && pdfjsLib.GlobalWorkerOptions) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
}

interface PdfCanvasViewerProps {
  documentId: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages?: number;
  highlights?: HighlightBoxItem[];
  activeIssue?: IssueItem | null;
  onJumpToFinding?: (target: { page_number?: number }) => void;
}

interface LoadedDoc {
  doc: pdfjsLib.PDFDocumentProxy;
}

export function PdfCanvasViewer({
  documentId,
  currentPage,
  onPageChange,
  totalPages,
  highlights = [],
  activeIssue,
  onJumpToFinding,
}: PdfCanvasViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [loaded, setLoaded] = useState<LoadedDoc | null>(null);
  const [pageCount, setPageCount] = useState<number>(totalPages ?? 1);
  const [zoom, setZoom] = useState<number>(1);
  const [renderScale, setRenderScale] = useState<number>(1);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [pageSize, setPageSize] = useState<{ width: number; height: number }>({
    width: 612,
    height: 792,
  });

  // Keep the loading task so we can destroy it on unmount / id change.
  const loadingTaskRef = useRef<pdfjsLib.PDFDocumentLoadingTask | null>(null);

  // Resize observer keeps the page fitted comfortably to the pane width.
  useEffect(() => {
    const scroll = scrollRef.current;
    if (!scroll) return;
    const update = () => {
      const available = scroll.clientWidth > 0 ? scroll.clientWidth - 48 : 600;
      const baseWidth = pageSize.width > 0 ? pageSize.width / (renderScale * zoom) : 612;
      setRenderScale(Math.max(available / baseWidth, 0.35));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(scroll);
    return () => observer.disconnect();
  }, [pageSize.width, renderScale, zoom]);

  // Open the document once; dispose on unmount / id change.
  useEffect(() => {
    let disposed = false;
    void loadingTaskRef.current?.destroy().catch(() => undefined);
    loadingTaskRef.current = null;

    async function open() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const response = await fetch(getPdfUrl(documentId), { cache: "force-cache" });
        if (!response.ok) throw new Error(`PDF request failed (${response.status}).`);
        const data = await response.arrayBuffer();
        const task = pdfjsLib.getDocument({ data });
        loadingTaskRef.current = task;
        const doc = await task.promise;
        if (disposed) {
          void task.destroy();
          return;
        }
        setPageCount(doc.numPages);
        setLoaded({ doc });
        setIsLoading(false);
      } catch (err) {
        if (!disposed) {
          setLoadError(err instanceof Error ? err.message : "Failed to load PDF.");
          setIsLoading(false);
        }
      }
    }
    void open();
    return () => {
      disposed = true;
      void loadingTaskRef.current?.destroy().catch(() => undefined);
      loadingTaskRef.current = null;
    };
  }, [documentId]);

  // Derive highlights if activeIssue is provided and highlights array is empty
  const effectiveHighlights = useMemo(() => {
    const list: HighlightBoxItem[] = [...highlights];
    if (list.length === 0 && activeIssue) {
      const loc = getIssueLocation(activeIssue);
      if (loc.bbox) {
        list.push({
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
          list.push({
            box: opBox,
            label: "Operand",
            variant: "operand",
          });
        }
      } else if (ev && ev.kind === "REFERENCE_DRIFT" && ev.target_location) {
        list.push({
          box: ev.target_location,
          label: "Target",
          variant: "target",
        });
      } else if (ev && ev.kind === "STANDARD" && ev.bibliography_location) {
        list.push({
          box: ev.bibliography_location,
          label: "Bibliography",
          variant: "target",
        });
      }
    }
    return list;
  }, [highlights, activeIssue]);

  // Render the requested page onto the canvas.
  const effectiveTotalPages = Math.max(totalPages ?? pageCount, 1);
  const pageNumber = Math.min(Math.max(1, currentPage), effectiveTotalPages);
  const renderTick = useRef(0);

  useEffect(() => {
    const doc = loaded?.doc;
    const canvas = canvasRef.current;
    if (!doc || !canvas || isLoading) return;

    const tick = ++renderTick.current;
    let cancelled = false;
    let renderTask: pdfjsLib.RenderTask | null = null;

    async function draw() {
      try {
        const liveDoc = loaded?.doc;
        const liveCanvas = canvasRef.current;
        if (!liveDoc || !liveCanvas) return;
        const page = await liveDoc.getPage(pageNumber);
        if (cancelled || tick !== renderTick.current) return;

        const scale = renderScale * zoom;
        const viewport = page.getViewport({ scale });
        const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

        const cssWidth = Math.floor(viewport.width);
        const cssHeight = Math.floor(viewport.height);

        liveCanvas.width = Math.floor(viewport.width * dpr);
        liveCanvas.height = Math.floor(viewport.height * dpr);
        liveCanvas.style.width = `${cssWidth}px`;
        liveCanvas.style.height = `${cssHeight}px`;

        setPageSize({ width: cssWidth, height: cssHeight });

        const context = liveCanvas.getContext("2d");
        if (!context) return;
        context.setTransform(dpr, 0, 0, dpr, 0, 0);
        renderTask = page.render({
          canvasContext: context,
          viewport,
          canvas: liveCanvas,
        });
        await renderTask.promise;
      } catch (err) {
        if (err instanceof Error && err.name === "RenderingCancelledException") return;
        if (!cancelled && tick === renderTick.current) {
          setLoadError(err instanceof Error ? err.message : "Failed to render page.");
        }
      }
    }
    void draw();

    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [loaded, pageNumber, renderScale, zoom, isLoading]);

  // Scroll to top when the requested page changes (jump from issue list).
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [pageNumber]);

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

  const changeZoom = (multiplier: number) => {
    setZoom((z) => Math.min(Math.max(z * multiplier, 0.4), 3));
  };

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center bg-sunken p-6">
        <div className="text-center">
          <p className="max-w-md text-sm text-red-500 dark:text-red-400 font-medium">{loadError}</p>
          <button
            type="button"
            className="btn btn-secondary btn-sm mt-3"
            onClick={() => {
              setLoadError(null);
              setIsLoading(true);
            }}
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-sunken">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-panel px-3 py-2 text-sm text-ink-soft shadow-xs">
        {/* Page Navigation */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onPageChange(1)}
            disabled={pageNumber <= 1}
            className="btn btn-secondary btn-sm p-1.5"
            aria-label="First page"
            title="First page"
          >
            <ChevronsLeft className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onPageChange(Math.max(1, pageNumber - 1))}
            disabled={pageNumber <= 1}
            className="btn btn-secondary btn-sm p-1.5"
            aria-label="Previous page (Left Arrow)"
            title="Previous page (Left Arrow)"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-xs px-2 text-ink font-semibold whitespace-nowrap">
            Page {pageNumber} / {isLoading ? "…" : effectiveTotalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(Math.min(effectiveTotalPages, pageNumber + 1))}
            disabled={pageNumber >= effectiveTotalPages}
            className="btn btn-secondary btn-sm p-1.5"
            aria-label="Next page (Right Arrow)"
            title="Next page (Right Arrow)"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onPageChange(effectiveTotalPages)}
            disabled={pageNumber >= effectiveTotalPages}
            className="btn btn-secondary btn-sm p-1.5"
            aria-label="Last page"
            title="Last page"
          >
            <ChevronsRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="btn btn-secondary btn-sm p-1.5"
            onClick={() => changeZoom(1 / 1.2)}
            aria-label="Zoom out"
            title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-xs text-ink-soft w-12 text-center select-none font-semibold">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm p-1.5"
            onClick={() => changeZoom(1.2)}
            aria-label="Zoom in"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm p-1.5"
            onClick={() => setZoom(1)}
            aria-label="Reset zoom (100%)"
            title="Reset zoom (100%)"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Canvas Scroll Area */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center bg-sunken">
          <div className="text-center text-muted">
            <div className="loading-spinner mx-auto mb-2" />
            <p className="text-xs font-mono">Rendering PDF page canvas…</p>
          </div>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-auto bg-sunken p-4 sm:p-6"
          data-testid="pdf-scroll-area"
        >
          <div className="flex min-h-full items-start justify-center">
            <div
              className="relative shadow-2xl rounded-sm bg-white transition-transform origin-top"
              style={{
                width: `${pageSize.width}px`,
                height: `${pageSize.height}px`,
              }}
            >
              <canvas
                ref={canvasRef}
                className="block w-full h-full rounded-sm"
                data-testid="pdf-canvas"
              />

              {/* Coordinate Highlight Overlay directly aligned to canvas dimensions */}
              <HighlightOverlay
                highlights={effectiveHighlights}
                pageIndex={pageNumber - 1} // 0-indexed for bounding boxes
                onSelect={() => {
                  if (onJumpToFinding) onJumpToFinding({ page_number: pageNumber });
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
