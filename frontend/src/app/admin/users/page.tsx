"use client";

import { AlertTriangle, LoaderCircle, Plus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, createManagedUser, getCurrentUser, listManagedUsers, resetManagedUserPassword, updateManagedUserStatus, type CreateManagedUserPayload, type ManagedUser } from "@/lib/api";
import { CreateUserModal } from "@/components/admin/create-user-modal";
import { UserTable } from "@/components/admin/user-table";

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const user = await getCurrentUser();
        if (user.role !== "LEAD_ENGINEER" && user.role !== "SUPERUSER") { router.replace("/"); return; }
        const managed = await listManagedUsers();
        if (active) setUsers(managed);
      } catch (caught) {
        if (active) setError(caught instanceof ApiError ? caught.message : "Could not load user management.");
      } finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [router]);

  async function create(payload: CreateManagedUserPayload) {
    setCreating(true); setError(null);
    try { const created = await createManagedUser(payload); setUsers((current) => [created, ...current]); setModalOpen(false); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not create user."); }
    finally { setCreating(false); }
  }

  async function toggleStatus(user: ManagedUser) {
    setBusyUserId(user.id); setError(null);
    try { const updated = await updateManagedUserStatus(user.id, !user.is_active); setUsers((current) => current.map((item) => item.id === updated.id ? updated : item)); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not update account status."); }
    finally { setBusyUserId(null); }
  }

  async function resetPassword(user: ManagedUser) {
    const password = window.prompt(`New temporary password for ${user.email}`);
    if (!password) return;
    if (password.length < 8) { setError("Temporary password must be at least 8 characters."); return; }
    setBusyUserId(user.id); setError(null);
    try { const updated = await resetManagedUserPassword(user.id, password); setUsers((current) => current.map((item) => item.id === updated.id ? updated : item)); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not reset password."); }
    finally { setBusyUserId(null); }
  }

  return <><div className="page-heading"><div><p className="eyebrow">Access control</p><h1>User Management</h1><p>Lead engineers and superusers can provision accounts, change status, and reset passwords.</p></div><button className="button button-primary" type="button" onClick={() => setModalOpen(true)}><Plus size={16} />Tambah User Baru</button></div>{error && <div className="alert alert-error" role="alert"><AlertTriangle size={16} /><span>{error}</span></div>}{loading ? <div className="panel loading-state"><LoaderCircle className="mx-auto animate-spin" size={20} />Loading users...</div> : users.length === 0 ? <div className="panel empty-state"><Users className="mx-auto text-primary" size={34} /><h2>No users found</h2></div> : <UserTable users={users} busyUserId={busyUserId} onToggleStatus={(user) => void toggleStatus(user)} onResetPassword={(user) => void resetPassword(user)} />}<CreateUserModal open={modalOpen} busy={creating} onClose={() => setModalOpen(false)} onSubmit={create} /></>;
}
