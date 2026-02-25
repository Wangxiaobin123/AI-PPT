"""HTML generation skill -- converts various input formats into styled HTML pages."""

from __future__ import annotations

import html as html_lib
import json
import re
import traceback

from src.generators.base import (
    ContentBlock,
    ContentType,
    GenerationMetadata,
    SectionData,
    StructuredContent,
)
from src.skills.base import BaseSkill
from src.skills.models import QACheck, QAReport, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Content format detection
# ---------------------------------------------------------------------------

def _detect_format(content: str) -> str:
    """Heuristically detect the format of *content*."""
    stripped = content.strip()

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

    first_line = stripped.split("\n", 1)[0]
    if "," in first_line and "<" not in first_line and first_line.count(",") >= 2:
        return "csv"

    if "<html" in stripped.lower() or stripped.startswith("<!") or "</" in stripped[:200]:
        return "html"

    if any(stripped.startswith(c) for c in ("# ", "## ", "### ")):
        return "markdown"
    if "\n# " in stripped or "\n## " in stripped:
        return "markdown"

    return "text"


# ---------------------------------------------------------------------------
# Parsers -> StructuredContent (sections-based)
# ---------------------------------------------------------------------------

def _parse_markdown_to_sections(content: str, title: str) -> StructuredContent:
    sections: list[SectionData] = []
    current_title = ""
    current_blocks: list[ContentBlock] = []
    doc_title = title

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("# ") and not stripped.startswith("## "):
            heading = stripped.lstrip("# ").strip()
            if not doc_title:
                doc_title = heading
            continue

        if stripped.startswith("## "):
            if current_title or current_blocks:
                sections.append(SectionData(title=current_title, blocks=current_blocks))
            current_title = stripped.lstrip("# ").strip()
            current_blocks = []
            continue

        if stripped.startswith("### "):
            level = len(stripped.split()[0])
            current_blocks.append(
                ContentBlock(type=ContentType.HEADING, content=stripped.lstrip("# ").strip(), level=level)
            )
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            item_text = stripped[2:].strip()
            if current_blocks and current_blocks[-1].type == ContentType.BULLET_LIST:
                current_blocks[-1].items.append(item_text)
            else:
                current_blocks.append(ContentBlock(type=ContentType.BULLET_LIST, items=[item_text]))
            continue

        if re.match(r"^\d+\.\s", stripped):
            item_text = re.sub(r"^\d+\.\s*", "", stripped)
            if current_blocks and current_blocks[-1].type == ContentType.NUMBERED_LIST:
                current_blocks[-1].items.append(item_text)
            else:
                current_blocks.append(ContentBlock(type=ContentType.NUMBERED_LIST, items=[item_text]))
            continue

        if stripped:
            current_blocks.append(ContentBlock(type=ContentType.TEXT, content=stripped))

    if current_title or current_blocks:
        sections.append(SectionData(title=current_title, blocks=current_blocks))

    return StructuredContent(title=doc_title or "Untitled", sections=sections)


def _parse_text_to_sections(content: str, title: str) -> StructuredContent:
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    blocks = [ContentBlock(type=ContentType.TEXT, content=p) for p in paragraphs]
    section = SectionData(title="", blocks=blocks)
    return StructuredContent(title=title or "Untitled", sections=[section])


def _parse_json_to_sections(content: str, title: str) -> StructuredContent:
    data = json.loads(content)
    if isinstance(data, dict) and ("sections" in data or "slides" in data):
        sc = StructuredContent.model_validate(data)
        if title:
            sc.title = title
        return sc
    if isinstance(data, list):
        sections = []
        for item in data:
            sec_title = item.get("title", "")
            body = item.get("body", item.get("content", ""))
            blocks = [ContentBlock(type=ContentType.TEXT, content=body)] if body else []
            sections.append(SectionData(title=sec_title, blocks=blocks))
        return StructuredContent(title=title or "Untitled", sections=sections)
    return _parse_text_to_sections(json.dumps(data, indent=2), title)


