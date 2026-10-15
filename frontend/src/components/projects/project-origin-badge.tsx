"use client";

import { CloudDownload, FolderPlus } from "lucide-react";
import type { Project } from "@/types/project";

/**
 * Origin badge for a project card or row.
 *
 * A project imported from BIMA carries ``bima_project_id``; a custom project
 * created inside PRISM has none. The same distinction drives the origin filter
 * and the deletion rule, so it is computed here rather than at each call site.
 */
export function ProjectOriginBadge({
  project,
  className = "",
}: {
  project: Pick<Project, "bima_project_id">;
  className?: string;
}) {
  const isBima = project.bima_project_id != null;

  return (
    <span
      title={isBima ? "Imported from BIMA" : "Created in PRISM"}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
        isBima
          ? "border-indigo-200 bg-indigo-50 text-indigo-700"
          : "border-slate-200 bg-slate-100 text-slate-600"
      } ${className}`}
    >
      {isBima ? <CloudDownload size={11} /> : <FolderPlus size={11} />}
      {isBima ? "BIMA" : "Custom"}
    </span>
  );
}
