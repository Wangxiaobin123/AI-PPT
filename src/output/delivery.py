"""Delivery service -- produces HTTP responses for file downloads."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

from src.output.manager import OutputManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Mapping from our internal format identifiers to standard MIME types.
_MEDIA_TYPES: dict[str, str] = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "html": "text/html",
    "txt": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
    "png": "image/png",
    "jpg": "image/jpeg",
    "svg": "image/svg+xml",
}

# Fallback when the format is not in _MEDIA_TYPES.
_DEFAULT_MEDIA_TYPE = "application/octet-stream"


class DeliveryService:
    """Thin wrapper around :class:`OutputManager` that builds FastAPI
    ``FileResponse`` instances for download endpoints.
    """

    def __init__(self, manager: OutputManager) -> None:
        self.manager = manager

    async def get_download_response(self, file_id: str) -> FileResponse:
        """Return a :class:`FileResponse` for the requested *file_id*.

        Raises
        ------
        FileNotFoundError
            If *file_id* is not present in the manager's registry or the
            underlying file no longer exists on disk.
        """
        stored = self.manager.get(file_id)
        if stored is None:
            raise FileNotFoundError(f"File not found: {file_id}")

        path = Path(stored.path)
        if not path.exists():
            raise FileNotFoundError(
                f"File record exists but file missing on disk: {stored.path}"
            )

        media_type = _MEDIA_TYPES.get(stored.format, _DEFAULT_MEDIA_TYPE)
        logger.info(
            "file_download",
            file_id=file_id,
            filename=stored.filename,
            media_type=media_type,
        )

        return FileResponse(
            path=stored.path,
            filename=stored.filename,
            media_type=media_type,
        )
