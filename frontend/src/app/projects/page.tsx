"use client";

import { AlertTriangle, FolderKanban, LoaderCircle, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError, listProjectDocuments, listProjects, type ProjectItem } from "@/lib/api";
import { ProjectCard } from "@/components/project/project-card";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      setError(null);
      const next = await listProjects();
      setProjects(next);
      const entries = await Promise.all(next.map(async (project) => [project.id, (await listProjectDocuments(project.id)).pagination.total] as const));
      setCounts(Object.fromEntries(entries));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load projects.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  return <><div className="page-heading"><div><p className="eyebrow">Portfolio overview</p><h1>Projects & plants</h1><p>Choose a project to review its controlled document register.</p></div><button className="button button-primary" type="button" disabled><Plus size={16} />New project</button></div>{error && <div className="alert alert-error" role="alert"><AlertTriangle size={16} /><span>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}{loading ? <div className="panel loading-state"><LoaderCircle className="mx-auto animate-spin" size={20} />Loading project register...</div> : projects.length === 0 ? <div className="panel empty-state"><FolderKanban className="mx-auto text-primary" size={34} /><h2>No projects assigned</h2><p>Projects become visible when documents are assigned to your account.</p></div> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{projects.map((project) => <ProjectCard key={project.id} project={project} documentCount={counts[project.id] ?? 0} />)}</div>}</>;
}
