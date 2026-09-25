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
import { useLocale } from "@/components/layout/locale-provider";

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectsUser, setProjectsUser] = useState<ManagedUser | null>(null);
  const { t } = useLocale();

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
        if (caught instanceof ApiError && caught.status === 401) {
          if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
            window.location.replace("/login");
            return;
          }
        }
        if (active) setError(caught instanceof ApiError ? caught.message : t("couldNotLoadUsers"));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [router, t]);

  async function create(payload: CreateManagedUserPayload) {
    setCreating(true);
    setError(null);
    try {
      const created = await createManagedUser(payload);
      setUsers((current) => [created, ...current]);
      setModalOpen(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotCreateUser"));
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
      setError(caught instanceof ApiError ? caught.message : t("couldNotUpdateStatus"));
    } finally {
      setBusyUserId(null);
    }
  }

  async function resetPassword(user: ManagedUser) {
    const password = window.prompt(t("temporaryPasswordPrompt", { email: user.email }));
    if (!password) return;
    if (password.length < 8) {
      setError(t("temporaryPasswordError"));
      return;
    }
    setBusyUserId(user.id);
    setError(null);
    try {
      const updated = await resetManagedUserPassword(user.id, password);
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("couldNotResetPassword"));
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header with clear hierarchy and generous spacing */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 border-b border-border pb-6">
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-accent-foreground">{t("adminAccessControl")}</p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">{t("userManagement")}</h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            {t("userManagementDescription")}
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 active:scale-[0.98] self-start sm:self-auto shrink-0"
          type="button"
          onClick={() => setModalOpen(true)}
        >
          <Plus size={16} />
          {t("addUser")}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800" role="alert">
          <AlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/60 bg-card p-12 text-sm text-muted-foreground shadow-sm">
          <LoaderCircle className="mb-3 animate-spin text-accent-foreground" size={28} />
          {t("loadingUsers")}
        </div>
      ) : users.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-card p-12 text-center shadow-sm">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-accent-foreground mb-3">
            <Users size={24} />
          </div>
          <h2 className="text-base font-bold text-foreground">{t("noUsers")}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{t("noUsersDescription")}</p>
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
