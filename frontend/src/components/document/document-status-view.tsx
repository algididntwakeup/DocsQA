"use client";

import { AlertTriangle, ArrowLeft, FileText, RotateCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  deleteDocument,
  getDocument,
  getDocumentStatus,
  subscribeDocumentEvents,
  type DocumentItem,
  type DocumentStatus,
} from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { ScanProgress } from "./scan-progress";
import { StatusBadge } from "./status-badge";

const TERMINAL = new Set(["COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"]);

export function DocumentStatusView({ id }: { id: string }) {
  const router = useRouter();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [scan, setScan] = useState<DocumentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const retryRef = useRef(1000);

  const handleDelete = async () => {
    if (!document) return;
    if (
      !window.confirm(
        `Are you sure you want to delete "${document.filename}"?\n\nThis will permanently delete the document, all findings, inspection metrics, and audit records.`
      )
    ) {
      return;
    }
    setIsDeleting(true);
    try {
      await deleteDocument(id);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete document.");
      setIsDeleting(false);
    }
  };

  const load = useCallback(async () => {
    try {
      const [nextDocument, nextScan] = await Promise.all([getDocument(id), getDocumentStatus(id)]);
      setError(null);
      setDocument(nextDocument);
      setScan(nextScan);
      retryRef.current = 1000;
      return nextScan;
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load document status.");
      retryRef.current = Math.min(Math.round(retryRef.current * 1.7), 8000);
      return null;
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    let unsubscribe: (() => void) | undefined;

    const startPolling = () => {
      if (!active) return;
      const poll = async () => {
        const next = await load();
        if (!active || (next && TERMINAL.has(next.status))) return;
        timer = window.setTimeout(() => void poll(), retryRef.current);
      };
      void poll();
    };

    const run = async () => {
      const initial = await load();
      if (!active || (initial && TERMINAL.has(initial.status))) return;

      if (typeof window !== "undefined" && "EventSource" in window) {
        try {
          unsubscribe = subscribeDocumentEvents(
            id,
            (event) => {
              if (!active) return;
              setScan((prev) =>
                prev
                  ? {
                      ...prev,
                      status: event.status as DocumentStatus["status"],
                      progress_pct: event.progress_pct,
                    }
                  : null
              );
              if (TERMINAL.has(event.status)) {
                void load();
              }
            },
            () => {
              if (active) void load();
            },
            () => {
              if (active && !timer) {
                startPolling();
              }
            }
          );
          return;
        } catch {
          // Fall through to polling
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
  }, [id, load]);

  return (
    <>
      <Link className="back-link" href="/"><ArrowLeft size={15} />Inspection register</Link>
      {error && <div className="alert alert-error" role="alert"><AlertTriangle /><span><strong>Status unavailable</strong>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}
      {!document || !scan ? <div className="panel loading-state" role="status">Reading pipeline telemetry…</div> : <>
        <div className="document-hero">
          <div className="document-icon"><FileText /></div>
          <div>
            <p className="eyebrow">Document inspection</p>
            <h1>{document.filename}</h1>
            <p>{formatBytes(document.size_bytes)} · Uploaded {formatDate(document.created_at)} · {document.page_count ? `${document.page_count} pages` : "Page count pending"}</p>
          </div>
          <div className="hero-status">
            <StatusBadge status={scan.status} />
            <button className="icon-button" type="button" onClick={() => void load()} aria-label="Refresh status" title="Refresh status">
              <RotateCw size={16} />
            </button>
            <button
              className="icon-button delete-action-btn"
              type="button"
              onClick={() => void handleDelete()}
              disabled={isDeleting}
              aria-label="Delete document"
              title="Delete document"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
        <ScanProgress scan={scan} />
        {TERMINAL.has(scan.status) && (
          <section className="panel next-step">
            <div>
              <p className="eyebrow">Quality Inspection</p>
              <h2>{scan.status === "FAILED" ? "Document needs attention" : "Quality Inspection Complete"}</h2>
              <p>
                {scan.status === "FAILED"
                  ? "Review the stage error above before retrying the source document."
                  : "Review findings, inspect coordinate overlays on the canonical PDF, and perform QA triage and lead sign-off."}
              </p>
            </div>
            {scan.status !== "FAILED" && (
              <div className="next-step-actions">
                <Link className="primary-action-button" href={`/documents/${id}/review`}>
                  Open Review Workspace
                </Link>
              </div>
            )}
          </section>
        )}
      </>}
    </>
  );
}
