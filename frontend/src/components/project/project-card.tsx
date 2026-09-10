import { CalendarDays, CheckCircle2, ChevronRight, FileText, MapPin, UserRound } from "lucide-react";
import Link from "next/link";
import type { ManagedUser, ProjectItem } from "@/lib/api";

export function ProjectCard({ project, documentCount, verifiedCount = 0, canAssign = false, engineers = [], onAssign }: { project: ProjectItem; documentCount: number; verifiedCount?: number; canAssign?: boolean; engineers?: ManagedUser[]; onAssign?: (projectId: string, userId: string | null) => void }) {
  const date = new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(project.created_at));
  return (
    <article className="rq-project-card">
      <Link className="rq-project-card-link" href={`/projects/${project.id}`}>
        <div className="rq-project-card-top"><div><span className="rq-area-badge"><MapPin size={13} />{project.plant_area ?? "Area not supplied"}</span><h2>{project.name}</h2></div><ChevronRight size={20} /></div>
      </Link>
      <div className="rq-project-stats"><span><FileText size={16} /><b>{documentCount}</b><small>Total documents</small></span><span><CheckCircle2 size={16} /><b>{verifiedCount}</b><small>Verified</small></span><span><CalendarDays size={16} /><b>{date}</b><small>Last update</small></span></div>
      <div className="rq-project-ownership"><span><UserRound size={13} />Dibuat oleh: <b>{project.created_by_name ?? "Unknown"}</b></span><span><UserRound size={13} />Ditugaskan ke: <b>{project.assigned_to_name ?? "Belum di-assign"}</b></span></div>
      {canAssign && onAssign && <label className="rq-project-assign"><span>Quick assign</span><select aria-label={`Assign ${project.name}`} value={project.assigned_to_id ?? ""} onChange={(event) => onAssign(project.id, event.target.value || null)}><option value="">Belum di-assign</option>{engineers.filter((user) => user.role === "ENGINEER" && user.is_active).map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}</select></label>}
    </article>
  );
}
