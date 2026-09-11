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
    void getCurrentUser().then((current) => {
      setUser(current); setFullName(current.full_name); setEmail(current.email);
    }).catch((caught) => setError(caught instanceof ApiError ? caught.message : t("loadProfileError"))).finally(() => setLoading(false));
  }, [t]);

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setSavingProfile(true);
    try {
      const updated = await updateProfile({ full_name: fullName.trim(), email: email.trim() });
      setUser(updated); setFullName(updated.full_name); setEmail(updated.email); toast.success(t("profileUpdated"));
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : t("updateProfileError")); }
    finally { setSavingProfile(false); }
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPasswordError(null); setPasswordSuccess(false);
    if (newPassword.length < 8) { setPasswordError(t("passwordMinLength")); return; }
    if (newPassword !== confirmation) { setPasswordError(t("passwordMismatch")); return; }
    setSavingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmation(""); setPasswordSuccess(true);
    } catch (caught) { setPasswordError(caught instanceof ApiError ? caught.message : t("changePasswordError")); }
    finally { setSavingPassword(false); }
  }

  return <div className="rq-page rq-settings-page"><div className="rq-page-heading"><div><p className="rq-kicker">{t("accountSettings")}</p><h1>{t("profile")}</h1><p>{t("personalDetailsHelp")}</p></div></div>{loading ? <div className="rq-settings-card"><div className="rq-empty"><LoaderCircle className="rq-spin" size={20} />{t("loadingReport")}</div></div> : <div className="grid gap-5 lg:grid-cols-2"><section className="rq-settings-card"><div className="rq-settings-card-heading"><span className="rq-settings-icon"><UserCircle size={19} /></span><div><h2>{t("personalDetails")}</h2><p>{t("personalDetailsHelp")}</p></div></div><form className="rq-settings-form" onSubmit={(event) => void submitProfile(event)}><label>{t("fullName")}<input required minLength={1} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label><label>{t("email")}<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{error && <p className="rq-form-error"><AlertTriangle size={15} />{error}</p>}{user && !error && <p className="rq-form-success"><CheckCircle2 size={15} />{t("profileLoadedFor", { role: user.role.replaceAll("_", " ") })}</p>}<button className="rq-primary-button" type="submit" disabled={savingProfile}>{savingProfile ? <LoaderCircle className="rq-spin" size={15} /> : <UserCircle size={15} />}{savingProfile ? t("saving") : t("saveProfile")}</button></form></section><section className="rq-settings-card"><div className="rq-settings-card-heading"><span className="rq-settings-icon"><KeyRound size={19} /></span><div><h2>{t("security")}</h2><p>{t("securityHelp")}</p></div></div><form className="rq-settings-form" onSubmit={(event) => void submitPassword(event)}><label>{t("currentPassword")}<input type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label><label>{t("newPassword")}<input type="password" autoComplete="new-password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label><label>{t("confirmNewPassword")}<input type="password" autoComplete="new-password" minLength={8} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>{passwordError && <p className="rq-form-error"><AlertTriangle size={15} />{passwordError}</p>}{passwordSuccess && <p className="rq-form-success"><CheckCircle2 size={15} />{t("passwordChanged")}</p>}<button className="rq-primary-button" type="submit" disabled={savingPassword}>{savingPassword ? <LoaderCircle className="rq-spin" size={15} /> : <KeyRound size={15} />}{savingPassword ? t("saving") : t("changePassword")}</button></form></section></div>}</div>;
}
