"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronDown, FolderKanban, KeyRound, LogOut, Menu, ShieldCheck, User, Users, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { getCurrentUser, logout, type UserSession } from "@/lib/api";
import { useLocale } from "./locale-provider";
import { LanguageToggle } from "./language-toggle";
import { ThemeToggle } from "./theme-toggle";
import { ReksolindoLogo } from "./reksolindo-logo";

function roleLabel(user: UserSession | null, t: (key: "roleEngineer" | "roleLead" | "roleSuperuser") => string) {
  if (user?.role === "LEAD_ENGINEER") return t("roleLead");
  if (user?.role === "SUPERUSER") return t("roleSuperuser");
  return t("roleEngineer");
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReviewPage = Boolean(pathname?.includes("/review"));
  const [user, setUser] = useState<UserSession | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const { t } = useLocale();

  useEffect(() => {
    if (pathname !== "/login") void getCurrentUser().then(setUser).catch(() => setUser(null));
  }, [pathname]);

  useEffect(() => {
    if (!profileOpen) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (!profileRef.current?.contains(event.target as Node)) setProfileOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setProfileOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [profileOpen]);

  if (pathname === "/login") return <>{children}</>;
  const canManageUsers = user?.role === "LEAD_ENGINEER" || user?.role === "SUPERUSER";
  const initials = user?.full_name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "RK";
  const navLinks = [
    { href: "/projects", label: t("projects"), icon: FolderKanban },
    { href: "/documents", label: t("inspectionWorkspace"), icon: ShieldCheck },
    ...(canManageUsers
      ? [{ href: "/admin/users", label: t("manageUsers"), icon: Users }]
      : []),
  ];

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-background text-foreground font-sans">
      <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-border bg-card/95 px-4 backdrop-blur-md sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-4 sm:gap-8">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground md:hidden"
            aria-expanded={navOpen}
            aria-controls="app-mobile-nav"
            aria-label={navOpen ? "Close navigation menu" : "Open navigation menu"}
            onClick={() => setNavOpen((open) => !open)}
          >
            {navOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
          <Link className="flex shrink-0 items-center transition hover:opacity-90" href="/projects" aria-label="PRISM home">
            <ReksolindoLogo />
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label={t("projects")}>
            {navLinks.map((link) => {
              const Icon = link.icon;
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    active
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                  href={link.href}
                >
                  <Icon size={15} />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <ThemeToggle />
          <LanguageToggle />
          <div className="h-4 w-[1px] bg-border" />
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              aria-expanded={profileOpen}
              aria-haspopup="menu"
              onClick={() => setProfileOpen((open) => !open)}
              className="flex max-w-[220px] items-center gap-2 rounded-lg p-1 text-left transition hover:bg-muted"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-accent text-xs font-bold text-accent-foreground">
                {initials}
              </span>
              <span className="hidden min-w-0 sm:block">
                <strong className="block max-w-[120px] truncate text-xs font-bold text-foreground">
                  {user?.full_name ?? t("workspaceUser")}
                </strong>
                <small className="block text-[10px] text-muted-foreground">
                  {roleLabel(user, t)}
                </small>
              </span>
              <ChevronDown
                size={14}
                className={`shrink-0 text-muted-foreground transition-transform duration-150 ${
                  profileOpen ? "rotate-180" : ""
                }`}
              />
            </button>
            {profileOpen && (
              <div
                className="absolute right-0 top-[calc(100%+8px)] z-50 w-64 overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-xl ring-1 ring-black/5"
                role="menu"
              >
                <div className="border-b border-border bg-muted/50 px-4 py-3">
                  <p className="truncate text-sm font-bold text-foreground">
                    {user?.full_name ?? t("workspaceUser")}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">{user?.email ?? ""}</p>
                  <span className="mt-2 inline-flex rounded-md bg-accent px-2 py-0.5 text-[10px] font-semibold text-accent-foreground ring-1 ring-primary/10">
                    {roleLabel(user, t)}
                  </span>
                </div>
                <div className="py-1">
                  <Link
                    role="menuitem"
                    href="/settings/profile"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <User size={14} className="text-muted-foreground" />
                    {t("profile")}
                  </Link>
                  <Link
                    role="menuitem"
                    href="/settings/password"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <KeyRound size={14} className="text-muted-foreground" />
                    {t("changePassword")}
                  </Link>
                </div>
                <div className="border-t border-border py-1">
                  <button
                    role="menuitem"
                    type="button"
                    onClick={() => void logout()}
                    className="flex w-full items-center gap-2 px-4 py-2 text-xs font-semibold text-destructive transition-colors hover:bg-destructive/10"
                  >
                    <LogOut size={14} />
                    {t("logout")}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
      {navOpen && (
        <nav
          id="app-mobile-nav"
          className="flex flex-col gap-1 border-b border-border bg-card px-4 py-3 md:hidden"
          aria-label={t("projects")}
        >
          {navLinks.map((link) => {
            const Icon = link.icon;
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
                href={link.href}
                onClick={() => setNavOpen(false)}
              >
                <Icon size={16} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      )}
      <main className="flex min-h-0 flex-1 flex-col">
        {isReviewPage ? (
          children
        ) : (
          <div className="mx-auto w-full max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">{children}</div>
        )}
      </main>
    </div>
  );
}
