import type { components } from "./api-schema";

export type DocumentItem = components["schemas"]["DocumentRead"];
export type DocumentList = components["schemas"]["DocumentListResponse"];
export type DocumentStatus = components["schemas"]["DocumentStatusResponse"];
export type DocumentUpload = components["schemas"]["DocumentUploadResponse"];

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    let code: string | undefined;
    try {
      const problem = (await response.json()) as { detail?: string; code?: string };
      message = problem.detail ?? message;
      code = problem.code;
    } catch {
      // Keep the safe fallback for a non-JSON upstream error.
    }
    throw new ApiError(message, response.status, code);
  }
  return (await response.json()) as T;
}

export function listDocuments(): Promise<DocumentList> {
  return request<DocumentList>("/documents?page=1&page_size=100", { cache: "no-store" });
}

export function getDocument(id: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(id)}`, { cache: "no-store" });
}

export function getDocumentStatus(id: string): Promise<DocumentStatus> {
  return request<DocumentStatus>(`/documents/${encodeURIComponent(id)}/status`, { cache: "no-store" });
}

export function uploadDocument(file: File): Promise<DocumentUpload> {
  const body = new FormData();
  body.append("file", file);
  return request<DocumentUpload>("/documents/upload", { method: "POST", body });
}
