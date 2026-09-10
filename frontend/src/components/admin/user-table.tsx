"use client";

import { KeyRound, Power } from "lucide-react";
import type { ManagedUser } from "@/lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function UserTable({ users, busyUserId, onToggleStatus, onResetPassword }: {
  users: ManagedUser[];
  busyUserId: string | null;
  onToggleStatus: (user: ManagedUser) => void;
  onResetPassword: (user: ManagedUser) => void;
}) {
  return <div className="panel overflow-hidden"><div className="table-scroll"><table><thead><tr><th>Nama Lengkap</th><th>Email</th><th>Role</th><th>Status Akun</th><th>Tanggal Dibuat</th><th>Aksi</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><strong>{user.full_name}</strong><small className="block text-muted">{user.total_documents_owned} owned documents</small></td><td>{user.email}</td><td><span className={`status-badge ${user.role === "ENGINEER" ? "status-active" : "status-success"}`}><i />{user.role === "ENGINEER" ? "Engineer" : user.role === "SUPERUSER" ? "Superuser" : "Lead"}</span></td><td><span className={`status-badge ${user.is_active ? "status-success" : "status-warning"}`}><i />{user.is_active ? "Aktif" : "Nonaktif"}</span></td><td className="whitespace-nowrap">{formatDate(user.created_at)}</td><td><div className="flex flex-wrap gap-2"><button className="button button-secondary btn-sm" type="button" disabled={busyUserId === user.id} onClick={() => onToggleStatus(user)}><Power size={13} />{user.is_active ? "Disable" : "Enable"}</button><button className="button button-secondary btn-sm" type="button" disabled={busyUserId === user.id} onClick={() => onResetPassword(user)}><KeyRound size={13} />Reset password</button></div></td></tr>)}</tbody></table></div></div>;
}
