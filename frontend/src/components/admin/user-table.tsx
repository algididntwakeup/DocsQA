"use client";

import { BriefcaseBusiness, KeyRound, Power, ShieldCheck } from "lucide-react";
import type { ManagedUser } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { useLocale } from "@/components/layout/locale-provider";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function UserTable({
  users,
  busyUserId,
  onToggleStatus,
  onResetPassword,
  onViewProjects,
  onToggleSuperuser,
}: {
  users: ManagedUser[];
  busyUserId: string | null;
  onToggleStatus: (user: ManagedUser) => void;
  onResetPassword: (user: ManagedUser) => void;
  onViewProjects: (user: ManagedUser) => void;
  onToggleSuperuser: (user: ManagedUser) => void;
}) {
  const { t } = useLocale();
  return (
    <Card className="overflow-hidden">
      <Table className="text-xs border-collapse">
        <TableHeader className="bg-muted/60">
          <TableRow>
            <TableHead>{t("fullName")}</TableHead>
            <TableHead>{t("email")}</TableHead>
            <TableHead>{t("department")}</TableHead>
            <TableHead>{t("role")}</TableHead>
            <TableHead>{t("superuserBadge")}</TableHead>
            <TableHead>{t("accountStatus")}</TableHead>
            <TableHead>{t("createdDate")}</TableHead>
            <TableHead className="text-right">{t("actions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell>
                <strong className="text-xs font-bold text-foreground block">{user.full_name}</strong>
                <span className="text-[11px] text-muted-foreground">{user.total_documents_owned} {t("ownedDocuments")}</span>
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{user.email}</TableCell>
              <TableCell>
                <span className="text-muted-foreground">{user.department ?? user.position ?? "—"}</span>
              </TableCell>
              <TableCell>
                {user.role === "ENGINEER" ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-accent px-3 py-1 text-xs font-bold text-accent-foreground ring-1 ring-primary/20 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                     {t("roleEngineer")}
                  </span>
                ) : user.role === "SUPERUSER" ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-100 px-3 py-1 text-xs font-bold text-purple-700 ring-1 ring-purple-500/30 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                     {t("roleSuperuser")}
                  </span>
                ) : user.role === "HRGA" ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-500/30 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                     {t("roleHrga")}
                  </span>
                ) : user.role === "FINANCE" ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-500/30 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                     {t("roleFinance")}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-500/30 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                     {t("roleLead")}
                  </span>
                )}
              </TableCell>
              <TableCell>
                {user.is_superuser ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-100 px-3 py-1 text-xs font-bold text-purple-700 ring-1 ring-purple-500/30 shadow-2xs">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                    {t("superuserBadge")}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {user.is_active ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-600/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                     {t("active")}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold text-muted-foreground ring-1 ring-slate-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                     {t("inactive")}
                  </span>
                )}
              </TableCell>
              <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(user.created_at)}</TableCell>
              <TableCell className="text-right">
                <div className="inline-flex items-center gap-2 justify-end">
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/60 transition shadow-2xs"
                    type="button"
                    onClick={() => onViewProjects(user)}
                  >
                    <BriefcaseBusiness size={13} className="text-muted-foreground" />
                     {t("viewProjects")}
                  </button>
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/60 transition shadow-2xs disabled:opacity-50"
                    type="button"
                    disabled={busyUserId === user.id}
                    onClick={() => onToggleStatus(user)}
                  >
                    <Power size={13} className={user.is_active ? "text-amber-500" : "text-emerald-500"} />
                    {user.is_active ? t("disable") : t("enable")}
                  </button>
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/60 transition shadow-2xs disabled:opacity-50"
                    type="button"
                    disabled={busyUserId === user.id}
                    onClick={() => onResetPassword(user)}
                  >
                    <KeyRound size={13} className="text-muted-foreground" />
                     {t("resetPassword")}
                  </button>
                  <button
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/60 transition shadow-2xs disabled:opacity-50"
                    type="button"
                    disabled={busyUserId === user.id}
                    onClick={() => onToggleSuperuser(user)}
                  >
                    <ShieldCheck size={13} className={user.is_superuser ? "text-purple-600" : "text-muted-foreground"} />
                    {user.is_superuser ? t("revokeSuperuser") : t("grantSuperuser")}
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
