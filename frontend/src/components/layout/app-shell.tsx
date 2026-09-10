"use client";

import { usePathname } from "next/navigation";
import { ClipboardCheck, FileStack, Gauge, Menu, Settings, X } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { ThemeToggle } from "./theme-toggle";

const navigation = [
  { href: "/", label: "Documents", icon: FileStack },
  { href: "/upload", label: "New inspection", icon: ClipboardCheck },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isReviewPage = pathname?.includes("/review");
  const [sidebarOpen, setSidebarOpen] = useState(
    () => typeof window === "undefined" || window.innerWidth > 1000,
  );

  return (
    <div className={`app-frame${sidebarOpen ? " sidebar-open" : " sidebar-collapsed"}`}>
      <button
        className="sidebar-backdrop"
        type="button"
        aria-label="Close navigation"
        onClick={() => setSidebarOpen(false)}
      />
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="sidebar-header">
          <Link className="brand" href="/" aria-label="REKSOLINDOQA home">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span><strong>REKSOLINDO</strong><small>Document assurance</small></span>
          </Link>
          <button
            className="sidebar-collapse-button"
            type="button"
            aria-label={sidebarOpen ? "Collapse navigation" : "Expand navigation"}
            title={sidebarOpen ? "Collapse navigation" : "Expand navigation"}
            onClick={() => setSidebarOpen((open) => !open)}
          >
            {sidebarOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </button>
        </div>
        <nav aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              className={`nav-link${
                (href === "/" ? pathname === "/" : pathname?.startsWith(href))
                  ? " nav-link-active"
                  : ""
              }`}
              href={href}
              key={href}
              title={label}
              aria-current={
                (href === "/" ? pathname === "/" : pathname?.startsWith(href))
                  ? "page"
                  : undefined
              }
              onClick={() => setSidebarOpen(false)}
            >
              <Icon size={17} aria-hidden="true" />{label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="system-panel">
          <div><Gauge size={15} aria-hidden="true" /><span>Local processing</span></div>
          <strong><i aria-hidden="true" />Operational</strong>
        </div>
        <button className="nav-link nav-button" type="button" disabled>
          <Settings size={17} aria-hidden="true" />Settings <span>Soon</span>
        </button>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div className="topbar-context">
            <button
              className="sidebar-toggle"
              type="button"
              aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen((open) => !open)}
            >
              {sidebarOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
            </button>
            <span className="environment-dot" />Local workspace
          </div>
          <div className="topbar-actions">
            <ThemeToggle />
            <div className="operator"><span>QA</span><p><strong>QA Engineer</strong><small>Single-user mode</small></p></div>
          </div>
        </header>
        <main className={isReviewPage ? "content content-compact" : "content"}>{children}</main>
      </div>
    </div>
  );
}
