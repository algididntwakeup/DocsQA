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
      <section className="panel empty-state">
        <div className="empty-icon"><FileText aria-hidden="true" /></div>
        <p className="eyebrow">Inspection register</p>
        <h2>No documents yet</h2>
        <p>Upload a native-text PDF or DOCX to begin the extraction lifecycle.</p>
        <Link className="button button-primary" href="/upload"><Plus size={16} />New inspection</Link>
      </section>
    );
  }

  return (
    <section className="panel document-register" aria-labelledby="register-heading">
      <div className="panel-heading">
        <div><p className="eyebrow">Inspection register</p><h2 id="register-heading">Recent documents</h2></div>
        <button className="icon-button" type="button" onClick={onRefresh} aria-label="Refresh documents"><RotateCw size={16} /></button>
      </div>
      {deleteError && (
        <div className="alert alert-error" role="alert" style={{ margin: "12px 18px" }}>
          <span><strong>Delete Failed:</strong> {deleteError}</span>
          <button type="button" onClick={() => setDeleteError(null)}>Dismiss</button>
        </div>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Pages</th>
              <th>Uploaded</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id}>
                <td>
                  <Link className="document-link" href={`/documents/${document.id}`}>
                    <FileText size={17} />
                    <span>
                      <strong>{document.filename}</strong>
                      <small>{formatBytes(document.size_bytes)} · {document.media_type.includes("pdf") ? "PDF" : "DOCX"}</small>
                    </span>
                  </Link>
                </td>
                <td><StatusBadge status={document.status} /></td>
                <td>
                  <div className="table-progress">
                    <progress max="100" value={document.progress_pct}>{document.progress_pct}%</progress>
                    <span>{document.progress_pct}%</span>
                  </div>
                </td>
                <td>{document.page_count ?? "—"}</td>
                <td><time dateTime={document.created_at}>{formatDate(document.created_at)}</time></td>
                <td style={{ textAlign: "right" }}>
                  <button
                    className="icon-button row-action-btn delete-action-btn"
                    type="button"
                    onClick={() => void handleDelete(document.id, document.filename)}
                    disabled={deletingId === document.id}
                    aria-label={`Delete ${document.filename}`}
                    title="Delete document"
                  >
                    {deletingId === document.id ? (
                      <Loader2 size={14} className="animate-spin" />
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
