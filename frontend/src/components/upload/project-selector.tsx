"use client";

import { useMemo, useState } from "react";
import { FolderKanban, Search } from "lucide-react";
import type { ProjectItem } from "@/lib/api";

interface ProjectSelectorProps {
  projects: ProjectItem[];
  selectedId: string | null;
  onSelect: (projectId: string) => void;
  loading?: boolean;
}

/**
 * Searchable project picker for the upload flow.
 *
 * A native `<select>` is used under the hood so keyboard navigation and mobile
 * pickers work without a combobox dependency; the surrounding card supplies the
 * Shadcn-style spacing and typography.
 */
export function ProjectSelector({
  projects,
  selectedId,
  onSelect,
  loading = false,
}: ProjectSelectorProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return projects;
    return projects.filter((project) =>
      [project.name, project.project_number ?? "", project.client_name ?? ""].some((value) =>
        value.toLowerCase().includes(needle),
      ),
    );
  }, [projects, query]);

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search your projects..."
          aria-label="Search projects"
          className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
        />
      </div>

      {loading ? (
        <div className="space-y-2" aria-label="Loading projects" role="status">
          {Array.from({ length: 3 }, (_, index) => (
            <div key={index} className="h-16 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-muted/30 px-4 py-8 text-center text-sm text-muted-foreground">
          {projects.length === 0
            ? "No projects in your workspace yet. Add one from BIMA first."
            : "No projects match your search."}
        </p>
      ) : (
        <ul
          className="max-h-72 space-y-2 overflow-y-auto pr-1"
          aria-label="Select a target project"
        >
          {filtered.map((project) => {
            const selected = project.id === selectedId;
            return (
              <li key={project.id}>
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => onSelect(project.id)}
                  className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                    selected
                      ? "border-primary/50 bg-accent shadow-sm"
                      : "border-border/70 bg-card hover:border-primary/30 hover:bg-muted/40"
                  }`}
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <FolderKanban size={17} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-foreground">
                      {project.name}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                      {[project.project_number, project.client_name]
                        .filter(Boolean)
                        .join(" · ") || "No project number"}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
