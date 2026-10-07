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
