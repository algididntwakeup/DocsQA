import type { ProjectItem } from "@/lib/api";

export interface Project extends ProjectItem {
  documents_count?: number;
}

export type ProjectViewMode = "grid" | "table";
export type ProjectSortField = "name" | "project_number" | "client_name" | "documents_count" | "updated_at";

/** One row of the flat BIMA project catalog annotated with its local import state. */
export interface BimaCatalogItem {
  id: number;
  number: string;
  name: string;
  client_name: string | null;
  is_imported: boolean;
  prism_project_id: string | null;
  is_mine: boolean;
  bima_owner_known: boolean;
}

/** Payload for the on-demand import; the catalog row carries every field PRISM needs. */
export interface ImportBimaPayload {
  bima_project_id: number;
  project_number: string;
  name: string;
  client_name?: string | null;
}
