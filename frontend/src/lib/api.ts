import type { components } from "./api-schema";
import { setLastCorrelationId } from "./correlation";

export type DocumentItem = Omit<components["schemas"]["DocumentRead"], "workflow_status" | "project_finished"> & {
  workflow_status?: components["schemas"]["DocumentWorkflowStatus"];
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  assigned_to_email?: string | null;
  project_finished?: boolean;
  project_name?: string | null;
  project_plant?: string | null;
  uploaded_by_name?: string | null;
};
export interface AssignedProjectDocument {
  id: string;
  title: string;
  workflow_status: string;
}
export interface AssignedProject {
  id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  plant_area?: string | null;
  created_at?: string;
  total_documents?: number;
  status?: string;
  documents?: AssignedProjectDocument[];
}
export type DocumentList = components["schemas"]["DocumentListResponse"];
export type DocumentStatus = components["schemas"]["DocumentStatusResponse"];
export type DocumentUpload = components["schemas"]["DocumentUploadResponse"];
export type IssueItem = components["schemas"]["IssueRead"];
export type IssueList = components["schemas"]["IssueListResponse"];
export type IssueCuration = components["schemas"]["IssueCurationRequest"];
export type ReviewReportPreview = components["schemas"]["ReviewReportPreview"];
export type TraceabilitySummary = components["schemas"]["TraceabilitySummaryResponse"];

export type UserRole = "ENGINEER" | "LEAD_ENGINEER" | "SUPERUSER" | "HRGA" | "FINANCE";
export type ManagedRole = "ENGINEER" | "LEAD_ENGINEER";
export type ReportLanguage = "en" | "id";
export type HeaderPlacement = "split_standard" | "split_inverted" | "both_left" | "both_right";
export interface HeaderTemplateConfig {
  enabled: boolean;
  title: string;
  company_logo?: string | null;
  client_logo?: string | null;
  placement: HeaderPlacement;
  show_divider: boolean;
}
export interface UserSession {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  bima_id?: number | null;
  department?: string | null;
  position?: string | null;
}
export interface ProjectItem {
  id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  plant_area?: string | null;
  project_number?: string | null;
  client_name?: string | null;
  owner_id: string;
  owner_name?: string | null;
  total_documents?: number;
  status?: string;
  finished_at?: string | null;
  created_at: string;
  updated_at?: string | null;
  header_config?: HeaderTemplateConfig;
}
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserSession;
}
export interface CreateProjectPayload {
  name: string;
  plant_area?: string;
  code?: string;
  description?: string;
  project_number?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface UpdateProfilePayload { full_name: string; email: string }

export interface ManagedUser extends UserSession {
  total_documents_owned: number;
}

export interface PortfolioOwnerCount {
  owner_id: string;
  owner_name: string;
  project_count: number;
  document_count: number;
}

export interface PortfolioStats {
  total_projects: number;
  finished_projects: number;
  total_documents: number;
  documents_by_status: Record<string, number>;
  documents_by_workflow: Record<string, number>;
  projects_by_owner: PortfolioOwnerCount[];
}

export interface CreateManagedUserPayload {
  email: string;
  full_name: string;
  role: ManagedRole | "HRGA" | "FINANCE";
  temporary_password: string;
}

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const publicApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");
    if (publicApiBase) {
      return publicApiBase.endsWith("/api/v1") ? publicApiBase : `${publicApiBase}/api/v1`;
    }
    return "/api/v1";
  }

  const internal = process.env.INTERNAL_BACKEND_URL;
  if (internal) {
    return `${internal.replace(/\/+$/, "")}/api/v1`;
  }
  return "http://backend:8000/api/v1";
}

let memoryAuthToken: string | null = null;

function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]+)/);
  if (!match) return null;
  try {
    const val = decodeURIComponent(match[1]);
    return val.startsWith("Bearer ") ? val.slice(7) : val;
  } catch {
    return null;
  }
}

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    try {
      const stored = sessionStorage.getItem("prism_auth_token") || localStorage.getItem("prism_auth_token");
      if (stored) return stored;
    } catch {
      // Ignore storage errors in restricted environments
    }
    const fromCookie = getTokenFromCookie();
    if (fromCookie) return fromCookie;
  }
  return memoryAuthToken;
}

