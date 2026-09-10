"use client";

import { ExternalLink, FolderKanban, LoaderCircle, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, listProjectsForUser, type AssignedProject, type ManagedUser } from "@/lib/api";

export function UserProjectsModal({ user, onClose }: { user: ManagedUser | null; onClose: () => void }) {
  const [projects, setProjects] = useState<AssignedProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!user) return;
    void listProjectsForUser(user.id).then(setProjects).catch((caught) => setError(caught instanceof ApiError ? caught.message : "Could not load projects.")).finally(() => setLoading(false));
  }, [user]);
  if (!user) return null;
   return <div className="rq-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="user-projects-title"><div className="rq-modal rq-user-projects-modal"><div className="rq-modal-header"><div><p className="rq-kicker">Assigned work</p><h2 id="user-projects-title">Projects for {user.full_name}</h2><p className="rq-modal-subtitle">Projects and documents currently assigned to this engineer.</p></div><button type="button" aria-label="Close" onClick={onClose}><X size={18} /></button></div>{loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={20} />Loading projects...</div> : error ? <p className="rq-form-error">{error}</p> : projects.length === 0 ? <div className="rq-empty"><FolderKanban size={28} /><p>No assigned documents.</p></div> : <div className="rq-project-list">{projects.map((project) => <div className="rq-project-list-item" key={project.id}><div className="min-w-0"><strong>{project.name}</strong><small>{project.plant_area ?? "Area not supplied"} · {project.total_documents ?? project.documents?.length ?? 0} documents · {project.status ?? "ACTIVE"}</small>{project.documents?.map((document) => <span className="mt-2 flex items-center gap-2 text-xs text-muted" key={document.id}><span className="truncate">{document.title}</span><b className="rq-workflow rq-workflow-analyzing">{document.workflow_status.replaceAll("_", " ")}</b></span>)}</div><Link className="rq-secondary-button shrink-0" href={`/projects/${project.id}`} onClick={onClose}>Open <ExternalLink size={13} /></Link></div>)}</div>}</div></div>;
}
