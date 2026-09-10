"use client";

import { usePathname } from "next/navigation";
import { FolderKanban, LogOut, Menu, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { getCurrentUser, logout, type UserSession } from "@/lib/api";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReviewPage = pathname?.includes("/review");
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    if (pathname !== "/login") void getCurrentUser().then(setUser).catch(() => setUser(null));
  }, [pathname]);

  if (pathname === "/login") return <>{children}</>;
  const canManageUsers = user?.role === "LEAD_ENGINEER" || user?.role === "SUPERUSER";
  const initials = user?.full_name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "RQ";

  return (
    <div className="rq-app">
      <header className="rq-nav">
        <div className="rq-nav-inner">
          <Link className="rq-brand" href="/projects"><span className="rq-brand-mark">R</span><span>Reksolindo</span><b>v1.0</b></Link>
          <button className="rq-menu-button" type="button" aria-label="Toggle navigation" onClick={() => setMenuOpen((open) => !open)}><Menu size={20} /></button>
          <nav className={`rq-main-nav${menuOpen ? " rq-main-nav-open" : ""}`} aria-label="Primary navigation">
            <Link className={pathname?.startsWith("/projects") ? "rq-nav-link rq-nav-link-active" : "rq-nav-link"} href="/projects" onClick={() => setMenuOpen(false)}><FolderKanban size={16} />Projects</Link>
            <Link className="rq-nav-link" href="/" onClick={() => setMenuOpen(false)}><ShieldCheck size={16} />Reference Library</Link>
            {canManageUsers && <Link className={pathname?.startsWith("/admin/users") ? "rq-nav-link rq-nav-link-active" : "rq-nav-link"} href="/admin/users" onClick={() => setMenuOpen(false)}><Users size={16} />Manage Users</Link>}
          </nav>
          <div className="rq-profile"><span className="rq-avatar">{initials}</span><span className="rq-profile-copy"><strong>{user?.full_name ?? "Workspace user"}</strong><small>{user?.role?.replaceAll("_", " ") ?? "Authenticated"}</small></span><button className="rq-logout" type="button" onClick={() => void logout()}><LogOut size={15} />Logout</button></div>
        </div>
      </header>
      <main className={isReviewPage ? "rq-content rq-content-review" : "rq-content"}>{children}</main>
    </div>
  );
}
