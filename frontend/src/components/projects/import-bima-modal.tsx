"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CircleAlert, CloudDownload, ExternalLink, LoaderCircle, Search, X } from "lucide-react";
import { toast } from "sonner";
import { useLocale } from "@/components/layout/locale-provider";
import { useBimaProjects, useImportBimaProject } from "@/hooks/use-bima-projects";
import { canManageFolders, folderPermissionMessage } from "@/lib/project-permissions";
import type { UserRole } from "@/lib/api";
import type { BimaProject } from "@/types/project";

interface ImportBimaModalProps {
  onImported?: () => void | Promise<void>;
  role?: UserRole | null;
}

export function ImportBimaModal({ onImported, role = null }: ImportBimaModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const projectsQuery = useBimaProjects(open);
  const importMutation = useImportBimaProject();
  const { t } = useLocale();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const projects = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = projectsQuery.data ?? [];
    if (!query) return items;

    return items.filter((project) =>
      [project.number, project.name, project.client_name ?? ""].some((value) => value.toLowerCase().includes(query)),
    );
  }, [projectsQuery.data, search]);

  function openImportedProject(project: BimaProject) {
    if (!project.prism_project_id) return;
    closeDialog();
    router.push(`/workspace/${project.prism_project_id}`);
  }

  async function handleImport(project: BimaProject) {
    setImportError(null);
    try {
      await importMutation.mutateAsync({ bima_project_id: project.id });
      toast.success(t("bimaImportSuccess"));
      await onImported?.();
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : t("bimaImportFailed");
      setImportError(message);
      toast.error(message);
    }
  }

  function closeDialog() {
    setOpen(false);
    setImportError(null);
  }

  return (
    <>
      <button
        className="inline-flex items-center gap-2 rounded-lg border border-primary/20 bg-card px-4 py-2.5 text-xs font-bold text-foreground transition hover:bg-muted/50"
        type="button"
        onClick={() => setOpen(true)}
      >
        <CloudDownload size={16} />
        {t("importFromBima")}
      </button>

      <dialog
        ref={dialogRef}
        className="m-auto max-h-[85vh] w-[min(92vw,42rem)] overflow-hidden rounded-2xl border border-border bg-card p-0 text-foreground shadow-2xl backdrop:bg-slate-950/50 backdrop:backdrop-blur-sm"
        aria-labelledby="import-bima-title"
        onCancel={() => setOpen(false)}
        onClose={() => setOpen(false)}
        onClick={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border/70 px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">{t("bimaIntegration")}</p>
            <h2 id="import-bima-title" className="mt-1 text-lg font-bold">{t("bimaModalTitle")}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{t("bimaModalDesc")}</p>
          </div>
          <button
            type="button"
            aria-label={t("closeDialog")}
            onClick={closeDialog}
            className="rounded-lg p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground"
          >
            <X size={18} />
          </button>
        </div>

        <div className="sticky top-0 z-10 border-b border-border/60 bg-card/95 p-4 backdrop-blur-sm">
          <label className="sr-only" htmlFor="bima-project-search">{t("bimaSearchLabel")}</label>
          <div className="relative">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              id="bima-project-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("bimaSearchPlaceholder")}
              className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
          </div>
        </div>

        <div className="max-h-[calc(85vh-11rem)] overflow-y-auto p-4">
          {importError && (
            <div role="alert" className="mb-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <CircleAlert size={16} className="mt-0.5 shrink-0" />
              <span>{importError}</span>
            </div>
          )}

          {projectsQuery.isPending ? (
            <div className="space-y-3" aria-label={t("bimaLoading")} role="status">
              {Array.from({ length: 4 }, (_, index) => (
                <div key={index} className="flex items-center gap-4 rounded-xl border border-border/70 p-4">
                  <div className="h-6 w-28 animate-pulse rounded bg-muted" />
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
                  </div>
                  <div className="h-8 w-16 animate-pulse rounded-lg bg-muted" />
                </div>
              ))}
            </div>
          ) : projectsQuery.isError ? (
            <div className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm font-semibold text-rose-700">{projectsQuery.error.message}</p>
              <button
                type="button"
                onClick={() => void projectsQuery.refetch()}
                className="rounded-lg border border-border px-3 py-2 text-xs font-semibold hover:bg-muted/50"
              >
                {t("retry")}
              </button>
            </div>
          ) : projects.length === 0 ? (
            <div className="flex min-h-40 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
              <Search size={24} className="text-border" />
              <p className="text-sm font-semibold">{t("emptySearch")}</p>
              <p className="text-xs">{t("emptySearchHint")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => {
                const isImporting = importMutation.isPending && importMutation.variables?.bima_project_id === project.id;
                const importAllowed = canManageFolders(role, project.number);
                return (
                  <div key={project.id} className="flex items-center gap-4 rounded-xl border border-border/70 bg-card p-4 transition hover:bg-muted/30">
                    <span className="max-w-32 shrink-0 truncate rounded-md bg-muted px-2 py-1 font-mono text-[11px] font-semibold text-muted-foreground" title={project.number}>
                      {project.number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-1 text-sm font-semibold text-foreground" title={project.name}>{project.name}</p>
                      <p className="mt-1 line-clamp-1 text-xs text-muted-foreground" title={project.client_name ?? undefined}>{project.client_name}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {project.is_imported ? (
                        <>
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[10px] font-bold text-emerald-800">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                            {t("bimaBadgeImported")}
                          </span>
                          <button
                            type="button"
                            onClick={() => openImportedProject(project)}
                            disabled={!project.prism_project_id}
                            title={t("openWorkspaceFor", { name: project.name })}
                            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-bold text-foreground transition hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <ExternalLink size={14} />
                            {t("bimaBtnOpenProject")}
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          disabled={importMutation.isPending || !importAllowed}
                          onClick={() => void handleImport(project)}
                          title={importAllowed ? undefined : folderPermissionMessage(project.number)}
                          className="inline-flex min-w-20 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isImporting && <LoaderCircle size={14} className="animate-spin" />}
                          {isImporting ? t("bimaBtnImporting") : t("bimaBtnImport")}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </dialog>
    </>
  );
}
