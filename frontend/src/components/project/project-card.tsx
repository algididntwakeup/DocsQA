import { CalendarDays, CheckCircle2, ChevronRight, FileText, MapPin, UserRound } from "lucide-react";
import Link from "next/link";
import type { ManagedUser, ProjectItem } from "@/lib/api";

export function ProjectCard({
  project,
  documentCount,
  verifiedCount = 0,
  canAssign = false,
  engineers = [],
  onAssign,
}: {
  project: ProjectItem;
  documentCount: number;
  verifiedCount?: number;
  canAssign?: boolean;
  engineers?: ManagedUser[];
  onAssign?: (projectId: string, userId: string | null) => void;
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
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1 text-slate-400">
            <UserRound size={12} /> Assigned:
          </span>
          <b className="font-semibold text-slate-800 truncate max-w-[130px]">
            {project.assigned_to_name ?? "Belum di-assign"}
          </b>
        </div>
      </div>

      {canAssign && onAssign && (
        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <label className="flex flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <span>Quick Assign</span>
            <select
              aria-label={`Assign ${project.name}`}
              value={project.assigned_to_id ?? ""}
              onChange={(event) => onAssign(project.id, event.target.value || null)}
              className="h-8 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs font-medium text-slate-800 transition focus:border-blue-500 focus:bg-white focus:outline-none"
            >
              <option value="">Belum di-assign</option>
              {engineers
                .filter((user) => user.role === "ENGINEER" && user.is_active)
                .map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
            </select>
          </label>
        </div>
      )}
    </article>
  );
}
