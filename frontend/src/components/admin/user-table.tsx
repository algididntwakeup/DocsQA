"use client";

import { BriefcaseBusiness, KeyRound, Power } from "lucide-react";
import type { ManagedUser } from "@/lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function UserTable({
  users,
  busyUserId,
  onToggleStatus,
  onResetPassword,
  onViewProjects,
}: {
  users: ManagedUser[];
  busyUserId: string | null;
  onToggleStatus: (user: ManagedUser) => void;
  onResetPassword: (user: ManagedUser) => void;
  onViewProjects: (user: ManagedUser) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-bold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-6 py-3.5">Nama Lengkap</th>
              <th className="px-6 py-3.5">Email</th>
              <th className="px-6 py-3.5">Role</th>
              <th className="px-6 py-3.5">Status Akun</th>
              <th className="px-6 py-3.5">Tanggal Dibuat</th>
              <th className="px-6 py-3.5 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="px-6 py-4">
                  <strong className="text-xs font-bold text-slate-900 block">{user.full_name}</strong>
                  <span className="text-[11px] text-slate-500">{user.total_documents_owned} owned documents</span>
                </td>
                <td className="px-6 py-4 font-mono text-xs text-slate-600">{user.email}</td>
                <td className="px-6 py-4">
                  {user.role === "ENGINEER" ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-bold text-blue-700 ring-1 ring-blue-600/30 shadow-2xs">
                      <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                      Engineer
                    </span>
                  ) : user.role === "SUPERUSER" ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-100 px-3 py-1 text-xs font-bold text-purple-700 ring-1 ring-purple-500/30 shadow-2xs">
                      <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                      Superuser
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-500/30 shadow-2xs">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                      Lead
                    </span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {user.is_active ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-600/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Aktif
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-slate-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                      Nonaktif
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-slate-500">{formatDate(user.created_at)}</td>
                <td className="px-6 py-4 text-right">
                  <div className="inline-flex items-center gap-2 justify-end">
                    <button
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition shadow-2xs"
                      type="button"
                      onClick={() => onViewProjects(user)}
                    >
                      <BriefcaseBusiness size={13} className="text-slate-500" />
                      Lihat Projects
                    </button>
                    <button
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition shadow-2xs disabled:opacity-50"
                      type="button"
                      disabled={busyUserId === user.id}
                      onClick={() => onToggleStatus(user)}
                    >
                      <Power size={13} className={user.is_active ? "text-amber-500" : "text-emerald-500"} />
                      {user.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition shadow-2xs disabled:opacity-50"
                      type="button"
                      disabled={busyUserId === user.id}
                      onClick={() => onResetPassword(user)}
                    >
                      <KeyRound size={13} className="text-slate-500" />
                      Reset password
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
