"use client";

import { AlertTriangle, FolderKanban, LoaderCircle, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, createProject, getCurrentUser, listProjectDocuments, listProjects, type ProjectItem } from "@/lib/api";
import { ProjectCard } from "@/components/project/project-card";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
   const [canCreateProject, setCanCreateProject] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [area, setArea] = useState("");
  const [creating, setCreating] = useState(false);
  const [verifiedCounts, setVerifiedCounts] = useState<Record<string, number>>({});
  const load = useCallback(async () => {
    try {
      setError(null);
      const next = await listProjects();
       setProjects(next);
        await getCurrentUser();
        setCanCreateProject(true);
      const entries = await Promise.all(next.map(async (project) => [project.id, (await listProjectDocuments(project.id)).pagination.total] as const));
       setCounts(Object.fromEntries(entries));
       setVerifiedCounts(Object.fromEntries(await Promise.all(next.map(async (project) => [project.id, (await listProjectDocuments(project.id)).documents.filter((item) => item.workflow_status === "VERIFIED_BY_LEAD").length] as const))));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load projects.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  async function submitProject(event: FormEvent) { event.preventDefault(); if (!name.trim()) return; setCreating(true); try { await createProject({ name: name.trim(), plant_area: area.trim() || undefined }); setModalOpen(false); setName(""); setArea(""); await load(); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not create project."); } finally { setCreating(false); } }
  return <div className="rq-page"><div className="rq-page-heading"><div><p className="rq-kicker">Portfolio overview</p><h1>Projects & plants</h1><p>Choose a project to review its controlled document register.</p></div>{canCreateProject && <button className="rq-primary-button" type="button" onClick={() => setModalOpen(true)}><Plus size={17} />Create project</button>}</div>{error && <div className="rq-alert" role="alert"><AlertTriangle size={16} /><span>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}{loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={22} />Loading project register...</div> : projects.length === 0 ? <div className="rq-empty"><FolderKanban size={34} /><h2>No projects assigned</h2><p>Projects become visible when documents are assigned to your account.</p></div> : <div className="rq-project-grid">{projects.map((project) => <ProjectCard key={project.id} project={project} documentCount={counts[project.id] ?? 0} verifiedCount={verifiedCounts[project.id] ?? 0} />)}</div>}
    {modalOpen && <div className="rq-modal-backdrop"><form className="rq-modal" onSubmit={submitProject}><div className="rq-modal-header"><div><p className="rq-kicker">Project setup</p><h2>Create a new project</h2></div><button type="button" aria-label="Close" onClick={() => setModalOpen(false)}><X size={18} /></button></div><label>Project name<input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Central Gas Plant" /></label><label>Area<input value={area} onChange={(event) => setArea(event.target.value)} placeholder="Central Gas Plant" /></label><div className="rq-modal-actions"><button type="button" className="rq-secondary-button" onClick={() => setModalOpen(false)}>Cancel</button><button className="rq-primary-button" disabled={creating}>{creating ? "Creating..." : "Create project"}</button></div></form></div>}
  </div>;
}
