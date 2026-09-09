import { toast } from "sonner";
import { getExportUrl, type ExportFormat } from "./api";

export async function downloadExport(
  documentId: string,
  format: ExportFormat,
  includeMinors = false,
): Promise<void> {
  const label = format === "docx" ? "DOCX report" : "annotated PDF";
  const toastId = toast.loading(`Generating ${label}...`);
  try {
    const response = await fetch(getExportUrl(documentId, format, includeMinors), {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Export failed (${response.status}).`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? `document-review.${format}`;
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
