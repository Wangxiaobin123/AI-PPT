"""PDF generation skill -- converts various input formats into PDF documents."""

from __future__ import annotations

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
# Parsers -> StructuredContent (sections-based, reuses docx patterns)
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
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return _parse_text_to_sections(text, title)


# ---------------------------------------------------------------------------
# The skill
# ---------------------------------------------------------------------------

class PdfSkill(BaseSkill):
    """Skill that generates PDF documents."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="pdf",
            description="Generate PDF documents from various input formats",
            input_formats=["html", "markdown", "json", "text", "csv"],
            output_format="pdf",
            version="1.0.0",
            tags=["document", "pdf", "report"],
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
                from src.generators.pdf_generator import PdfGenerator
                generator = PdfGenerator()
            except ImportError:
                logger.warning("pdf_generator_not_found", detail="Using fallback generator")
                generator = _FallbackPdfGenerator()

            output_bytes = await generator.generate(structured, gen_meta)

            return SkillResult(
                success=True,
                output_format="pdf",
                content_bytes=output_bytes,
                metadata={
                    "title": structured.title,
                    "section_count": len(structured.sections),
                    "content_format": content_format,
                    "template": template,
                },
            )

        except Exception as exc:
            logger.exception("pdf_skill_error")
            return SkillResult(
                success=False,
                output_format="pdf",
                error=f"{type(exc).__name__}: {exc}",
                metadata={"traceback": traceback.format_exc()},
            )

    async def qa_check(self, result: SkillResult) -> QAReport:
        report = await super().qa_check(result)
        if result.content_bytes:
            is_pdf = result.content_bytes[:5] == b"%PDF-"
            report.checks.append(
                QACheck(
                    name="valid_pdf_header",
                    passed=is_pdf,
                    detail="File starts with %PDF- header" if is_pdf else "Invalid PDF header",
                )
            )
            report.passed = report.passed and is_pdf
        return report


# ---------------------------------------------------------------------------
# Fallback generator
# ---------------------------------------------------------------------------

class _FallbackPdfGenerator:
    """Minimal PDF generator using reportlab."""

    async def generate(self, content: StructuredContent, metadata: GenerationMetadata) -> bytes:
        from io import BytesIO

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib import colors

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()

        # Custom styles.
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=22,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=14,
            textColor=colors.grey,
            spaceAfter=18,
            alignment=1,  # center
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=8,
            spaceBefore=14,
        )
        sub_heading_style = ParagraphStyle(
            "SubHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceAfter=6,
            spaceBefore=10,
        )
        body_style = styles["BodyText"]
        bullet_style = ParagraphStyle(
            "BulletItem",
            parent=body_style,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=2,
            spaceAfter=2,
        )
        code_style = ParagraphStyle(
            "CodeBlock",
            parent=body_style,
            fontName="Courier",
            fontSize=9,
            leftIndent=12,
            spaceBefore=4,
            spaceAfter=4,
        )

        story: list = []

        # Title
        if content.title:
            story.append(Paragraph(content.title, title_style))

        if content.subtitle:
            story.append(Paragraph(content.subtitle, subtitle_style))

        if content.title or content.subtitle:
            story.append(Spacer(1, 12))

        for section in content.sections:
            if section.title:
                story.append(Paragraph(section.title, section_style))

            for block in section.blocks:
                if block.type == ContentType.HEADING:
                    story.append(Paragraph(block.content, sub_heading_style))

                elif block.type == ContentType.TEXT:
                    story.append(Paragraph(block.content, body_style))
                    story.append(Spacer(1, 4))

                elif block.type == ContentType.BULLET_LIST:
                    for item in block.items:
                        story.append(
                            Paragraph(f"\u2022  {item}", bullet_style)
                        )
                    story.append(Spacer(1, 4))

                elif block.type == ContentType.NUMBERED_LIST:
                    for i, item in enumerate(block.items, start=1):
                        story.append(
                            Paragraph(f"{i}.  {item}", bullet_style)
                        )
                    story.append(Spacer(1, 4))

                elif block.type == ContentType.TABLE and block.rows:
                    table_data = [row[:] for row in block.rows]
                    t = Table(table_data, repeatRows=1)
                    t_style = TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ])
                    t.setStyle(t_style)
                    story.append(t)
                    story.append(Spacer(1, 8))

                elif block.type == ContentType.CODE:
                    # Escape XML-sensitive chars for Paragraph.
                    escaped = (
                        block.content
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(Paragraph(escaped, code_style))
                    story.append(Spacer(1, 4))

        if not story:
            story.append(Paragraph("(empty document)", body_style))

        doc.build(story)
        return buf.getvalue()
