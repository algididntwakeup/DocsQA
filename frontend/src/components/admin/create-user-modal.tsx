"use client";

import { X } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { CreateManagedUserPayload, UserRole } from "@/lib/api";

export function CreateUserModal({
  open,
  busy,
  onClose,
  onSubmit,
}: {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateManagedUserPayload) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Exclude<UserRole, "SUPERUSER">>("ENGINEER");

  if (!open) return null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ full_name: name.trim(), email: email.trim(), temporary_password: password, role });
    setName("");
    setEmail("");
    setPassword("");
    setRole("ENGINEER");
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="dialog" aria-modal="true" aria-labelledby="create-user-title">
    <div className="w-full max-w-lg border border-line bg-panel p-6 shadow-xl">
      <div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Account provisioning</p><h2 id="create-user-title" className="mt-2 text-xl font-semibold">Tambah User Baru</h2><p className="mt-1 text-sm text-muted">Berikan password sementara yang aman untuk user baru.</p></div><button type="button" className="button button-secondary btn-sm" aria-label="Close" onClick={onClose}><X size={16} /></button></div>
      <form className="mt-6 space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block text-xs font-medium text-ink-soft">Nama Lengkap<input className="mt-2 w-full border border-line-strong bg-input-bg px-3 py-3 text-sm text-ink" required value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="block text-xs font-medium text-ink-soft">Email<input className="mt-2 w-full border border-line-strong bg-input-bg px-3 py-3 text-sm text-ink" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label className="block text-xs font-medium text-ink-soft">Password Awal<input className="mt-2 w-full border border-line-strong bg-input-bg px-3 py-3 text-sm text-ink" type="password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label className="block text-xs font-medium text-ink-soft">Role<select className="filter-select mt-2 w-full" value={role} onChange={(event) => setRole(event.target.value as typeof role)}><option value="ENGINEER">Engineer</option><option value="LEAD_ENGINEER">Lead Engineer</option></select></label>
        <div className="flex justify-end gap-2 pt-2"><button type="button" className="button button-secondary" onClick={onClose}>Batal</button><button type="submit" className="button button-primary" disabled={busy}>{busy ? "Creating..." : "Create user"}</button></div>
      </form>
    </div>
  </div>;
}
