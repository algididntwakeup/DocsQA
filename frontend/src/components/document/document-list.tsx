"use client";

import { FileText, Loader2, Plus, RotateCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { deleteDocument, type DocumentItem } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";

const workflowStyles: Record<string, string> = {
  ANALYZING: "bg-blue-50 text-blue-700 ring-blue-600/10",
  REVIEWED_BY_ENGINEER: "bg-amber-50 text-amber-700 ring-amber-600/10",
  VERIFIED_BY_LEAD: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
};

function workflowLabel(status?: string) {
  return status === "REVIEWED_BY_ENGINEER" ? "Reviewed" : status === "VERIFIED_BY_LEAD" ? "Verified" : "Analyzing";
}

export function DocumentList({ documents, onRefresh }: { documents: DocumentItem[]; onRefresh: () => void }) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  async function handleDelete(document: DocumentItem) {
    if (!window.confirm(`Hapus "${document.filename}" secara permanen?`)) return;
    setDeletingId(document.id);
    try { await deleteDocument(document.id); onRefresh(); } finally { setDeletingId(null); }
  }

  if (!documents.length) return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-sm"><FileText className="mx-auto text-blue-600" size={28} /><h2 className="mt-3 text-base font-bold text-slate-900">No documents yet</h2><p className="mt-1 text-xs text-slate-500">Upload dokumen teknis untuk memulai inspection lifecycle.</p><Link href="/upload" className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold !text-white hover:bg-blue-700"><Plus size={16} /> Dokumen Baru</Link></section>;

  return <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="register-heading">
    <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Inspection register</p><h2 id="register-heading" className="mt-1 text-base font-bold text-slate-900">Document control log</h2></div><button type="button" onClick={onRefresh} aria-label="Refresh documents" className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"><RotateCw size={14} /></button></div>
    <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-xs"><thead className="border-b border-slate-200 bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500"><tr><th className="px-5 py-3">Dokumen</th><th className="px-5 py-3">Proyek & Plant</th><th className="px-5 py-3">Uploaded By</th><th className="px-5 py-3">Assigned PIC</th><th className="px-5 py-3">Workflow Status</th><th className="px-5 py-3 text-right">Aksi</th></tr></thead><tbody className="divide-y divide-slate-100">{documents.map((document) => <tr key={document.id} className="transition-colors hover:bg-slate-50/70"><td className="px-5 py-4"><Link href={`/documents/${document.id}`} className="group flex items-start gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600"><FileText size={17} /></span><span><strong className="block max-w-[260px] truncate font-bold text-slate-900 group-hover:text-blue-600">{document.filename}</strong><span className="mt-1 block text-[11px] text-slate-500">{document.media_type.includes("pdf") ? "PDF" : "DOCX"} · {formatBytes(document.size_bytes)} · {formatDate(document.created_at)}</span></span></Link></td><td className="px-5 py-4"><Link href={document.project_id ? `/projects/${document.project_id}` : "#"} className="font-semibold text-slate-800 hover:text-blue-600">{document.project_name ?? "Unassigned project"}</Link><span className="mt-1 block text-[11px] text-slate-500">{document.project_plant ?? "Plant area not set"}</span></td><td className="px-5 py-4 text-slate-700">{document.uploaded_by_name ?? document.owner_name ?? "Unknown"}</td><td className="px-5 py-4">{document.assigned_to_name ? <span className="font-medium text-slate-700">{document.assigned_to_name}</span> : <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-500">Belum di-assign</span>}</td><td className="px-5 py-4"><span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold ring-1 ${workflowStyles[document.workflow_status ?? "ANALYZING"] ?? workflowStyles.ANALYZING}`}>{workflowLabel(document.workflow_status)}</span></td><td className="px-5 py-4 text-right"><div className="flex justify-end gap-2"><Link href={`/documents/${document.id}/review`} className="rounded-lg bg-blue-600 px-3 py-2 text-[10px] font-bold !text-white hover:bg-blue-700">Buka Review</Link><button type="button" onClick={() => void handleDelete(document)} disabled={deletingId === document.id} aria-label={`Delete ${document.filename}`} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50">{deletingId === document.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}</button></div></td></tr>)}</tbody></table></div>
  </section>;
}
