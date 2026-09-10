"use client";

import { ArrowRight, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
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
    <div className="rq-login-page">
      <div className="rq-login-card">
        <section className="rq-login-aside">
          <div className="rq-brand rq-brand-light"><span className="rq-brand-mark">R</span><span>Reksolindo</span><b>v1.0</b></div>
          <div><p className="rq-kicker">Document assurance platform</p><h1>Clarity for every engineering review.</h1><p>Keep plant documents, ownership, and lead verification in one calm workspace.</p></div>
          <div className="rq-login-trust"><ShieldCheck size={18} /> Role-aware project access</div>
        </section>
        <section className="rq-login-form-section"><div className="rq-login-heading"><p className="rq-kicker">Secure workspace</p><h2>Welcome back</h2><p>Sign in with your engineering account to continue.</p></div>
          <form className="rq-form" onSubmit={submit}>
            <label>Email<div className="rq-input-wrap"><Mail size={17} /><input type="email" autoComplete="email" placeholder="you@company.com" required value={email} onChange={(event) => setEmail(event.target.value)} /></div></label>
            <label>Password<div className="rq-input-wrap"><LockKeyhole size={17} /><input type="password" autoComplete="current-password" placeholder="Enter your password" required value={password} onChange={(event) => setPassword(event.target.value)} /></div></label>
            {error && <p className="rq-form-error" role="alert">{error}</p>}
            <button className="rq-submit" type="submit" disabled={submitting}><LockKeyhole size={16} />{submitting ? "Signing in..." : "Sign in · Enter workspace"}<ArrowRight size={16} /></button>
          </form>
        </section>
      </div>
    </div>
  );
}
