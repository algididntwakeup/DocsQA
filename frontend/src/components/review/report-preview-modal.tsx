"use client";
import { useEffect, useState } from "react";
import { AlertOctagon, CheckCircle2, Download, FileCheck2, FileText, Shield, X } from "lucide-react";
import { getReportPreview, type ReviewReportPreview } from "@/lib/api";
import { downloadExport } from "@/lib/download";
import { useLocale } from "@/components/layout/locale-provider";
interface ReportPreviewModalProps { documentId: string; documentFilename: string; isOpen: boolean; onClose: () => void; }
export function ReportPreviewModal({ documentId, documentFilename, isOpen, onClose }: ReportPreviewModalProps) {
  const { locale, t } = useLocale();
  const [preview, setPreview] = useState<ReviewReportPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    queueMicrotask(() => { if (active) setIsLoading(true); });
    getReportPreview(documentId, locale).then((data) => { if (active) { setPreview(data); setError(null); setIsLoading(false); } }).catch((caught: unknown) => { if (active) { setError(caught instanceof Error ? caught.message : t("reportError")); setIsLoading(false); } });
    return () => { active = false; };
  }, [documentId, isOpen, locale, t]);
  useEffect(() => { const handleKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape" && isOpen) onClose(); }; window.addEventListener("keydown", handleKeyDown); return () => window.removeEventListener("keydown", handleKeyDown); }, [isOpen, onClose]);
  if (!isOpen) return null;
  return <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="report-preview-title"><div className="modal-container max-w-2xl" onClick={(event) => event.stopPropagation()}>
    <header className="modal-header"><div className="flex items-center gap-2"><FileCheck2 size={20} className="text-sky-500" /><div><h2 id="report-preview-title" className="text-base font-semibold text-ink">{t("reportPreview")}</h2><p className="text-xs text-muted">Deterministic engineering review composition for {documentFilename}</p></div></div><button type="button" className="icon-button text-muted" onClick={onClose} aria-label="Close report preview"><X size={16} /></button></header>
    <div className="modal-body p-5 space-y-5">{isLoading ? <div className="py-12 text-center text-muted space-y-2"><div className="animate-spin inline-block w-6 h-6 border-2 border-current border-t-transparent rounded-full" /><p className="text-sm">{locale === "en" ? "Calculating report composition..." : t("loadingReport")}</p></div> : error ? <div className="alert alert-error" role="alert">{error}</div> : preview ? <>
      <div className={`p-4 rounded-lg border ${preview.blockers > 0 ? "bg-amber-500/10 border-amber-500/30" : "bg-emerald-500/10 border-emerald-500/30"}`}><div className="flex items-start gap-3">{preview.blockers > 0 ? <AlertOctagon size={20} className="text-amber-500" /> : <CheckCircle2 size={20} className="text-emerald-500" />}<div><h3 className="text-sm font-semibold">{t("summaryJudgement")}</h3><p className="text-xs mt-1 leading-relaxed">{preview.summary_judgement}</p></div></div></div>
      <div><h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Draft Report Scorecard</h3><div className="grid grid-cols-2 sm:grid-cols-4 gap-3"><div className="panel p-3 text-center"><span className="text-2xl font-bold text-ink">{preview.included_findings}</span><span className="block text-xs text-muted mt-0.5">{t("included")} {t("findings")}</span></div><div className="panel p-3 text-center"><span className="text-2xl font-bold text-ink">{preview.blockers}</span><span className="block text-xs text-muted mt-0.5">{t("blockers")}</span></div><div className="panel p-3 text-center"><span className="text-2xl font-bold text-ink">{preview.counts_by_severity.CRITICAL ?? 0}</span><span className="block text-xs text-muted mt-0.5">{t("severityCritical")}</span></div><div className="panel p-3 text-center"><span className="text-2xl font-bold text-ink">{preview.counts_by_severity.HIGH ?? 0}</span><span className="block text-xs text-muted mt-0.5">{t("severityHigh")}</span></div></div></div>
      <div className="p-3 bg-muted/10 rounded-md border border-line text-xs text-muted space-y-1"><div className="flex items-center gap-1.5 font-medium text-ink"><Shield size={14} className="text-sky-500" /><span>Limits of this review</span></div><p>Assesses internal consistency, technical terminology, document structure, references, and table calculations. It does not validate external-standard compliance or certify operational safety.</p></div>
      <div><h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Export Deliverables</h3><div className="grid grid-cols-1 sm:grid-cols-2 gap-3"><button type="button" className="button button-primary flex items-center justify-center gap-2 py-2.5" onClick={() => void downloadExport(documentId, "docx", false, locale)}><Download size={16} /><span>{t("downloadDocx")}</span></button><button type="button" className="button button-secondary flex items-center justify-center gap-2 py-2.5" onClick={() => void downloadExport(documentId, "pdf")}><FileText size={16} /><span>{t("downloadPdf")}</span></button></div></div>
    </> : null}</div>
  </div></div>;
}
