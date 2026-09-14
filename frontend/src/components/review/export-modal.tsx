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
  badgeClass: string;
  description: string;
  icon: React.ReactNode;
  testId: string;
  actionLabel: string;
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
      format: "pdf",
      title: "PDF Review Report",
      extension: ".pdf",
      badge: "Recommended",
      badgeClass: "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      description: "Production-ready read-only review report with exact layouts and tables rendered via Headless LibreOffice.",
      icon: <FileText size={24} className="text-emerald-500 dark:text-emerald-400" />,
      testId: "export-pdf-btn",
      actionLabel: "Download PDF",
    },
    {
      format: "docx",
      title: "DOCX Review Report",
      extension: ".docx",
      badge: "Editable",
      badgeClass: "text-sky-600 dark:text-sky-400 bg-sky-500/10 border-sky-500/20",
      description: "Editable Microsoft Word document for reviewers who need to add manual revisions or comments.",
      icon: <FileCheck2 size={24} className="text-sky-500 dark:text-sky-400" />,
      testId: "export-docx-btn",
      actionLabel: "Download DOCX",
    },
    {
      format: "annotated_pdf",
      title: "Annotated Source PDF",
      extension: ".pdf",
      badge: "Visual Inspection",
      badgeClass: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      description: "Original source PDF overlaid with bounding boxes and callout popups indicating exact finding locations and reviewer notes for included findings.",
      icon: <FileText size={24} className="text-amber-500 dark:text-amber-400" />,
      testId: "export-annotated-pdf-btn",
      actionLabel: "Download Overlay",
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
              <label className="inline-flex items-center gap-2 cursor-pointer font-medium text-ink">
                <input
                  type="radio"
                  name="report-language"
                  value="en"
                  checked={reportLanguage === "en"}
                  onChange={() => setReportLanguage("en")}
                  className="accent-primary"
                />
                <span>English</span>
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer font-medium text-ink">
                <input
                  type="radio"
                  name="report-language"
                  value="id"
                  checked={reportLanguage === "id"}
                  onChange={() => setReportLanguage("id")}
                  className="accent-primary"
                />
                <span>Bahasa Indonesia</span>
              </label>
            </div>
            <p className="mt-2 text-[11px] text-muted">{t("reportLanguageHelp")}</p>
          </fieldset>
          <label className="flex items-start gap-2 rounded-lg border border-line bg-muted/5 p-3 text-xs text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={includeMinors}
              onChange={(event) => setIncludeMinors(event.target.checked)}
              className="mt-0.5 accent-primary"
            />
            <span>
              <span className="block font-semibold text-ink">{t("includeMinors")}</span>
              <span>Include spelling, grammar, and informational findings in the export. Off by default to keep the report concise.</span>
            </span>
          </label>
          <div className="grid grid-cols-1 gap-3">
            {options.map((option) => (
              <div key={option.format} className="panel p-4 flex flex-col justify-between hover:border-sky-500/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted/10 shrink-0">{option.icon}</div>
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-ink truncate">{option.title}</h3>
                        <span className="text-[10px] font-mono text-muted bg-muted/20 px-1.5 py-0.5 rounded">{option.extension}</span>
                      </div>
                      <span className={`text-[10px] font-medium border px-2 py-0.5 rounded-full shrink-0 ${option.badgeClass}`}>
                        {option.badge}
                      </span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">{option.description}</p>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-line flex justify-end">
                  <button
                    type="button"
                    data-testid={option.testId}
                    className="button button-primary btn-sm flex items-center gap-1.5"
                    onClick={() => {
                      if (option.format === "pdf" || option.format === "docx") {
                        void downloadExport(documentId, option.format, includeMinors, reportLanguage);
                      } else {
                        void downloadExport(documentId, option.format, includeMinors);
                      }
                    }}
                  >
                    <Download size={13} />
                    <span>{option.actionLabel}</span>
                    <ExternalLink size={11} className="opacity-60 ml-0.5" />
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
