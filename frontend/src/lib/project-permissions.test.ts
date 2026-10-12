import { describe, expect, it } from "vitest";
import {
  canCreateProject,
  canManageFolders,
  createPermissionMessage,
  folderPermissionMessage,
  isPrivileged,
  projectKind,
} from "./project-permissions";

const ENGINEERING_NUMBER = "13726486.01";
const INTERNAL_NUMBER = "03-2026-001";

describe("projectKind", () => {
  it("classifies numbers by BIMA prefix", () => {
    expect(projectKind(ENGINEERING_NUMBER)).toBe("ENGINEERING");
    expect(projectKind(" 13726486.01 ")).toBe("ENGINEERING");
    expect(projectKind(INTERNAL_NUMBER)).toBe("INTERNAL");
    expect(projectKind("99001")).toBe("UNCLASSIFIED");
    expect(projectKind(null)).toBe("UNCLASSIFIED");
    expect(projectKind(undefined)).toBe("UNCLASSIFIED");
    expect(projectKind("")).toBe("UNCLASSIFIED");
  });
});

describe("canManageFolders", () => {
  it("lets engineering roles manage engineering projects", () => {
    expect(canManageFolders("ENGINEER", ENGINEERING_NUMBER)).toBe(true);
    expect(canManageFolders("LEAD_ENGINEER", ENGINEERING_NUMBER)).toBe(true);
    expect(canManageFolders("SUPERUSER", ENGINEERING_NUMBER)).toBe(true);
  });

  it("blocks internal roles from engineering projects", () => {
    expect(canManageFolders("HRGA", ENGINEERING_NUMBER)).toBe(false);
    expect(canManageFolders("FINANCE", ENGINEERING_NUMBER)).toBe(false);
  });

  it("lets internal roles manage internal projects only", () => {
    expect(canManageFolders("HRGA", INTERNAL_NUMBER)).toBe(true);
    expect(canManageFolders("FINANCE", INTERNAL_NUMBER)).toBe(true);
    expect(canManageFolders("SUPERUSER", INTERNAL_NUMBER)).toBe(true);
    expect(canManageFolders("ENGINEER", INTERNAL_NUMBER)).toBe(false);
    expect(canManageFolders("LEAD_ENGINEER", INTERNAL_NUMBER)).toBe(false);
  });

  it("keeps unclassified projects unrestricted", () => {
    expect(canManageFolders("ENGINEER", null)).toBe(true);
    expect(canManageFolders("HRGA", "99001")).toBe(true);
  });
});

describe("canCreateProject", () => {
  it("requires a matching role for numbered projects", () => {
    expect(canCreateProject("ENGINEER", ENGINEERING_NUMBER)).toBe(true);
    expect(canCreateProject("HRGA", INTERNAL_NUMBER)).toBe(true);
    expect(canCreateProject("ENGINEER", INTERNAL_NUMBER)).toBe(false);
    expect(canCreateProject("HRGA", ENGINEERING_NUMBER)).toBe(false);
  });

  it("keeps unnumbered creation lead-only", () => {
    expect(canCreateProject("ENGINEER", null)).toBe(false);
    expect(canCreateProject("HRGA", null)).toBe(false);
    expect(canCreateProject("LEAD_ENGINEER", null)).toBe(true);
    expect(canCreateProject("SUPERUSER", null)).toBe(true);
  });
});

describe("isPrivileged", () => {
  it("covers only lead engineers and superusers", () => {
    expect(isPrivileged("LEAD_ENGINEER")).toBe(true);
    expect(isPrivileged("SUPERUSER")).toBe(true);
    expect(isPrivileged("ENGINEER")).toBe(false);
    expect(isPrivileged("HRGA")).toBe(false);
    expect(isPrivileged("FINANCE")).toBe(false);
    expect(isPrivileged(null)).toBe(false);
  });
});

describe("permission messages", () => {
  it("names the required prefix", () => {
    expect(folderPermissionMessage(ENGINEERING_NUMBER)).toContain("13");
    expect(folderPermissionMessage(INTERNAL_NUMBER)).toContain("03");
    expect(createPermissionMessage(ENGINEERING_NUMBER)).toContain("13");
    expect(createPermissionMessage(INTERNAL_NUMBER)).toContain("03");
  });
});
