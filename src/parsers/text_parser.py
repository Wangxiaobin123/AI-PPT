"""Plain-text parser: converts plain text into StructuredContent.

Strategy:
- Split text by double newlines into paragraphs.
- If the first line is short (< 80 chars) and followed by a blank line, treat
  it as the document title.
- Each remaining paragraph becomes a TEXT content block.
- Content is grouped into a single slide and section.
"""

from __future__ import annotations

import re
from typing import Optional

from src.generators.base import (
    ContentBlock,
    ContentType,
    SectionData,
    SlideData,
    StructuredContent,
)

_TITLE_MAX_LENGTH = 80


class TextParser:
    """Parse plain text into :class:`StructuredContent`."""

    def parse(self, text: str) -> StructuredContent:
        """Parse a plain-text string and return StructuredContent."""
        content = StructuredContent()

        if not text or not text.strip():
            return content

        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Split into paragraphs on double-newlines
        paragraphs = re.split(r"\n\s*\n", text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return content

        # Determine title
        first = paragraphs[0]
        start_index = 0

        # Use first paragraph as title if it is a single short line
        if "\n" not in first and len(first) <= _TITLE_MAX_LENGTH:
            content.title = first
            start_index = 1

        # Build blocks from remaining paragraphs
        blocks: list[ContentBlock] = []
        for para in paragraphs[start_index:]:
            blocks.append(ContentBlock(type=ContentType.TEXT, content=para))

        # Build a single slide and section
        slide_title = content.title or "Untitled"
        content.slides.append(
            SlideData(
                title=slide_title,
                blocks=list(blocks),
                layout="content" if blocks else "title",
            )
        )
        content.sections.append(
            SectionData(title=slide_title, blocks=list(blocks))
        )

        return content

    def parse_file(self, path: str, encoding: Optional[str] = None) -> StructuredContent:
        """Read a text file from *path* and parse it.

        Tries utf-8 first, then latin-1 as a fallback.
        """
        raw = self._read_file(path, encoding)
        return self.parse(raw)

    @staticmethod
    def _read_file(path: str, encoding: Optional[str] = None) -> str:
        if encoding:
            with open(path, "r", encoding=encoding) as fh:
                return fh.read()
        for enc in ("utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as fh:
                    return fh.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
