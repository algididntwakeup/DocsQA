import { CalendarDays, ChevronRight, FileText, MapPin } from "lucide-react";
import Link from "next/link";
import type { ProjectItem } from "@/lib/api";

export function ProjectCard({ project, documentCount }: { project: ProjectItem; documentCount: number }) {
  const date = new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(project.created_at));
  return (
    <Link className="group panel block p-5 transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md" href={`/projects/${project.id}`}>
      <div className="flex items-start justify-between gap-4"><div><p className="eyebrow m-0">{project.code ?? "Project register"}</p><h2 className="mt-2 text-lg font-semibold tracking-tight text-ink">{project.name}</h2></div><ChevronRight className="text-muted transition group-hover:translate-x-1 group-hover:text-primary" size={19} /></div>
      <div className="mt-7 grid grid-cols-2 gap-4 border-t border-line pt-4 text-xs"><span className="flex items-center gap-2 text-muted"><MapPin size={14} className="text-primary" />{project.plant_area ?? "Area not supplied"}</span><span className="flex items-center gap-2 text-muted"><FileText size={14} className="text-primary" />{documentCount} documents</span><span className="col-span-2 flex items-center gap-2 font-mono text-[10px] uppercase text-muted"><CalendarDays size={13} />{date}</span></div>
    </Link>
  );
}
