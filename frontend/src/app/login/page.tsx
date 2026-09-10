"use client";

import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.push("/projects");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-110px)] max-w-5xl items-center justify-center py-10">
      <div className="grid w-full max-w-4xl overflow-hidden border border-line bg-panel shadow-sm md:grid-cols-[1.05fr_.95fr]">
        <section className="hidden bg-slate-950 p-10 text-white md:block">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-sky-300">REKSOLINDO / CONTROL ROOM</p>
          <h1 className="mt-20 max-w-sm text-4xl font-semibold leading-tight tracking-tight">Keep every project review moving.</h1>
          <p className="mt-5 max-w-sm text-sm leading-6 text-slate-300">A shared workspace for plant documents, engineering ownership, and lead verification.</p>
          <div className="mt-16 flex items-center gap-3 text-xs text-slate-300"><ShieldCheck size={18} className="text-emerald-400" /> Role-aware project access</div>
        </section>
        <section className="p-7 sm:p-10">
          <div className="mb-9"><p className="eyebrow">Secure workspace</p><h2 className="mt-2 text-2xl font-semibold tracking-tight">Sign in to Document QC</h2><p className="mt-2 text-sm text-muted">Use your engineering account to continue.</p></div>
          <form className="space-y-5" onSubmit={submit}>
            <label className="block text-xs font-medium text-ink-soft">Email<input className="mt-2 w-full border border-line-strong bg-input-bg px-3 py-3 text-sm text-ink" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label className="block text-xs font-medium text-ink-soft">Password<input className="mt-2 w-full border border-line-strong bg-input-bg px-3 py-3 text-sm text-ink" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {error && <p className="border border-danger px-3 py-2 text-xs text-danger" role="alert">{error}</p>}
            <button className="button button-primary w-full" type="submit" disabled={submitting}><LockKeyhole size={15} />{submitting ? "Authenticating..." : "Enter workspace"}<ArrowRight size={15} /></button>
          </form>
        </section>
      </div>
    </div>
  );
}
