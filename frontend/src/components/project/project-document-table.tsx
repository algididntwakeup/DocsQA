"use client";

import { AlertTriangle, ExternalLink, FileText, LoaderCircle, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import type { DocumentItem, UserRole } from "@/lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function shortId(id: string | null | undefined) {
  return id ? `${id.slice(0, 8)}...` : "Unassigned";
}

export function ProjectDocumentTable({
  documents,
  role,
  loading,
  onUpload,
  onFiltersChange,
}: {
  documents: DocumentItem[];
  role: UserRole;
  loading: boolean;
  onUpload: (file: File) => Promise<void>;
  onFiltersChange: (filters: { engineerId?: string; sortBy: "date_desc" | "date_asc"; hasBlockers?: boolean }) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [engineer, setEngineer] = useState("all");
  const [sort, setSort] = useState<"date_desc" | "date_asc">("date_desc");
  const [blockers, setBlockers] = useState("all");
  const engineers = useMemo(() => Array.from(new Set(documents.map((item) => item.owner_id).filter((id): id is string => Boolean(id)))), [documents]);
  const visible = useMemo(() => documents, [documents]);

  async function chooseFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    try { await onUpload(file); } finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  function changeFilters(nextEngineer: string, nextSort: "date_desc" | "date_asc", nextBlockers: string) {
    onFiltersChange({
      engineerId: nextEngineer === "all" ? undefined : nextEngineer,
      sortBy: nextSort,
      hasBlockers: nextBlockers === "all" ? undefined : nextBlockers === "yes",
    });
  }

  return <section className="panel overflow-hidden">
    <div className="panel-heading flex-wrap"><div><p className="eyebrow">Document register</p><h2>{documents.length} controlled documents</h2></div><div><input ref={inputRef} className="sr-only" type="file" accept="application/pdf,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => void chooseFile(event.target.files?.[0])} /><button className="button button-primary" type="button" disabled={uploading} onClick={() => inputRef.current?.click()}><UploadCloud size={15} />{uploading ? "Uploading..." : "Upload new document"}</button></div></div>
     {role === "LEAD_ENGINEER" && <div className="flex flex-wrap items-center gap-3 border-b border-line bg-sunken p-3 text-xs"><label className="flex items-center gap-2 text-muted">Engineer<select className="filter-select" value={engineer} onChange={(event) => { setEngineer(event.target.value); changeFilters(event.target.value, sort, blockers); }}><option value="all">All engineers</option>{engineers.map((id) => <option key={id} value={id}>{shortId(id)}</option>)}</select></label><label className="flex items-center gap-2 text-muted">Sort<select className="filter-select" value={sort} onChange={(event) => { const value = event.target.value as typeof sort; setSort(value); changeFilters(engineer, value, blockers); }}><option value="date_desc">Newest first</option><option value="date_asc">Oldest first</option></select></label><label className="flex items-center gap-2 text-muted">Blockers<select className="filter-select" value={blockers} onChange={(event) => { setBlockers(event.target.value); changeFilters(engineer, sort, event.target.value); }}><option value="all">All documents</option><option value="yes">Has blockers</option><option value="no">No blockers</option></select></label></div>}
     {loading ? <div className="loading-state"><LoaderCircle className="mx-auto animate-spin" size={20} />Loading documents...</div> : visible.length === 0 ? <div className="empty-state"><FileText className="mx-auto text-primary" size={30} /><h2>No documents match</h2><p>Upload a document or adjust the register filters.</p></div> : <div className="table-scroll"><table><thead><tr><th>Document</th><th>Uploaded</th>{role === "LEAD_ENGINEER" && <th>Uploaded by</th>}<th>Workflow</th><th>Action</th></tr></thead><tbody>{visible.map((document) => { const workflow = document.workflow_status ?? "ANALYZING"; return <tr key={document.id}><td><div className="document-link"><FileText size={16} /><span><strong title={document.filename}>{document.filename}</strong><small>{document.status} · {document.progress_pct}% processed</small></span></div></td><td className="whitespace-nowrap">{formatDate(document.created_at)}</td>{role === "LEAD_ENGINEER" && <td className="font-mono text-[10px]">{shortId(document.owner_id)}</td>}<td><span className={`status-badge ${workflow === "VERIFIED_BY_LEAD" ? "status-success" : workflow === "REVIEWED_BY_ENGINEER" ? "status-active" : "status-warning"}`}><i />{workflow.replaceAll("_", " ")}</span></td><td><Link className="button button-secondary btn-sm" href={`/documents/${document.id}/review`}>Open review <ExternalLink size={13} /></Link></td></tr>; })}</tbody></table></div>}
    {role === "LEAD_ENGINEER" && blockers !== "all" && <p className="flex items-center gap-2 border-t border-line px-4 py-3 text-xs text-muted"><AlertTriangle size={14} className="text-warning" />Blocker filtering is applied server-side when the project register is loaded.</p>}
  </section>;
}