def _parse_csv_to_sections(content: str, title: str) -> StructuredContent:
    rows: list[list[str]] = []
    for line in content.strip().split("\n"):
        if line.strip():
            rows.append([cell.strip() for cell in line.split(",")])
    table_block = ContentBlock(type=ContentType.TABLE, rows=rows)
    section = SectionData(title=title or "Data", blocks=[table_block])
    return StructuredContent(title=title or "Data", sections=[section])


def _parse_html_to_sections(content: str, title: str) -> StructuredContent:
    """When input is already HTML, wrap it as a single text block preserving raw HTML."""
    return StructuredContent(
        title=title or "Untitled",
        sections=[
            SectionData(
                title="",
                blocks=[ContentBlock(type=ContentType.TEXT, content=content, metadata={"raw_html": True})],
            )
        ],
    )


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

_DEFAULT_CSS = """\
:root {
  --primary: #2563eb;
  --bg: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --border: #e2e8f0;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}
h1 { font-size: 2rem; margin-bottom: 0.5rem; color: var(--primary); }
h2 { font-size: 1.5rem; margin: 1.5rem 0 0.75rem; border-bottom: 2px solid var(--border); padding-bottom: 0.25rem; }
h3, h4 { font-size: 1.15rem; margin: 1rem 0 0.5rem; }
p { margin-bottom: 0.75rem; }
ul, ol { margin: 0.5rem 0 0.75rem 1.5rem; }
li { margin-bottom: 0.25rem; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
th { background: #f1f5f9; font-weight: 600; }
pre, code { font-family: "Fira Code", "Consolas", monospace; background: #f8fafc; border-radius: 4px; }
pre { padding: 1rem; overflow-x: auto; margin: 0.75rem 0; border: 1px solid var(--border); }
code { padding: 0.15rem 0.35rem; font-size: 0.9em; }
.subtitle { color: var(--muted); font-size: 1.1rem; margin-bottom: 1.5rem; }
"""


def _render_block(block: ContentBlock) -> str:
    """Render a single ContentBlock to an HTML fragment."""
    if block.metadata.get("raw_html"):
        return block.content

    if block.type == ContentType.HEADING:
        tag = f"h{min(block.level, 6)}"
        return f"<{tag}>{html_lib.escape(block.content)}</{tag}>"

    if block.type == ContentType.TEXT:
        return f"<p>{html_lib.escape(block.content)}</p>"

    if block.type == ContentType.BULLET_LIST:
        items = "".join(f"<li>{html_lib.escape(i)}</li>" for i in block.items)
        return f"<ul>{items}</ul>"

    if block.type == ContentType.NUMBERED_LIST:
        items = "".join(f"<li>{html_lib.escape(i)}</li>" for i in block.items)
        return f"<ol>{items}</ol>"

    if block.type == ContentType.TABLE and block.rows:
        header_row = block.rows[0]
        thead = "<tr>" + "".join(f"<th>{html_lib.escape(c)}</th>" for c in header_row) + "</tr>"
        tbody_rows = ""
        for row in block.rows[1:]:
            tbody_rows += "<tr>" + "".join(f"<td>{html_lib.escape(c)}</td>" for c in row) + "</tr>"
        return f"<table><thead>{thead}</thead><tbody>{tbody_rows}</tbody></table>"

    if block.type == ContentType.CODE:
        return f"<pre><code>{html_lib.escape(block.content)}</code></pre>"

    if block.type == ContentType.IMAGE:
        url = block.metadata.get("url", "")
        alt = html_lib.escape(block.content or "image")
        return f'<figure><img src="{html_lib.escape(url)}" alt="{alt}" style="max-width:100%;" /><figcaption>{alt}</figcaption></figure>'

    return f"<p>{html_lib.escape(block.content)}</p>"


# ---------------------------------------------------------------------------
# The skill
# ---------------------------------------------------------------------------

