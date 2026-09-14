import { toast } from "sonner";
import { getExportUrl, type ExportFormat, type ReportLanguage } from "./api";

export async function downloadExport(
  documentId: string,
  format: ExportFormat,
  includeMinors = false,
  language: ReportLanguage = "en",
): Promise<void> {
  const label =
    format === "pdf"
      ? "PDF review report"
      : format === "docx"
      ? "DOCX review report"
      : "annotated PDF";
  const toastId = toast.loading(`Generating ${label}...`);
  try {
    const response = await fetch(getExportUrl(documentId, format, includeMinors, language), {
      credentials: "include",
    });
    if (!response.ok) {
      let detail = `Export failed (${response.status}).`;
      try {
        const errorJson = await response.json();
        if (errorJson?.detail) {
          detail = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use default detail
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename =
      disposition.match(/filename="?([^";]+)"?/i)?.[1] ??
      `document-review.${format === "annotated_pdf" ? "pdf" : format}`;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast.success(`${label} ready`, { id: toastId });
  } catch (error) {
    toast.error(error instanceof Error ? error.message : `Could not generate ${label}.`, { id: toastId });
  }
}
