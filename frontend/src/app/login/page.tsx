"use client";

import { ArrowRight, KeyRound, LockKeyhole, Mail, ShieldCheck, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, login } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { ReksolindoLogo } from "@/components/layout/reksolindo-logo";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLocale();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      router.push("/projects");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("unableSignIn"));
    } finally {
      setSubmitting(false);
    }
  }

  function startSso() {
    const redirectUri = typeof window !== "undefined"
      ? `${window.location.origin}/auth/sso/callback`
      : `${process.env.NEXT_PUBLIC_APP_URL ?? ""}/auth/sso/callback`;
    const clientId = process.env.NEXT_PUBLIC_BIMA_CLIENT_ID ?? "prism";
    const bimaBase = (process.env.NEXT_PUBLIC_BIMA_BASE_URL ?? "https://bima.reksolindo.co.id").replace(/\/+$/, "");
    window.location.href = `${bimaBase}/sso/authorize?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=profile%20roles%20permissions%20email%20department`;
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-background p-4 sm:p-6 font-sans">
      <div className="absolute right-6 top-6 flex items-center gap-2">
        <ThemeToggle />
        <LanguageToggle />
      </div>

      <div className="grid w-full max-w-4xl overflow-hidden rounded-3xl border border-border bg-card shadow-xl shadow-slate-900/5 md:grid-cols-2">
        {/* Aside / Branding Panel */}
        <section className="flex flex-col justify-between bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 p-8 sm:p-10 text-white">
          <div>
            <ReksolindoLogo variant="dark" />
          </div>

          <div className="my-10 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400">
              {t("loginKicker")}
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
              {t("loginTitle")}
            </h1>
            <p className="text-xs text-border leading-relaxed max-w-sm">
              {t("loginDescription")}
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
            <ShieldCheck size={16} />
            <span>{t("roleAware")}</span>
          </div>
        </section>

        {/* Login Form Panel */}
        <section className="flex flex-col justify-center p-8 sm:p-12">
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">
              {t("secureWorkspace")}
            </p>
            <h2 className="text-xl font-bold text-foreground">{t("welcomeBack")}</h2>
            <p className="text-xs text-muted-foreground">{t("signInDescription")}</p>
          </div>

          <form className="mt-8 space-y-4" onSubmit={submit}>
            <div>
               <label htmlFor="username" className="block text-xs font-semibold text-foreground">
                  {t("usernameOrEmail")}
              </label>
              <div className="relative mt-1">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                   id="username"
                   aria-label="Email"
                   type="text"
                   autoComplete="username"
                    placeholder={t("usernameOrEmail")}
                  required
                   value={username}
                   onChange={(event) => setUsername(event.target.value)}
                  className="h-10 w-full rounded-xl border border-border bg-card pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-foreground">
                {t("password")}
              </label>
              <div className="relative mt-1">
                <LockKeyhole size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder={t("enterPassword")}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="h-10 w-full rounded-xl border border-border bg-card pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none"
                />
              </div>
            </div>

            {error && (
              <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs font-medium text-rose-700" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-primary-foreground shadow-xs transition hover:bg-primary/90 disabled:opacity-50"
            >
              <LockKeyhole size={15} />
              <span>{submitting ? t("signingIn") : t("signIn")}</span>
              <ArrowRight size={15} />
            </button>
          </form>
          <div className="my-6 flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            <span>{t("instantSignIn")}</span>
            <span className="h-px flex-1 bg-border" />
          </div>
          <button
            type="button"
            onClick={startSso}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-primary/20 bg-accent px-4 text-xs font-bold text-accent-foreground transition hover:border-primary/40 hover:bg-accent/80"
          >
            <Sparkles size={15} />
            {t("bimaSso")}
            <KeyRound size={15} />
          </button>
        </section>
      </div>
    </div>
  );
}
