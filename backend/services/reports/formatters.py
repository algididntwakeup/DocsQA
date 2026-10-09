"""Locale-aware formatters used by report renderers."""

from __future__ import annotations

from datetime import date, datetime

from domain.enums import ReportLanguage
from services.reports.i18n import translate_severity, translate_status

_INDONESIAN_MONTHS = (
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)


def _parse_date(value: date | datetime | str) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        for pattern in (
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ):
            try:
                return datetime.strptime(text, pattern).date()
            except ValueError:
                continue
    return None


def format_report_date(value: date | datetime | str | None, language: ReportLanguage | str) -> str:
    """Format a report date without relying on the host machine's locale."""
    if value is None:
        return ""
    parsed = _parse_date(value)
    if parsed is None:
        return str(value).strip()
    locale = str(getattr(language, "value", language)).lower()
    if locale == "id":
        return f"{parsed.day:02d} {_INDONESIAN_MONTHS[parsed.month - 1]} {parsed.year}"
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


__all__ = ["format_report_date", "translate_severity", "translate_status"]
