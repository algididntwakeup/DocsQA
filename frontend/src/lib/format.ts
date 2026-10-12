import { translate, type Locale } from "./i18n";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && value >= 1024; index += 1) {
    value /= 1024;
    unit = units[index];
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit}`;
}

export function formatDate(value: string, locale: Locale = "en"): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function humanize(value: string): string {
  return value.toLowerCase().replaceAll("_", " ");
}

/**
 * Locale-aware relative timestamp, e.g. "2 hours ago" / "2 jam lalu".
 * Falls back to an absolute date beyond one year so the label stays useful.
 */
export function formatRelativeTime(value: string, locale: Locale = "en"): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const elapsedMs = Date.now() - date.getTime();
  const elapsedSeconds = Math.floor(elapsedMs / 1000);
  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  const elapsedDays = Math.floor(elapsedHours / 24);

  if (elapsedSeconds < 60) return translate(locale, "relativeJustNow");
  if (elapsedMinutes < 2) return translate(locale, "relativeMinuteAgo");
  if (elapsedMinutes < 60) return translate(locale, "relativeMinutesAgo", { count: elapsedMinutes });
  if (elapsedHours < 2) return translate(locale, "relativeHourAgo");
  if (elapsedHours < 24) return translate(locale, "relativeHoursAgo", { count: elapsedHours });
  if (elapsedDays < 2) return translate(locale, "relativeYesterday");
  if (elapsedDays < 30) return translate(locale, "relativeDaysAgo", { count: elapsedDays });
  const elapsedMonths = Math.floor(elapsedDays / 30);
  if (elapsedMonths < 2) return translate(locale, "relativeMonthAgo");
  if (elapsedMonths < 12) return translate(locale, "relativeMonthsAgo", { count: elapsedMonths });
  const elapsedYears = Math.floor(elapsedMonths / 12);
  if (elapsedYears < 2) return translate(locale, "relativeYearAgo");
  if (elapsedYears < 5) return translate(locale, "relativeYearsAgo", { count: elapsedYears });
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}
