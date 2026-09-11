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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs font-sans"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-user-title"
    >
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Account Provisioning</p>
            <h2 id="create-user-title" className="mt-1 text-lg font-bold text-slate-900">
              Tambah User Baru
            </h2>
            <p className="text-xs text-slate-500">Berikan password sementara yang aman untuk user baru.</p>
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <form className="mt-4 space-y-4" onSubmit={(event) => void submit(event)}>
          <div>
            <label className="block text-xs font-semibold text-slate-700">Nama Lengkap</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. John Doe"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700">Email</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="e.g. engineer@reksolindo.com"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700">Password Awal</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
              type="password"
              minLength={8}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 karakter"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700">Role</label>
            <select
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
              value={role}
              onChange={(event) => setRole(event.target.value as typeof role)}
            >
              <option value="ENGINEER">Engineer</option>
              <option value="LEAD_ENGINEER">Lead Engineer</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-100">
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              onClick={onClose}
            >
              Batal
            </button>
            <button
              type="submit"
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50"
              disabled={busy}
            >
              {busy ? "Creating..." : "Create user"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