export function setAuthToken(token: string | null): void {
  memoryAuthToken = token;
  if (typeof window !== "undefined") {
    try {
      if (token) {
        sessionStorage.setItem("prism_auth_token", token);
        localStorage.setItem("prism_auth_token", token);
        document.cookie = `access_token=Bearer ${encodeURIComponent(token)}; path=/; max-age=86400; SameSite=Lax`;
      } else {
        sessionStorage.removeItem("prism_auth_token");
        localStorage.removeItem("prism_auth_token");
        document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
      }
    } catch {
      // Ignore storage errors in restricted environments
    }
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly correlationId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  let correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  setLastCorrelationId(correlationId ?? null);
  if (response.status === 401 && typeof window !== "undefined") {
    setAuthToken(null);
    const currentPath = window.location.pathname;
    if (currentPath !== "/login" && !currentPath.startsWith("/auth/sso")) {
      window.location.replace("/login");
    }
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    let code: string | undefined;
    try {
      const problem = (await response.json()) as {
        detail?: string | { message?: string };
        code?: string;
        error_code?: string;
        message?: string;
        correlation_id?: string;
      };
      message = typeof problem.detail === "string" ? problem.detail : problem.detail?.message ?? message;
      message = problem.message ?? message;
      code = problem.code ?? problem.error_code;
      correlationId ??= problem.correlation_id;
    } catch {
      // Keep fallback
    }
    setLastCorrelationId(correlationId ?? null);
    throw new ApiError(message, response.status, code, correlationId);
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, init);
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await request<LoginResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (res?.access_token) {
    setAuthToken(res.access_token);
  }
  return res;
}

export async function exchangeSsoToken(token: string): Promise<LoginResponse> {
  const res = await request<LoginResponse>("/auth/sso/exchange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (res?.access_token) setAuthToken(res.access_token);
  return res;
}

export async function logout(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST" });
  } finally {
    setAuthToken(null);
  }
  if (typeof window !== "undefined") window.location.pathname = "/login";
}

export function getCurrentUser(): Promise<UserSession> {
  return request<UserSession>("/auth/me", { cache: "no-store" });
}

export function updateProfile(payload: UpdateProfilePayload): Promise<UserSession> {
  return request<UserSession>("/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function changePassword(payload: ChangePasswordPayload): Promise<UserSession> {
  return request<UserSession>("/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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

export function updateManagedUserSuperuser(userId: string, isSuperuser: boolean): Promise<ManagedUser> {
  return request<ManagedUser>(`/auth/users/${encodeURIComponent(userId)}/superuser`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_superuser: isSuperuser }),
  });
}

export function fetchPortfolioStats(): Promise<PortfolioStats> {
  return request<PortfolioStats>("/projects/stats", { cache: "no-store" });
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

export function updateProjectHeaderConfig(projectId: string, headerConfig: HeaderTemplateConfig): Promise<ProjectItem> {
  return request<ProjectItem>(`/projects/${encodeURIComponent(projectId)}/header-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ header_config: headerConfig }),
  });
}

export function listProjectsForUser(userId: string): Promise<AssignedProject[]> {
  return request<AssignedProject[]>(`/auth/users/${encodeURIComponent(userId)}/projects`, { cache: "no-store" });
}

export function listEngineers(): Promise<ManagedUser[]> {
  return listManagedUsers().then((users) => users.filter((user) => user.role === "ENGINEER" && user.is_active));
}

export function claimDocument(documentId: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(documentId)}/claim`, { method: "POST" });
}

export function assignDocument(
  documentId: string,
  engineerId: string | null,
  overrideWip = false,
): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(documentId)}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ engineer_id: engineerId, override_wip: overrideWip }),
  });
}

