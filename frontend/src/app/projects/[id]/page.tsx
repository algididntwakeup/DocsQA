"use client";

import { AlertTriangle, ArrowLeft, MapPin, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getCurrentUser, listEngineers, listProjectDocuments, listProjects, uploadProjectDocument, type DocumentItem, type ManagedUser, type ProjectItem, type UserRole } from "@/lib/api";

const isProcessingStatus = (status: string) => status === "QUEUED" || status === "PROCESSING" || status === "ANALYZING";
import { ProjectDocumentTable } from "@/components/project/project-document-table";
import { useLocale } from "@/components/layout/locale-provider";

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [role, setRole] = useState<UserRole>("ENGINEER");
  const [currentUserId, setCurrentUserId] = useState<string>();
  const [engineers, setEngineers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{ engineerId?: string; sortBy: "date_desc" | "date_asc"; hasBlockers?: boolean }>({ sortBy: "date_desc" });
  const loadingRef = useRef(false);
  const { t } = useLocale();

  useEffect(() => {
    const timer = window.setTimeout(() => void params.then(({ id }) => setProjectId(id)), 0);
    return () => window.clearTimeout(timer);
  }, [params]);

  const load = useCallback(async () => {
    if (!projectId || loadingRef.current) return;
    loadingRef.current = true;
    try {
      setError(null);
      const user = await getCurrentUser();
      const [projects, result, activeEngineers] = await Promise.all([
        listProjects(), listProjectDocuments(projectId, filters),
        user.role === "LEAD_ENGINEER" || user.role === "SUPERUSER" ? listEngineers() : Promise.resolve([]),
      ]);
      setProject(projects.find((item) => item.id === projectId) ?? null);
      setDocuments(result.documents);
      setRole(user.role); setCurrentUserId(user.id); setEngineers(activeEngineers);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          window.location.replace("/login");
          return;
        }
      }
      setError(caught instanceof ApiError ? caught.message : t("couldNotLoadProjects"));
    } finally {
      loadingRef.current = false; setLoading(false);
    }
  }, [filters, projectId, t]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!documents.some((document) => isProcessingStatus(String(document.status)))) return;
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [documents, load]);


  async function upload(file: File) {
    if (!projectId) return;
    try {
      await uploadProjectDocument(projectId, file);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("uploadCouldNotComplete"));
    }
  }

  if (loading && !project) {
    return (
      <div className="py-4">
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-card p-12 text-muted-foreground">
          <RefreshCw className="animate-spin text-accent-foreground" size={24} />
          <span className="text-xs font-semibold">{t("loadingProjects")}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1 font-semibold text-accent-foreground hover:text-primary hover:underline"
        >
          <ArrowLeft size={13} />
            {t("projects")}
        </Link>
        <span>/</span>
        <span className="text-foreground truncate font-semibold">{project?.name ?? t("project")}</span>
      </nav>

      {/* Detail Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{t("inspectionRegister")}</p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-foreground">{project?.name ?? t("project")}</h1>
          <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin size={14} className="text-accent-foreground" />
            {project?.plant_area ?? t("areaNotSupplied")}
            {project?.code && ` · ${project.code}`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground shadow-sm hover:bg-muted/40 self-start sm:self-auto transition"
        >
          <RefreshCw size={13} />
          {t("refresh")}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800" role="alert">
          <AlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={() => void load()}
            className="font-bold underline hover:text-rose-950"
          >
            {t("retry")}
          </button>
        </div>
      )}

      <ProjectDocumentTable
        projectId={projectId ?? undefined}
        projectFinished={project?.status === "FINISHED"}
        documents={documents}
        role={role}
        currentUserId={currentUserId}
        engineers={engineers}
        loading={loading}
        onUpload={upload}
        onFiltersChange={setFilters}
        onChanged={load}
      />
    </div>
  );
}
