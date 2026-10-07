import type { ProjectItem } from "@/lib/api";

export interface Project extends ProjectItem {
  project_number?: string | null;
  client_name?: string | null;
  documents_count?: number;
  updated_at?: string | null;
}

export type ProjectViewMode = "grid" | "table";
export type ProjectSortField = "name" | "project_number" | "client_name" | "documents_count" | "updated_at";
export interface BimaProject {
  id: number;
  number: string;
  name: string;
  client_name: string;
  is_imported: boolean;
  prism_project_id?: string | null;
}

export interface ImportBimaPayload {
  bima_project_id: number;
}
