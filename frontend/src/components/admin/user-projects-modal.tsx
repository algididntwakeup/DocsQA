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
    setLoading(true);
    void listProjectsForUser(user.id)
      .then(setProjects)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "Could not load projects."))
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-projects-title"
    >
      <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Assigned Work</p>
            <h2 id="user-projects-title" className="text-lg font-bold text-slate-900">
              Projects for {user.full_name}
            </h2>
            <p className="text-xs text-slate-500">
              Projects and documents currently assigned to this engineer.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-4">
          {loading ? (
            <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 text-slate-400">
              <LoaderCircle className="animate-spin text-blue-600" size={24} />
              <span className="text-xs font-semibold">Loading projects...</span>
            </div>
          ) : error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">{error}</p>
          ) : projects.length === 0 ? (
            <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 text-center text-slate-400">
              <FolderKanban size={32} className="text-slate-300" />
              <p className="text-xs font-medium">No assigned documents.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <strong className="block text-sm font-bold text-slate-900">{project.name}</strong>
                    <small className="block mt-0.5 text-xs text-slate-500">
                      {project.plant_area ?? "Area not supplied"} · {project.total_documents ?? project.documents?.length ?? 0} documents · {project.status ?? "ACTIVE"}
                    </small>
                    {project.documents?.map((document) => (
                      <span key={document.id} className="mt-2 flex items-center gap-2 text-xs text-slate-600">
                        <span className="truncate">{document.title}</span>
                        <b className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">
                          {document.workflow_status.replaceAll("_", " ")}
                        </b>
                      </span>
                    ))}
                  </div>
                  <Link
                    href={`/projects/${project.id}`}
                    onClick={onClose}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 shrink-0"
                  >
                    Open <ExternalLink size={13} />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
