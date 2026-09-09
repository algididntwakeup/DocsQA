"use client";

import { useEffect, useState } from "react";
import {
  Download,
  FileCheck2,
  FileText,
  X,
  ExternalLink,
} from "lucide-react";
import { type ExportFormat } from "@/lib/api";
import { downloadExport } from "@/lib/download";

interface ExportModalProps {
  documentId: string;
  documentFilename: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ExportOption {
  format: ExportFormat;
  title: string;
  extension: string;
  badge: string;
  description: string;
  icon: React.ReactNode;
}

export function ExportModal({
  documentId,
  documentFilename,
  isOpen,
  onClose,
}: ExportModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const [includeMinors, setIncludeMinors] = useState(false);

  if (!isOpen) return null;

  const exportOptions: ExportOption[] = [
    {
      format: "docx",
      title: "DOCX Review Report",
      extension: ".docx",
      badge: "Official Deliverable",
      description:
        "Deterministic Word document including summary judgement, scorecard, blockers, next-revision recommendations, language findings, and reviewer notes.",
      icon: <FileCheck2 size={24} className="text-sky-500 dark:text-sky-400" />,
    },
    {
      format: "pdf",
      title: "Annotated Source PDF",
      extension: ".pdf",
      badge: "Visual Inspection",
      description:
        "Original source PDF overlaid with bounding boxes and callout popups indicating exact finding locations and reviewer notes for included findings.",
      icon: <FileText size={24} className="text-emerald-500 dark:text-emerald-400" />,
    },
  ];

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
    >
      <div
        className="modal-container max-w-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <div className="flex items-center gap-2">
            <Download size={18} className="text-sky-500 dark:text-sky-400" />
            <h2 id="export-modal-title" className="text-base font-semibold text-ink">
              Export Review Deliverables
            </h2>
          </div>
          <button
            type="button"
            className="icon-button text-muted hover:text-ink transition-colors"
            onClick={onClose}
            aria-label="Close export modal"
          >
            <X size={16} />
          </button>
        </header>

        <div className="modal-body p-5 space-y-4">
          <p className="text-xs text-muted">
            Select an export format for document{" "}
            <strong className="text-ink font-semibold">{documentFilename}</strong>. Generated outputs reflect only findings marked as included in report.
          </p>

          <label className="flex items-start gap-2 rounded-lg border border-line bg-muted/5 p-3 text-xs text-muted">
            <input
              type="checkbox"
              checked={includeMinors}
              onChange={(event) => setIncludeMinors(event.target.checked)}
              className="mt-0.5"
            />
            <span>
              <span className="block font-semibold text-ink">Include minor findings</span>
              <span>Include spelling, grammar, and informational findings in the export. Off by default to keep the report concise.</span>
            </span>
          </label>

          <div className="grid grid-cols-1 gap-3">
            {exportOptions.map((opt) => {
              return (
                <div
                  key={opt.format}
                  className="panel p-4 flex flex-col justify-between hover:border-sky-500/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-muted/10 shrink-0">
                      {opt.icon}
                    </div>
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-ink truncate">
                            {opt.title}
                          </h3>
                          <span className="text-[10px] font-mono text-muted bg-muted/20 px-1.5 py-0.5 rounded">
                            {opt.extension}
                          </span>
                        </div>
                        <span className="text-[10px] font-medium text-sky-600 dark:text-sky-400 bg-sky-500/10 border border-sky-500/20 px-1.5 py-0.5 rounded-full shrink-0">
                          {opt.badge}
                        </span>
                      </div>
                      <p className="text-xs text-muted leading-relaxed">
                        {opt.description}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-line flex justify-end">
                    <button
                      type="button"
                      data-testid={`export-${opt.format}-btn`}
                      className="button button-primary btn-sm flex items-center gap-1.5"
                       onClick={() => void downloadExport(documentId, opt.format, includeMinors)}
                    >
                      <Download size={13} />
                      <span>Download {opt.extension.toUpperCase().slice(1)}</span>
                      <ExternalLink size={11} className="opacity-60 ml-0.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
