"use client";

import { Activity, AlertTriangle, CheckCircle2, Clock3, Plus, Radio } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, listDocuments, subscribeDocumentEvents, type DocumentItem } from "@/lib/api";
import { DocumentList } from "./document-list";

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      setError(null);
      setDocuments((await listDocuments()).documents);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not reach the Document QC API.");
    } finally {
      setLoading(false);
    }
  }, []);
  const activeDocumentIds = useMemo(
    () => documents
      .filter((item) => item.status === "QUEUED" || item.status === "PROCESSING")
      .map((item) => item.id)
      .join(","),
    [documents]
  );
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (!documents.some((item) => item.status === "QUEUED" || item.status === "PROCESSING")) return;
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [documents, load]);
  useEffect(() => {
    if (!activeDocumentIds || typeof EventSource === "undefined") return;

    const unsubscribers = activeDocumentIds.split(",").map((documentId) =>
      subscribeDocumentEvents(
        documentId,
        (event) => {
          setDocuments((current) =>
            current.map((item) =>
              item.id === documentId
                ? {
                    ...item,
                    status: event.status as DocumentItem["status"],
                    progress_pct: event.progress_pct,
                    updated_at: new Date().toISOString(),
                  }
                : item
            )
          );
          if (event.status === "COMPLETED" || event.status === "COMPLETED_WITH_WARNINGS" || event.status === "FAILED") {
            void load();
          }
        },
        undefined,
        () => {
          // The existing polling loop remains the fallback when SSE is unavailable.
        }
      )
    );

    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [activeDocumentIds, load]);
  const metrics = useMemo(() => ({
    active: documents.filter((d) => d.status === "QUEUED" || d.status === "PROCESSING").length,
    completed: documents.filter((d) => d.status.startsWith("COMPLETED")).length,
    failed: documents.filter((d) => d.status === "FAILED").length,
  }), [documents]);
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">Material document control</p><h1>Inspection workspace</h1><p>Monitor ingestion and extraction readiness across active QA documents.</p></div>
        <Link className="button button-primary" href="/upload"><Plus size={16} />New inspection</Link>
      </div>
      <div className="metric-grid" aria-label="Document summary">
        <article><Activity /><span><small>Total documents</small><strong>{documents.length}</strong></span></article>
        <article><Clock3 /><span><small>In processing</small><strong>{metrics.active}</strong></span></article>
        <article><CheckCircle2 /><span><small>Extracted</small><strong>{metrics.completed}</strong></span></article>
        <article><AlertTriangle /><span><small>Needs attention</small><strong>{metrics.failed}</strong></span></article>
      </div>
      {error && <div className="alert alert-error" role="alert"><AlertTriangle /><span><strong>API unavailable</strong>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}
       {loading ? <div className="panel loading-state" role="status">Loading inspection register…</div> : <>
         {metrics.active > 0 && <div className="live-monitor" role="status" aria-live="polite"><Radio size={15} /><span><strong>Live monitoring active</strong> Processing progress may take a while. You can keep this page open and leave to the other tab while waiting.</span><span className="live-pulse" aria-hidden="true" /></div>}
         <DocumentList documents={documents} onRefresh={() => void load()} />
       </>}
    </>
  );
}
