import { ClipboardCheck, FileStack, Gauge, Settings } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { ThemeToggle } from "./theme-toggle";

const navigation = [
  { href: "/", label: "Documents", icon: FileStack },
  { href: "/upload", label: "New inspection", icon: ClipboardCheck },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="MatQC home">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span><strong>MATQC</strong><small>Document assurance</small></span>
        </Link>
        <nav aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link className="nav-link" href={href} key={href}>
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
          <div><span className="environment-dot" />Local workspace</div>
          <div className="topbar-actions">
            <ThemeToggle />
            <div className="operator"><span>QA</span><p><strong>QA Engineer</strong><small>Single-user mode</small></p></div>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
