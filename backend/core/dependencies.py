"""FastAPI dependencies that expose locally configured infrastructure."""

from functools import lru_cache

from core.config import settings
from services.storage import LocalStorage
from services.uploads import UploadService


@lru_cache
def get_storage() -> LocalStorage:
    """Return the process-local development storage adapter."""

    return LocalStorage(settings.STORAGE_ROOT)


def get_upload_service() -> UploadService:
    """Return the upload service bound to the configured local storage."""

    return UploadService(get_storage(), settings)
