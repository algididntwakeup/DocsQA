"use client";

import { AlertTriangle, CheckCircle2, LoaderCircle, UserCircle } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ApiError, getCurrentUser, updateProfile, type UserSession } from "@/lib/api";

export default function ProfileSettingsPage() {
  const [user, setUser] = useState<UserSession | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getCurrentUser().then((current) => {
      setUser(current); setFullName(current.full_name); setEmail(current.email);
    }).catch((caught) => setError(caught instanceof ApiError ? caught.message : "Could not load profile.")).finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setSaving(true);
    try {
      const updated = await updateProfile({ full_name: fullName.trim(), email: email.trim() });
      setUser(updated); setFullName(updated.full_name); setEmail(updated.email);
      toast.success("Profile updated successfully.");
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not update profile."); }
    finally { setSaving(false); }
  }

  return <div className="rq-page rq-settings-page"><div className="rq-page-heading"><div><p className="rq-kicker">Account settings</p><h1>Profile</h1><p>Keep your display name and workspace email current.</p></div></div><section className="rq-settings-card">{loading ? <div className="rq-empty"><LoaderCircle className="rq-spin" size={20} />Loading profile...</div> : <><div className="rq-settings-card-heading"><span className="rq-settings-icon"><UserCircle size={19} /></span><div><h2>Personal details</h2><p>These details are visible to reviewers and in project metadata.</p></div></div><form className="rq-settings-form" onSubmit={(event) => void submit(event)}><label>Nama Lengkap<input required minLength={1} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{error && <p className="rq-form-error"><AlertTriangle size={15} />{error}</p>}{user && !error && <p className="rq-form-success"><CheckCircle2 size={15} />Profile loaded for {user.role.replaceAll("_", " ")}.</p>}<button className="rq-primary-button" type="submit" disabled={saving}>{saving ? <LoaderCircle className="rq-spin" size={15} /> : <UserCircle size={15} />}{saving ? "Saving..." : "Save profile"}</button></form></>}</section></div>;
}
