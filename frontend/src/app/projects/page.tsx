"use client";

import { AlertTriangle, CloudDownload, FolderKanban, LoaderCircle, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, createProject, deleteProject, finishProject, getCurrentUser, listProjectDocuments, listProjects, syncBimaProjects, type ProjectItem } from "@/lib/api";
import { ProjectCard } from "@/components/project/project-card";
import { useLocale } from "@/components/layout/locale-provider";
import { ImportBimaModal } from "@/components/projects/import-bima-modal";

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
  const [syncing, setSyncing] = useState(false);
  const { t } = useLocale();

  const load = useCallback(async () => {
    try {
      setError(null);
      const next = await listProjects();
      setProjects(next);
      const current = await getCurrentUser();
      setCanCreateProject(current.role === "LEAD_ENGINEER" || current.role === "SUPERUSER");
      setCurrentRole(current.role);
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
      if (caught instanceof ApiError && caught.status === 401) {
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          window.location.replace("/login");
          return;
        }
      }
      setError(caught instanceof ApiError ? caught.message : t("couldNotLoadProjects"));
    } finally {
      setLoading(false);
    }
  }, [t]);

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
       setError(caught instanceof ApiError ? caught.message : t("couldNotCreateProject"));
    } finally {
      setCreating(false);
    }
  }

  async function handleFinish(projectId: string) {
    if (!window.confirm(t("finishProjectConfirm"))) return;
    try {
      await finishProject(projectId);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotFinishProject"));
    }
  }

  async function handleDelete(projectId: string) {
    if (!window.confirm(t("deleteProjectConfirm"))) return;
    try {
      await deleteProject(projectId);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotDeleteProject"));
    }
  }

  async function handleBimaSync() {
    setSyncing(true);
    try {
      await syncBimaProjects();
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotSyncProjects"));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Heading */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{t("portfolioOverview")}</p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-foreground">{t("projectsPlants")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("projectDescription")}</p>
        </div>
        <div className="flex flex-wrap gap-2 self-start sm:self-auto">
          <ImportBimaModal onImported={() => void load()} />
          {canCreateProject && (
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:opacity-50"
              type="button"
              onClick={() => setModalOpen(true)}
              disabled={syncing}
            >
              <Plus size={16} />
              {t("createProject")}
            </button>
          )}
          {canCreateProject && (
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-primary/20 bg-accent px-4 py-2.5 text-xs font-bold text-accent-foreground transition hover:bg-accent/80 disabled:opacity-50"
              type="button"
              onClick={() => void handleBimaSync()}
              disabled={syncing}
            >
              <CloudDownload size={16} />
              {syncing ? t("syncing") : t("syncProjects")}
            </button>
          )}
        </div>
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
             {t("retry")}
          </button>
        </div>
      )}

      {/* Grid Content */}
      {loading ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-card/50 p-12 text-muted-foreground">
          <LoaderCircle className="animate-spin text-accent-foreground" size={28} />
          <span className="text-sm font-medium">{t("loadingProjects")}</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-card p-12 text-center text-muted-foreground shadow-sm">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            <FolderKanban size={24} />
          </div>
          <h2 className="text-base font-bold text-foreground">{t("noProjects")}</h2>
          <p className="max-w-md text-xs text-muted-foreground">{t("noProjectsDescription")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              documentCount={counts[project.id] ?? 0}
              verifiedCount={verifiedCounts[project.id] ?? 0}
              canManage={currentRole === "LEAD_ENGINEER" || currentRole === "SUPERUSER"}
              onFinish={handleFinish}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
      {/* Modal Create Project */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs">
          <form className="w-full max-w-md rounded-xl border border-border/60 bg-card p-6 shadow-2xl" onSubmit={submitProject}>
            <div className="flex items-start justify-between border-b border-border/60 pb-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">{t("projectSetup")}</p>
                <h2 className="text-lg font-bold text-foreground">{t("newProject")}</h2>
              </div>
              <button
                type="button"
                 aria-label={t("close")}
                onClick={() => setModalOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <label className="block text-xs font-bold text-foreground">
                 {t("projectName")}
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Central Gas Plant Phase II"
                  className="mt-1 h-10 w-full rounded-lg border border-border px-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
                />
              </label>

              <label className="block text-xs font-bold text-foreground">
                 {t("plantArea")}
                <input
                  value={area}
                  onChange={(event) => setArea(event.target.value)}
                  placeholder="e.g. Compressor Station Area 3"
                  className="mt-1 h-10 w-full rounded-lg border border-border px-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
                />
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-border/60 pt-4">
              <button
                type="button"
                className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted/40"
                onClick={() => setModalOpen(false)}
              >
                 {t("cancel")}
              </button>
              <button
                className="rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
                disabled={creating}
              >
                 {creating ? t("creating") : t("createProject")}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
