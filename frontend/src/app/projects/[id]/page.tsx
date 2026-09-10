"use client";

import { AlertTriangle, ArrowLeft, MapPin, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getCurrentUser, listProjectDocuments, listProjects, uploadProjectDocument, type DocumentItem, type ProjectItem, type UserRole } from "@/lib/api";
import { ProjectDocumentTable } from "@/components/project/project-document-table";

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [role, setRole] = useState<UserRole>("ENGINEER");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{ engineerId?: string; sortBy: "date_desc" | "date_asc"; hasBlockers?: boolean }>({ sortBy: "date_desc" });
  useEffect(() => { const timer = window.setTimeout(() => void params.then(({ id }) => setProjectId(id)), 0); return () => window.clearTimeout(timer); }, [params]);
  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setError(null);
      const [projects, result, user] = await Promise.all([listProjects(), listProjectDocuments(projectId, filters), getCurrentUser()]);
      setProject(projects.find((item) => item.id === projectId) ?? null);
      setDocuments(result.documents);
      setRole(user.role);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not load project details."); } finally { setLoading(false); }
  }, [filters, projectId]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  async function upload(file: File) {
    if (!projectId) return;
    try { await uploadProjectDocument(projectId, file); await load(); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Upload failed."); }
  }
  if (loading && !project) return <div className="panel loading-state">Loading project...</div>;
  return <><Link className="back-link" href="/projects"><ArrowLeft size={14} />Back to projects</Link><div className="page-heading"><div><p className="eyebrow">Project document control</p><h1>{project?.name ?? "Project"}</h1><p className="flex items-center gap-2"><MapPin size={14} />{project?.plant_area ?? "Area not supplied"}{project?.code && ` · ${project.code}`}</p></div><button className="button button-secondary" type="button" onClick={() => void load()}><RefreshCw size={15} />Refresh</button></div>{error && <div className="alert alert-error" role="alert"><AlertTriangle size={16} /><span>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}<ProjectDocumentTable documents={documents} role={role} loading={loading} onUpload={upload} onFiltersChange={setFilters} /></>;
}
