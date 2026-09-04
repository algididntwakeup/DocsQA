"use client";

import { FilePlus2, UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";
import { formatBytes } from "@/lib/format";

const MAX_FILES = 20;
const MAX_BYTES = 50 * 1024 * 1024;

export function DropZone({ files, onChange, disabled = false }: { files: File[]; onChange: (files: File[]) => void; disabled?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [validation, setValidation] = useState<string | null>(null);

  function addFiles(incoming: FileList | File[]) {
    const next = Array.from(incoming);
    const invalid = next.find((file) => ![".pdf", ".docx"].some((extension) => file.name.toLowerCase().endsWith(extension)) || file.size > MAX_BYTES);
    if (invalid) {
      setValidation(`${invalid.name} must be a PDF/DOCX no larger than 50 MiB.`);
      return;
    }
    if (files.length + next.length > MAX_FILES) {
      setValidation(`A batch can contain at most ${MAX_FILES} files.`);
      return;
    }
    setValidation(null);
    onChange([...files, ...next].filter((file, index, all) => all.findIndex((item) => item.name === file.name && item.size === file.size) === index));
  }

  return (
    <div>
      <div
        className={`drop-zone${dragging ? " is-dragging" : ""}${disabled ? " is-disabled" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); if (!disabled) addFiles(event.dataTransfer.files); }}
      >
        <input ref={inputRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" multiple disabled={disabled} onChange={(event) => event.target.files && addFiles(event.target.files)} />
        <div className="drop-icon"><UploadCloud aria-hidden="true" /></div>
        <h2>Drop inspection documents here</h2>
        <p>Native-text PDF or DOCX · 50 MiB each · up to 20 files</p>
        <button className="button button-secondary" type="button" disabled={disabled} onClick={() => inputRef.current?.click()}><FilePlus2 size={16} />Browse files</button>
      </div>
      {validation && <p className="field-error" role="alert">{validation}</p>}
      {files.length > 0 && <ul className="file-queue" aria-label="Files ready to upload">{files.map((file, index) => (
        <li key={`${file.name}-${file.size}`}><span><strong>{file.name}</strong><small>{formatBytes(file.size)}</small></span><button type="button" disabled={disabled} aria-label={`Remove ${file.name}`} onClick={() => onChange(files.filter((_, itemIndex) => itemIndex !== index))}><X size={15} /></button></li>
      ))}</ul>}
    </div>
  );
}
