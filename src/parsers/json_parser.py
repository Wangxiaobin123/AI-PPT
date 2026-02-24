"""JSON parser: converts JSON data into StructuredContent.

Supports two main shapes:

1. **Structured format** -- a dict with ``title``, ``slides``, ``sections``,
   etc. that maps closely to :class:`StructuredContent`.

2. **Flat data array** -- a list of dicts (e.g. ``[{"col": "val"}, ...]``)
   which is converted into a table format suitable for XLSX and table blocks.

Nested structures are flattened using dot-notation keys.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Union

from src.generators.base import (
    ContentBlock,
    ContentType,
    SectionData,
    SlideData,
    StructuredContent,
)


class JsonParser:
    """Parse JSON text or files into :class:`StructuredContent`."""

    def parse(self, text: str) -> StructuredContent:
        """Parse a JSON *text* string and return StructuredContent."""
        data = json.loads(text)
        return self._convert(data)

    def parse_file(self, path: str) -> StructuredContent:
        """Read a JSON file from *path* and parse it."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return self._convert(data)

    # ------------------------------------------------------------------
    # Private implementation
    # ------------------------------------------------------------------

    def _convert(self, data: Any) -> StructuredContent:
        """Route to the appropriate handler based on the shape of *data*."""
        if isinstance(data, list):
            return self._convert_flat_array(data)
        if isinstance(data, dict):
            # If the dict has recognizable keys, treat it as structured
            if any(k in data for k in ("title", "slides", "sections", "sheets")):
                return self._convert_structured(data)
            # Otherwise treat it as a single-record array
            return self._convert_flat_array([data])
        # Scalar fallback
        return StructuredContent(
            title="Data",
            sections=[SectionData(title="Data", blocks=[
                ContentBlock(type=ContentType.TEXT, content=str(data))
            ])],
            slides=[SlideData(title="Data", blocks=[
                ContentBlock(type=ContentType.TEXT, content=str(data))
            ])],
        )

    # ------------------------------------------------------------------
    # Structured dict conversion
    # ------------------------------------------------------------------

    def _convert_structured(self, data: dict) -> StructuredContent:
        """Convert a dict with ``title``, ``slides``, ``sections``, etc."""
        content = StructuredContent(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            author=data.get("author", ""),
            metadata=data.get("metadata", {}),
        )

        # --- Slides ---
        for slide_raw in data.get("slides", []):
            content.slides.append(self._parse_slide(slide_raw))

        # --- Sections ---
        for section_raw in data.get("sections", []):
            content.sections.append(self._parse_section(section_raw))

        # --- Sheets ---
        for sheet_raw in data.get("sheets", []):
            content.sheets.append(self._normalise_sheet(sheet_raw))

        # If slides were provided but no sections, mirror slides into sections
        if content.slides and not content.sections:
            for slide in content.slides:
                content.sections.append(
                    SectionData(title=slide.title, blocks=list(slide.blocks))
                )

        # Likewise, if sections but no slides
        if content.sections and not content.slides:
            for section in content.sections:
                content.slides.append(
                    SlideData(title=section.title, blocks=list(section.blocks))
                )

        return content

    def _parse_slide(self, raw: dict) -> SlideData:
        title = raw.get("title", "")
        subtitle = raw.get("subtitle", "")
        layout = raw.get("layout", "content")
        notes = raw.get("notes", "")
        blocks = [self._parse_block(b) for b in raw.get("blocks", [])]
        return SlideData(
            title=title, subtitle=subtitle, blocks=blocks,
            layout=layout, notes=notes,
        )

    def _parse_section(self, raw: dict) -> SectionData:
        title = raw.get("title", "")
        blocks = [self._parse_block(b) for b in raw.get("blocks", [])]
        return SectionData(title=title, blocks=blocks)

    @staticmethod
    def _parse_block(raw: dict) -> ContentBlock:
        block_type = raw.get("type", "text")
        # Accept both enum values and plain strings
        try:
            ct = ContentType(block_type)
        except ValueError:
            ct = ContentType.TEXT

        return ContentBlock(
            type=ct,
            content=raw.get("content", ""),
            level=raw.get("level", 1),
            items=raw.get("items", []),
            rows=raw.get("rows", []),
            metadata=raw.get("metadata", {}),
        )

    @staticmethod
    def _normalise_sheet(raw: dict) -> dict:
        return {
            "name": raw.get("name", "Sheet1"),
            "headers": raw.get("headers", []),
            "rows": raw.get("rows", []),
        }

    # ------------------------------------------------------------------
    # Flat array conversion (list of dicts -> table)
    # ------------------------------------------------------------------

    def _convert_flat_array(self, data: list) -> StructuredContent:
        """Convert ``[{"col": "val"}, ...]`` into a table-based StructuredContent."""
        if not data:
            return StructuredContent(title="Data")

        # Flatten nested dicts
        flat_rows = [self._flatten_dict(row) if isinstance(row, dict) else {"value": str(row)} for row in data]

        # Gather all unique keys in order of first appearance
        headers: list[str] = []
        seen: set[str] = set()
        for row in flat_rows:
            for key in row:
                if key not in seen:
                    headers.append(key)
                    seen.add(key)

        # Build rows
        rows: list[list[str]] = []
        for row in flat_rows:
            rows.append([str(row.get(h, "")) for h in headers])

        # Table block (first row = headers)
        table_block = ContentBlock(
            type=ContentType.TABLE,
            rows=[headers] + rows,
        )

        title = "Data"
        content = StructuredContent(
            title=title,
            slides=[SlideData(title=title, blocks=[table_block], layout="content")],
            sections=[SectionData(title=title, blocks=[table_block])],
            sheets=[{"name": "Sheet1", "headers": headers, "rows": rows}],
        )
        return content

    # ------------------------------------------------------------------
    # Flatten nested dicts
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
        """Flatten a nested dict into dot-notation keys.

        Example: ``{"a": {"b": 1}}`` -> ``{"a.b": "1"}``
        """
        items: list[tuple[str, str]] = []
        for key, value in d.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(
                    JsonParser._flatten_dict(value, parent_key=new_key, sep=sep).items()
                )
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                items.append((new_key, ", ".join(str(v) for v in value)))
            else:
                items.append((new_key, str(value)))
        return dict(items)
