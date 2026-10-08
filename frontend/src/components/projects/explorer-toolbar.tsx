"use client";

import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Grid2X2, List, Search } from "lucide-react";
import type { ProjectSortField, ProjectViewMode } from "@/types/project";

interface ExplorerToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  sortBy: ProjectSortField;
  onSortByChange: (field: ProjectSortField) => void;
  sortDirection: "asc" | "desc";
  onToggleSortDirection: () => void;
  viewMode: ProjectViewMode;
  onViewModeChange: (mode: ProjectViewMode) => void;
  rightSlot?: ReactNode;
}

const sortOptions: Array<{ value: ProjectSortField; label: string }> = [
  { value: "name", label: "Nama" },
  { value: "project_number", label: "Nomor Proyek" },
  { value: "client_name", label: "Klien" },
  { value: "documents_count", label: "Jumlah Dokumen" },
  { value: "updated_at", label: "Tanggal Update" },
];

export function ExplorerToolbar({
  search,
  onSearchChange,
  sortBy,
  onSortByChange,
  sortDirection,
  onToggleSortDirection,
  viewMode,
  onViewModeChange,
  rightSlot,
}: ExplorerToolbarProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-card p-3 shadow-sm xl:flex-row xl:items-center">
      <label className="relative min-w-0 flex-1">
        <span className="sr-only">Cari proyek</span>
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Cari nama proyek, nomor proyek, atau klien..."
          className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="project-sort">Urutkan proyek</label>
        <select
          id="project-sort"
          value={sortBy}
          onChange={(event) => onSortByChange(event.target.value as ProjectSortField)}
          className="h-10 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
        >
          {sortOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <button
          type="button"
          onClick={onToggleSortDirection}
          aria-label={sortDirection === "asc" ? "Urutan naik" : "Urutan turun"}
          title={sortDirection === "asc" ? "Urutan naik" : "Urutan turun"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition hover:bg-muted hover:text-foreground"
        >
          {sortDirection === "asc" ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
        </button>

        <div className="inline-flex rounded-lg border border-border bg-background p-1" role="group" aria-label="Mode tampilan proyek">
          <button
            type="button"
            aria-label="Tampilan grid"
            aria-pressed={viewMode === "grid"}
            title="Tampilan grid"
            onClick={() => onViewModeChange("grid")}
            className={`inline-flex h-8 w-9 items-center justify-center rounded-md transition ${viewMode === "grid" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <Grid2X2 size={16} />
          </button>
          <button
            type="button"
            aria-label="Tampilan tabel"
            aria-pressed={viewMode === "table"}
            title="Tampilan tabel"
            onClick={() => onViewModeChange("table")}
            className={`inline-flex h-8 w-9 items-center justify-center rounded-md transition ${viewMode === "table" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      {rightSlot && <div className="flex shrink-0 items-center justify-end">{rightSlot}</div>}
    </div>
  );
}