export function createProject(payload: CreateProjectPayload): Promise<ProjectItem> {
  return request<ProjectItem>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
export function finishProject(projectId: string): Promise<ProjectItem> {
  return request<ProjectItem>(`/projects/${encodeURIComponent(projectId)}/finish`, {
    method: "POST",
  });
}

export function deleteProject(projectId: string): Promise<void> {
  return request<void>(`/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
}

export function listProjectDocuments(
  projectId: string,
  options: {
    engineerId?: string;
    sortBy?: "date_desc" | "date_asc";
    hasBlockers?: boolean;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<DocumentList> {
  const params = new URLSearchParams({
    sort_by: options.sortBy ?? "date_desc",
    page: String(options.page ?? 1),
    page_size: String(options.pageSize ?? 20),
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

export interface DocumentListFilters {
  projectId?: string;
  assignedToId?: string;
  workflowStatus?: string;
  page?: number;
  pageSize?: number;
}

export function listDocuments(filters: DocumentListFilters = {}): Promise<DocumentList> {
  const params = new URLSearchParams({
    page: String(filters.page ?? 1),
    page_size: String(filters.pageSize ?? 20),
  });
  if (filters.projectId) params.set("project_id", filters.projectId);
  if (filters.assignedToId) params.set("assigned_to_id", filters.assignedToId);
  if (filters.workflowStatus) params.set("workflow_status", filters.workflowStatus);
  return request<DocumentList>(`/documents?${params.toString()}`, { cache: "no-store" });
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
  return request<DocumentStatus>(`/documents/${encodeURIComponent(id)}/status`, {
    cache: "no-store",
  });
}

export function retryDocumentAnalysis(id: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/documents/${encodeURIComponent(id)}/retry`, {
    method: "POST",
  });
}

export function uploadDocument(file: File): Promise<DocumentUpload> {
  const body = new FormData();
  body.append("file", file);
  return request<DocumentUpload>("/documents/upload", { method: "POST", body });
}

export function getPdfUrl(id: string): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(id)}/pdf`;
}

export function getFileUrl(id: string): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(id)}/file`;
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


export function curateIssue(issueId: string, payload: IssueCuration): Promise<IssueItem> {
  return request<IssueItem>(`/issues/${encodeURIComponent(issueId)}/curation`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getReportPreview(documentId: string, language: ReportLanguage = "en"): Promise<ReviewReportPreview> {
  return request<ReviewReportPreview>(`/documents/${encodeURIComponent(documentId)}/report?language=${language}`, { cache: "no-store" });
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

export type ExportFormat = "pdf" | "docx" | "annotated_pdf";

export function getExportUrl(
  documentId: string,
  format: ExportFormat,
  includeMinors = false,
  language: ReportLanguage = "en",
  includeLanguageMechanics = false,
): string {
  const params = new URLSearchParams({ format, lang: language });
  if (includeMinors) params.set("include_minors", "true");
  params.set("include_language_mechanics", String(includeLanguageMechanics));
  params.set("language", language);
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/export?${params.toString()}`;
}

export async function downloadDocumentReport(
  documentId: string,
  format: ExportFormat,
  language: ReportLanguage = "en",
  includeMinors = false,
  includeLanguageMechanics = false,
): Promise<void> {
  const label =
    format === "pdf"
      ? "PDF review report"
      : format === "docx"
      ? "DOCX review report"
      : "annotated source PDF";
  const url = getExportUrl(
    documentId,
    format,
    includeMinors,
    language,
    includeLanguageMechanics,
  );
  const response = await fetch(url, {
    credentials: "include",
  });
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  setLastCorrelationId(correlationId ?? null);
  if (!response.ok) {
    throw new ApiError(`Export of ${label} failed (${response.status}).`, response.status, undefined, correlationId);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename =
    disposition.match(/filename="?([^";]+)"?/i)?.[1] ??
    `document-review.${format === "annotated_pdf" ? "pdf" : format}`;
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
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
  let stopped = false;
  let eventSource: EventSource | undefined;
  let reconnectTimer: number | undefined;
  let attempts = 0;

  const connect = () => {
    if (stopped) return;
    eventSource = new EventSource(url, { withCredentials: true });
    eventSource.addEventListener("progress", (e) => {
      try { onProgress(JSON.parse(e.data) as DocumentProgressEvent); } catch { /* Ignore malformed progress message */ }
    });
    eventSource.addEventListener("close", () => {
      eventSource?.close();
      onClose?.();
    });
    eventSource.onerror = (err) => {
      onError?.(err);
      eventSource?.close();
      if (stopped || attempts >= 5) {
        onClose?.();
        return;
      }
      const delay = Math.min(30_000, 1_000 * 2 ** attempts++);
      reconnectTimer = window.setTimeout(connect, delay);
    };
  };
  connect();
  return () => {
    stopped = true;
    if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    eventSource?.close();
  };
}
