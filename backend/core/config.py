"""
Application configuration — loaded from environment variables.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Document QC API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "PRISM - Document Assurance Platform"
    DEBUG: bool = False

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str = ""
    LOCAL_FALLBACK_EMAILS: str = ""

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://docqc:docqc@postgres:5432/docqc"

    # ── Redis / Celery ───────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ── File Storage ─────────────────────────────────────────────────
    STORAGE_ROOT: Path = Path("./data")
    MAX_FILE_SIZE_MB: int = 50
    MAX_PAGE_COUNT: int = 200
    MAX_BATCH_SIZE: int = 20
    DOCUMENT_RETENTION_DAYS: int = 90
    MAX_DOCX_ENTRY_COUNT: int = 1_000
    MAX_DOCX_UNCOMPRESSED_BYTES: int = 200 * 1024 * 1024
    MAX_DOCX_COMPRESSION_RATIO: int = 100

    # ── Authentication ──────────────────────────────────────────────
    AUTH_MODE: Literal["disabled", "required"] = "disabled"
    SECRET_KEY: str = "change-this-development-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False

    # ── BIMA identity provider ────────────────────────────────────────
    BIMA_BASE_URL: str = "https://bima.reksolindo.co.id"
    BIMA_CLIENT_ID: str = "prism"
    BIMA_TIMEOUT_SECONDS: float = 10.0

    # ── NLP / LanguageTool ───────────────────────────────────────────
    LANGUAGE_TOOL_HOST: str = "http://languagetool:8081"

    @property
    def cors_origins(self) -> list[str]:
        value = self.CORS_ORIGINS.strip()
        if not value:
            return []
        if value.startswith("["):
            import json

            parsed = json.loads(value)
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def local_fallback_emails(self) -> list[str]:
        return [
            email.strip().lower()
            for email in self.LOCAL_FALLBACK_EMAILS.split(",")
            if email.strip()
        ]

    # ── Table Math Tolerance ─────────────────────────────────────────
    TABLE_MATH_TOLERANCE_PERCENT: float = 0.5
    TABLE_MATH_TOLERANCE_UNIT: float = 1.0


settings = Settings()
