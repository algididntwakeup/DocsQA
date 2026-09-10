"use client";

import { AlertTriangle, CheckCircle2, KeyRound, LoaderCircle } from "lucide-react";
import { FormEvent, useState } from "react";
import { ApiError, changePassword } from "@/lib/api";

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    if (newPassword.length < 8) { setError("New password must be at least 8 characters."); return; }
    if (newPassword !== confirmation) { setError("New password confirmation does not match."); return; }
    setSaving(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmation(""); setSuccess(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not change password.");
    } finally { setSaving(false); }
  }

  return <div className="rq-page rq-settings-page"><div className="rq-page-heading"><div><p className="rq-kicker">Account settings</p><h1>Change password</h1><p>Update the password for your authenticated workspace account.</p></div></div><section className="rq-settings-card"><div className="rq-settings-card-heading"><span className="rq-settings-icon"><KeyRound size={19} /></span><div><h2>Secure your account</h2><p>Your current password is required before a new password can be saved.</p></div></div><form className="rq-settings-form" onSubmit={submit}><label>Current password<input type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label><label>New password<input type="password" autoComplete="new-password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength={8} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>{error && <p className="rq-form-error"><AlertTriangle size={15} />{error}</p>}{success && <p className="rq-form-success"><CheckCircle2 size={15} />Password changed successfully.</p>}<button className="rq-primary-button" type="submit" disabled={saving}>{saving ? <LoaderCircle className="rq-spin" size={15} /> : <KeyRound size={15} />}{saving ? "Saving..." : "Change password"}</button></form></section></div>;
}
