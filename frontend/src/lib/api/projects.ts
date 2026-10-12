import { apiRequest, type ProjectItem } from "@/lib/api";
import type { BimaProject, ImportBimaPayload } from "@/types/project";

export function fetchBimaProjects(): Promise<BimaProject[]> {
  return apiRequest<BimaProject[]>("/bima/catalog", { cache: "no-store" });
}

export function importBimaProject(payload: ImportBimaPayload): Promise<ProjectItem> {
  return apiRequest<ProjectItem>("/projects/import-bima", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
