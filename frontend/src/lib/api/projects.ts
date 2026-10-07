import { apiRequest, type ProjectItem } from "@/lib/api";
import type { BimaProject, ImportBimaPayload } from "@/types/project";

interface BimaProjectsResponse {
  success: boolean;
  data: BimaProject[];
}

export async function fetchBimaProjects(): Promise<BimaProject[]> {
  const response = await apiRequest<BimaProjectsResponse>("/bima/projects", { cache: "no-store" });
  if (!response.success) {
    throw new Error("Gagal memuat daftar proyek BIMA.");
  }
  return response.data;
}

export function importBimaProject(payload: ImportBimaPayload): Promise<ProjectItem> {
  return apiRequest<ProjectItem>("/projects/import-bima", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
