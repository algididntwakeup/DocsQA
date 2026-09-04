"use client";

import { AlertTriangle, ArrowRight, CheckCircle2, ShieldCheck, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ApiError, uploadDocument, type DocumentUpload } from "@/lib/api";
import { DropZone } from "./drop-zone";

type UploadResult = { file: string; document?: DocumentUpload; error?: string };

export function UploadWorkspace() {
  const [files, setFiles] = useState<File[]>([]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<UploadResult[]>([]);

  async function submit() {
    setRunning(true);
    setResults([]);
    const completed: UploadResult[] = [];
    for (const file of files) {
      try {
        completed.push({ file: file.name, document: await uploadDocument(file) });
      } catch (caught) {
        completed.push({ file: file.name, error: caught instanceof ApiError ? caught.message : "Upload could not be completed." });
      }
      setResults([...completed]);
    }
    setRunning(false);
  }

  return (
    <>
      <div className="page-heading compact"><div><p className="eyebrow">Controlled ingestion</p><h1>New document inspection</h1><p>Files stay in your local processing environment.</p></div></div>
      <div className="upload-layout">
        <section className="panel upload-panel">
          <div className="panel-heading"><div><p className="eyebrow">Step 01</p><h2>Select source documents</h2></div><span className="queue-count">{files.length}/20</span></div>
          <DropZone files={files} onChange={setFiles} disabled={running} />
          <div className="upload-actions"><p><ShieldCheck size={15} />Type and archive structure are verified server-side.</p><button className="button button-primary" type="button" disabled={files.length === 0 || running} onClick={() => void submit()}><Upload size={16} />{running ? `Uploading ${results.length + 1} of ${files.length}…` : `Begin inspection${files.length ? ` (${files.length})` : ""}`}</button></div>
        </section>
        <aside className="panel protocol-panel"><p className="eyebrow">Ingestion protocol</p><h2>Validation sequence</h2><ol><li><span>01</span><div><strong>Signature check</strong><p>Confirms PDF or DOCX bytes, not only the extension.</p></div></li><li><span>02</span><div><strong>Secure persistence</strong><p>Streams into isolated local object storage.</p></div></li><li><span>03</span><div><strong>Extraction queue</strong><p>Dispatches a versioned worker stage for each document.</p></div></li></ol></aside>
      </div>
      {results.length > 0 && <section className="panel result-panel" aria-live="polite"><div className="panel-heading"><div><p className="eyebrow">Batch result</p><h2>Ingestion report</h2></div><span>{results.length}/{files.length}</span></div><ul>{results.map((result) => <li key={result.file} className={result.error ? "result-error" : "result-success"}>{result.error ? <AlertTriangle /> : <CheckCircle2 />}<span><strong>{result.file}</strong><small>{result.error ?? (result.document?.deduplicated ? "Existing active scan reused" : "Queued for extraction")}</small></span>{result.document && <Link href={`/documents/${result.document.id}`} aria-label={`View status for ${result.file}`}><ArrowRight /></Link>}</li>)}</ul></section>}
    </>
  );
}
