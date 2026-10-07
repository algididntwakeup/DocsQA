"use client";

import { useMemo, type ReactNode } from "react";
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import type { Column, ColumnDef, OnChangeFn, SortingState, Table } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Folder } from "lucide-react";
import { ProjectActionsMenu } from "@/components/projects/project-actions-menu";
import type { Project } from "@/types/project";

interface UseProjectTableOptions {
  projects: Project[];
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  canManage?: boolean;
  onFinish?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}

interface ProjectTableViewProps {
  table: Table<Project>;
  onOpen: (projectId: string) => void;
}

function SortableHeading({ column, label, icon }: { column: Column<Project, unknown>; label: string; icon?: ReactNode }) {
  const sorted = column.getIsSorted();
  return (
    <button
      type="button"
      onClick={column.getToggleSortingHandler()}
      className="inline-flex items-center gap-2 text-left font-semibold text-muted-foreground transition hover:text-foreground"
    >
      {icon}
      {label}
      {sorted === "asc" ? <ArrowUp size={13} /> : sorted === "desc" ? <ArrowDown size={13} /> : <ArrowUpDown size={13} className="opacity-40" />}
    </button>
  );
}
function displayModifiedDate(project: Project): string {
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(
    new Date(project.updated_at ?? project.created_at),
  );
}

export function useProjectTable({ projects, sorting, onSortingChange, canManage, onFinish, onDelete }: UseProjectTableOptions) {
  const columns = useMemo<ColumnDef<Project, unknown>[]>(() => [
    {
      id: "name",
      accessorFn: (project) => project.name,
      header: ({ column }) => <SortableHeading column={column} label="Name" icon={<Folder size={15} />} />,
      cell: ({ row }) => (
        <span className="flex min-w-48 items-center gap-2 font-semibold text-foreground">
          <Folder size={15} className="shrink-0 text-accent-foreground" />
          <span className="truncate">{row.original.name}</span>
        </span>
      ),
    },
    {
      id: "project_number",
      accessorFn: (project) => project.project_number ?? project.code ?? "",
      header: ({ column }) => <SortableHeading column={column} label="Project No." />,
      cell: ({ getValue }) => <span className="font-mono text-xs text-muted-foreground">{getValue<string>() || "—"}</span>,
    },
    {
      id: "client_name",
      accessorFn: (project) => project.client_name ?? "",
      header: ({ column }) => <SortableHeading column={column} label="Client" />,
      cell: ({ getValue }) => <span className="block max-w-56 truncate text-xs text-muted-foreground">{getValue<string>() || "—"}</span>,
    },
    {
      id: "documents_count",
      accessorFn: (project) => project.documents_count ?? project.total_documents ?? 0,
      header: ({ column }) => <SortableHeading column={column} label="Documents" />,
      cell: ({ getValue }) => <span className="tabular-nums text-xs text-muted-foreground">{getValue<number>()}</span>,
    },
    {
      id: "updated_at",
      accessorFn: (project) => Date.parse(project.updated_at ?? project.created_at) || 0,
      header: ({ column }) => <SortableHeading column={column} label="Last Modified" />,
      cell: ({ row }) => <time className="whitespace-nowrap text-xs text-muted-foreground" dateTime={row.original.updated_at ?? row.original.created_at}>{displayModifiedDate(row.original)}</time>,
    },
    {
      id: "actions",
      enableSorting: false,
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => <ProjectActionsMenu project={row.original} canManage={canManage} onFinish={onFinish} onDelete={onDelete} />,
    },
  ], [canManage, onDelete, onFinish]);

  // TanStack Table's instance is intentionally passed to the explorer table view.
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack's supported table API is required here.
  return useReactTable({
    data: projects,
    columns,
    state: { sorting },
    onSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
}

export function ProjectTableView({ table, onOpen }: ProjectTableViewProps) {
  const rows = table.getRowModel().rows;

  return (
    <div className="overflow-x-auto rounded-xl border border-border/70 bg-card shadow-sm">
      <table className="w-full min-w-[860px] border-collapse text-left">
        <thead className="border-b border-border bg-muted/50 text-[11px] uppercase tracking-wide">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} scope="col" className="px-4 py-3.5 font-semibold">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-border/70">
          {rows.map((row) => (
            <tr
              key={row.id}
              role="link"
              tabIndex={0}
              aria-label={`Buka workspace ${row.original.name}`}
              onClick={(event) => {
                const target = event.target;
                if (target instanceof Element && target.closest("button, a, summary")) return;
                onOpen(row.original.id);
              }}
              onKeyDown={(event) => {
                const target = event.target;
                if (target instanceof Element && target.closest("button, a, summary")) return;
                if (event.key === "Enter") {
                  event.preventDefault();
                  onOpen(row.original.id);
                }
              }}
              className="cursor-pointer outline-none transition hover:bg-muted/40 focus-visible:bg-muted/50"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3.5 align-middle text-sm">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProjectTableSkeleton({ count = 7 }: { count?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border/70 bg-card" role="status" aria-label="Memuat daftar proyek">
      <div className="grid min-w-[860px] grid-cols-[2fr_1fr_1.5fr_0.7fr_1.2fr_0.6fr] gap-4 border-b border-border bg-muted/50 px-4 py-4">
        {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-3 animate-pulse rounded bg-muted-foreground/20" />)}
      </div>
      {Array.from({ length: count }, (_, row) => (
        <div key={row} className="grid min-w-[860px] grid-cols-[2fr_1fr_1.5fr_0.7fr_1.2fr_0.6fr] gap-4 border-b border-border/70 px-4 py-4 last:border-b-0">
          {Array.from({ length: 6 }, (_, column) => <div key={column} className="h-4 animate-pulse rounded bg-muted" />)}
        </div>
      ))}
    </div>
  );
}
