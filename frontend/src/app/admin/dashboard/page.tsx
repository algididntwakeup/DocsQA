"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, FolderKanban, LoaderCircle, ShieldCheck, Users } from "lucide-react";
import { ApiError, getCurrentUser, listManagedUsers, type ManagedUser, type UserSession } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";

export default function SuperuserDashboardPage() {
  const router = useRouter();
  const { t } = useLocale();
  const [user, setUser] = useState<UserSession | null>(null);
  const [users, setUsers] = useState<ManagedUser[]>([]);
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

        const managed = await listManagedUsers().catch(() => []);
        if (active) {
          setUsers(managed);
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
            <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700">
              <Activity size={13} />
              {t("activeProject")}
            </span>
          </div>
          <h2 className="mt-3 text-sm font-bold text-foreground">{t("portfolioOverview")}</h2>
          <Link
            href="/projects"
            className="mt-2 inline-flex text-xs font-semibold text-primary hover:underline"
          >
            {t("projects")} →
          </Link>
        </article>
      </section>
    </div>
  );
}
