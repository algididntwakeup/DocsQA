"use client";

import { AlertTriangle, ArrowLeft, MapPin, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getCurrentUser, listEngineers, listProjectDocuments, listProjects, uploadProjectDocument, type DocumentItem, type ManagedUser, type ProjectItem, type UserRole } from "@/lib/api";
import { ProjectDocumentTable } from "@/components/project/project-document-table";

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

  useEffect(() => {
    const timer = window.setTimeout(() => void params.then(({ id }) => setProjectId(id)), 0);
    return () => window.clearTimeout(timer);
  }, [params]);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setError(null);
      const user = await getCurrentUser();
      const [projects, result, activeEngineers] = await Promise.all([
        listProjects(),
        listProjectDocuments(projectId, filters),
        user.role === "LEAD_ENGINEER" || user.role === "SUPERUSER" ? listEngineers() : Promise.resolve([]),
      ]);
      setProject(projects.find((item) => item.id === projectId) ?? null);
      setDocuments(result.documents);
      setRole(user.role);
      setCurrentUserId(user.id);
      setEngineers(activeEngineers);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load project details.");
    } finally {
      setLoading(false);
    }
  }, [filters, projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function upload(file: File) {
    if (!projectId) return;
    try {
      await uploadProjectDocument(projectId, file);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Upload failed.");
    }
  }

  if (loading && !project) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-slate-400">
          <RefreshCw className="animate-spin text-blue-600" size={24} />
          <span className="text-xs font-semibold">Loading project details...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 hover:underline"
        >
          <ArrowLeft size={13} />
          Projects
        </Link>
        <span>/</span>
        <span className="text-slate-800 truncate font-semibold">{project?.name ?? "Project"}</span>
      </nav>

      {/* Detail Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Document Inspection Register</p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{project?.name ?? "Project"}</h1>
          <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-slate-500">
            <MapPin size={14} className="text-blue-600" />
            {project?.plant_area ?? "Area not supplied"}
            {project?.code && ` · ${project.code}`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 self-start sm:self-auto transition"
        >
          <RefreshCw size={13} />
          Refresh
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
            Retry
          </button>
        </div>
      )}

      <ProjectDocumentTable
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
