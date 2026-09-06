"use client";

import { useEffect } from "react";
import {
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Table,
  X,
  ExternalLink,
} from "lucide-react";
import { getExportUrl, type ExportFormat } from "@/lib/api";

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
  description: string;
  badge: string;
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

  if (!isOpen) return null;

  const exportOptions: ExportOption[] = [
    {
      format: "pdf",
      title: "Annotated PDF Document",
      extension: ".pdf",
      badge: "Visual Inspection",
      description:
        "Canonical PDF document overlaid with color-coded bounding boxes and interactive callout popups indicating exact finding locations.",
      icon: <FileText size={22} className="text-sky-400" />,
    },
    {
      format: "xlsx",
      title: "Executive & Engineering Workbook",
      extension: ".xlsx",
      badge: "Multi-Sheet Report",
      description:
        "Formatted Excel workbook containing Summary KPIs, Traceability issues, Linguistic checks, and the complete tamper-evident Audit Trail.",
      icon: <FileSpreadsheet size={22} className="text-emerald-400" />,
    },
    {
      format: "csv",
      title: "Flat Findings Log",
      extension: ".csv",
      badge: "Tabular Data",
      description:
        "RFC 4180 flat CSV export containing all findings, stated vs computed values, tolerance margins, and recorded reviewer dispositions.",
      icon: <Table size={22} className="text-amber-400" />,
    },
    {
      format: "json",
      title: "Audit & Evidence Package",
      extension: ".json",
      badge: "Cryptographic Bundle",
      description:
        "Comprehensive JSON verification bundle with document SHA-256 hash, raw analyzer evidence payloads, and full append-only audit event history.",
      icon: <FileCode size={22} className="text-purple-400" />,
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
        className="modal-container max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <div className="flex items-center gap-2">
            <Download size={18} className="text-sky-400" />
            <h2 id="export-modal-title" className="text-base font-semibold text-slate-100">
              Export Findings & Audit Package
            </h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close export modal"
          >
            <X size={16} />
          </button>
        </header>

        <div className="modal-body p-5 space-y-4">
          <p className="text-xs text-slate-400">
            Select an export format for document <strong className="text-slate-200">{documentFilename}</strong>. All exports reflect current QA decisions, dispositions, and the complete audit trail.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {exportOptions.map((opt) => (
              <a
                key={opt.format}
                href={getExportUrl(documentId, opt.format)}
                download
                target="_blank"
                rel="noreferrer"
                className="flex flex-col justify-between p-4 rounded-md border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-sky-500/50 transition-colors group cursor-pointer"
                data-testid={`export-${opt.format}-btn`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-2 rounded bg-slate-800/80 border border-slate-700/60">
                      {opt.icon}
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {opt.badge}
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-slate-200 group-hover:text-sky-300 transition-colors flex items-center gap-1.5">
                    {opt.title}
                    <span className="text-xs text-slate-500 font-mono">{opt.extension}</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                    {opt.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-sky-400 font-medium group-hover:text-sky-300">
                  <span>Download file</span>
                  <ExternalLink size={13} />
                </div>
              </a>
            ))}
          </div>
        </div>

        <footer className="modal-footer flex items-center justify-end p-4 border-t border-slate-800 bg-slate-950/40">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onClose}
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}
