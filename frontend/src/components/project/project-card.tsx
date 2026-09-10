import { CalendarDays, CheckCircle2, ChevronRight, FileText, MapPin } from "lucide-react";
import Link from "next/link";
import type { ProjectItem } from "@/lib/api";

export function ProjectCard({ project, documentCount, verifiedCount = 0 }: { project: ProjectItem; documentCount: number; verifiedCount?: number }) {
  const date = new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(project.created_at));
  return (
    <Link className="rq-project-card" href={`/projects/${project.id}`}>
      <div className="rq-project-card-top"><div><span className="rq-area-badge"><MapPin size={13} />{project.plant_area ?? "Area not supplied"}</span><h2>{project.name}</h2></div><ChevronRight size={20} /></div>
      <div className="rq-project-stats"><span><FileText size={16} /><b>{documentCount}</b><small>Total documents</small></span><span><CheckCircle2 size={16} /><b>{verifiedCount}</b><small>Verified</small></span><span><CalendarDays size={16} /><b>{date}</b><small>Last update</small></span></div>
    </Link>
  );
}
