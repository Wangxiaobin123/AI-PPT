"""Output file management -- stores, indexes, and retrieves generated files."""

from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel

from src.utils.file_utils import ensure_dir, generate_filename
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StoredFile(BaseModel):
    """Metadata record for a file that has been persisted to disk."""

    file_id: str
    path: str
    filename: str
    format: str
    size_bytes: int


class OutputManager:
    """Manages the lifecycle of generated output files.

    Files are written to *output_dir* and tracked in an in-memory registry
    keyed by ``file_id``.  This is intentionally simple -- a production
    deployment would swap the in-memory dict for a database or object store.
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)
        self._files: dict[str, StoredFile] = {}

    async def store(
        self,
        content_bytes: bytes,
        format: str,
        prefix: str = "output",
    ) -> StoredFile:
        """Persist *content_bytes* to disk and register the file.

        Parameters
        ----------
        content_bytes:
            Raw bytes of the generated document.
        format:
            File extension / format identifier (e.g. ``"pptx"``).
        prefix:
            Prefix used when generating the filename on disk.

        Returns
        -------
        StoredFile
            The metadata record for the newly stored file.
        """
        file_id = uuid.uuid4().hex[:12]
        filename = generate_filename(prefix, format)
        file_path = self.output_dir / filename

        # Write the file
        file_path.write_bytes(content_bytes)

        stored = StoredFile(
            file_id=file_id,
            path=str(file_path.resolve()),
            filename=filename,
            format=format,
            size_bytes=len(content_bytes),
        )

        self._files[file_id] = stored
        logger.info(
            "file_stored",
            file_id=file_id,
            filename=filename,
            format=format,
            size_bytes=len(content_bytes),
        )
        return stored

    async def store_from_path(self, source_path: str | Path, format: str) -> StoredFile:
        """Register an already-written file (e.g. one produced by a skill).

        If *source_path* is outside ``output_dir`` the file is **not** copied;
        we simply record its location.  A production implementation would copy
        or move the file into managed storage.
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        file_id = uuid.uuid4().hex[:12]
        stored = StoredFile(
            file_id=file_id,
            path=str(source.resolve()),
            filename=source.name,
            format=format,
            size_bytes=source.stat().st_size,
        )
        self._files[file_id] = stored
        logger.info(
            "file_registered",
            file_id=file_id,
            filename=source.name,
            format=format,
        )
        return stored

    def get(self, file_id: str) -> StoredFile | None:
        """Look up a stored file by its ID.  Returns ``None`` if not found."""
        return self._files.get(file_id)

    def list_files(self) -> list[StoredFile]:
        """Return all stored file records."""
        return list(self._files.values())

    def delete(self, file_id: str) -> bool:
        """Remove a file from disk and the registry.  Returns ``True`` on success."""
        stored = self._files.pop(file_id, None)
        if stored is None:
            return False

        path = Path(stored.path)
        if path.exists():
            path.unlink()
            logger.info("file_deleted", file_id=file_id, path=stored.path)

        return True
