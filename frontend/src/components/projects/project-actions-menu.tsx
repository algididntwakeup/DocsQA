"use client";

import Link from "next/link";
import { Clipboard, ExternalLink, MoreHorizontal, Trash2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import type { Project } from "@/types/project";

interface ProjectActionsMenuProps {
  project: Project;
  canManage?: boolean;
  onFinish?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}

export function ProjectActionsMenu({ project, canManage = false, onFinish, onDelete }: ProjectActionsMenuProps) {
  const projectNumber = project.project_number ?? project.code ?? "";

  async function copyProjectNumber() {
    if (!projectNumber) return;
    try {
      await navigator.clipboard.writeText(projectNumber);
      toast.success("Nomor proyek disalin.");
    } catch {
      toast.error("Nomor proyek tidak dapat disalin.");
    }
  }

  return (
    <details className="relative">
      <summary
        aria-label={`Aksi untuk ${project.name}`}
        title="Aksi proyek"
        className="flex size-8 cursor-pointer list-none items-center justify-center rounded-lg border border-border/70 bg-card text-muted-foreground transition hover:bg-muted hover:text-foreground [&::-webkit-details-marker]:hidden"
      >
        <MoreHorizontal size={17} />
      </summary>
      <div className="absolute right-0 top-10 z-30 min-w-52 rounded-xl border border-border bg-card p-1.5 shadow-xl">
        <Link
          href={`/workspace/${project.id}`}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-foreground hover:bg-muted"
        >
          <ExternalLink size={14} />
          Buka Workspace
        </Link>
        <button
          type="button"
          disabled={!projectNumber}
          onClick={() => void copyProjectNumber()}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Clipboard size={14} />
          Salin Nomor Proyek
        </button>
        {canManage && project.status !== "FINISHED" && onFinish && (
          <button
            type="button"
            onClick={() => onFinish(project.id)}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-foreground hover:bg-muted"
          >
            <CheckCircle2 size={14} />
            Selesaikan Proyek
          </button>
        )}
        {canManage && project.status !== "FINISHED" && onDelete && (
          <button
            type="button"
            disabled={(project.documents_count ?? project.total_documents ?? 0) > 0}
            title={(project.documents_count ?? project.total_documents ?? 0) > 0 ? "Hanya project kosong yang dapat dihapus" : "Hapus proyek"}
            onClick={() => onDelete(project.id)}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 size={14} />
            Hapus Proyek
          </button>
        )}
      </div>
    </details>
  );
}
