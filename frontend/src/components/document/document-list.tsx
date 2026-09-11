"use client";

import { useState } from "react";
import { FileText, Loader2, Plus, RotateCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { deleteDocument, type DocumentItem } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function DocumentList({ documents, onRefresh }: { documents: DocumentItem[]; onRefresh: () => void }) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async (id: string, filename: string) => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${filename}"?\n\nThis will permanently delete the document, all findings, inspection metrics, and audit records.`
      )
    ) {
      return;
    }
    setDeletingId(id);
    setDeleteError(null);
    try {
      await deleteDocument(id);
      onRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete document.";
      setDeleteError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  if (documents.length === 0) {
    return (
      <section className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-xs">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600 mb-3">
          <FileText size={24} />
        </div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Inspection register</p>
        <h2 className="mt-1 text-base font-bold text-slate-900">No documents yet</h2>
        <p className="mt-1 text-xs text-slate-500 max-w-sm">Upload a native-text PDF or DOCX to begin the extraction lifecycle.</p>
        <Link
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-blue-700"
          href="/upload"
        >
          <Plus size={16} />
          New inspection
        </Link>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs" aria-labelledby="register-heading">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-white">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Inspection register</p>
          <h2 id="register-heading" className="text-base font-bold text-slate-900">Recent documents</h2>
        </div>
        <button
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition shadow-2xs"
          type="button"
          onClick={onRefresh}
          aria-label="Refresh documents"
        >
          <RotateCw size={14} />
        </button>
      </div>

      {deleteError && (
        <div className="flex items-center justify-between border-b border-rose-200 bg-rose-50 px-6 py-3 text-xs text-rose-800" role="alert">
          <span><strong>Delete Failed:</strong> {deleteError}</span>
          <button type="button" onClick={() => setDeleteError(null)} className="font-bold underline hover:text-rose-950">Dismiss</button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-bold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-6 py-3.5">Document</th>
              <th className="px-6 py-3.5">Status</th>
              <th className="px-6 py-3.5">Progress</th>
              <th className="px-6 py-3.5">Pages</th>
              <th className="px-6 py-3.5">Uploaded</th>
              <th className="px-6 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {documents.map((document) => (
              <tr key={document.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="px-6 py-4">
                  <Link className="inline-flex items-center gap-3 group" href={`/documents/${document.id}`}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-500/10 group-hover:bg-blue-100 transition">
                      <FileText size={18} />
                    </div>
                    <div>
                      <strong className="block text-xs font-bold text-slate-900 group-hover:text-blue-600 transition truncate max-w-sm">
                        {document.filename}
                      </strong>
                      <span className="block text-[11px] text-slate-500">
                        {formatBytes(document.size_bytes)} · {document.media_type.includes("pdf") ? "PDF" : "DOCX"}
                      </span>
                    </div>
                  </Link>
                </td>
                <td className="px-6 py-4">
                  <div className="inline-flex items-center gap-2">
                    <StatusBadge status={document.status} />
                    {(document.status === "QUEUED" || document.status === "PROCESSING") && (
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2 min-w-[120px]">
                    <div className="w-20 bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${document.progress_pct}%` }} />
                    </div>
                    <span className="font-mono text-xs font-semibold text-slate-700">{document.progress_pct}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 font-mono text-xs text-slate-600">{document.page_count ?? "—"}</td>
                <td className="px-6 py-4 whitespace-nowrap text-slate-500"><time dateTime={document.created_at}>{formatDate(document.created_at)}</time></td>
                <td className="px-6 py-4 text-right">
                  <button
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 transition shadow-2xs disabled:opacity-50"
                    type="button"
                    onClick={() => void handleDelete(document.id, document.filename)}
                    disabled={deletingId === document.id}
                    aria-label={`Delete ${document.filename}`}
                    title="Delete document"
                  >
                    {deletingId === document.id ? (
                      <Loader2 size={14} className="animate-spin text-rose-600" />
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
