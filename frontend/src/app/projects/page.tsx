"use client";

import { AlertTriangle, FolderKanban, LoaderCircle, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, assignProject, createProject, getCurrentUser, listManagedUsers, listProjectDocuments, listProjects, type ManagedUser, type ProjectItem } from "@/lib/api";
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
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [engineers, setEngineers] = useState<ManagedUser[]>([]);

  const load = useCallback(async () => {
    try {
      setError(null);
      const next = await listProjects();
      setProjects(next);
      const current = await getCurrentUser();
      setCanCreateProject(true);
      setCurrentRole(current.role);
      if (current.role === "LEAD_ENGINEER" || current.role === "SUPERUSER") {
        setEngineers(await listManagedUsers());
      }
      const entries = await Promise.all(
        next.map(async (project) => [project.id, (await listProjectDocuments(project.id)).pagination.total] as const)
      );
      setCounts(Object.fromEntries(entries));
      setVerifiedCounts(
        Object.fromEntries(
          await Promise.all(
            next.map(
              async (project) =>
                [
                  project.id,
                  (await listProjectDocuments(project.id)).documents.filter((item) => item.workflow_status === "VERIFIED_BY_LEAD").length,
                ] as const
            )
          )
        )
      );
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load projects.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function submitProject(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createProject({ name: name.trim(), plant_area: area.trim() || undefined });
      setModalOpen(false);
      setName("");
      setArea("");
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create project.");
    } finally {
      setCreating(false);
    }
  }

  async function handleAssign(projectId: string, userId: string | null) {
    try {
      await assignProject(projectId, userId);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not assign project.");
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8">
      {/* Page Heading */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Portfolio Overview</p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Projects & Plants</h1>
          <p className="mt-1 text-sm text-slate-600">Choose a project to inspect and curate its controlled document register.</p>
        </div>
        {canCreateProject && (
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-blue-700 self-start sm:self-auto"
            type="button"
            onClick={() => setModalOpen(true)}
          >
            <Plus size={16} />
            Create Project
          </button>
        )}
      </div>

      {/* Error Alert */}
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

      {/* Grid Content */}
      {loading ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white/50 p-12 text-slate-400">
          <LoaderCircle className="animate-spin text-blue-600" size={28} />
          <span className="text-sm font-medium">Loading project portfolio...</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center text-slate-500 shadow-xs">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <FolderKanban size={24} />
          </div>
          <h2 className="text-base font-bold text-slate-900">No Projects Found</h2>
          <p className="max-w-md text-xs text-slate-500">Projects will appear once assigned or created by your engineering team lead.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              documentCount={counts[project.id] ?? 0}
              verifiedCount={verifiedCounts[project.id] ?? 0}
              canAssign={currentRole === "LEAD_ENGINEER" || currentRole === "SUPERUSER"}
              engineers={engineers}
              onAssign={handleAssign}
            />
          ))}
        </div>
      )}

      {/* Modal Create Project */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs">
          <form className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl" onSubmit={submitProject}>
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Project Setup</p>
                <h2 className="text-lg font-bold text-slate-900">Create a New Project</h2>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setModalOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <label className="block text-xs font-bold text-slate-700">
                Project Name
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Central Gas Plant Phase II"
                  className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs font-bold text-slate-700">
                Plant Area
                <input
                  value={area}
                  onChange={(event) => setArea(event.target.value)}
                  placeholder="e.g. Compressor Station Area 3"
                  className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
                />
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-4">
              <button
                type="button"
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => setModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50"
                disabled={creating}
              >
                {creating ? "Creating..." : "Create Project"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
