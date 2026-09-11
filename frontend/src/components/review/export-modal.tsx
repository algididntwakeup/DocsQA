"use client";

import { useEffect, useState } from "react";
import { Download, FileCheck2, FileText, X, ExternalLink } from "lucide-react";
import { type ExportFormat, type ReportLanguage } from "@/lib/api";
import { downloadExport } from "@/lib/download";
import { useLocale } from "@/components/layout/locale-provider";

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

export function ExportModal({ documentId, documentFilename, isOpen, onClose }: ExportModalProps) {
  const { locale, t } = useLocale();
  const [includeMinors, setIncludeMinors] = useState(false);
  const [reportLanguage, setReportLanguage] = useState<ReportLanguage>(locale);

  useEffect(() => {
    if (isOpen) queueMicrotask(() => setReportLanguage(locale));
  }, [isOpen, locale]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const options: ExportOption[] = [
    {
      format: "docx",
      title: "DOCX Review Report",
      extension: ".docx",
      badge: "Official Deliverable",
      description: "Deterministic Word document including summary judgement, scorecard, blockers, next-revision recommendations, language findings, and reviewer notes.",
      icon: <FileCheck2 size={24} className="text-sky-500 dark:text-sky-400" />,
    },
    {
      format: "pdf",
      title: "Annotated Source PDF",
      extension: ".pdf",
      badge: "Visual Inspection",
      description: "Original source PDF overlaid with bounding boxes and callout popups indicating exact finding locations and reviewer notes for included findings.",
      icon: <FileText size={24} className="text-emerald-500 dark:text-emerald-400" />,
    },
  ];

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="export-modal-title">
      <div className="modal-container max-w-xl" onClick={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <div className="flex items-center gap-2">
            <Download size={18} className="text-sky-500" />
            <h2 id="export-modal-title" className="text-base font-semibold text-ink">{t("export")} Review Deliverables</h2>
          </div>
          <button type="button" className="icon-button text-muted" onClick={onClose} aria-label="Close export modal"><X size={16} /></button>
        </header>
        <div className="modal-body p-5 space-y-4">
          <p className="text-xs text-muted">
            Select an export format for document <strong className="text-ink font-semibold">{documentFilename}</strong>. Generated outputs reflect only findings marked as included in report.
          </p>
          <fieldset className="rounded-lg border border-line bg-muted/5 p-3 text-xs text-muted">
            <legend className="font-semibold text-ink">{t("reportLanguage")}</legend>
            <div className="flex gap-4 mt-2">
              <label><input type="radio" name="report-language" checked={reportLanguage === "en"} onChange={() => setReportLanguage("en")} /> English</label>
              <label><input type="radio" name="report-language" checked={reportLanguage === "id"} onChange={() => setReportLanguage("id")} /> Bahasa Indonesia</label>
            </div>
            <p className="mt-2">{t("reportLanguageHelp")}</p>
          </fieldset>
          <label className="flex items-start gap-2 rounded-lg border border-line bg-muted/5 p-3 text-xs text-muted">
            <input type="checkbox" checked={includeMinors} onChange={(event) => setIncludeMinors(event.target.checked)} className="mt-0.5" />
            <span><span className="block font-semibold text-ink">{t("includeMinors")}</span><span>Include spelling, grammar, and informational findings in the export. Off by default to keep the report concise.</span></span>
          </label>
          <div className="grid grid-cols-1 gap-3">
            {options.map((option) => (
              <div key={option.format} className="panel p-4 flex flex-col justify-between hover:border-sky-500/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted/10 shrink-0">{option.icon}</div>
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2"><h3 className="text-sm font-semibold text-ink truncate">{option.title}</h3><span className="text-[10px] font-mono text-muted bg-muted/20 px-1.5 py-0.5 rounded">{option.extension}</span></div>
                      <span className="text-[10px] font-medium text-sky-600 bg-sky-500/10 border border-sky-500/20 px-1.5 py-0.5 rounded-full shrink-0">{option.badge}</span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">{option.description}</p>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-line flex justify-end">
                  <button type="button" data-testid={`export-${option.format}-btn`} className="button button-primary btn-sm flex items-center gap-1.5" onClick={() => option.format === "docx" ? void downloadExport(documentId, option.format, includeMinors, reportLanguage) : void downloadExport(documentId, option.format, includeMinors)}>
                    <Download size={13} /><span>Download {option.extension.toUpperCase().slice(1)}</span><ExternalLink size={11} className="opacity-60 ml-0.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
