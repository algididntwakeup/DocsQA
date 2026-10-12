import type { UserRole } from "@/lib/api";
import type { TranslationKey } from "@/lib/i18n";

/**
 * Client-side mirror of `backend/services/permission_service.py`.
 *
 * PRISM splits workspaces by BIMA project-number prefix:
 * `13` engineering projects and `03` internal HR/GA/Finance projects.
 * These helpers gate the create-project and BIMA-import actions so users are
 * told about the rule before the API returns 403.
 */

export const ENGINEERING_PREFIX = "13";
export const INTERNAL_PREFIX = "03";

export type ProjectKind = "ENGINEERING" | "INTERNAL" | "UNCLASSIFIED";

const ENGINEERING_ROLES: UserRole[] = ["ENGINEER", "LEAD_ENGINEER", "SUPERUSER"];
const INTERNAL_ROLES: UserRole[] = ["HRGA", "FINANCE", "SUPERUSER"];
const PRIVILEGED_ROLES: UserRole[] = ["LEAD_ENGINEER", "SUPERUSER"];

export function projectKind(projectNumber: string | null | undefined): ProjectKind {
  const number = (projectNumber ?? "").trim();
  if (number.startsWith(ENGINEERING_PREFIX)) return "ENGINEERING";
  if (number.startsWith(INTERNAL_PREFIX)) return "INTERNAL";
  return "UNCLASSIFIED";
}

export function isPrivileged(role: UserRole | null | undefined): boolean {
  return role != null && PRIVILEGED_ROLES.includes(role);
}

export function canManageFolders(
  role: UserRole | null | undefined,
  projectNumber: string | null | undefined,
): boolean {
  const kind = projectKind(projectNumber);
  if (kind === "UNCLASSIFIED") return true;
  if (!role) return false;
  const allowed = kind === "ENGINEERING" ? ENGINEERING_ROLES : INTERNAL_ROLES;
  return allowed.includes(role);
}

export function canCreateProject(
  role: UserRole | null | undefined,
  projectNumber: string | null | undefined,
): boolean {
  if (projectKind(projectNumber) === "UNCLASSIFIED") return isPrivileged(role);
  return canManageFolders(role, projectNumber);
}

/** Whether the role may create at least one kind of project. */
export function canCreateAnyProject(role: UserRole | null | undefined): boolean {
  return role === "SUPERUSER"
    || role === "LEAD_ENGINEER"
    || role === "ENGINEER"
    || role === "HRGA"
    || role === "FINANCE";
}

export function folderPermissionMessageKey(projectNumber: string | null | undefined): TranslationKey {
  const kind = projectKind(projectNumber);
  if (kind === "ENGINEERING") return "folderPermissionEngineering";
  if (kind === "INTERNAL") return "folderPermissionInternal";
  return "folderPermissionUnclassified";
}

export function createPermissionMessage(projectNumber: string | null | undefined): string {
  const kind = projectKind(projectNumber);
  if (kind === "ENGINEERING") {
    return "Hanya engineer, lead engineer, atau superuser yang dapat membuat proyek Engineering (nomor prefix 13).";
  }
  if (kind === "INTERNAL") {
    return "Hanya HR/GA, finance, atau superuser yang dapat membuat proyek Internal (nomor prefix 03).";
  }
  return "Hanya lead engineer atau superuser yang dapat membuat proyek tanpa nomor proyek.";
}

/** Explain which prefixes the signed-in role may create. */
export function createScopeHint(role: UserRole | null | undefined): string {
  if (role === "SUPERUSER") return "Superuser dapat membuat proyek Engineering (13) dan Internal (03).";
  if (role === "HRGA" || role === "FINANCE") {
    return "Proyek Internal wajib berprefix 03, contoh: 03-2026-001.";
  }
  if (role === "LEAD_ENGINEER") {
    return "Proyek Engineering wajib berprefix 13, contoh: 13726486.01.";
  }
  return "Proyek Engineering wajib berprefix 13, contoh: 13726486.01.";
}
