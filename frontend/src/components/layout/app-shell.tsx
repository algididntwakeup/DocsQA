"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronDown, FolderKanban, KeyRound, LogOut, ShieldCheck, User, Users } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { getCurrentUser, logout, type UserSession } from "@/lib/api";
import { useLocale } from "./locale-provider";
import { LanguageToggle } from "./language-toggle";
import { ReksolindoLogo } from "./reksolindo-logo";

function roleLabel(user: UserSession | null, t: (key: "roleEngineer" | "roleLead" | "roleSuperuser") => string) {
  if (user?.role === "LEAD_ENGINEER") return t("roleLead");
  if (user?.role === "SUPERUSER") return t("roleSuperuser");
  return t("roleEngineer");
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReviewPage = pathname?.includes("/review");
  const [user, setUser] = useState<UserSession | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
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

  if (pathname === "/login" || isReviewPage) return <>{children}</>;
  const canManageUsers = user?.role === "LEAD_ENGINEER" || user?.role === "SUPERUSER";
  const initials = user?.full_name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "RK";

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-50 text-slate-900 flex flex-col font-sans">
      <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur-md sm:px-6 shadow-2xs">
        <div className="flex min-w-0 items-center gap-8">
          <Link className="flex shrink-0 items-center transition hover:opacity-90" href="/projects" aria-label="Reksolindo Home">
            <ReksolindoLogo />
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label={t("projects")}>
            <Link
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                pathname?.startsWith("/projects")
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
              href="/projects"
            >
              <FolderKanban size={15} />
              {t("projects")}
            </Link>
            <Link
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                pathname?.startsWith("/documents")
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
              href="/documents"
            >
              <ShieldCheck size={15} />
              Inspection Workspace
            </Link>
            {canManageUsers && (
              <Link
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                  pathname?.startsWith("/admin/users")
                    ? "bg-blue-50 text-blue-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
                href="/admin/users"
              >
                <Users size={15} />
                {t("manageUsers")}
              </Link>
            )}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <LanguageToggle />
          <div className="h-4 w-[1px] bg-slate-200" />
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              aria-expanded={profileOpen}
              aria-haspopup="menu"
              onClick={() => setProfileOpen((open) => !open)}
              className="flex max-w-[220px] items-center gap-2 rounded-lg p-1 text-left transition hover:bg-slate-100"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-blue-200 bg-blue-50 text-xs font-bold text-blue-700">
                {initials}
              </span>
              <span className="hidden min-w-0 sm:block">
                <strong className="block max-w-[120px] truncate text-xs font-bold text-slate-800">
                  {user?.full_name ?? t("workspaceUser")}
                </strong>
                <small className="block text-[10px] text-slate-500">
                  {roleLabel(user, t)}
                </small>
              </span>
              <ChevronDown
                size={14}
                className={`shrink-0 text-slate-400 transition-transform duration-150 ${
                  profileOpen ? "rotate-180" : ""
                }`}
              />
            </button>
            {profileOpen && (
              <div
                className="absolute right-0 top-[calc(100%+8px)] z-50 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10 ring-1 ring-black/5"
                role="menu"
              >
                <div className="border-b border-slate-100 px-4 py-3 bg-slate-50/50">
                  <p className="truncate text-sm font-bold text-slate-900">
                    {user?.full_name ?? t("workspaceUser")}
                  </p>
                  <p className="truncate text-xs text-slate-500">{user?.email ?? ""}</p>
                  <span className="mt-2 inline-flex rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 ring-1 ring-blue-700/10">
                    {roleLabel(user, t)}
                  </span>
                </div>
                <div className="py-1">
                  <Link
                    role="menuitem"
                    href="/settings/profile"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900"
                  >
                    <User size={14} className="text-slate-400" />
                    {t("profile")}
                  </Link>
                  <Link
                    role="menuitem"
                    href="/settings/password"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900"
                  >
                    <KeyRound size={14} className="text-slate-400" />
                    {t("changePassword")}
                  </Link>
                </div>
                <div className="border-t border-slate-100 py-1">
                  <button
                    role="menuitem"
                    type="button"
                    onClick={() => void logout()}
                    className="flex w-full items-center gap-2 px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors"
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
      <main className="flex-1 w-full">{children}</main>
    </div>
  );
}
