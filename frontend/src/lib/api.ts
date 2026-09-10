import type { components } from "./api-schema";

export type DocumentItem = Omit<components["schemas"]["DocumentRead"], "workflow_status"> & {
  workflow_status?: components["schemas"]["DocumentWorkflowStatus"];
};
export type DocumentList = components["schemas"]["DocumentListResponse"];
export type DocumentStatus = components["schemas"]["DocumentStatusResponse"];
export type DocumentUpload = components["schemas"]["DocumentUploadResponse"];
export type IssueItem = components["schemas"]["IssueRead"];
export type IssueList = components["schemas"]["IssueListResponse"];
export type IssueCuration = components["schemas"]["IssueCurationRequest"];
export type ReviewReportPreview = components["schemas"]["ReviewReportPreview"];
export type TraceabilitySummary = components["schemas"]["TraceabilitySummaryResponse"];

export type UserRole = "ENGINEER" | "LEAD_ENGINEER" | "SUPERUSER";
export interface UserSession {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserSession;
}
export interface ProjectItem {
  id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  plant_area?: string | null;
  created_by_id: string;
  created_at: string;
}

export interface CreateProjectPayload {
  name: string;
  plant_area?: string;
  code?: string;
  description?: string;
}

export interface ManagedUser extends UserSession {
  total_documents_owned: number;
}

export interface CreateManagedUserPayload {
  email: string;
  full_name: string;
  role: Exclude<UserRole, "SUPERUSER">;
  temporary_password: string;
}

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const custom = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (custom && !custom.includes("localhost:8000") && !custom.includes("127.0.0.1:8000")) {
      return custom.replace(/\/+$/, "");
    }
    return "/api/v1";
  }

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
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.pathname = "/login";
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    let code: string | undefined;
    try {
      const problem = (await response.json()) as { detail?: string; code?: string };
      message = problem.detail ?? message;
      code = problem.code;
    } catch {
      // Keep fallback
    }
    throw new ApiError(message, response.status, code);
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await request<void>("/auth/logout", { method: "POST" });
  if (typeof window !== "undefined") window.location.pathname = "/login";
}

export function getCurrentUser(): Promise<UserSession> {
  return request<UserSession>("/auth/me", { cache: "no-store" });
}

export function listManagedUsers(): Promise<ManagedUser[]> {
  return request<ManagedUser[]>("/auth/users", { cache: "no-store" });
}

export function createManagedUser(payload: CreateManagedUserPayload): Promise<ManagedUser> {
  return request<ManagedUser>("/auth/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateManagedUserStatus(userId: string, isActive: boolean): Promise<ManagedUser> {
  return request<ManagedUser>(`/auth/users/${encodeURIComponent(userId)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
}

export function resetManagedUserPassword(userId: string, temporaryPassword: string): Promise<ManagedUser> {
  return request<ManagedUser>(`/auth/users/${encodeURIComponent(userId)}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temporary_password: temporaryPassword }),
  });
}

export function listProjects(): Promise<ProjectItem[]> {
  return request<ProjectItem[]>("/projects", { cache: "no-store" });
}

export function createProject(payload: CreateProjectPayload): Promise<ProjectItem> {
  return request<ProjectItem>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listProjectDocuments(
  projectId: string,
  options: { engineerId?: string; sortBy?: "date_desc" | "date_asc"; hasBlockers?: boolean } = {},
): Promise<DocumentList> {
  const params = new URLSearchParams({
    sort_by: options.sortBy ?? "date_desc",
    page: "1",
    page_size: "100",
  });
  if (options.engineerId) params.set("engineer_id", options.engineerId);
  if (options.hasBlockers !== undefined) params.set("has_blockers", String(options.hasBlockers));
  return request<DocumentList>(`/projects/${encodeURIComponent(projectId)}/documents?${params}`, {
    cache: "no-store",
  });
}

export function uploadProjectDocument(projectId: string, file: File): Promise<DocumentUpload> {
  const body = new FormData();
  body.append("file", file);
  return request<DocumentUpload>(`/projects/${encodeURIComponent(projectId)}/documents/upload`, {
    method: "POST",
    body,
  });
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

export async function listAllDocumentIssues(id: string): Promise<IssueItem[]> {
  const first = await listDocumentIssues(id, undefined, 1, 100);
  if (first.pagination.total <= first.issues.length) return first.issues;
  const pageCount = Math.ceil(first.pagination.total / 100);
  const rest = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      listDocumentIssues(id, undefined, index + 2, 100)
    )
  );
  return [first.issues, ...rest.map((page) => page.issues)].flat();
}

export function curateIssue(issueId: string, payload: IssueCuration): Promise<IssueItem> {
  return request<IssueItem>(`/issues/${encodeURIComponent(issueId)}/curation`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getReportPreview(documentId: string): Promise<ReviewReportPreview> {
  return request<ReviewReportPreview>(`/documents/${encodeURIComponent(documentId)}/report`, {
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
  if (ev.kind === "LAYOUT") {
    return ev.bounding_box
      ? { page_number: ev.page_index + 1, bbox: ev.bounding_box }
      : { page_number: ev.page_index + 1 };
  }
  if (ev.kind === "BUDINSKI") {
    return ev.bounding_box
      ? { page_number: ev.bounding_box.page_index + 1, bbox: ev.bounding_box }
      : {};
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

export type ExportFormat = "pdf" | "docx";

export function getExportUrl(
  documentId: string,
  format: ExportFormat,
  includeMinors = false
): string {
  const minorParam = includeMinors ? "&include_minors=true" : "";
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/export?format=${format}${minorParam}`;
}

export interface DocumentProgressStage {
  name: string;
  status: string;
  progress_pct?: number;
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
  const eventSource = new EventSource(url, { withCredentials: true });

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
