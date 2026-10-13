"use client";

import { FileText, Loader2, Plus, RotateCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { deleteDocument, type DocumentItem } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useLocale } from "@/components/layout/locale-provider";
import { Card } from "@/components/ui/card";

const workflowStyles: Record<string, string> = {
  ANALYZING: "bg-accent text-accent-foreground ring-primary/10",
  REVIEWED_BY_ENGINEER: "bg-amber-50 text-amber-700 ring-amber-600/10",
  VERIFIED_BY_LEAD: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
};

function workflowLabel(status?: string) {
  return status === "REVIEWED_BY_ENGINEER" ? "Reviewed" : status === "VERIFIED_BY_LEAD" ? "Verified" : "Analyzing";
}

export function DocumentList({ documents, onRefresh }: { documents: DocumentItem[]; onRefresh: () => void }) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { t } = useLocale();
  async function handleDelete(document: DocumentItem) {
    if (!window.confirm(`${t("deleteDocument")}: "${document.filename}"?`)) return;
    setDeletingId(document.id);
    try { await deleteDocument(document.id); onRefresh(); } finally { setDeletingId(null); }
  }

  if (!documents.length) return <section className="rounded-2xl border border-dashed border-border bg-card p-12 text-center shadow-sm"><FileText className="mx-auto text-accent-foreground" size={28} /><h2 className="mt-3 text-base font-bold text-foreground">{t("noDocuments")}</h2><p className="mt-1 text-xs text-muted-foreground">{t("noDocumentsDescription")}</p><Link href="/upload" className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground hover:bg-primary/90"><Plus size={16} /> {t("newDocument")}</Link></section>;

  return (
    <Card className="overflow-hidden" aria-labelledby="register-heading">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">{t("inspectionRegister")}</p>
          <h2 id="register-heading" className="mt-1 text-base font-bold text-foreground">{t("documentControlLog")}</h2>
        </div>
        <button type="button" onClick={onRefresh} aria-label={t("refresh")} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-muted/60"><RotateCw size={14} /></button>
      </div>
      <Table className="min-w-[980px] text-xs">
        <TableHeader className="bg-muted/60">
          <TableRow>
            <TableHead>Document</TableHead>
            <TableHead>Project &amp; Plant</TableHead>
            <TableHead>Uploaded By</TableHead>
            <TableHead>Assigned PIC</TableHead>
            <TableHead>Workflow Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((document) => (
            <TableRow key={document.id}>
              <TableCell>
                <Link href={`/documents/${document.id}`} className="group flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground"><FileText size={17} /></span>
                  <span>
                    <strong className="block max-w-[260px] truncate font-bold text-foreground group-hover:text-accent-foreground">{document.filename}</strong>
                    <span className="mt-1 block text-[11px] text-muted-foreground">{document.media_type.includes("pdf") ? "PDF" : "DOCX"} · {formatBytes(document.size_bytes)} · {formatDate(document.created_at)}</span>
                  </span>
                </Link>
              </TableCell>
              <TableCell>
                <Link href={document.project_id ? `/projects/${document.project_id}` : "#"} className="font-semibold text-foreground hover:text-accent-foreground">{document.project_name ?? "Unassigned project"}</Link>
                <span className="mt-1 block text-[11px] text-muted-foreground">{document.project_plant ?? "Plant area not set"}</span>
              </TableCell>
              <TableCell className="text-muted-foreground">{document.uploaded_by_name ?? document.owner_name ?? "Unknown"}</TableCell>
              <TableCell>
                {document.assigned_to_name ? <span className="font-medium text-foreground">{document.assigned_to_name}</span> : <span className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-semibold text-muted-foreground">Unassigned</span>}
              </TableCell>
              <TableCell>
                <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold ring-1 ${workflowStyles[document.workflow_status ?? "ANALYZING"] ?? workflowStyles.ANALYZING}`}>{workflowLabel(document.workflow_status)}</span>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Link href={`/documents/${document.id}/review`} className="rounded-lg bg-primary px-3 py-2 text-[10px] font-bold text-primary-foreground hover:bg-primary/90">Open Review</Link>
                  <button type="button" onClick={() => void handleDelete(document)} disabled={deletingId === document.id} aria-label={`Delete ${document.filename}`} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border text-muted-foreground hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50">{deletingId === document.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}</button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
