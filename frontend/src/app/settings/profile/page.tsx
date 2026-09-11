"use client";

import { AlertTriangle, CheckCircle2, KeyRound, LoaderCircle, UserCircle } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ApiError, changePassword, getCurrentUser, updateProfile, type UserSession } from "@/lib/api";
import { useLocale } from "@/components/layout/locale-provider";

export default function ProfileSettingsPage() {
  const { t } = useLocale();
  const [user, setUser] = useState<UserSession | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  useEffect(() => {
    void getCurrentUser()
      .then((current) => {
        setUser(current);
        setFullName(current.full_name);
        setEmail(current.email);
      })
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : t("loadProfileError")))
      .finally(() => setLoading(false));
  }, [t]);

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSavingProfile(true);
    try {
      const updated = await updateProfile({ full_name: fullName.trim(), email: email.trim() });
      setUser(updated);
      setFullName(updated.full_name);
      setEmail(updated.email);
      toast.success(t("profileUpdated"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("updateProfileError"));
    } finally {
      setSavingProfile(false);
    }
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);
    if (newPassword.length < 8) {
      setPasswordError(t("passwordMinLength"));
      return;
    }
    if (newPassword !== confirmation) {
      setPasswordError(t("passwordMismatch"));
      return;
    }
    setSavingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setPasswordSuccess(true);
    } catch (caught) {
      setPasswordError(caught instanceof ApiError ? caught.message : t("changePasswordError"));
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 space-y-6 font-sans">
      <div className="border-b border-slate-200 pb-5">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{t("accountSettings")}</p>
        <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{t("profile")}</h1>
        <p className="mt-1 text-xs text-slate-600">{t("personalDetailsHelp")}</p>
      </div>

      {loading ? (
        <div className="flex min-h-[260px] items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-slate-400">
          <LoaderCircle className="animate-spin text-blue-600" size={24} />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Profile Details Card */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <UserCircle size={22} />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">{t("personalDetails")}</h2>
                <p className="text-xs text-slate-500">{t("personalDetailsHelp")}</p>
              </div>
            </div>

            <form className="space-y-4" onSubmit={(event) => void submitProfile(event)}>
              <div>
                <label htmlFor="fullName" className="block text-xs font-semibold text-slate-700">
                  {t("fullName")}
                </label>
                <input
                  id="fullName"
                  required
                  minLength={1}
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-xs font-semibold text-slate-700">
                  {t("email")}
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              {error && (
                <p className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700">
                  <AlertTriangle size={15} />
                  <span>{error}</span>
                </p>
              )}

              {user && !error && (
                <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/50 p-2.5 text-xs text-emerald-700">
                  <CheckCircle2 size={15} />
                  <span>{t("profileLoadedFor", { role: user.role.replaceAll("_", " ") })}</span>
                </p>
              )}

              <button
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50 transition"
                type="submit"
                disabled={savingProfile}
              >
                {savingProfile ? <LoaderCircle className="animate-spin" size={15} /> : <UserCircle size={15} />}
                <span>{savingProfile ? t("saving") : t("saveProfile")}</span>
              </button>
            </form>
          </section>

          {/* Security Card */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <KeyRound size={22} />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">{t("security")}</h2>
                <p className="text-xs text-slate-500">{t("securityHelp")}</p>
              </div>
            </div>

            <form className="space-y-4" onSubmit={(event) => void submitPassword(event)}>
              <div>
                <label htmlFor="currentPassword" className="block text-xs font-semibold text-slate-700">
                  {t("currentPassword")}
                </label>
                <input
                  id="currentPassword"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="newPassword" className="block text-xs font-semibold text-slate-700">
                  {t("newPassword")}
                </label>
                <input
                  id="newPassword"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="confirmNewPassword" className="block text-xs font-semibold text-slate-700">
                  {t("confirmNewPassword")}
                </label>
                <input
                  id="confirmNewPassword"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              {passwordError && (
                <p className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700">
                  <AlertTriangle size={15} />
                  <span>{passwordError}</span>
                </p>
              )}

              {passwordSuccess && (
                <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/50 p-2.5 text-xs text-emerald-700">
                  <CheckCircle2 size={15} />
                  <span>{t("passwordChanged")}</span>
                </p>
              )}

              <button
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50 transition"
                type="submit"
                disabled={savingPassword}
              >
                {savingPassword ? <LoaderCircle className="animate-spin" size={15} /> : <KeyRound size={15} />}
                <span>{savingPassword ? t("saving") : t("changePassword")}</span>
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
