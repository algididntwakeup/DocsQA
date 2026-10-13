"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, ExternalLink, LoaderCircle, RotateCw } from "lucide-react";
import Link from "next/link";
import {
  ApiError,
  getDocument,
  getDocumentStatus,
  subscribeDocumentEvents,
  type DocumentItem,
  type DocumentStatus,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { ScanProgress } from "@/components/document/scan-progress";
import { StatusBadge } from "@/components/document/status-badge";

const TERMINAL = new Set(["COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"]);

interface ProcessingStageProps {
  documentId: string;
  filename: string;
  projectName: string | null;
  onStartOver: () => void;
}

/**
 * In-place pipeline telemetry for the unified upload flow.
 *
 * Reuses the same SSE-with-polling fallback as the standalone status route, so
 * the live stage feed behaves identically; only the chrome differs. Rendered
 * inside the flow's AnimatePresence wrapper, so it morphs in without a route
 * change.
 */
export function ProcessingStage({
  documentId,
  filename,
  projectName,
  onStartOver,
}: ProcessingStageProps) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [scan, setScan] = useState<DocumentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const retryRef = useRef(1000);

  const load = useCallback(async () => {
    try {
      const [nextDocument, nextScan] = await Promise.all([
        getDocument(documentId),
        getDocumentStatus(documentId),
      ]);
      setDocument(nextDocument);
      setScan(nextScan);
      setError(null);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not load document status.",
      );
    }
  }, [documentId]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    let unsubscribe: (() => void) | undefined;

    // Kick the first fetch off the synchronous effect path: setState called
    // directly in an effect body triggers cascading renders.
    void Promise.resolve().then(() => {
      if (active) void load();
    });

    const startPolling = () => {
      const poll = async () => {
        if (!active) return;
        await load();
        retryRef.current = Math.min(retryRef.current * 1.5, 8000);
        timer = window.setTimeout(poll, retryRef.current);
      };
      timer = window.setTimeout(poll, retryRef.current);
    };

    const run = async () => {
      if (typeof window !== "undefined" && "EventSource" in window) {
        try {
          unsubscribe = subscribeDocumentEvents(documentId, (event) => {
            if (!active) return;
            setScan((previous) => {
              if (!previous) return previous;
              return {
                ...previous,
                status: event.status as DocumentStatus["status"],
                progress_pct: event.progress_pct,
                stages: event.stages.map((update) => {
                  const existing = previous.stages.find(
                    (stage) => stage.name === update.name,
                  );
                  return {
                    ...(existing ?? {}),
                    name: update.name as DocumentStatus["stages"][number]["name"],
                    status: update.status as DocumentStatus["stages"][number]["status"],
                    progress_pct: update.progress_pct ?? existing?.progress_pct ?? 0,
                  } as DocumentStatus["stages"][number];
                }),
                updated_at: new Date().toISOString(),
              };
            });
            if (TERMINAL.has(event.status)) void load();
          });
          return;
        } catch {
          // Fall through to polling.
        }
      }
      startPolling();
    };

    void run();

    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
      if (unsubscribe) unsubscribe();
    };
  }, [documentId, load]);

  const isComplete = scan !== null && TERMINAL.has(scan.status);
  const isFailed = scan?.status === "FAILED";

  return (
    <div className="flex flex-col gap-6">
      <Card className="p-6 sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-accent-foreground">
              Step 03 · Pipeline telemetry
            </p>
            <h2 className="mt-1 truncate text-lg font-bold text-foreground" title={filename}>
              {filename}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {projectName ? `Filed under ${projectName}` : "Processing started"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {scan && <StatusBadge status={scan.status} />}
            <button
              type="button"
              onClick={() => void load()}
              aria-label="Refresh status"
              className="inline-flex size-8 items-center justify-center rounded-lg border border-border text-muted-foreground transition hover:bg-muted/60"
            >
              <RotateCw size={15} />
            </button>
          </div>
        </div>
      </Card>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!scan ? (
        <Card className="flex items-center justify-center gap-3 p-12 text-sm text-muted-foreground">
          <LoaderCircle size={17} className="animate-spin" />
          Reading pipeline telemetry...
        </Card>
      ) : (
        <ScanProgress scan={scan} />
      )}

      {isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Card className="flex flex-col items-start gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div className="flex items-start gap-4">
              <span
                className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${
                  isFailed ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"
                }`}
              >
                {isFailed ? <AlertTriangle size={21} /> : <CheckCircle2 size={21} />}
              </span>
              <div>
                <h3 className="text-base font-bold text-foreground">
                  {isFailed ? "Document needs attention" : "Quality inspection complete"}
                </h3>
                <p className="mt-1 max-w-lg text-sm leading-relaxed text-muted-foreground">
                  {isFailed
                    ? "Review the stage error above, then retry the source document."
                    : "Review findings, inspect coordinate overlays on the canonical PDF, and perform QA triage."}
                </p>
              </div>
            </div>

            <div className="flex shrink-0 flex-col items-stretch gap-3 sm:items-end">
              {!isFailed && (
                <Link
                  href={`/documents/${documentId}/review`}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90"
                >
                  <ExternalLink size={16} />
                  Open Review Workspace
                </Link>
              )}
              <button
                type="button"
                onClick={onStartOver}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:bg-muted/60"
              >
                Upload another document
              </button>
            </div>
          </Card>
        </motion.div>
      )}

      {!isComplete && document && (
        <p className="text-center text-xs text-muted-foreground">
          This page updates automatically. You can leave it open while the pipeline runs.
        </p>
      )}
    </div>
  );
}
