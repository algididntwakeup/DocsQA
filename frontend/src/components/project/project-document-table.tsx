"use client";

import { AlertTriangle, ArrowUpDown, ExternalLink, FileText, LoaderCircle, Search, Trash2, UploadCloud, UserRound } from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiError, assignDocument, claimDocument, deleteDocument, type DocumentItem, type ManagedUser, type UserRole } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { AlertDialog } from "@/components/ui/alert-dialog";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(typeof navigator !== "undefined" ? navigator.language : "en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function shortId(id: string | null | undefined) {
  return id ? `${id.slice(0, 8)}...` : "Unassigned";
}
function isProcessingStatus(status: DocumentItem["status"]): boolean {
  const normalized = String(status);
  return normalized === "QUEUED" || normalized === "PROCESSING" || normalized === "ANALYZING";
}


export function ProjectDocumentTable({
  documents,
  projectId,
  role,
  loading,
  onUpload,
  onFiltersChange,
  currentUserId,
  engineers: availableEngineers,
  onChanged,
  projectFinished = false,
  onLoadMore,
  hasMore = false,
  loadingMore = false,
}: {
  documents: DocumentItem[];
  projectId?: string;
  role: UserRole;
  loading: boolean;
  onUpload: (file: File) => Promise<void>;
  onFiltersChange: (filters: { engineerId?: string; sortBy: "date_desc" | "date_asc"; hasBlockers?: boolean }) => void;
  currentUserId?: string;
  engineers?: ManagedUser[];
  onChanged?: () => Promise<void>;
  projectFinished?: boolean;
  onLoadMore?: () => Promise<void>;
  hasMore?: boolean;
  loadingMore?: boolean;
}) {
  const { t } = useLocale();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [engineer, setEngineer] = useState("all");
  const [sort, setSort] = useState<"date_desc" | "date_asc">("date_desc");
  const [blockers, setBlockers] = useState("all");
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [overrideRequest, setOverrideRequest] = useState<{ documentId: string; engineerId: string; message: string } | null>(null);
  const [deleteRequest, setDeleteRequest] = useState<DocumentItem | null>(null);
  const visible = useMemo(() => documents.filter((item) => item.filename.toLowerCase().includes(search.toLowerCase())), [documents, search]);

  async function chooseFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    try { await onUpload(file); } finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  async function claim(documentId: string) {
    setBusyId(documentId);
      try { await claimDocument(documentId); toast.success(t("claim")); await onChanged?.(); }
    catch (caught) { toast.error(caught instanceof ApiError ? caught.message : t("couldNotLoadDocument")); }
    finally { setBusyId(null); }
  }

  async function assign(documentId: string, engineerId: string | null, override = false) {
    setBusyId(documentId);
      try { await assignDocument(documentId, engineerId, override); setOverrideRequest(null); toast.success(t("save")); await onChanged?.(); }
    catch (caught) {
      if (!override && engineerId && caught instanceof ApiError && caught.status === 400) setOverrideRequest({ documentId, engineerId, message: caught.message });
      else toast.error(caught instanceof ApiError ? caught.message : "Could not assign document.");
    } finally { setBusyId(null); }
  }

  async function removeDocument(document: DocumentItem) {
    setBusyId(document.id);
    try {
      await deleteDocument(document.id);
      setDeleteRequest(null);
      toast.success("Document deleted successfully.");
      await onChanged?.();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not delete the document.");
    } finally {
      setBusyId(null);
    }
  }

  function changeFilters(nextEngineer: string, nextSort: "date_desc" | "date_asc", nextBlockers: string) {
    onFiltersChange({
      engineerId: nextEngineer === "all" ? undefined : nextEngineer,
      sortBy: nextSort,
      hasBlockers: nextBlockers === "all" ? undefined : nextBlockers === "yes",
    });
  }

  return (
    <Card className="overflow-hidden">
      {/* Table Header */}
       <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border p-5 sm:px-6">
        <div>
           <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{t("inspectionRegister")}</p>
           <h2 className="text-lg font-bold text-foreground">{documents.length} {t("documents")}</h2>
        </div>
        <div>
          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept="application/pdf,.pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => void chooseFile(event.target.files?.[0])}
          />
          {!projectFinished && (
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-xs transition hover:bg-primary/90 disabled:opacity-50"
              type="button"
              disabled={uploading}
              onClick={() => inputRef.current?.click()}
            >
              <UploadCloud size={16} />
               {uploading ? t("uploading") : t("uploadDocument")}
            </button>
          )}
        </div>
      </div>

      {/* Filter Controls */}
      {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && (
        <div className="flex flex-wrap items-center gap-3 border-b border-border bg-muted/60 p-3 sm:px-6">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search document or unit code..."
              className="h-9 w-full rounded-lg border border-border bg-card pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
            />
          </div>
          <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <span>Engineer</span>
            <select
              aria-label="Engineer"
              value={engineer}
              onChange={(event) => { setEngineer(event.target.value); changeFilters(event.target.value, sort, blockers); }}
              className="h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground focus:border-ring focus:outline-none"
            >
              <option value="all">All engineers</option>
               {(availableEngineers ?? []).map((engineerOption) => <option key={engineerOption.id} value={engineerOption.id}>{engineerOption.full_name}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <span>Blockers</span>
            <select
              aria-label="Blockers"
              value={blockers}
              onChange={(event) => { setBlockers(event.target.value); changeFilters(engineer, sort, event.target.value); }}
              className="h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground focus:border-ring focus:outline-none"
            >
              <option value="all">All items</option>
              <option value="yes">Only blockers</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <ArrowUpDown size={13} className="text-muted-foreground" />
            <span>Sort:</span>
            <select
              value={sort}
              onChange={(event) => { const value = event.target.value as typeof sort; setSort(value); changeFilters(engineer, value, blockers); }}
              className="h-9 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground focus:border-ring focus:outline-none"
            >
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
            </select>
          </label>
        </div>
      )}

      {/* Table Content */}
      {loading ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 p-8 text-muted-foreground">
          <LoaderCircle className="animate-spin text-accent-foreground" size={24} />
          <span className="text-xs font-medium">Loading documents...</span>
        </div>
      ) : visible.length === 0 ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
          <FileText size={36} className="text-muted-foreground" />
          <h3 className="text-sm font-bold text-foreground">No documents match</h3>
          <p className="text-xs text-muted-foreground">Upload a document or adjust the register filters.</p>
        </div>
      ) : (
        <Table className="text-left text-xs text-foreground">
          <TableHeader className="border-b border-border bg-muted/60 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            <TableRow>
              <TableHead className="px-6 py-3">Document & Code</TableHead>
              <TableHead className="px-4 py-3">Type</TableHead>
              {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && <TableHead className="px-4 py-3">Uploaded by</TableHead>}
              <TableHead className="px-4 py-3">Assigned PIC</TableHead>
              <TableHead className="px-4 py-3">Workflow Status</TableHead>
              <TableHead className="px-4 py-3">Findings</TableHead>
              <TableHead className="px-6 py-3 text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-border/60">
            {visible.map((document) => {
              const hasActiveTask = Boolean(currentUserId) && documents.some(
                (item) => item.project_id === projectId
                  && item.assigned_to_id === currentUserId
                  && (item.workflow_status ?? "ANALYZING") === "ANALYZING",
              );
              const workflow = document.workflow_status ?? "ANALYZING";
              const processing = isProcessingStatus(document.status);
              const isAssignedToCurrentUser = Boolean(currentUserId) && document.assigned_to_id === currentUserId;
              const progressLabel = `${document.progress_pct}%`;
              return (
                <TableRow key={document.id} className="hover:bg-muted/60">
                  <TableCell className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground ring-1 ring-primary/10">
                        <FileText size={18} />
                      </div>
                      <div className="min-w-0">
                        <strong className="block max-w-[280px] truncate text-xs font-bold text-foreground" title={document.filename}>
                          {document.filename}
                        </strong>
                        <span className="text-[10px] text-muted-foreground">
                          {shortId(document.id)} · {formatDate(document.created_at)}
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="px-4 py-3.5">
                    <span className="rounded bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground">
                      {document.media_type.includes("pdf") ? "PDF" : "DOCX"}
                    </span>
                  </TableCell>
                  {(role === "LEAD_ENGINEER" || role === "SUPERUSER") && (
                    <TableCell className="px-4 py-3.5 text-muted-foreground text-xs">{document.owner_name ?? "Unknown uploader"}</TableCell>
                  )}
                  <TableCell className="px-4 py-3.5">
                    {role === "LEAD_ENGINEER" || role === "SUPERUSER" ? (
                      <select
                        aria-label={`Assign ${document.filename}`}
                        value={document.assigned_to_id ?? ""}
                        disabled={projectFinished || busyId === document.id}
                        onChange={(event) => void assign(document.id, event.target.value || null)}
                        className="h-7 rounded-md border border-border bg-card px-2 text-xs text-foreground focus:border-ring focus:outline-none disabled:opacity-60"
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
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-0.5 text-xs font-bold text-accent-foreground ring-1 ring-primary/10">
                            <UserRound size={12} />
                            Tugas Anda
                          </span>
                          <Link
                            href={`/documents/${document.id}/review`}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-accent-foreground hover:text-primary hover:underline"
                          >
                            Review <ExternalLink size={11} />
                          </Link>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs text-foreground font-medium">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-foreground">
                            {(document.assigned_to_name ?? "?").slice(0, 2).toUpperCase()}
                          </span>
                          Dikerjakan oleh {document.assigned_to_name ?? "Assigned"}
                        </span>
                      )
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-[11px]">Unassigned</span>
                        <button
                          type="button"
                          disabled={projectFinished || hasActiveTask || busyId === document.id}
                          title={hasActiveTask ? "Selesaikan tugas aktif Anda terlebih dahulu" : "Ambil Tugas"}
                          onClick={() => void claim(document.id)}
                          className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-accent px-2 py-1 text-[11px] font-semibold text-accent-foreground hover:bg-accent/80 disabled:opacity-50"
                        >
                          <UserRound size={12} />
                          {busyId === document.id ? "Claiming..." : "Ambil Tugas"}
                        </button>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="px-4 py-3.5">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      workflow === "VERIFIED_BY_LEAD"
                        ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-700/10"
                        : workflow === "REVIEWED_BY_ENGINEER"
                        ? "bg-amber-50 text-amber-700 ring-1 ring-amber-700/10"
                        : "bg-accent text-accent-foreground ring-1 ring-primary/10"
                    }`}>
                      <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      {workflow.replaceAll("_", " ")}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3.5">
                    <div className="flex items-center gap-1">
                      <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold text-rose-700">0 Blocker</span>
                      <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">0 Major</span>
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-3">
                    <button
                      type="button"
                      aria-label={`Delete ${document.filename}`}
                      title={document.assigned_to_id || workflow === "REVIEWED_BY_ENGINEER" || workflow === "VERIFIED_BY_LEAD" ? "Documents in progress or already verified cannot be deleted" : "Delete document"}
                      disabled={Boolean(document.assigned_to_id) || workflow === "REVIEWED_BY_ENGINEER" || workflow === "VERIFIED_BY_LEAD" || busyId === document.id || projectFinished}
                      onClick={() => setDeleteRequest(document)}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground shadow-2xs transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Trash2 size={14} />
                    </button>
                    {processing ? (
                      <button
                        type="button"
                        disabled
                        aria-label={`Open Workspace ${document.filename}`}
                        title="The workspace is available once processing finishes"
                        className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs font-bold text-muted-foreground disabled:cursor-not-allowed"
                      >
                        Analyzing... <span aria-label={`Progress ${progressLabel}`}>{progressLabel}</span>
                      </button>
                    ) : (
                      <Link
                        className="inline-flex items-center gap-1 text-xs font-bold text-accent-foreground hover:text-primary hover:underline"
                        href={`/documents/${document.id}/review`}
                      >
                        Open Workspace <ExternalLink size={13} />
                      </Link>
                    )}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
      {hasMore && onLoadMore && (
        <div className="flex justify-center border-t border-border bg-card px-6 py-3">
          <button
            type="button"
            disabled={loadingMore}
            onClick={() => void onLoadMore()}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted disabled:opacity-50"
          >
            {loadingMore ? "Loading…" : `Load more documents (${documents.length})`}
          </button>
        </div>
      )}

      {role === "LEAD_ENGINEER" && blockers !== "all" && (
        <p className="flex items-center gap-2 border-t border-border bg-muted/60 px-6 py-3 text-xs text-muted-foreground">
          <AlertTriangle size={14} className="text-amber-500" />
          Blocker filtering is applied server-side when the project register is loaded.
        </p>
      )}

      {overrideRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600">WIP Override</p>
                <h3 className="text-base font-bold text-foreground">Engineer has an active task</h3>
                <p className="mt-1 text-xs text-muted-foreground">{overrideRequest.message}</p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setOverrideRequest(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                ×
              </button>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/60"
                onClick={() => setOverrideRequest(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                onClick={() => void assign(overrideRequest.documentId, overrideRequest.engineerId, true)}
              >
                Confirm Emergency Assignment
              </button>
            </div>
          </div>
        </div>
      )}

      <AlertDialog
        open={deleteRequest !== null}
        onOpenChange={(next) => {
          if (!next) setDeleteRequest(null);
        }}
        title="Delete Document"
        description="Are you sure you want to delete this document? This action cannot be undone."
        confirmLabel="Yes, Delete Document"
        cancelLabel="Cancel"
        busyLabel="Deleting..."
        busy={busyId === deleteRequest?.id}
        onConfirm={() => {
          if (deleteRequest) void removeDocument(deleteRequest);
        }}
      />
    </Card>
  );
}
