"use client";

import { ExternalLink, FolderKanban, LoaderCircle, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, listProjectsForUser, type ManagedUser, type ProjectItem } from "@/lib/api";

export function UserProjectsModal({ user, onClose }: { user: ManagedUser | null; onClose: () => void }) {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!user) return;
    void listProjectsForUser(user.id).then(setProjects).catch((caught) => setError(caught instanceof ApiError ? caught.message : "Could not load projects.")).finally(() => setLoading(false));
  }, [user]);
  if (!user) return null;
  return <div className="rq-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="user-projects-title"><div className="rq-modal rq-user-projects-modal"><div className="rq-modal-header"><div><p className="rq-kicker">Assigned work</p><h2 id="user-projects-title">Projects for {user.full_name}</h2><p className="rq-modal-subtitle">Projects currently assigned to this account.</p></div><button type="button" aria-label="Close" onClick={onClose}><X size={18} /></button></div>{loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={20} />Loading projects...</div> : error ? <p className="rq-form-error">{error}</p> : projects.length === 0 ? <div className="rq-empty"><FolderKanban size={28} /><p>No projects assigned.</p></div> : <div className="rq-project-list">{projects.map((project) => <div className="rq-project-list-item" key={project.id}><div><strong>{project.name}</strong><small>{project.plant_area ?? "Area not supplied"} · {project.total_documents ?? 0} documents · {project.status ?? "ACTIVE"}</small></div><Link className="rq-secondary-button" href={`/projects/${project.id}`} onClick={onClose}>Open <ExternalLink size={13} /></Link></div>)}</div>}</div></div>;
}
