"""CSV parser: converts CSV data into StructuredContent.

Uses Python's built-in csv module.  The first row is treated as column headers
and subsequent rows as data.  Output populates both:
- ``sheets`` (for XLSX generation)
- ``table`` blocks inside slides/sections (for PPTX / DOCX / PDF / HTML)

Handles common encodings (utf-8, utf-8-sig, latin-1).
"""

from __future__ import annotations

import csv
import io
import os
from typing import Optional

from src.generators.base import (
    ContentBlock,
    ContentType,
    SectionData,
    SlideData,
    StructuredContent,
)

# Maximum number of data rows to include in a single table block to keep
# slides readable.  The full data always goes into ``sheets``.
_MAX_TABLE_ROWS_PER_SLIDE = 20


class CsvParser:
    """Parse CSV text or files into :class:`StructuredContent`."""

    def parse(
        self,
        text: str,
        *,
        title: Optional[str] = None,
        delimiter: str = ",",
        sheet_name: str = "Sheet1",
    ) -> StructuredContent:
        """Parse CSV *text* (a string) and return StructuredContent.

        Parameters
        ----------
        text:
            The raw CSV string.
        title:
            An optional title for the document.  If not provided, defaults to
            the sheet name.
        delimiter:
            Field delimiter (default ``","``).
        sheet_name:
            Name used for the sheet entry in ``sheets``.
        """
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        return self._build_content(rows, title=title, sheet_name=sheet_name)

    def parse_file(
        self,
        path: str,
        *,
        title: Optional[str] = None,
        delimiter: str = ",",
        sheet_name: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> StructuredContent:
        """Read a CSV file from *path* and parse it.

        If *encoding* is ``None`` the parser will try utf-8-sig, utf-8, and
        latin-1 in order.
        """
        raw = self._read_file(path, encoding=encoding)
        if sheet_name is None:
            sheet_name = os.path.splitext(os.path.basename(path))[0]
        if title is None:
            title = sheet_name
        return self.parse(raw, title=title, delimiter=delimiter, sheet_name=sheet_name)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file(path: str, encoding: Optional[str] = None) -> str:
        """Read the file with encoding fallback."""
        if encoding:
            with open(path, "r", encoding=encoding) as fh:
                return fh.read()

        # Try common encodings in order
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as fh:
                    return fh.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        # Last resort: read with errors replaced
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()

    @staticmethod
    def _build_content(
        rows: list[list[str]],
        *,
        title: Optional[str] = None,
        sheet_name: str = "Sheet1",
    ) -> StructuredContent:
        """Build a StructuredContent from a list of row lists."""
        content = StructuredContent()

        if not rows:
            content.title = title or ""
            return content

        headers = rows[0]
        data_rows = rows[1:]

        content.title = title or sheet_name

        # ---- Populate sheets for XLSX output ----
        content.sheets.append(
            {
                "name": sheet_name,
                "headers": headers,
                "rows": [list(row) for row in data_rows],
            }
        )

        # ---- Populate slides / sections with table blocks ----
        # If the dataset is large, chunk into multiple slides.
        chunk_start = 0
        slide_index = 0
        while chunk_start < len(data_rows) or slide_index == 0:
            chunk_end = chunk_start + _MAX_TABLE_ROWS_PER_SLIDE
            chunk = data_rows[chunk_start:chunk_end]

            # Build the table block: first row is headers, rest is data
            table_rows = [headers] + chunk
            block = ContentBlock(type=ContentType.TABLE, rows=table_rows)

            slide_title = content.title
            if slide_index > 0:
                slide_title = f"{content.title} (continued {slide_index + 1})"

            content.slides.append(
                SlideData(
                    title=slide_title,
                    blocks=[block],
                    layout="content",
                )
            )
            content.sections.append(
                SectionData(title=slide_title, blocks=[block])
            )

            chunk_start = chunk_end
            slide_index += 1
            if chunk_start >= len(data_rows):
                break

        return content
