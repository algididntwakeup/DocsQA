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
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 border-b border-slate-200 pb-6">
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Material document control</p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Inspection workspace</h1>
          <p className="text-sm text-slate-600 max-w-2xl">Monitor ingestion and extraction readiness across active QA documents.</p>
        </div>
        <Link
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-blue-700 active:scale-[0.98] self-start sm:self-auto shrink-0"
          href="/upload"
        >
          <Plus size={16} />
          New inspection
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" aria-label="Document summary">
        <article className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-500/10">
            <Activity size={20} />
          </div>
          <div>
            <small className="block text-xs font-medium text-slate-500">Total documents</small>
            <strong className="text-xl font-bold text-slate-900">{documents.length}</strong>
          </div>
        </article>

        <article className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600 ring-1 ring-amber-500/10">
            <Clock3 size={20} />
          </div>
          <div>
            <small className="block text-xs font-medium text-slate-500">In processing</small>
            <strong className="text-xl font-bold text-slate-900">{metrics.active}</strong>
          </div>
        </article>

        <article className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-500/10">
            <CheckCircle2 size={20} />
          </div>
          <div>
            <small className="block text-xs font-medium text-slate-500">Extracted</small>
            <strong className="text-xl font-bold text-slate-900">{metrics.completed}</strong>
          </div>
        </article>

        <article className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600 ring-1 ring-rose-500/10">
            <AlertTriangle size={20} />
          </div>
          <div>
            <small className="block text-xs font-medium text-slate-500">Needs attention</small>
            <strong className="text-xl font-bold text-slate-900">{metrics.failed}</strong>
          </div>
        </article>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800" role="alert">
          <AlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span className="flex-1"><strong className="font-semibold">API unavailable: </strong>{error}</span>
          <button type="button" onClick={() => void load()} className="font-bold underline hover:text-rose-950">Retry</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white p-12 text-sm text-slate-500 shadow-xs" role="status">
          Loading inspection register…
        </div>
      ) : (
        <>
          {metrics.active > 0 && (
            <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50/70 px-4 py-3 text-xs text-blue-900 shadow-2xs" role="status" aria-live="polite">
              <Radio size={16} className="text-blue-600 animate-pulse shrink-0" />
              <div className="flex-1">
                <strong className="font-semibold">Live monitoring active: </strong> Processing progress may take a while. You can keep this page open and leave to the other tab while waiting.
              </div>
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-600"></span>
              </span>
            </div>
          )}
          <DocumentList documents={documents} onRefresh={() => void load()} />
        </>
      )}
    </div>
  );
}
