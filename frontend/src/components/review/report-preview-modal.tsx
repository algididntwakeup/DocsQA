"use client";

import { useEffect, useState } from "react";
import {
  AlertOctagon,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  Shield,
  X,
} from "lucide-react";
import {
  getExportUrl,
  getReportPreview,
  type ReviewReportPreview,
} from "@/lib/api";

interface ReportPreviewModalProps {
  documentId: string;
  documentFilename: string;
  isOpen: boolean;
  onClose: () => void;
}

export function ReportPreviewModal({
  documentId,
  documentFilename,
  isOpen,
  onClose,
}: ReportPreviewModalProps) {
  const [preview, setPreview] = useState<ReviewReportPreview | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;

    getReportPreview(documentId)
      .then((data) => {
        if (active) {
          setPreview(data);
          setError(null);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load report preview");
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [documentId, isOpen]);

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

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-preview-title"
    >
      <div
        className="modal-container max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <div className="flex items-center gap-2">
            <FileCheck2 size={20} className="text-sky-500 dark:text-sky-400" />
            <div>
              <h2 id="report-preview-title" className="text-base font-semibold text-ink">
                Review Report Preview
              </h2>
              <p className="text-xs text-muted">
                Deterministic engineering review composition for {documentFilename}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="icon-button text-muted hover:text-ink transition-colors"
            onClick={onClose}
            aria-label="Close report preview"
          >
            <X size={16} />
          </button>
        </header>

        <div className="modal-body p-5 space-y-5">
          {isLoading ? (
            <div className="py-12 text-center text-muted space-y-2">
              <div className="animate-spin inline-block w-6 h-6 border-2 border-current border-t-transparent rounded-full" />
              <p className="text-sm">Calculating report composition...</p>
            </div>
          ) : error ? (
            <div className="alert alert-error" role="alert">
              <span>{error}</span>
            </div>
          ) : preview ? (
            <>
              {/* Summary Judgement */}
              <div
                className={`p-4 rounded-lg border ${
                  preview.blockers > 0
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                    : "bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200"
                }`}
              >
                <div className="flex items-start gap-3">
                  {preview.blockers > 0 ? (
                    <AlertOctagon size={20} className="text-amber-500 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 size={20} className="text-emerald-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h3 className="text-sm font-semibold">Summary Judgement</h3>
                    <p className="text-xs mt-1 leading-relaxed">{preview.summary_judgement}</p>
                  </div>
                </div>
              </div>

              {/* Scorecard Table */}
              <div>
                <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                  Draft Report Scorecard
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="panel p-3 text-center">
                    <span className="text-2xl font-bold text-ink">
                      {preview.included_findings}
                    </span>
                    <span className="block text-xs text-muted mt-0.5">Included Findings</span>
                  </div>
                  <div className="panel p-3 text-center">
                    <span
                      className={`text-2xl font-bold ${
                        preview.blockers > 0 ? "text-red-500" : "text-ink"
                      }`}
                    >
                      {preview.blockers}
                    </span>
                    <span className="block text-xs text-muted mt-0.5">Blockers (Crit/High)</span>
                  </div>
                  <div className="panel p-3 text-center">
                    <span className="text-2xl font-bold text-ink">
                      {preview.counts_by_severity["CRITICAL"] ?? 0}
                    </span>
                    <span className="block text-xs text-muted mt-0.5">Critical</span>
                  </div>
                  <div className="panel p-3 text-center">
                    <span className="text-2xl font-bold text-ink">
                      {preview.counts_by_severity["HIGH"] ?? 0}
                    </span>
                    <span className="block text-xs text-muted mt-0.5">High</span>
                  </div>
                </div>
              </div>

              {/* Review Limits Notice */}
              <div className="p-3 bg-muted/10 rounded-md border border-line text-xs text-muted space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-ink">
                  <Shield size={14} className="text-sky-500" />
                  <span>Limits of this review</span>
                </div>
                <p>
                  Assesses internal consistency, technical terminology, document structure, references, and table calculations. It does not validate external-standard compliance or certify operational safety.
                </p>
              </div>

              {/* Export Buttons */}
              <div>
                <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                  Export Deliverables
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <a
                    href={getExportUrl(documentId, "docx")}
                    className="button button-primary flex items-center justify-center gap-2 py-2.5"
                    download
                  >
                    <Download size={16} />
                    <span>Download DOCX Report</span>
                  </a>
                  <a
                    href={getExportUrl(documentId, "pdf")}
                    className="button button-secondary flex items-center justify-center gap-2 py-2.5"
                    download
                  >
                    <FileText size={16} />
                    <span>Download Annotated PDF</span>
                  </a>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
