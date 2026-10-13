import { describe, expect, it } from "vitest";
import { translate } from "./i18n";
import { formatRelativeTime } from "./format";

const workspaceKeys = [
  "searchLabel", "searchPlaceholder", "sortBy", "sortName", "sortNumber", "sortClient", "sortDocsCount", "sortUpdated",
  "sortAscending", "sortDescending", "viewModeLabel", "viewGrid", "viewTable", "importFromBima",
  "colName", "colNumber", "colClient", "colDocs", "colModified", "colActions", "docCount",
  "openWorkspaceFor", "numberNotAvailable", "clientNotAvailable", "emptySearch", "emptySearchHint", "clearSearch",
  "emptyWorkspace", "loadingProjectList", "projectActions", "actionsForProject", "copyProjectNumber",
  "projectNumberCopied", "projectNumberCopyFailed",
  "bimaIntegration", "bimaModalTitle", "bimaModalDesc", "bimaSearchLabel", "bimaSearchPlaceholder",
  "bimaCloseDialog", "bimaEmptyTitle", "bimaEmptyHint", "bimaAddToFolder", "bimaAddingToFolder",
  "bimaBadgeInFolder", "bimaOpenWorkspaceTitle", "openWorkspace", "bimaLoading", "bimaLoadFailed", "bimaImportSuccess", "bimaImportFailed",
  "bimaMyProjectBadge", "bimaFilterMine",
  "relativeJustNow", "relativeMinuteAgo", "relativeMinutesAgo", "relativeHourAgo", "relativeHoursAgo",
  "relativeYesterday", "relativeDaysAgo", "relativeMonthAgo", "relativeMonthsAgo", "relativeYearAgo", "relativeYearsAgo",
] as const;

const indonesianWordPattern = /\b(Tambah|Proyek|Klien|Dokumen|Impor|Sudah|Memuat|Mengimpor|Urutkan|Tampilan|Cari|Salin|Buka|Terakhir|Aksi|Kemarin|Belum|jam|hari|menit|bulan|tahun)\b/;

describe("workspace & BIMA dictionaries", () => {
  it("defines every key in both locales with distinct copy", () => {
    for (const key of workspaceKeys) {
      const en = translate("en", key);
      const id = translate("id", key);
      expect(en, `missing EN translation for ${key}`).not.toBe(key);
      expect(id, `missing ID translation for ${key}`).not.toBe(key);
      expect(id, `ID copy identical to EN for ${key}`).not.toBe(en);
    }
  });

  it("keeps English copy free of Indonesian words", () => {
    for (const key of workspaceKeys) {
      expect(translate("en", key), `Indonesian leak in EN value for ${key}`).not.toMatch(indonesianWordPattern);
    }
  });

  it("keeps Indonesian copy free of English UI phrases", () => {
    expect(translate("id", "importFromBima")).toBe("Tambah dari BIMA");
    expect(translate("id", "searchPlaceholder")).toBe("Cari proyek berdasarkan nama, nomor, atau klien...");
    expect(translate("id", "viewTable")).toBe("Tampilan Tabel");
    expect(translate("id", "bimaAddToFolder")).toBe("Tambah ke Folder");
    expect(translate("id", "bimaAddingToFolder")).toBe("Menambahkan...");
    expect(translate("id", "bimaBadgeInFolder")).toBe("Sudah di Folder");
    expect(translate("id", "openWorkspace")).toBe("Buka Workspace");
    expect(translate("id", "bimaImportSuccess")).toBe("Proyek berhasil diimpor ke PRISM");
  });

  it("matches the required English copy for the BIMA modal and empty states", () => {
    expect(translate("en", "importFromBima")).toBe("Add from BIMA");
    expect(translate("en", "bimaModalTitle")).toBe("Choose a project to import");
    expect(translate("en", "bimaModalDesc")).toBe("Search by project number, title, or client name.");
    expect(translate("en", "bimaSearchPlaceholder")).toBe("Search project number, name, or client...");
    expect(translate("en", "bimaAddingToFolder")).toBe("Adding...");
    expect(translate("en", "bimaBadgeInFolder")).toBe("Already in Folder");
    expect(translate("en", "openWorkspace")).toBe("Open Workspace");
    expect(translate("en", "bimaLoading")).toBe("Loading BIMA projects...");
    expect(translate("en", "bimaImportSuccess")).toBe("Project successfully imported to PRISM");
    expect(translate("en", "emptySearch")).toBe("No projects match your search.");
    expect(translate("en", "emptyWorkspace")).toBe("No projects yet. Import from BIMA to get started.");
  });

  it("interpolates the document count placeholder in both locales", () => {
    expect(translate("en", "docCount", { count: 3 })).toBe("3 Documents");
    expect(translate("id", "docCount", { count: 3 })).toBe("3 Dokumen");
  });
});

describe("formatRelativeTime", () => {
  const hoursAgo = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();

  it("localizes recent hours in both locales", () => {
    expect(formatRelativeTime(hoursAgo(2), "en")).toBe("2 hours ago");
    expect(formatRelativeTime(hoursAgo(2), "id")).toBe("2 jam lalu");
  });

  it("localizes yesterday and multi-day offsets", () => {
    expect(formatRelativeTime(hoursAgo(26), "en")).toBe("Yesterday");
    expect(formatRelativeTime(hoursAgo(26), "id")).toBe("Kemarin");
    expect(formatRelativeTime(hoursAgo(24 * 3), "en")).toBe("3 days ago");
    expect(formatRelativeTime(hoursAgo(24 * 3), "id")).toBe("3 hari lalu");
  });

  it("returns an empty label for invalid timestamps", () => {
    expect(formatRelativeTime("not-a-date", "en")).toBe("");
    expect(formatRelativeTime("not-a-date", "id")).toBe("");
  });
});
