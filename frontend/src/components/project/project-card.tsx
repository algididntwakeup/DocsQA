import { CalendarDays, CheckCircle2, ChevronRight, CircleCheck, FileText, MapPin, Trash2, UserRound } from "lucide-react";
import Link from "next/link";
import type { ProjectItem } from "@/lib/api";

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
  const date = new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(
    new Date(project.created_at)
  );

  return (
    <article className="group relative flex min-h-[220px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition duration-200 hover:-translate-y-0.5 hover:border-blue-400 hover:shadow-md">
      <Link className="block focus:outline-none" href={`/projects/${project.id}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-700/10">
              <MapPin size={12} />
              {project.plant_area ?? "Area not supplied"}
            </span>
            <h2 className="text-base font-bold tracking-tight text-slate-900 group-hover:text-blue-600 transition-colors">
              {project.name}
            </h2>
          </div>
          <ChevronRight
            size={18}
            className="text-slate-400 transition-transform duration-150 group-hover:translate-x-1 group-hover:text-blue-600 shrink-0 mt-1"
          />
        </div>
      </Link>

      <div className="mt-4 grid grid-cols-3 gap-2 border-y border-slate-100 py-3 text-center">
        <div className="flex flex-col items-center">
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <FileText size={13} className="text-blue-600" /> Docs
          </span>
          <b className="mt-0.5 text-sm font-bold text-slate-900">{documentCount}</b>
        </div>
        <div className="flex flex-col items-center border-x border-slate-100">
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <CheckCircle2 size={13} className="text-emerald-600" /> Verified
          </span>
          <b className="mt-0.5 text-sm font-bold text-slate-900">{verifiedCount}</b>
        </div>
        <div className="flex flex-col items-center">
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <CalendarDays size={13} className="text-amber-600" /> Updated
          </span>
          <small className="mt-0.5 text-[11px] font-semibold text-slate-700 truncate max-w-[80px]">
            {date}
          </small>
        </div>
      </div>

      <div className="mt-3 space-y-1 text-xs text-slate-600">
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1 text-slate-400">
            <UserRound size={12} /> Created:
          </span>
          <b className="font-semibold text-slate-800 truncate max-w-[130px]">
            {project.created_by_name ?? "System"}
          </b>
        </div>
      </div>

      <div className="mt-5 -mx-5 -mb-5 flex min-h-[52px] items-center justify-between gap-3 rounded-b-2xl border-t border-slate-100 bg-slate-50/70 px-5 py-2.5">
        {project.status === "FINISHED" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-700 ring-1 ring-emerald-700/10">
            <CircleCheck size={12} /> Finished
          </span>
        ) : <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500"><span className="h-1.5 w-1.5 rounded-full bg-blue-500" />Active project</span>}
        {canManage && project.status !== "FINISHED" && onFinish && onDelete && (
          <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onFinish(project.id)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-[11px] font-bold text-white shadow-xs transition hover:bg-blue-700 active:scale-[0.98]"
          >
            <CheckCircle2 size={12} />
            Finish Project
          </button>
          <button
            type="button"
            aria-label={`Delete ${project.name}`}
            disabled={documentCount > 0}
            title={documentCount > 0 ? "Hanya project kosong yang dapat dihapus" : "Delete project"}
            onClick={() => onDelete(project.id)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 shadow-2xs transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 size={14} />
          </button>
          </div>
        )}
      </div>
    </article>
  );
}
