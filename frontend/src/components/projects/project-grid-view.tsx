import Link from "next/link";
import { CalendarClock, FileText, FolderOpen } from "lucide-react";
import { ProjectActionsMenu } from "@/components/projects/project-actions-menu";
import type { Project } from "@/types/project";

interface ProjectGridViewProps {
  projects: Project[];
  canManage?: boolean;
  onFinish?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}

function formatModifiedDate(project: Project): string {
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(
    new Date(project.updated_at ?? project.created_at),
  );
}

export function ProjectGridView({ projects, canManage, onFinish, onDelete }: ProjectGridViewProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
      {projects.map((project) => {
        const projectNumber = project.project_number ?? project.code;
        const documentCount = project.documents_count ?? project.total_documents ?? 0;

        return (
          <article
            key={project.id}
            className="group relative min-h-52 overflow-visible rounded-2xl border border-border/70 bg-card shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
          >
            <Link
              href={`/workspace/${project.id}`}
              aria-label={`Buka workspace ${project.name}`}
              className="block min-h-52 rounded-2xl p-5 pr-16 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="flex size-11 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                  <FolderOpen size={21} />
                </span>
                {projectNumber ? (
                  <span className="max-w-40 truncate rounded-md border border-border/70 bg-muted/70 px-2 py-1 font-mono text-[11px] font-semibold text-muted-foreground" title={projectNumber}>
                    {projectNumber}
                  </span>
                ) : <span className="text-xs text-muted-foreground">Nomor belum tersedia</span>}
              </div>

              <h2 className="mt-4 line-clamp-2 text-base font-bold leading-6 text-foreground group-hover:text-accent-foreground">
                {project.name}
              </h2>
              <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                {project.client_name || "Klien belum tersedia"}
              </p>

              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/70 pt-3 text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <FileText size={13} />
                  {documentCount} dokumen
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <CalendarClock size={13} />
                  {formatModifiedDate(project)}
                </span>
              </div>
            </Link>

            <div className="absolute right-4 top-4 z-20">
              <ProjectActionsMenu project={project} canManage={canManage} onFinish={onFinish} onDelete={onDelete} />
            </div>
          </article>
        );
      })}
    </div>
  );
}

export function ProjectGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4" aria-label="Memuat proyek" role="status">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="min-h-52 animate-pulse rounded-2xl border border-border/70 bg-card p-5">
          <div className="flex items-center justify-between">
            <div className="size-11 rounded-xl bg-muted" />
            <div className="h-6 w-28 rounded bg-muted" />
          </div>
          <div className="mt-5 h-4 w-4/5 rounded bg-muted" />
          <div className="mt-2 h-3 w-2/3 rounded bg-muted" />
          <div className="mt-7 border-t border-border pt-4">
            <div className="h-3 w-3/4 rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}
