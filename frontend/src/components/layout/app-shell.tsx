"use client";

import { usePathname } from "next/navigation";
import { FolderKanban, LogOut, Menu, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { getCurrentUser, logout, type UserSession } from "@/lib/api";
import { useLocale } from "./locale-provider";
import { LanguageToggle } from "./language-toggle";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReviewPage = pathname?.includes("/review");
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState<UserSession | null>(null);
  const { t } = useLocale();

  useEffect(() => {
    if (pathname !== "/login") void getCurrentUser().then(setUser).catch(() => setUser(null));
  }, [pathname]);

  if (pathname === "/login" || isReviewPage) return <>{children}</>;
  const canManageUsers = user?.role === "LEAD_ENGINEER" || user?.role === "SUPERUSER";
  const initials = user?.full_name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "RQ";

  return (
    <div className="rq-app min-h-screen flex flex-col overflow-x-hidden bg-slate-950 text-slate-100">
      <header className="rq-nav">
        <div className="rq-nav-inner">
          <Link className="rq-brand" href="/projects"><span className="rq-brand-mark">R</span><span>Reksolindo QA </span><b>v1.0</b></Link>
          <button className="rq-menu-button" type="button" aria-label={t("toggleNavigation")} onClick={() => setMenuOpen((open) => !open)}><Menu size={20} /></button>
          <nav className={`rq-main-nav${menuOpen ? " rq-main-nav-open" : ""}`} aria-label={t("projects")}>
            <Link className={pathname?.startsWith("/projects") ? "rq-nav-link rq-nav-link-active" : "rq-nav-link"} href="/projects" onClick={() => setMenuOpen(false)}><FolderKanban size={16} />{t("projects")}</Link>
            <Link className="rq-nav-link" href="/" onClick={() => setMenuOpen(false)}><ShieldCheck size={16} />{t("referenceLibrary")}</Link>
            {canManageUsers && <Link className={pathname?.startsWith("/admin/users") ? "rq-nav-link rq-nav-link-active" : "rq-nav-link"} href="/admin/users" onClick={() => setMenuOpen(false)}><Users size={16} />{t("manageUsers")}</Link>}
           </nav>
           <div className="flex items-center gap-2"><LanguageToggle /><Link className="rq-profile" href="/settings/profile" aria-label={t("accountSettings")}><span className="rq-avatar">{initials}</span><span className="rq-profile-copy"><strong>{user?.full_name ?? t("workspaceUser")}</strong><small>{user?.role?.replaceAll("_", " ") ?? t("authenticated")}</small></span></Link><button className="rq-logout" type="button" onClick={() => void logout()}><LogOut size={15} />{t("logout")}</button></div>
        </div>
      </header>
      <main className={isReviewPage ? "rq-content rq-content-review" : "rq-content"}>{children}</main>
    </div>
  );
}
