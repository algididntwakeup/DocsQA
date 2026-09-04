"""
Application configuration — loaded from environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Document QC API."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "Document QC API"
    DEBUG: bool = False

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docqc"

    # ── Redis / Celery ───────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── File Storage ─────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # ── NLP / LanguageTool ───────────────────────────────────────────
    LANGUAGE_TOOL_HOST: str = "http://localhost:8081"

    # ── Table Math Tolerance ─────────────────────────────────────────
    TABLE_MATH_TOLERANCE_PERCENT: float = 0.5
    TABLE_MATH_TOLERANCE_UNIT: float = 1.0

settings = Settings()
