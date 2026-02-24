"""File renderer -- persists skill output bytes to the filesystem.

The :class:`FileRenderer` takes a :class:`SkillResult` whose
``content_bytes`` field is populated and writes them to disk under the
configured ``output_dir``, returning a :class:`RenderedFile` descriptor.
"""

from __future__ import annotations

import os
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
from pydantic import BaseModel

from src.skills.models import SkillResult
from src.utils.file_utils import ensure_dir, generate_filename
from src.utils.logging import get_logger

logger = get_logger("engine.renderer")


class RenderedFile(BaseModel):
    """Descriptor for a file that has been written to disk.

    Attributes:
        file_path: Absolute path to the rendered file.
        format: The output format (e.g. ``"pptx"``).
        size_bytes: Size of the written file in bytes.
        filename: Just the filename portion (e.g. ``"output_a1b2c3d4.pptx"``).
    """

    file_path: str
    format: str
    size_bytes: int
    filename: str


class FileRenderer:
    """Write :class:`SkillResult` content to disk.

    Parameters
    ----------
    output_dir:
        Root directory where files will be stored.  Created if it does not
        exist.
    """

    def __init__(self, output_dir: str = "./output") -> None:
        self.output_dir: Path = ensure_dir(output_dir)

    async def render(
        self,
        skill_result: SkillResult,
        prefix: str = "output",
    ) -> RenderedFile:
        """Persist *skill_result* content bytes and return a descriptor.

        Parameters
        ----------
        skill_result:
            Must have non-empty ``content_bytes`` and a valid ``output_format``.
        prefix:
            Filename prefix (e.g. the skill name or a user-supplied title).

        Returns
        -------
        RenderedFile
            Metadata about the written file.

        Raises
        ------
        ValueError
            When ``skill_result.content_bytes`` is empty.
        """
        if not skill_result.content_bytes:
            raise ValueError("Cannot render a SkillResult with empty content_bytes")

        # Derive the extension from the output format.
        fmt = skill_result.output_format.lower().strip()
        extension = fmt if fmt else "bin"

        # Generate a unique filename.
        filename = generate_filename(prefix, extension)
        file_path = self.output_dir / filename

        logger.info(
            "render_start",
            filename=filename,
            format=fmt,
            size=len(skill_result.content_bytes),
        )

        # Write asynchronously to avoid blocking the event loop.
        async with aiofiles.open(file_path, mode="wb") as fh:
            await fh.write(skill_result.content_bytes)

        size_bytes = os.path.getsize(file_path)

        rendered = RenderedFile(
            file_path=str(file_path.resolve()),
            format=fmt,
            size_bytes=size_bytes,
            filename=filename,
        )

        logger.info(
            "render_complete",
            file_path=rendered.file_path,
            size_bytes=rendered.size_bytes,
        )
        return rendered
