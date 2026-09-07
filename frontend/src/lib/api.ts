import type { components } from "./api-schema";

export type DocumentItem = components["schemas"]["DocumentRead"];
export type DocumentList = components["schemas"]["DocumentListResponse"];
export type DocumentStatus = components["schemas"]["DocumentStatusResponse"];
export type DocumentUpload = components["schemas"]["DocumentUploadResponse"];
export type IssueItem = components["schemas"]["IssueRead"];
export type IssueList = components["schemas"]["IssueListResponse"];
export type IssueDecision = components["schemas"]["IssueDecisionRequest"];
export type IssueDisposition = components["schemas"]["IssueDispositionRequest"];
export type BulkDecision = components["schemas"]["BulkDecisionRequest"];
export type BulkDecisionResult = components["schemas"]["BulkDecisionResponse"];
export type DocumentDisposition = components["schemas"]["DocumentDispositionRequest"];
export type AuditEventItem = components["schemas"]["AuditEventRead"];
export type AuditEventList = components["schemas"]["AuditEventListResponse"];
export type TraceabilitySummary = components["schemas"]["TraceabilitySummaryResponse"];

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    // In browser: use relative /api/v1 to route through Next.js proxy rewrites
    // unless an explicit non-localhost base URL is provided.
    const custom = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (custom && !custom.includes("localhost:8000") && !custom.includes("127.0.0.1:8000")) {
      return custom.replace(/\/+$/, "");
    }
    return "/api/v1";
  }

  // In Node.js / SSR:
  const internal = process.env.INTERNAL_API_URL;
  if (internal) {
    return `${internal.replace(/\/+$/, "")}/api/v1`;
  }
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");
}


export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
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
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export function listDocuments(): Promise<DocumentList> {
  return request<DocumentList>("/documents?page=1&page_size=100", { cache: "no-store" });
}

export function getDocument(id: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(id)}`, { cache: "no-store" });
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function getDocumentStatus(id: string): Promise<DocumentStatus> {
  return request<DocumentStatus>(`/documents/${encodeURIComponent(id)}/status`, { cache: "no-store" });
}

export function uploadDocument(file: File): Promise<DocumentUpload> {
  const body = new FormData();
  body.append("file", file);
  return request<DocumentUpload>("/documents/upload", { method: "POST", body });
}

export function getPdfUrl(id: string): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(id)}/pdf`;
}

export function listDocumentIssues(
  id: string,
  category?: string,
  page = 1,
  pageSize = 100
): Promise<IssueList> {
  const categoryParam = category ? `&category=${encodeURIComponent(category)}` : "";
  return request<IssueList>(
    `/documents/${encodeURIComponent(id)}/issues?page=${page}&page_size=${pageSize}${categoryParam}`,
    { cache: "no-store" }
  );
}

export function decideIssue(issueId: string, payload: IssueDecision): Promise<IssueItem> {
  return request<IssueItem>(`/issues/${encodeURIComponent(issueId)}/decision`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function disposeIssue(issueId: string, payload: IssueDisposition): Promise<IssueItem> {
  return request<IssueItem>(`/issues/${encodeURIComponent(issueId)}/disposition`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function bulkDecideIssues(payload: BulkDecision): Promise<BulkDecisionResult> {
  return request<BulkDecisionResult>("/issues/bulk-decision", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function setDocumentDisposition(
  documentId: string,
  payload: DocumentDisposition
): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(documentId)}/disposition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listAuditEvents(documentId: string): Promise<AuditEventList> {
  return request<AuditEventList>(`/documents/${encodeURIComponent(documentId)}/audit-events`, {
    cache: "no-store",
  });
}

export function getTraceabilitySummary(documentId: string): Promise<TraceabilitySummary> {
  return request<TraceabilitySummary>(`/documents/${encodeURIComponent(documentId)}/traceability-summary`, {
    cache: "no-store",
  });
}

export function getIssueLocation(issue: IssueItem): {
  page_number?: number;
  bbox?: components["schemas"]["BoundingBox"];
} {
  const ev = issue.evidence;
  if (!ev) return {};
  if (ev.kind === "TABLE_MATH") {
    const loc = ev.total_location;
    return { page_number: loc.page_index + 1, bbox: loc };
  }
  if (ev.kind === "REFERENCE_DRIFT") {
    const loc = ev.entry_location;
    return { page_number: loc.page_index + 1, bbox: loc };
  }
  if (ev.kind === "REVISION") {
    const loc = ev.locations?.[0];
    return loc ? { page_number: loc.page_index + 1, bbox: loc } : {};
  }
  if (ev.kind === "STANDARD") {
    const loc = ev.body_location;
    return loc ? { page_number: loc.page_index + 1, bbox: loc } : {};
  }
  if (ev.kind === "LINGUISTIC") {
    const loc = ev.location;
    if (!loc) return {};
    if ("page_width" in loc) {
      return { page_number: loc.page_index + 1, bbox: loc };
    }
    return { page_number: loc.page_index + 1 };
  }
  return {};
}

export interface DictionaryTermItem {
  id: string;
  term: string;
  scope: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  rationale?: string | null;
  approved_at?: string | null;
  approved_by?: string | null;
  created_at: string;
}

export interface DictionaryTermList {
  terms: DictionaryTermItem[];
  page_info: {
    page: number;
    page_size: number;
    total: number;
  };
}

export interface DictionaryTermCreate {
  term: string;
  scope?: string;
  rationale?: string;
}

export interface DictionaryTermApproval {
  status: "APPROVED" | "REJECTED";
  rationale?: string;
}

export function listDictionaryTerms(
  scope?: string,
  status?: string,
  page = 1,
  pageSize = 50
): Promise<DictionaryTermList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (scope) params.append("scope", scope);
  if (status) params.append("status", status);
  return request<DictionaryTermList>(`/dictionary/terms?${params.toString()}`, {
    cache: "no-store",
  });
}

export function createDictionaryTerm(
  payload: DictionaryTermCreate
): Promise<DictionaryTermItem> {
  return request<DictionaryTermItem>("/dictionary/terms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function approveDictionaryTerm(
  termId: string,
  payload: DictionaryTermApproval
): Promise<DictionaryTermItem> {
  return request<DictionaryTermItem>(
    `/dictionary/terms/${encodeURIComponent(termId)}/approve`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export type ExportFormat = "pdf" | "xlsx" | "csv" | "json";

export function getExportUrl(documentId: string, format: ExportFormat): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/export?format=${format}`;
}

export interface DocumentProgressStage {
  name: string;
  status: string;
}

export interface DocumentProgressEvent {
  document_id: string;
  status: string;
  progress_pct: number;
  stages: DocumentProgressStage[];
}

export function subscribeDocumentEvents(
  documentId: string,
  onProgress: (event: DocumentProgressEvent) => void,
  onClose?: () => void,
  onError?: (err: Event) => void
): () => void {
  const url = `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/events`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("progress", (e) => {
    try {
      const data = JSON.parse(e.data) as DocumentProgressEvent;
      onProgress(data);
    } catch {
      // Ignore malformed progress message
    }
  });

  eventSource.addEventListener("close", () => {
    eventSource.close();
    onClose?.();
  });

  eventSource.onerror = (err) => {
    onError?.(err);
  };

  return () => {
    eventSource.close();
  };
}


