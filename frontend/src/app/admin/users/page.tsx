"use client";

import { AlertTriangle, LoaderCircle, Plus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createManagedUser,
  getCurrentUser,
  listManagedUsers,
  resetManagedUserPassword,
  updateManagedUserStatus,
  type CreateManagedUserPayload,
  type ManagedUser,
} from "@/lib/api";
import { CreateUserModal } from "@/components/admin/create-user-modal";
import { UserTable } from "@/components/admin/user-table";
import { UserProjectsModal } from "@/components/admin/user-projects-modal";

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectsUser, setProjectsUser] = useState<ManagedUser | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const user = await getCurrentUser();
        if (user.role !== "LEAD_ENGINEER" && user.role !== "SUPERUSER") {
          router.replace("/");
          return;
        }
        const managed = await listManagedUsers();
        if (active) setUsers(managed);
      } catch (caught) {
        if (active) setError(caught instanceof ApiError ? caught.message : "Could not load user management.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [router]);

  async function create(payload: CreateManagedUserPayload) {
    setCreating(true);
    setError(null);
    try {
      const created = await createManagedUser(payload);
      setUsers((current) => [created, ...current]);
      setModalOpen(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create user.");
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(user: ManagedUser) {
    setBusyUserId(user.id);
    setError(null);
    try {
      const updated = await updateManagedUserStatus(user.id, !user.is_active);
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not update account status.");
    } finally {
      setBusyUserId(null);
    }
  }

  async function resetPassword(user: ManagedUser) {
    const password = window.prompt(`New temporary password for ${user.email}`);
    if (!password) return;
    if (password.length < 8) {
      setError("Temporary password must be at least 8 characters.");
      return;
    }
    setBusyUserId(user.id);
    setError(null);
    try {
      const updated = await resetManagedUserPassword(user.id, password);
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not reset password.");
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8 font-sans">
      {/* Header with clear hierarchy and generous spacing */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 border-b border-slate-200 pb-6">
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Access Control</p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">User Management</h1>
          <p className="text-sm text-slate-600 max-w-2xl">
            Lead engineers and superusers can provision accounts, change status, and reset passwords.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-blue-700 active:scale-[0.98] self-start sm:self-auto shrink-0"
          type="button"
          onClick={() => setModalOpen(true)}
        >
          <Plus size={16} />
          Tambah User Baru
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800" role="alert">
          <AlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-12 text-sm text-slate-500 shadow-xs">
          <LoaderCircle className="mb-3 animate-spin text-blue-600" size={28} />
          Loading users...
        </div>
      ) : users.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-xs">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600 mb-3">
            <Users size={24} />
          </div>
          <h2 className="text-base font-bold text-slate-900">No users found</h2>
          <p className="mt-1 text-xs text-slate-500">Add a new user to grant platform access.</p>
        </div>
      ) : (
        <UserTable
          users={users}
          busyUserId={busyUserId}
          onToggleStatus={(user) => void toggleStatus(user)}
          onResetPassword={(user) => void resetPassword(user)}
          onViewProjects={setProjectsUser}
        />
      )}

      <CreateUserModal
        open={modalOpen}
        busy={creating}
        onClose={() => setModalOpen(false)}
        onSubmit={create}
      />
      <UserProjectsModal
        user={projectsUser}
        onClose={() => setProjectsUser(null)}
      />
    </div>
  );
}
