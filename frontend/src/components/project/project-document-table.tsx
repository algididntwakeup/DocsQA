"use client";

import { AlertTriangle, ArrowUpDown, ExternalLink, FileText, LoaderCircle, Search, UploadCloud, UserRound } from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { ApiError, assignDocument, claimDocument, type DocumentItem, type ManagedUser, type UserRole } from "@/lib/api";

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
  currentUserId,
  engineers: availableEngineers,
  onChanged,
}: {
  documents: DocumentItem[];
  role: UserRole;
  loading: boolean;
  onUpload: (file: File) => Promise<void>;
  onFiltersChange: (filters: { engineerId?: string; sortBy: "date_desc" | "date_asc"; hasBlockers?: boolean }) => void;
  currentUserId?: string;
  engineers?: ManagedUser[];
  onChanged?: () => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [engineer, setEngineer] = useState("all");
  const [sort, setSort] = useState<"date_desc" | "date_asc">("date_desc");
  const [blockers, setBlockers] = useState("all");
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [overrideRequest, setOverrideRequest] = useState<{ documentId: string; engineerId: string; message: string } | null>(null);
  const ownerEngineerIds = useMemo(() => Array.from(new Set(documents.map((item) => item.owner_id).filter((id): id is string => Boolean(id)))), [documents]);
  const visible = useMemo(() => documents.filter((item) => item.filename.toLowerCase().includes(search.toLowerCase())), [documents, search]);

  async function chooseFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    try { await onUpload(file); } finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  async function claim(documentId: string) {
    setBusyId(documentId);
    try { await claimDocument(documentId); await onChanged?.(); }
    catch (caught) { window.alert(caught instanceof ApiError ? caught.message : "Could not claim document."); }
    finally { setBusyId(null); }
  }

  async function assign(documentId: string, engineerId: string, override = false) {
    setBusyId(documentId);
    try { await assignDocument(documentId, engineerId, override); setOverrideRequest(null); await onChanged?.(); }
    catch (caught) {
      if (!override && caught instanceof ApiError && caught.status === 400) setOverrideRequest({ documentId, engineerId, message: caught.message });
      else window.alert(caught instanceof ApiError ? caught.message : "Could not assign document.");
    } finally { setBusyId(null); }
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
       {role === "LEAD_ENGINEER" || role === "SUPERUSER" ? <div className="rq-controls"><label className="rq-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search document or unit code..." /></label><label><span>Engineer</span><select value={engineer} onChange={(event) => { setEngineer(event.target.value); changeFilters(event.target.value, sort, blockers); }}><option value="all">All engineers</option>{ownerEngineerIds.map((id) => <option key={id} value={id}>{shortId(id)}</option>)}</select></label><label className="rq-toggle"><input type="checkbox" checked={blockers === "yes"} onChange={(event) => { const value = event.target.checked ? "yes" : "all"; setBlockers(value); changeFilters(engineer, sort, value); }} /><span>Only blockers</span></label><label className="sr-only">Blockers<select aria-label="Blockers" value={blockers} onChange={(event) => { setBlockers(event.target.value); changeFilters(engineer, sort, event.target.value); }}><option value="all">All documents</option><option value="yes">Has blockers</option></select></label><label><span><ArrowUpDown size={13} />Uploaded</span><select value={sort} onChange={(event) => { const value = event.target.value as typeof sort; setSort(value); changeFilters(engineer, value, blockers); }}><option value="date_desc">Newest first</option><option value="date_asc">Oldest first</option></select></label></div> : null}
       {loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={22} />Loading documents...</div> : visible.length === 0 ? <div className="rq-empty"><FileText size={30} /><h2>No documents match</h2><p>Upload a document or adjust the register filters.</p></div> : <div className="rq-table-scroll"><table className="rq-data-table"><thead><tr><th>Document & code</th><th>Sub-discipline / type</th>{(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <th>Uploaded by</th>}<th>Assigned PIC</th><th>Workflow status</th><th>Findings</th><th /></tr></thead><tbody>{visible.map((document) => { const workflow = document.workflow_status ?? "ANALYZING"; const hasActiveTask = documents.some((item) => item.assigned_to_id === currentUserId && item.workflow_status === "ANALYZING"); return <tr key={document.id}><td><div className="rq-doc-cell"><span className="rq-doc-icon"><FileText size={17} /></span><span><strong title={document.filename}>{document.filename}</strong><small>{shortId(document.id)} · {formatDate(document.created_at)}</small></span></div></td><td><span className="rq-type-badge">{document.media_type.includes("pdf") ? "PDF" : "DOCX"}</span></td>{(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <td className="rq-muted-cell">{shortId(document.owner_id)}</td>}<td>{role === "LEAD_ENGINEER" || role === "SUPERUSER" ? <select aria-label={`Assign ${document.filename}`} value={document.assigned_to_id ?? ""} disabled={busyId === document.id} onChange={(event) => { if (event.target.value) void assign(document.id, event.target.value); }}><option value="">Unassigned</option>{(availableEngineers ?? []).map((engineerOption) => <option key={engineerOption.id} value={engineerOption.id}>{engineerOption.full_name}</option>)}</select> : document.assigned_to_id ? <span className="flex items-center gap-2 text-xs"><span className="rq-avatar">{(document.assigned_to_name ?? "?").split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</span>{document.assigned_to_name ?? "Assigned"}</span> : <span className="flex items-center gap-2"><span className="rq-type-badge">Unassigned</span><button className="rq-secondary-button" type="button" disabled={hasActiveTask || busyId === document.id} title={hasActiveTask ? "Selesaikan tugas aktifmu terlebih dahulu" : "Claim document"} onClick={() => void claim(document.id)}><UserRound size={13} />{busyId === document.id ? "Claiming..." : "Ambil Tugas / Claim"}</button></span>}</td><td><span className={`rq-workflow rq-workflow-${workflow.toLowerCase()}`}><i />{workflow.replaceAll("_", " ")}</span></td><td><span className="rq-finding-badge rq-finding-blocker">Blocker 0</span><span className="rq-finding-badge rq-finding-major">Major 0</span></td><td><Link className="rq-review-link" href={`/documents/${document.id}/review`}>Open review <ExternalLink size={14} /></Link></td></tr>; })}</tbody></table></div>}
     {role === "LEAD_ENGINEER" && blockers !== "all" && <p className="flex items-center gap-2 border-t border-line px-4 py-3 text-xs text-muted"><AlertTriangle size={14} className="text-warning" />Blocker filtering is applied server-side when the project register is loaded.</p>}
     {overrideRequest && <div className="rq-modal-backdrop" role="dialog" aria-modal="true"><div className="rq-modal"><div className="rq-modal-header"><div><p className="rq-kicker">WIP override</p><h2>Engineer has an active task</h2><p className="rq-modal-subtitle">{overrideRequest.message}</p></div><button type="button" aria-label="Close" onClick={() => setOverrideRequest(null)}>×</button></div><div className="flex justify-end gap-2"><button className="rq-secondary-button" type="button" onClick={() => setOverrideRequest(null)}>Cancel</button><button className="rq-primary-button" type="button" onClick={() => void assign(overrideRequest.documentId, overrideRequest.engineerId, true)}>Confirm emergency assignment</button></div></div></div>}
    </section>;
}

