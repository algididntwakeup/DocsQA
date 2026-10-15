"use client";

import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Grid2X2, List, Search } from "lucide-react";
import { useLocale } from "@/components/layout/locale-provider";
import type { TranslationKey } from "@/lib/i18n";
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
  origin: ProjectOriginFilter;
  onOriginChange: (origin: ProjectOriginFilter) => void;
  rightSlot?: ReactNode;
}

/** How the explorer narrows projects by where they came from. */
export type ProjectOriginFilter = "all" | "bima" | "custom";

const originOptions: Array<{ value: ProjectOriginFilter; labelKey: TranslationKey }> = [
  { value: "all", labelKey: "originAll" },
  { value: "bima", labelKey: "originBima" },
  { value: "custom", labelKey: "originCustom" },
];

const sortOptions: Array<{ value: ProjectSortField; labelKey: TranslationKey }> = [
  { value: "name", labelKey: "sortName" },
  { value: "project_number", labelKey: "sortNumber" },
  { value: "client_name", labelKey: "sortClient" },
  { value: "documents_count", labelKey: "sortDocsCount" },
  { value: "updated_at", labelKey: "sortUpdated" },
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
  origin,
  onOriginChange,
  rightSlot,
}: ExplorerToolbarProps) {
  const { t } = useLocale();
  const sortDirectionLabel = sortDirection === "asc" ? t("sortAscending") : t("sortDescending");

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-card p-3 shadow-sm xl:flex-row xl:items-center">
      <label className="relative min-w-0 flex-1">
        <span className="sr-only">{t("searchLabel")}</span>
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="project-sort">{t("sortBy")}</label>
        <select
          id="project-sort"
          value={sortBy}
          onChange={(event) => onSortByChange(event.target.value as ProjectSortField)}
          className="h-10 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
        >
          {sortOptions.map((option) => <option key={option.value} value={option.value}>{t(option.labelKey)}</option>)}
        </select>
        <button
          type="button"
          onClick={onToggleSortDirection}
          aria-label={sortDirectionLabel}
          title={sortDirectionLabel}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition hover:bg-muted hover:text-foreground"
        >
          {sortDirection === "asc" ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
        </button>

        <label className="sr-only" htmlFor="project-origin">{t("originFilterLabel")}</label>
        <select
          id="project-origin"
          value={origin}
          onChange={(event) => onOriginChange(event.target.value as ProjectOriginFilter)}
          className="h-10 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
        >
          {originOptions.map((option) => (
            <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
          ))}
        </select>

        <div className="inline-flex rounded-lg border border-border bg-background p-1" role="group" aria-label={t("viewModeLabel")}>
          <button
            type="button"
            aria-label={t("viewGrid")}
            aria-pressed={viewMode === "grid"}
            title={t("viewGrid")}
            onClick={() => onViewModeChange("grid")}
            className={`inline-flex h-8 w-9 items-center justify-center rounded-md transition ${viewMode === "grid" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <Grid2X2 size={16} />
          </button>
          <button
            type="button"
            aria-label={t("viewTable")}
            aria-pressed={viewMode === "table"}
            title={t("viewTable")}
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
