"use client";

import { AlertTriangle, FolderKanban, Plus, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { SortingState } from "@tanstack/react-table";
import { ApiError, createProject, deleteProject, finishProject, getCurrentUser, listProjectDocuments, listProjects, type UserRole } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";
import { canCreateAnyProject, canCreateProject, createPermissionMessage, createScopeHint, isPrivileged } from "@/lib/project-permissions";
import { ExplorerToolbar } from "@/components/projects/explorer-toolbar";
import { ProjectGridSkeleton, ProjectGridView } from "@/components/projects/project-grid-view";
import { ProjectTableSkeleton, ProjectTableView, useProjectTable } from "@/components/projects/project-table-view";
import { useViewMode } from "@/hooks/use-view-mode";
import type { Project, ProjectSortField } from "@/types/project";
import { ImportBimaModal } from "@/components/projects/import-bima-modal";

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [canOpenCreateModal, setCanOpenCreateModal] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [area, setArea] = useState("");
  const [projectNumber, setProjectNumber] = useState("");
  const [creating, setCreating] = useState(false);
  const [currentRole, setCurrentRole] = useState<UserRole | null>(null);
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "updated_at", desc: true }]);
  const [viewMode, setViewMode] = useViewMode();
  const { t } = useLocale();
  const canManage = isPrivileged(currentRole);
  const createAllowed = canCreateProject(currentRole, projectNumber);
  const createBlockedReason = createAllowed ? null : createPermissionMessage(projectNumber);
  const sortBy = (sorting[0]?.id ?? "updated_at") as ProjectSortField;
  const sortDirection = sorting[0]?.desc ? "desc" : "asc";

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase();
    return projects
      .map((project) => ({
        ...project,
        project_number: project.project_number ?? project.code ?? null,
        documents_count: counts[project.id] ?? project.documents_count ?? project.total_documents ?? 0,
      }))
      .filter((project) => {
        if (!query) return true;
        return [project.name, project.project_number ?? "", project.client_name ?? ""]
          .some((value) => value.toLowerCase().includes(query));
      });
  }, [counts, projects, search]);

  const projectTable = useProjectTable({
    projects: filteredProjects,
    sorting,
    onSortingChange: setSorting,
    canManage,
    onFinish: handleFinish,
    onDelete: handleDelete,
  });
  const sortedProjects = projectTable.getRowModel().rows.map((row) => row.original);

  const load = useCallback(async () => {
    try {
      setError(null);
      const next = await listProjects();
      setProjects(next);
      const current = await getCurrentUser();
      setCanOpenCreateModal(canCreateAnyProject(current.role));
      setCurrentRole(current.role);
      const entries = await Promise.all(
        next.map(async (project) => [project.id, (await listProjectDocuments(project.id)).pagination.total] as const)
      );
      setCounts(Object.fromEntries(entries));
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
    if (!createAllowed) {
      setError(createBlockedReason ?? t("couldNotCreateProject"));
      return;
    }
    setCreating(true);
    try {
      await createProject({
        name: name.trim(),
        plant_area: area.trim() || undefined,
        project_number: projectNumber.trim() || undefined,
      });
      setModalOpen(false);
      setName("");
      setArea("");
      setProjectNumber("");
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

  function handleSortByChange(field: ProjectSortField) {
    setSorting((current) => [{ id: field, desc: current[0]?.desc ?? true }]);
  }

  function toggleSortDirection() {
    setSorting((current) => [{ id: current[0]?.id ?? "updated_at", desc: !(current[0]?.desc ?? true) }]);
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
          {canOpenCreateModal && (
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:opacity-50"
              type="button"
              onClick={() => setModalOpen(true)}
              title={createScopeHint(currentRole)}
            >
              <Plus size={16} />
              {t("createProject")}
            </button>
          )}
        </div>
      </div>

      <ExplorerToolbar
        search={search}
        onSearchChange={setSearch}
        sortBy={sortBy}
        onSortByChange={handleSortByChange}
        sortDirection={sortDirection}
        onToggleSortDirection={toggleSortDirection}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        rightSlot={(
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ImportBimaModal onImported={() => void load()} role={currentRole} />
          </div>
        )}
      />

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

      {loading ? (
        viewMode === "grid" ? <ProjectGridSkeleton /> : <ProjectTableSkeleton />
      ) : projects.length === 0 ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-card p-12 text-center text-muted-foreground shadow-sm">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            <FolderKanban size={24} />
          </div>
          <h2 className="text-base font-bold text-foreground">{t("noProjects")}</h2>
          <p className="max-w-md text-xs text-muted-foreground">{t("noProjectsDescription")}</p>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <FolderKanban size={28} className="text-muted-foreground" />
          <p className="mt-3 text-sm font-semibold text-foreground">Tidak ada proyek yang cocok.</p>
          <p className="mt-1 max-w-sm text-xs text-muted-foreground">Ubah kata kunci pencarian atau bersihkan pencarian untuk melihat proyek lainnya.</p>
          <button type="button" onClick={() => setSearch("")} className="mt-4 rounded-lg border border-border px-3 py-2 text-xs font-semibold hover:bg-muted">
            Bersihkan pencarian
          </button>
        </div>
      ) : viewMode === "grid" ? (
        <ProjectGridView projects={sortedProjects} canManage={canManage} onFinish={handleFinish} onDelete={handleDelete} />
      ) : (
        <ProjectTableView table={projectTable} onOpen={(projectId) => router.push(`/workspace/${projectId}`)} />
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

              <label className="block text-xs font-bold text-foreground">
                Nomor Proyek
                <input
                  value={projectNumber}
                  onChange={(event) => setProjectNumber(event.target.value)}
                  placeholder="e.g. 13726486.01 (Engineering) / 03-2026-001 (Internal)"
                  className="mt-1 h-10 w-full rounded-lg border border-border px-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
                />
                <span className="mt-1 block text-[10px] font-medium text-muted-foreground">
                  {createScopeHint(currentRole)}
                </span>
              </label>
            </div>

            {!createAllowed && projectNumber.trim() !== "" && (
              <p role="alert" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] font-medium text-amber-800">
                {createBlockedReason}
              </p>
            )}

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
                disabled={creating || !createAllowed}
                title={createAllowed ? undefined : createBlockedReason ?? undefined}
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
