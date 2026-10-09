"use client";

import { X } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { CreateManagedUserPayload } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";

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
  const { t } = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<CreateManagedUserPayload["role"]>("ENGINEER");

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
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-border/60 pb-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">{t("accountProvisioning")}</p>
            <h2 id="create-user-title" className="mt-1 text-lg font-bold text-foreground">
              {t("addUser")}
            </h2>
            <p className="text-xs text-muted-foreground">{t("temporaryPasswordHelp")}</p>
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
             aria-label={t("close")}
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <form className="mt-4 space-y-4" onSubmit={(event) => void submit(event)}>
          <div>
             <label className="block text-xs font-semibold text-foreground">{t("fullName")}</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs text-foreground focus:border-ring focus:outline-none"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. John Doe"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground">Email</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs text-foreground focus:border-ring focus:outline-none"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="e.g. engineer@reksolindo.com"
            />
          </div>

          <div>
             <label className="block text-xs font-semibold text-foreground">{t("initialPassword")}</label>
            <input
              className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs text-foreground focus:border-ring focus:outline-none"
              type="password"
              minLength={8}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
               placeholder={t("minimumPassword")}
            />
          </div>

          <div>
             <label className="block text-xs font-semibold text-foreground">{t("role")}</label>
            <select
              className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs text-foreground focus:border-ring focus:outline-none"
              value={role}
              onChange={(event) => setRole(event.target.value as typeof role)}
            >
              <option value="ENGINEER">Engineer</option>
              <option value="LEAD_ENGINEER">Lead Engineer</option>
              <option value="HRGA">HR/GA</option>
              <option value="FINANCE">Finance</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-border/60">
            <button
              type="button"
              className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted/40"
              onClick={onClose}
            >
               {t("cancel")}
            </button>
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 disabled:opacity-50"
              disabled={busy}
            >
               {busy ? t("creatingUser") : t("createUser")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
