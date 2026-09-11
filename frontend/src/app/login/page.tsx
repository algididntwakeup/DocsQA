"use client";

import { ArrowRight, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, login } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";
import { LanguageToggle } from "@/components/layout/language-toggle";
export default function LoginPage() {
  const router = useRouter();
  const { t } = useLocale();
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
      setError(caught instanceof ApiError ? caught.message : t("unableSignIn"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rq-login-page"><div className="absolute right-4 top-4"><LanguageToggle /></div>
      <div className="rq-login-card">
        <section className="rq-login-aside">
          <div className="rq-brand rq-brand-light"><span className="rq-brand-mark">R</span><span>Reksolindo QA</span><b>v1.0</b></div>
          <div><p className="rq-kicker">{t("loginKicker")}</p><h1>{t("loginTitle")}</h1><p>{t("loginDescription")}</p></div>
          <div className="rq-login-trust"><ShieldCheck size={18} /> {t("roleAware")}</div>
        </section>
        <section className="rq-login-form-section"><div className="rq-login-heading"><p className="rq-kicker">{t("secureWorkspace")}</p><h2>{t("welcomeBack")}</h2><p>{t("signInDescription")}</p></div>
          <form className="rq-form" onSubmit={submit}>
            <label>{t("email")}<div className="rq-input-wrap"><Mail size={17} /><input type="email" autoComplete="email" placeholder="you@company.com" required value={email} onChange={(event) => setEmail(event.target.value)} /></div></label>
            <label>{t("password")}<div className="rq-input-wrap"><LockKeyhole size={17} /><input type="password" autoComplete="current-password" placeholder={t("enterPassword")} required value={password} onChange={(event) => setPassword(event.target.value)} /></div></label>
            {error && <p className="rq-form-error" role="alert">{error}</p>}
            <button className="rq-submit" type="submit" disabled={submitting}><LockKeyhole size={16} />{submitting ? t("signingIn") : t("signIn")}<ArrowRight size={16} /></button>
          </form>
        </section>
      </div>
    </div>
  );
}
