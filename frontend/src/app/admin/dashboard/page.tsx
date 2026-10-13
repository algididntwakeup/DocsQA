"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, FolderKanban, LoaderCircle, ShieldCheck, Users } from "lucide-react";
import {
  ApiError,
  fetchPortfolioStats,
  getCurrentUser,
  listManagedUsers,
  type ManagedUser,
  type PortfolioStats,
  type UserSession,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useLocale } from "@/components/layout/locale-provider";

export default function SuperuserDashboardPage() {
  const router = useRouter();
  const { t } = useLocale();
  const [user, setUser] = useState<UserSession | null>(null);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const currentUser = await getCurrentUser();
        // The dashboard is a superuser control panel: everyone else is sent
        // back to the project explorer.
        if (!currentUser.is_superuser) {
          router.replace("/projects");
          return;
        }
        if (active) setUser(currentUser);

        // Both calls are required, and a refusal must surface as a message: a
        // swallowed error here previously rendered every counter as 0.
        const [managed, portfolio] = await Promise.all([
          listManagedUsers(),
          fetchPortfolioStats(),
        ]);
        if (active) {
          setUsers(managed);
          setStats(portfolio);
          setLoading(false);
        }
      } catch (caught) {
        if (!active) return;
        if (caught instanceof ApiError && caught.status === 401) {
          router.replace("/login");
          return;
        }
        setError(caught instanceof Error ? caught.message : "Could not load the dashboard.");
        setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [router]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center gap-2 text-sm text-muted-foreground">
        <LoaderCircle size={16} className="animate-spin" />
        {t("loading")}
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-3xl p-6 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  const leadCount = users.filter((account) => account.role === "LEAD_ENGINEER").length;
  const engineerCount = users.filter((account) => account.role === "ENGINEER").length;
  const owners = stats?.projects_by_owner ?? [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <header className="rounded-2xl border border-border/70 bg-card p-6 shadow-sm">
        <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">
          {t("roleSuperuser")}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-foreground">
          Superuser Dashboard — PRISM Control Panel
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {user?.full_name} · {user?.email}
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <Users size={18} />
            </span>
            <span className="text-2xl font-bold text-foreground">{users.length}</span>
          </div>
          <h2 className="mt-3 text-sm font-bold text-foreground">{t("manageUsers")}</h2>
          <Link
            href="/admin/users"
            className="mt-2 inline-flex text-xs font-semibold text-primary hover:underline"
          >
            {t("manageUsers")} →
          </Link>
        </article>

        <article className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <ShieldCheck size={18} />
            </span>
            <span className="text-2xl font-bold text-foreground">{leadCount}</span>
          </div>
          <h2 className="mt-3 text-sm font-bold text-foreground">{t("roleLead")}</h2>
          <p className="mt-2 text-xs text-muted-foreground">
            {engineerCount} {t("roleEngineer")}
          </p>
        </article>

        <article className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <FolderKanban size={18} />
            </span>
            <span className="text-2xl font-bold text-foreground">{stats?.total_projects ?? 0}</span>
          </div>
          <h2 className="mt-3 text-sm font-bold text-foreground">{t("portfolioOverview")}</h2>
          <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
            <Activity size={12} className="text-emerald-600" />
            {stats?.total_documents ?? 0} {t("totalDocuments")} · {stats?.finished_projects ?? 0}{" "}
            {t("finishedProjects")}
          </p>
          <Link
            href="/projects"
            className="mt-2 inline-flex text-xs font-semibold text-primary hover:underline"
          >
            {t("projects")} →
          </Link>
        </article>
      </section>

      {owners.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-bold text-foreground">{t("projectsByOwner")}</h2>
          <Card className="overflow-hidden">
            <Table className="text-xs border-collapse">
              <TableHeader className="bg-muted/60">
                <TableRow>
                  <TableHead>{t("owner")}</TableHead>
                  <TableHead className="text-right">{t("projectCount")}</TableHead>
                  <TableHead className="text-right">{t("documentCount")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {owners.map((owner) => (
                  <TableRow key={owner.owner_id}>
                    <TableCell className="font-semibold text-foreground">{owner.owner_name}</TableCell>
                    <TableCell className="text-right text-muted-foreground">{owner.project_count}</TableCell>
                    <TableCell className="text-right text-muted-foreground">{owner.document_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </section>
      )}
    </div>
  );
}