class HtmlDesignSkill(BaseSkill):
    """Skill that generates styled HTML pages."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="html",
            description="Generate styled HTML pages from various input formats",
            input_formats=["html", "markdown", "json", "text", "csv"],
            output_format="html",
            version="1.0.0",
            tags=["web", "html", "design"],
        )

    async def validate_params(self, params: dict) -> bool:
        if "content" not in params:
            return False
        if not isinstance(params["content"], str):
            return False
        if not params["content"].strip():
            return False
        return True

    async def execute(self, params: dict, context: dict) -> SkillResult:
        try:
            content_str: str = params["content"]
            content_format: str = params.get("content_format", "") or _detect_format(content_str)
            title: str = params.get("title", "")
            template: str = params.get("template", "default")
            style: dict = params.get("style", {})

            parser_map = {
                "markdown": _parse_markdown_to_sections,
                "text": _parse_text_to_sections,
                "json": _parse_json_to_sections,
                "csv": _parse_csv_to_sections,
                "html": _parse_html_to_sections,
            }
            parser = parser_map.get(content_format, _parse_text_to_sections)
            structured = parser(content_str, title)

            gen_meta = GenerationMetadata(template=template, style=style)

            try:
                from src.generators.html_generator import HtmlGenerator
                generator = HtmlGenerator()
                output_bytes = await generator.generate(structured, gen_meta)
            except ImportError:
                logger.warning("html_generator_not_found", detail="Using fallback renderer")
                output_bytes = self._fallback_render(structured, gen_meta)

            return SkillResult(
                success=True,
                output_format="html",
                content_bytes=output_bytes,
                metadata={
                    "title": structured.title,
                    "section_count": len(structured.sections),
                    "content_format": content_format,
                    "template": template,
                },
            )

        except Exception as exc:
            logger.exception("html_skill_error")
            return SkillResult(
                success=False,
                output_format="html",
                error=f"{type(exc).__name__}: {exc}",
                metadata={"traceback": traceback.format_exc()},
            )

    # ------------------------------------------------------------------
    # Fallback renderer
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_render(content: StructuredContent, metadata: GenerationMetadata) -> bytes:
        """Render StructuredContent directly to an HTML string."""
        custom_css = metadata.style.get("css", "")
        primary_color = metadata.style.get("primary_color", "")
        css = _DEFAULT_CSS
        if primary_color:
            css = css.replace("#2563eb", primary_color)
        if custom_css:
            css += "\n" + custom_css

        parts: list[str] = []
        parts.append("<!DOCTYPE html>")
        parts.append(f"<html lang=\"en\"><head><meta charset=\"UTF-8\">")
        parts.append(f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">")
        parts.append(f"<title>{html_lib.escape(content.title)}</title>")
        parts.append(f"<style>{css}</style>")
        parts.append("</head><body>")

        if content.title:
            parts.append(f"<h1>{html_lib.escape(content.title)}</h1>")
        if content.subtitle:
            parts.append(f"<p class=\"subtitle\">{html_lib.escape(content.subtitle)}</p>")

        for section in content.sections:
            parts.append("<section>")
            if section.title:
                parts.append(f"<h2>{html_lib.escape(section.title)}</h2>")
            for block in section.blocks:
                parts.append(_render_block(block))
            parts.append("</section>")

        parts.append("</body></html>")
        return "\n".join(parts).encode("utf-8")

    # ------------------------------------------------------------------
    # QA
    # ------------------------------------------------------------------

    async def qa_check(self, result: SkillResult) -> QAReport:
        report = await super().qa_check(result)
        if result.content_bytes:
            text = result.content_bytes.decode("utf-8", errors="replace")
            has_doctype = text.strip().lower().startswith("<!doctype html>")
            report.checks.append(
                QACheck(
                    name="valid_html_doctype",
                    passed=has_doctype,
                    detail="Starts with <!DOCTYPE html>" if has_doctype else "Missing DOCTYPE",
                )
            )
            has_closing_html = "</html>" in text.lower()
            report.checks.append(
                QACheck(
                    name="valid_html_closing",
                    passed=has_closing_html,
                    detail="Has closing </html> tag" if has_closing_html else "Missing </html>",
                )
            )
            report.passed = report.passed and has_doctype and has_closing_html
        return report
