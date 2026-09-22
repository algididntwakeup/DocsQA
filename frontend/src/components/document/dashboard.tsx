"use client";

import { AlertTriangle, CheckCircle2, Clock3, FileSearch, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiError,
  getCurrentUser,
  listDocuments,
  listEngineers,
  listProjects,
  subscribeDocumentEvents,
  type DocumentItem,
  type ManagedUser,
  type ProjectItem,
  type UserRole,
} from "@/lib/api";
import { DocumentList } from "./document-list";
import { useLocale } from "@/components/layout/locale-provider";

const leadRoles: UserRole[] = ["LEAD_ENGINEER", "SUPERUSER"];

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [role, setRole] = useState<UserRole | null>(null);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [engineers, setEngineers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ search: "", projectId: "", engineerId: "", status: "" });
  const { t } = useLocale();

  const isLead = role !== null && leadRoles.includes(role);

  async function load(nextFilters = filters) {
    try {
      setError(null);
      const result = await listDocuments({
        projectId: isLead ? nextFilters.projectId || undefined : undefined,
        assignedToId: isLead ? nextFilters.engineerId || undefined : undefined,
        workflowStatus: isLead ? nextFilters.status || undefined : undefined,
      });
      setDocuments(result.documents);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotReachApi"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    void getCurrentUser()
      .then(async (user) => {
        if (!leadRoles.includes(user.role)) return [user, [] as ProjectItem[], [] as ManagedUser[]] as const;
        const [projectItems, engineerItems] = await Promise.all([listProjects(), listEngineers()]);
        return [user, projectItems, engineerItems] as const;
      })
      .then(([user, projectItems, engineerItems]) => {
        if (!active) return;
        setRole(user.role);
        setProjects(projectItems);
        setEngineers(engineerItems);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof ApiError ? caught.message : t("couldNotLoadWorkspace"));
      });
    return () => { active = false; };
  }, [t]);

  useEffect(() => {
    if (role === null) return;
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  // The role transition is the fetch boundary; filter changes are handled by the filter form.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  useEffect(() => {
    const activeIds = documents
      .filter((item) => item.status === "QUEUED" || item.status === "PROCESSING")
      .map((item) => item.id);
    if (!activeIds.length) return;
    const unsubscribers = activeIds.map((id) => subscribeDocumentEvents(id, (event) => {
      setDocuments((current) => current.map((item) => item.id === id ? {
        ...item,
        status: event.status as DocumentItem["status"],
        progress_pct: event.progress_pct,
        updated_at: new Date().toISOString(),
      } : item));
    }));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [documents]);

  const visibleDocuments = documents.filter((document) =>
    document.filename.toLowerCase().includes(filters.search.toLowerCase().trim())
  );
  const active = documents.filter((item) => item.status === "QUEUED" || item.status === "PROCESSING").length;
  const reviewed = documents.filter((item) => item.workflow_status === "REVIEWED_BY_ENGINEER").length;
  const verified = documents.filter((item) => item.workflow_status === "VERIFIED_BY_LEAD").length;

  const applyFilters = () => void load(filters);

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl space-y-7 px-4 py-8 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-5 border-b border-slate-200 pb-6 sm:flex-row sm:items-end">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-600">{t("inspectionWorkspace")}</p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {isLead ? `${t("inspectionRegister")} (Master Log)` : `${t("inspectionWorkspace")} - ${t("documents")}`}
            </h1>
             <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
               {t("documentDescription")}
             </p>
          </div>
          <Link href="/upload" className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-blue-700">
            <Plus size={16} /> {t("newDocument")}
          </Link>
        </header>

        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Document summary">
          {([
            [FileSearch, t("totalDocuments"), documents.length, "bg-blue-50 text-blue-600"],
            [Clock3, t("beingAnalyzed"), active, "bg-amber-50 text-amber-600"],
            [AlertTriangle, t("awaitingVerification"), reviewed, "bg-orange-50 text-orange-600"],
            [CheckCircle2, t("verifiedDocuments"), verified, "bg-emerald-50 text-emerald-600"],
          ] as [typeof FileSearch, string, number, string][]).map(([SummaryIcon, label, value, color]) => {
            return <article key={String(label)} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl ${color}`}><SummaryIcon size={18} /></div>
              <p className="text-xs font-medium text-slate-500">{label}</p><strong className="mt-1 block text-xl font-bold text-slate-900">{value}</strong>
            </article>;
          })}
        </section>

        {isLead && <form onSubmit={(event) => { event.preventDefault(); applyFilters(); }} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[1.5fr_1fr_1fr_1fr_auto]">
           <input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder={t("searchDocument")} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-900 outline-none ring-blue-500 focus:ring-2" />
          <select value={filters.projectId} onChange={(event) => setFilters({ ...filters, projectId: event.target.value })} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"><option value="">Semua proyek</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          <select value={filters.engineerId} onChange={(event) => setFilters({ ...filters, engineerId: event.target.value })} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"><option value="">Semua engineer</option>{engineers.map((engineer) => <option key={engineer.id} value={engineer.id}>{engineer.full_name}</option>)}</select>
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-blue-500"><option value="">Semua status</option><option value="ANALYZING">Analyzing</option><option value="REVIEWED_BY_ENGINEER">Reviewed</option><option value="VERIFIED_BY_LEAD">Verified</option></select>
           <button type="submit" className="h-10 rounded-lg bg-slate-900 px-4 text-xs font-bold text-white hover:bg-slate-800">{t("apply")}</button>
        </form>}

        {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{error}</div>}
        {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">{t("loadingRegister")}</div> : <DocumentList documents={visibleDocuments} onRefresh={() => void load()} />}
      </div>
    </main>
  );
}
