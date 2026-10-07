import type { ProjectItem } from "@/lib/api";

export interface Project extends ProjectItem {
  project_number?: string | null;
  client_name?: string | null;
  documents_count?: number;
  updated_at?: string | null;
}

export type ProjectViewMode = "grid" | "table";
export type ProjectSortField = "name" | "project_number" | "client_name" | "documents_count" | "updated_at";
