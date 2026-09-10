"use client";

import { AlertTriangle, ArrowUpDown, ExternalLink, FileText, LoaderCircle, Search, UploadCloud } from "lucide-react";
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
  const [search, setSearch] = useState("");
  const engineers = useMemo(() => Array.from(new Set(documents.map((item) => item.owner_id).filter((id): id is string => Boolean(id)))), [documents]);
  const visible = useMemo(() => documents.filter((item) => item.filename.toLowerCase().includes(search.toLowerCase())), [documents, search]);

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

  return <section className="rq-table-card">
     <div className="rq-table-heading"><div><p className="rq-kicker">Document inspection data table</p><h2>{documents.length} controlled documents</h2></div><div><input ref={inputRef} className="sr-only" type="file" accept="application/pdf,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => void chooseFile(event.target.files?.[0])} /><button className="rq-primary-button" type="button" disabled={uploading} onClick={() => inputRef.current?.click()}><UploadCloud size={16} />{uploading ? "Uploading..." : "Upload document"}</button></div></div>
      {role === "LEAD_ENGINEER" || role === "SUPERUSER" ? <div className="rq-controls"><label className="rq-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search document or unit code..." /></label><label><span>Engineer</span><select value={engineer} onChange={(event) => { setEngineer(event.target.value); changeFilters(event.target.value, sort, blockers); }}><option value="all">All engineers</option>{engineers.map((id) => <option key={id} value={id}>{shortId(id)}</option>)}</select></label><label className="rq-toggle"><input type="checkbox" checked={blockers === "yes"} onChange={(event) => { const value = event.target.checked ? "yes" : "all"; setBlockers(value); changeFilters(engineer, sort, value); }} /><span>Only blockers</span></label><label className="sr-only">Blockers<select aria-label="Blockers" value={blockers} onChange={(event) => { setBlockers(event.target.value); changeFilters(engineer, sort, event.target.value); }}><option value="all">All documents</option><option value="yes">Has blockers</option></select></label><label><span><ArrowUpDown size={13} />Uploaded</span><select value={sort} onChange={(event) => { const value = event.target.value as typeof sort; setSort(value); changeFilters(engineer, value, blockers); }}><option value="date_desc">Newest first</option><option value="date_asc">Oldest first</option></select></label></div> : null}
      {loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={22} />Loading documents...</div> : visible.length === 0 ? <div className="rq-empty"><FileText size={30} /><h2>No documents match</h2><p>Upload a document or adjust the register filters.</p></div> : <div className="rq-table-scroll"><table className="rq-data-table"><thead><tr><th>Document & code</th><th>Sub-discipline / type</th>{(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <th>Uploaded by</th>}<th>Workflow status</th><th>Findings</th><th /></tr></thead><tbody>{visible.map((document) => { const workflow = document.workflow_status ?? "ANALYZING"; return <tr key={document.id}><td><div className="rq-doc-cell"><span className="rq-doc-icon"><FileText size={17} /></span><span><strong title={document.filename}>{document.filename}</strong><small>{shortId(document.id)} · {formatDate(document.created_at)}</small></span></div></td><td><span className="rq-type-badge">{document.media_type.includes("pdf") ? "PDF" : "DOCX"}</span></td>{(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <td className="rq-muted-cell">{shortId(document.owner_id)}</td>}<td><span className={`rq-workflow rq-workflow-${workflow.toLowerCase()}`}><i />{workflow.replaceAll("_", " ")}</span></td><td><span className="rq-finding-badge rq-finding-blocker">Blocker 0</span><span className="rq-finding-badge rq-finding-major">Major 0</span></td><td><Link className="rq-review-link" href={`/documents/${document.id}/review`}>Open review <ExternalLink size={14} /></Link></td></tr>; })}</tbody></table></div>}
    {role === "LEAD_ENGINEER" && blockers !== "all" && <p className="flex items-center gap-2 border-t border-line px-4 py-3 text-xs text-muted"><AlertTriangle size={14} className="text-warning" />Blocker filtering is applied server-side when the project register is loaded.</p>}
  </section>;
}
