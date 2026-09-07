"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Maximize2,
  Minimize2,
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

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 10.0; // 1000% zoom allows inspecting dense CAD & micro-tables

export function PdfCanvasViewer({
  documentId,
  currentPage,
  onPageChange,
  totalPages,
  highlights = [],
  activeIssue,
  onJumpToFinding,
}: PdfCanvasViewerProps) {
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [loaded, setLoaded] = useState<LoadedDoc | null>(null);
  const [pageCount, setPageCount] = useState<number>(totalPages ?? 1);
  const [zoom, setZoom] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [intrinsicSize, setIntrinsicSize] = useState<{ width: number; height: number }>({
    width: 612,
    height: 792,
  });
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Keep a ref to the latest zoom for native event handlers
  const zoomRef = useRef<number>(zoom);
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  // Sync fullscreen state
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  const toggleFullscreen = async () => {
    const el = viewerRef.current;
    if (!el) return;
    try {
      if (!document.fullscreenElement) {
        await el.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      // Ignore if fullscreen is not permitted by browser context
    }
  };

  // Keep the loading task so we can destroy it on unmount / id change.
  const loadingTaskRef = useRef<pdfjsLib.PDFDocumentLoadingTask | null>(null);

  // Resize observer measures scroll pane width without cascading re-renders
  useEffect(() => {
    const scroll = scrollRef.current;
    if (!scroll) return;
    const update = () => {
      const w = scroll.clientWidth;
      if (w > 0) {
        setContainerWidth((prev) => {
          // Ignore changes <= 24px (e.g. scrollbar appearing/disappearing) to prevent layout oscillation
          if (prev === 0 || Math.abs(prev - w) > 24) {
            return w;
          }
          return prev;
        });
      }
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(scroll);
    return () => observer.disconnect();
  }, []);

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

        try {
          const firstPage = await doc.getPage(1);
          const unscaled = firstPage.getViewport({ scale: 1 });
          setIntrinsicSize({ width: unscaled.width, height: unscaled.height });
        } catch {
          // fallback to initial 612 x 792 if first page unscaled viewport cannot be read
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

  const effectiveTotalPages = Math.max(totalPages ?? pageCount, 1);
  const pageNumber = Math.min(Math.max(1, currentPage), effectiveTotalPages);

  // Pure derived calculations for fit scale and rendered size
  const fitScale = useMemo(() => {
    const available = containerWidth > 48 ? containerWidth - 48 : 600;
    const base = intrinsicSize.width > 0 ? intrinsicSize.width : 612;
    return Math.max(available / base, 0.35);
  }, [containerWidth, intrinsicSize.width]);

  const renderScale = fitScale * zoom;

  const renderedSize = useMemo(() => {
    return {
      width: Math.floor((intrinsicSize.width || 612) * renderScale),
      height: Math.floor((intrinsicSize.height || 792) * renderScale),
    };
  }, [intrinsicSize, renderScale]);

  const renderTick = useRef(0);

  // Render the requested page onto the canvas.
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

        // Check if page intrinsic size differs (e.g. landscape vs portrait)
        const unscaled = page.getViewport({ scale: 1 });
        setIntrinsicSize((prev) => {
          if (
            Math.abs(prev.width - unscaled.width) < 1 &&
            Math.abs(prev.height - unscaled.height) < 1
          ) {
            return prev;
          }
          return { width: unscaled.width, height: unscaled.height };
        });

        const viewport = page.getViewport({ scale: renderScale });
        const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

        const cssWidth = Math.floor(viewport.width);
        const cssHeight = Math.floor(viewport.height);

        liveCanvas.width = Math.floor(viewport.width * dpr);
        liveCanvas.height = Math.floor(viewport.height * dpr);
        liveCanvas.style.width = `${cssWidth}px`;
        liveCanvas.style.height = `${cssHeight}px`;

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
  }, [loaded, pageNumber, renderScale, isLoading]);

  // Scroll to top only when the requested page actually changes
  const prevPageRef = useRef(pageNumber);
  useEffect(() => {
    if (prevPageRef.current !== pageNumber) {
      prevPageRef.current = pageNumber;
      scrollRef.current?.scrollTo({ top: 0, behavior: "instant" });
    }
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

  // Enable trackpad pinch-to-zoom and Ctrl+wheel zooming
  useEffect(() => {
    const scrollEl = scrollRef.current;
    if (!scrollEl) return;

    const handleWheel = (e: WheelEvent) => {
      // Trackpad pinch-to-zoom or mouse Ctrl+wheel
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();

        // Natural exponential scaling based on deltaY
        const delta = -e.deltaY;
        const factor = Math.exp(delta * 0.005);

        const currentZoom = zoomRef.current;
        const nextZoom = Math.min(Math.max(currentZoom * factor, MIN_ZOOM), MAX_ZOOM);
        const roundedZoom = Math.round(nextZoom * 100) / 100;

        if (roundedZoom !== currentZoom) {
          const rect = scrollEl.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;
          const scrollLeft = scrollEl.scrollLeft;
          const scrollTop = scrollEl.scrollTop;
          const ratio = roundedZoom / currentZoom;

          setZoom(roundedZoom);

          requestAnimationFrame(() => {
            if (scrollRef.current) {
              scrollRef.current.scrollLeft = (scrollLeft + mouseX) * ratio - mouseX;
              scrollRef.current.scrollTop = (scrollTop + mouseY) * ratio - mouseY;
            }
          });
        }
      }
    };

    const handleGesture = (e: Event) => {
      e.preventDefault();
    };

    scrollEl.addEventListener("wheel", handleWheel, { passive: false });
    scrollEl.addEventListener("gesturestart", handleGesture, { passive: false });
    scrollEl.addEventListener("gesturechange", handleGesture, { passive: false });

    return () => {
      scrollEl.removeEventListener("wheel", handleWheel);
      scrollEl.removeEventListener("gesturestart", handleGesture);
      scrollEl.removeEventListener("gesturechange", handleGesture);
    };
  }, []);

  const changeZoom = (multiplier: number) => {
    setZoom((z) => {
      const next = Math.min(Math.max(z * multiplier, MIN_ZOOM), MAX_ZOOM);
      return Math.round(next * 100) / 100;
    });
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
    <div ref={viewerRef} className="flex h-full min-h-0 flex-col bg-sunken">
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
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="font-mono text-xs text-ink-soft hover:text-primary w-14 text-center select-none font-semibold cursor-pointer rounded px-1 py-0.5 hover:bg-panel-raised transition-colors"
            title="Click to reset zoom to 100%"
            aria-label={`Current zoom ${Math.round(zoom * 100)}%, click to reset to 100%`}
          >
            {Math.round(zoom * 100)}%
          </button>
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
            className={`btn btn-secondary btn-sm p-1.5 transition-colors ${
              isFullscreen ? "bg-accent/20 text-accent border-accent/40" : ""
            }`}
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? "Exit fullscreen" : "Full screen"}
            title={isFullscreen ? "Exit fullscreen (Esc)" : "Full screen"}
            data-testid="pdf-fullscreen-btn"
          >
            {isFullscreen ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
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
          className="flex-1 overflow-auto bg-sunken p-4 sm:p-6 [scrollbar-gutter:stable]"
          data-testid="pdf-scroll-area"
        >
          <div className="flex min-h-full items-start justify-center">
            <div
              className="relative shadow-2xl rounded-sm bg-white"
              style={{
                width: `${renderedSize.width}px`,
                height: `${renderedSize.height}px`,
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
