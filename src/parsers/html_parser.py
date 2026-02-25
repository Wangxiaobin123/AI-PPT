"""HTML parser: converts HTML into StructuredContent using BeautifulSoup4.

Handles:
- h1-h6 tags -> heading blocks (slides/sections split at h1)
- p tags -> text blocks
- ul -> bullet_list blocks
- ol -> numbered_list blocks
- table -> table blocks
- img -> image blocks
- pre/code -> code blocks
"""

from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from src.generators.base import (
    ContentBlock,
    ContentType,
    SectionData,
    SlideData,
    StructuredContent,
)


class HtmlParser:
    """Parse HTML markup into a :class:`StructuredContent` instance."""

    def parse(self, html: str) -> StructuredContent:
        """Parse an HTML string and return StructuredContent."""
        soup = BeautifulSoup(html, "html.parser")

        # If there is an explicit <body>, use it; otherwise parse the whole tree.
        body = soup.body if soup.body else soup

        content = StructuredContent()

        # Try to pull <title> for the document title
        if soup.title and soup.title.string:
            content.title = soup.title.string.strip()

        # Walk top-level elements and group into slides/sections by h1
        current_blocks: list[ContentBlock] = []
        slide_title = ""
        slide_subtitle = ""
        section_title = ""
        first_h1_seen = False

        def _commit() -> None:
            nonlocal current_blocks, slide_title, slide_subtitle, section_title
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

        for element in body.children:
            if isinstance(element, NavigableString):
                text = element.strip()
                if text:
                    current_blocks.append(ContentBlock(type=ContentType.TEXT, content=text))
                continue

            if not isinstance(element, Tag):
                continue

            tag_name = element.name.lower() if element.name else ""

            # --- Headings ---
            if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag_name[1])
                text = element.get_text(strip=True)
                if level == 1:
                    if first_h1_seen:
                        _commit()
                    else:
                        first_h1_seen = True
                        if not content.title:
                            content.title = text
                    slide_title = text
                    section_title = text
                elif level == 2:
                    if not slide_subtitle:
                        slide_subtitle = text
                    current_blocks.append(
                        ContentBlock(type=ContentType.HEADING, content=text, level=level)
                    )
                else:
                    current_blocks.append(
                        ContentBlock(type=ContentType.HEADING, content=text, level=level)
                    )

            # --- Paragraph ---
            elif tag_name == "p":
                # Check if the paragraph contains only an image
                imgs = element.find_all("img")
                if imgs and element.get_text(strip=True) == "":
                    for img in imgs:
                        current_blocks.append(self._parse_img(img))
                else:
                    text = element.get_text(strip=True)
                    if text:
                        current_blocks.append(ContentBlock(type=ContentType.TEXT, content=text))

            # --- Unordered list ---
            elif tag_name == "ul":
                items = [li.get_text(strip=True) for li in element.find_all("li", recursive=False)]
                if items:
                    current_blocks.append(
                        ContentBlock(type=ContentType.BULLET_LIST, items=items)
                    )

            # --- Ordered list ---
            elif tag_name == "ol":
                items = [li.get_text(strip=True) for li in element.find_all("li", recursive=False)]
                if items:
                    current_blocks.append(
                        ContentBlock(type=ContentType.NUMBERED_LIST, items=items)
                    )

            # --- Table ---
            elif tag_name == "table":
                current_blocks.append(self._parse_table(element))

            # --- Image ---
            elif tag_name == "img":
                current_blocks.append(self._parse_img(element))

            # --- Pre / code ---
            elif tag_name == "pre":
                code_tag = element.find("code")
                code_text = code_tag.get_text() if code_tag else element.get_text()
                language = ""
                if code_tag:
                    classes = code_tag.get("class", [])
                    for cls in classes:
                        if cls.startswith("language-"):
                            language = cls[len("language-"):]
                            break
                metadata = {"language": language} if language else {}
                current_blocks.append(
                    ContentBlock(type=ContentType.CODE, content=code_text, metadata=metadata)
                )

            elif tag_name == "code":
                # Inline code outside <pre> treated as a small code block
                current_blocks.append(
                    ContentBlock(type=ContentType.CODE, content=element.get_text())
                )

            # --- Div / article / section: recurse into children ---
            elif tag_name in ("div", "article", "section", "main", "header", "footer", "nav"):
                inner = self._parse_container(element)
                current_blocks.extend(inner)

            else:
                # Fallback: extract text if present
                text = element.get_text(strip=True)
                if text:
                    current_blocks.append(ContentBlock(type=ContentType.TEXT, content=text))

        # Flush remaining
        _commit()

        if not content.title and content.slides:
            content.title = content.slides[0].title

        return content

    def parse_file(self, path: str) -> StructuredContent:
        """Read an HTML file and parse it."""
        with open(path, "r", encoding="utf-8") as fh:
            return self.parse(fh.read())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_img(tag: Tag) -> ContentBlock:
        src = tag.get("src", "")
        alt = tag.get("alt", "")
        return ContentBlock(
            type=ContentType.IMAGE,
            content=alt,
            metadata={"url": src, "alt": alt},
        )

    @staticmethod
    def _parse_table(table: Tag) -> ContentBlock:
        rows: list[list[str]] = []

        # Header rows from <thead>
        thead = table.find("thead")
        if thead:
            for tr in thead.find_all("tr"):
                cells = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)

        # Body rows from <tbody> or direct <tr>
        tbody = table.find("tbody")
        row_source = tbody if tbody else table
        for tr in row_source.find_all("tr", recursive=False):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]
            if cells:
                # Avoid duplicating header rows already captured via thead
                if thead and rows and cells == rows[0]:
                    continue
                rows.append(cells)

        return ContentBlock(type=ContentType.TABLE, rows=rows)

    def _parse_container(self, element: Tag) -> list[ContentBlock]:
        """Recursively extract blocks from container elements (div, section, etc.)."""
        blocks: list[ContentBlock] = []
        for child in element.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    blocks.append(ContentBlock(type=ContentType.TEXT, content=text))
                continue
            if not isinstance(child, Tag):
                continue
            tag = child.name.lower() if child.name else ""
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag[1])
                blocks.append(
                    ContentBlock(
                        type=ContentType.HEADING,
                        content=child.get_text(strip=True),
                        level=level,
                    )
                )
            elif tag == "p":
                text = child.get_text(strip=True)
                if text:
                    blocks.append(ContentBlock(type=ContentType.TEXT, content=text))
            elif tag == "ul":
                items = [li.get_text(strip=True) for li in child.find_all("li", recursive=False)]
                if items:
                    blocks.append(ContentBlock(type=ContentType.BULLET_LIST, items=items))
            elif tag == "ol":
                items = [li.get_text(strip=True) for li in child.find_all("li", recursive=False)]
                if items:
                    blocks.append(ContentBlock(type=ContentType.NUMBERED_LIST, items=items))
            elif tag == "table":
                blocks.append(self._parse_table(child))
            elif tag == "img":
                blocks.append(self._parse_img(child))
            elif tag == "pre":
                code_tag = child.find("code")
                code_text = code_tag.get_text() if code_tag else child.get_text()
                blocks.append(ContentBlock(type=ContentType.CODE, content=code_text))
            elif tag in ("div", "article", "section", "main", "header", "footer", "nav"):
                blocks.extend(self._parse_container(child))
            else:
                text = child.get_text(strip=True)
                if text:
                    blocks.append(ContentBlock(type=ContentType.TEXT, content=text))
        return blocks
