"use client";

import { AlertTriangle, ArrowUpDown, ExternalLink, FileText, LoaderCircle, Search, UploadCloud, UserRound } from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
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
  const visible = useMemo(() => documents.filter((item) => item.filename.toLowerCase().includes(search.toLowerCase())), [documents, search]);

  async function chooseFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    try { await onUpload(file); } finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  async function claim(documentId: string) {
    setBusyId(documentId);
    try { await claimDocument(documentId); toast.success("Document claimed successfully."); await onChanged?.(); }
    catch (caught) { toast.error(caught instanceof ApiError ? caught.message : "Could not claim document."); }
    finally { setBusyId(null); }
  }

  async function assign(documentId: string, engineerId: string | null, override = false) {
    setBusyId(documentId);
    try { await assignDocument(documentId, engineerId, override); setOverrideRequest(null); toast.success("Document assignment updated."); await onChanged?.(); }
    catch (caught) {
      if (!override && engineerId && caught instanceof ApiError && caught.status === 400) setOverrideRequest({ documentId, engineerId, message: caught.message });
      else toast.error(caught instanceof ApiError ? caught.message : "Could not assign document.");
    } finally { setBusyId(null); }
  }

  function changeFilters(nextEngineer: string, nextSort: "date_desc" | "date_asc", nextBlockers: string) {
    onFiltersChange({
      engineerId: nextEngineer === "all" ? undefined : nextEngineer,
      sortBy: nextSort,
      hasBlockers: nextBlockers === "all" ? undefined : nextBlockers === "yes",
    });
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      {/* Table Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 p-5 sm:px-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Document Inspection Register</p>
          <h2 className="text-lg font-bold text-slate-900">{documents.length} controlled documents</h2>
        </div>
        <div>
          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept="application/pdf,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => void chooseFile(event.target.files?.[0])}
          />
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-blue-700 disabled:opacity-50"
            type="button"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            <UploadCloud size={16} />
            {uploading ? "Uploading..." : "Upload Document"}
          </button>
        </div>
      </div>

      {/* Filter Controls */}
      {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && (
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-slate-50/70 p-3 sm:px-6">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search document or unit code..."
              className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-xs text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <span>Engineer</span>
            <select
              aria-label="Engineer"
              value={engineer}
              onChange={(event) => { setEngineer(event.target.value); changeFilters(event.target.value, sort, blockers); }}
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
            >
              <option value="all">All engineers</option>
               {(availableEngineers ?? []).map((engineerOption) => <option key={engineerOption.id} value={engineerOption.id}>{engineerOption.full_name}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <span>Blockers</span>
            <select
              aria-label="Blockers"
              value={blockers}
              onChange={(event) => { setBlockers(event.target.value); changeFilters(engineer, sort, event.target.value); }}
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
            >
              <option value="all">All items</option>
              <option value="yes">Only blockers</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
            <ArrowUpDown size={13} className="text-slate-400" />
            <span>Sort:</span>
            <select
              value={sort}
              onChange={(event) => { const value = event.target.value as typeof sort; setSort(value); changeFilters(engineer, value, blockers); }}
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
            >
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
            </select>
          </label>
        </div>
      )}

      {/* Table Content */}
      {loading ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 p-8 text-slate-400">
          <LoaderCircle className="animate-spin text-blue-600" size={24} />
          <span className="text-xs font-medium">Loading documents...</span>
        </div>
      ) : visible.length === 0 ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 p-8 text-center text-slate-400">
          <FileText size={36} className="text-slate-300" />
          <h3 className="text-sm font-bold text-slate-700">No documents match</h3>
          <p className="text-xs text-slate-500">Upload a document or adjust the register filters.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-3">Document & Code</th>
                <th className="px-4 py-3">Type</th>
                {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <th className="px-4 py-3">Uploaded by</th>}
                <th className="px-4 py-3">Assigned PIC</th>
                <th className="px-4 py-3">Workflow Status</th>
                <th className="px-4 py-3">Findings</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visible.map((document) => {
                const workflow = document.workflow_status ?? "ANALYZING";
                const hasActiveTask = Boolean(currentUserId) && documents.some(
                  (item) => item.assigned_to_id === currentUserId && (item.workflow_status ?? "ANALYZING") === "ANALYZING"
                );
                const isAssignedToCurrentUser = Boolean(currentUserId) && document.assigned_to_id === currentUserId;
                return (
                  <tr key={document.id} className="transition hover:bg-slate-50/80">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-700/10">
                          <FileText size={18} />
                        </div>
                        <div className="min-w-0">
                          <strong className="block max-w-[280px] truncate text-xs font-bold text-slate-900" title={document.filename}>
                            {document.filename}
                          </strong>
                          <span className="text-[10px] text-slate-400">
                            {shortId(document.id)} · {formatDate(document.created_at)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                        {document.media_type.includes("pdf") ? "PDF" : "DOCX"}
                      </span>
                    </td>
                    {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && (
                       <td className="px-4 py-3.5 text-slate-600 text-xs">{document.owner_name ?? "Unknown uploader"}</td>
                    )}
                    <td className="px-4 py-3.5">
                      {role === "LEAD_ENGINEER" || role === "SUPERUSER" ? (
                        <select
                          aria-label={`Assign ${document.filename}`}
                          value={document.assigned_to_id ?? ""}
                          disabled={busyId === document.id}
                           onChange={(event) => void assign(document.id, event.target.value || null)}
                          className="h-7 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
                        >
                          <option value="">Unassigned</option>
                          {(availableEngineers ?? []).map((engineerOption) => (
                            <option key={engineerOption.id} value={engineerOption.id}>
                              {engineerOption.full_name}
                            </option>
                          ))}
                        </select>
                      ) : document.assigned_to_id ? (
                        isAssignedToCurrentUser ? (
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-700 ring-1 ring-blue-700/10">
                              <UserRound size={12} />
                              Tugas Anda
                            </span>
                            <Link
                              href={`/documents/${document.id}/review`}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              Review <ExternalLink size={11} />
                            </Link>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-700">
                              {(document.assigned_to_name ?? "?").slice(0, 2).toUpperCase()}
                            </span>
                            Dikerjakan oleh {document.assigned_to_name ?? "Assigned"}
                          </span>
                        )
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 text-[11px]">Unassigned</span>
                          <button
                            type="button"
                            disabled={hasActiveTask || busyId === document.id}
                            title={hasActiveTask ? "Selesaikan tugas aktif Anda terlebih dahulu" : "Ambil Tugas"}
                            onClick={() => void claim(document.id)}
                            className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                          >
                            <UserRound size={12} />
                            {busyId === document.id ? "Claiming..." : "Ambil Tugas"}
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        workflow === "VERIFIED_BY_LEAD"
                          ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-700/10"
                          : workflow === "REVIEWED_BY_ENGINEER"
                          ? "bg-amber-50 text-amber-700 ring-1 ring-amber-700/10"
                          : "bg-blue-50 text-blue-700 ring-1 ring-blue-700/10"
                      }`}>
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                        {workflow.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1">
                        <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold text-rose-700">0 Blocker</span>
                        <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">0 Major</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <Link
                        className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline"
                        href={`/documents/${document.id}/review`}
                      >
                        Open Review <ExternalLink size={13} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {role === "LEAD_ENGINEER" && blockers !== "all" && (
        <p className="flex items-center gap-2 border-t border-slate-100 bg-slate-50 px-6 py-3 text-xs text-slate-500">
          <AlertTriangle size={14} className="text-amber-500" />
          Blocker filtering is applied server-side when the project register is loaded.
        </p>
      )}

      {overrideRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600">WIP Override</p>
                <h3 className="text-base font-bold text-slate-900">Engineer has an active task</h3>
                <p className="mt-1 text-xs text-slate-600">{overrideRequest.message}</p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setOverrideRequest(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => setOverrideRequest(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                onClick={() => void assign(overrideRequest.documentId, overrideRequest.engineerId, true)}
              >
                Confirm Emergency Assignment
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
