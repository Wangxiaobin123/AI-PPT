"""Markdown parser: converts Markdown text into StructuredContent.

Uses regex-based parsing (no external markdown library) to handle:
- Headings (# through ######)
- Bullet lists (- or *)
- Numbered lists (1. 2. 3.)
- Tables (| header | ... |)
- Fenced code blocks (```)
- Images (![alt](url))
- Plain paragraphs as text blocks

Slides are split at H1 boundaries; sections are populated for DOCX/PDF output.
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


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#*)?\s*$")
_RE_BULLET = re.compile(r"^(\s*)[-*]\s+(.+)$")
_RE_NUMBERED = re.compile(r"^(\s*)\d+\.\s+(.+)$")
_RE_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_RE_TABLE_SEP = re.compile(r"^\|[\s:_-]+(?:\|[\s:_-]+)*\|$")
_RE_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
_RE_CODE_FENCE = re.compile(r"^```(\w*)\s*$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_table_row(line: str) -> list[str]:
    """Extract cell values from a markdown table row."""
    return [cell.strip() for cell in line.strip("|").split("|")]


def _flush_list(
    items: list[str], list_type: ContentType, blocks: list[ContentBlock]
) -> None:
    """Flush accumulated list items into a ContentBlock and clear the buffer."""
    if items:
        blocks.append(ContentBlock(type=list_type, items=list(items)))
        items.clear()


def _flush_table(
    table_rows: list[list[str]], blocks: list[ContentBlock]
) -> None:
    """Flush accumulated table rows into a ContentBlock and clear the buffer."""
    if table_rows:
        blocks.append(ContentBlock(type=ContentType.TABLE, rows=list(table_rows)))
        table_rows.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MarkdownParser:
    """Parse Markdown text into a :class:`StructuredContent` instance."""

    def parse(self, text: str) -> StructuredContent:
        """Parse *text* (a Markdown string) and return a StructuredContent."""
        lines = text.splitlines()
        return self._parse_lines(lines)

    def parse_file(self, path: str) -> StructuredContent:
        """Read a Markdown file from *path* and parse it."""
        with open(path, "r", encoding="utf-8") as fh:
            return self.parse(fh.read())

    # ------------------------------------------------------------------
    # Private implementation
    # ------------------------------------------------------------------

    def _parse_lines(self, lines: list[str]) -> StructuredContent:
        """Walk through lines and build StructuredContent."""

        content = StructuredContent()

        # Accumulation buffers
        current_blocks: list[ContentBlock] = []
        bullet_items: list[str] = []
        numbered_items: list[str] = []
        table_rows: list[list[str]] = []
        in_code_block = False
        code_lang = ""
        code_lines: list[str] = []

        # Track slide / section boundaries (split on H1)
        slide_title = ""
        slide_subtitle = ""
        section_title = ""
        first_h1_seen = False

        def _commit_slide_and_section() -> None:
            """Push accumulated blocks as a new slide and section."""
            nonlocal current_blocks, slide_title, slide_subtitle, section_title
            # Flush any pending list / table
            _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
            _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)
            _flush_table(table_rows, current_blocks)

            if slide_title or current_blocks:
                layout = "title" if (not current_blocks and slide_title) else "content"
                content.slides.append(
                    SlideData(
                        title=slide_title,
                        subtitle=slide_subtitle,
                        blocks=list(current_blocks),
                        layout=layout,
                    )
                )
                content.sections.append(
                    SectionData(title=section_title or slide_title, blocks=list(current_blocks))
                )
            current_blocks = []
            slide_title = ""
            slide_subtitle = ""
            section_title = ""

        i = 0
        while i < len(lines):
            line = lines[i]

            # ---- Code fence handling ----
            if in_code_block:
                fence_match = _RE_CODE_FENCE.match(line)
                if fence_match and not line.strip().startswith("```" + " "):
                    # Closing fence
                    metadata = {"language": code_lang} if code_lang else {}
                    current_blocks.append(
                        ContentBlock(
                            type=ContentType.CODE,
                            content="\n".join(code_lines),
                            metadata=metadata,
                        )
                    )
                    in_code_block = False
                    code_lines = []
                    code_lang = ""
                else:
                    code_lines.append(line)
                i += 1
                continue

            # ---- Opening code fence ----
            fence_match = _RE_CODE_FENCE.match(line)
            if fence_match:
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)
                _flush_table(table_rows, current_blocks)
                in_code_block = True
                code_lang = fence_match.group(1)
                i += 1
                continue

            # ---- Image ----
            img_match = _RE_IMAGE.match(line.strip())
            if img_match:
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)
                _flush_table(table_rows, current_blocks)
                alt_text = img_match.group(1)
                url = img_match.group(2)
                current_blocks.append(
                    ContentBlock(
                        type=ContentType.IMAGE,
                        content=alt_text,
                        metadata={"url": url, "alt": alt_text},
                    )
                )
                i += 1
                continue

            # ---- Heading ----
            heading_match = _RE_HEADING.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()

                # Flush pending lists / tables before heading
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)
                _flush_table(table_rows, current_blocks)

                if level == 1:
                    # H1: start a new slide/section boundary
                    if first_h1_seen:
                        _commit_slide_and_section()
                    else:
                        first_h1_seen = True
                        # Use the very first H1 as the overall document title
                        content.title = text

                    slide_title = text
                    section_title = text
                elif level == 2:
                    # H2: subtitle for the current slide, also a heading block
                    if not slide_subtitle:
                        slide_subtitle = text
                    current_blocks.append(
                        ContentBlock(type=ContentType.HEADING, content=text, level=level)
                    )
                else:
                    current_blocks.append(
                        ContentBlock(type=ContentType.HEADING, content=text, level=level)
                    )
                i += 1
                continue

            # ---- Table ----
            table_match = _RE_TABLE_ROW.match(line.strip())
            if table_match:
                # Flush any pending lists first
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)

                # Check if this is a separator row
                if _RE_TABLE_SEP.match(line.strip()):
                    # Skip separator rows
                    i += 1
                    continue

                table_rows.append(_parse_table_row(line.strip()))
                i += 1
                continue
            else:
                # If we were accumulating table rows and now hit a non-table line, flush
                _flush_table(table_rows, current_blocks)

            # ---- Bullet list ----
            bullet_match = _RE_BULLET.match(line)
            if bullet_match:
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)
                _flush_table(table_rows, current_blocks)
                bullet_items.append(bullet_match.group(2).strip())
                i += 1
                continue
            else:
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)

            # ---- Numbered list ----
            numbered_match = _RE_NUMBERED.match(line)
            if numbered_match:
                _flush_list(bullet_items, ContentType.BULLET_LIST, current_blocks)
                _flush_table(table_rows, current_blocks)
                numbered_items.append(numbered_match.group(2).strip())
                i += 1
                continue
            else:
                _flush_list(numbered_items, ContentType.NUMBERED_LIST, current_blocks)

            # ---- Blank line (skip) ----
            if not line.strip():
                i += 1
                continue

            # ---- Plain text paragraph ----
            current_blocks.append(
                ContentBlock(type=ContentType.TEXT, content=line.strip())
            )
            i += 1

        # ---- End of file: flush remaining code block if still open ----
        if in_code_block and code_lines:
            metadata = {"language": code_lang} if code_lang else {}
            current_blocks.append(
                ContentBlock(
                    type=ContentType.CODE,
                    content="\n".join(code_lines),
                    metadata=metadata,
                )
            )

        # Commit the last slide/section
        _commit_slide_and_section()

        # If no title was set from H1, derive from first slide
        if not content.title and content.slides:
            content.title = content.slides[0].title

        return content
