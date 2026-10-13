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
    return "Only engineers, lead engineers, or superusers can create engineering projects (number prefix 13).";
  }
  if (kind === "INTERNAL") {
    return "Only HR/GA, finance, or superusers can create internal projects (number prefix 03).";
  }
  return "Only lead engineers or superusers can create projects without a project number.";
}

/** Explain which prefixes the signed-in role may create. */
export function createScopeHint(role: UserRole | null | undefined): string {
  if (role === "SUPERUSER") return "Superusers can create both engineering (13) and internal (03) projects.";
  if (role === "HRGA" || role === "FINANCE") {
    return "Internal projects must use the 03 prefix, for example: 03-2026-001.";
  }
  if (role === "LEAD_ENGINEER") {
    return "Engineering projects must use the 13 prefix, for example: 13726486.01.";
  }
  return "Engineering projects must use the 13 prefix, for example: 13726486.01.";
}
