import { FileText, Plus, RotateCw } from "lucide-react";
import Link from "next/link";
import type { DocumentItem } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function DocumentList({ documents, onRefresh }: { documents: DocumentItem[]; onRefresh: () => void }) {
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
      <div className="table-scroll">
        <table>
          <thead><tr><th>Document</th><th>Status</th><th>Progress</th><th>Pages</th><th>Uploaded</th></tr></thead>
          <tbody>{documents.map((document) => (
            <tr key={document.id}>
              <td><Link className="document-link" href={`/documents/${document.id}`}><FileText size={17} /><span><strong>{document.filename}</strong><small>{formatBytes(document.size_bytes)} · {document.media_type.includes("pdf") ? "PDF" : "DOCX"}</small></span></Link></td>
              <td><StatusBadge status={document.status} /></td>
              <td><div className="table-progress"><progress max="100" value={document.progress_pct}>{document.progress_pct}%</progress><span>{document.progress_pct}%</span></div></td>
              <td>{document.page_count ?? "—"}</td>
              <td><time dateTime={document.created_at}>{formatDate(document.created_at)}</time></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}
