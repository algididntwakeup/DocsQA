import { CalendarDays, CheckCircle2, ChevronRight, CircleCheck, FileText, MapPin, Trash2, UserRound } from "lucide-react";
import Link from "next/link";
import type { ProjectItem } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { useLocale } from "@/components/layout/locale-provider";

export function ProjectCard({
  project,
  documentCount,
  verifiedCount = 0,
  canManage = false,
  onFinish,
  onDelete,
}: {
  project: ProjectItem;
  documentCount: number;
  verifiedCount?: number;
  canManage?: boolean;
  onFinish?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}) {
  const { locale, t } = useLocale();
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
    new Date(project.created_at)
  );

  return (
    <Card className="group relative flex min-h-[220px] flex-col justify-between p-5 transition duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md">
      <Link className="block focus:outline-none" href={`/projects/${project.id}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-accent px-2 py-0.5 text-[11px] font-semibold text-accent-foreground ring-1 ring-primary/10">
              <MapPin size={12} />
              {project.plant_area ?? t("areaNotSupplied")}
            </span>
            <h2 className="text-base font-bold tracking-tight text-foreground group-hover:text-accent-foreground transition-colors">
              {project.name}
            </h2>
          </div>
          <ChevronRight
            size={18}
            className="text-muted-foreground transition-transform duration-150 group-hover:translate-x-1 group-hover:text-accent-foreground shrink-0 mt-1"
          />
        </div>
      </Link>

      <div className="mt-4 grid grid-cols-3 gap-2 border-y border-border/60 py-3 text-center">
        <div className="flex flex-col items-center">
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <FileText size={13} className="text-accent-foreground" /> {t("docs")}
          </span>
          <b className="mt-0.5 text-sm font-bold text-foreground">{documentCount}</b>
        </div>
        <div className="flex flex-col items-center border-x border-border/60">
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <CheckCircle2 size={13} className="text-emerald-600" /> {t("verified")}
          </span>
          <b className="mt-0.5 text-sm font-bold text-foreground">{verifiedCount}</b>
        </div>
        <div className="flex flex-col items-center">
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <CalendarDays size={13} className="text-amber-600" /> {t("updated")}
          </span>
          <small className="mt-0.5 text-[11px] font-semibold text-foreground truncate max-w-[80px]">
            {date}
          </small>
        </div>
      </div>

      <div className="mt-3 space-y-1 text-xs text-muted-foreground">
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1 text-muted-foreground">
            <UserRound size={12} /> {t("created")}:
          </span>
          <b className="font-semibold text-foreground truncate max-w-[130px]">
            {project.owner_name ?? t("system")}
          </b>
        </div>
      </div>

      <div className="mt-5 -mx-5 -mb-5 flex min-h-[52px] items-center justify-between gap-3 rounded-b-2xl border-t border-border/60 bg-muted/70 px-5 py-2.5">
        {project.status === "FINISHED" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-700 ring-1 ring-emerald-700/10">
             <CircleCheck size={12} /> {t("finished")}
          </span>
         ) : <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground"><span className="h-1.5 w-1.5 rounded-full bg-primary" />{t("activeProject")}</span>}
        {canManage && project.status !== "FINISHED" && onFinish && onDelete && (
          <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onFinish(project.id)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-[11px] font-bold text-primary-foreground shadow-xs transition hover:bg-primary/90 active:scale-[0.98]"
          >
            <CheckCircle2 size={12} />
             {t("finish")}
          </button>
          <button
            type="button"
            aria-label={`Delete ${project.name}`}
            disabled={documentCount > 0}
            title={documentCount > 0 ? "Hanya project kosong yang dapat dihapus" : "Delete project"}
            onClick={() => onDelete(project.id)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground shadow-2xs transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 size={14} />
          </button>
          </div>
        )}
      </div>
    </Card>
  );
}
