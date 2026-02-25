#!/usr/bin/env python3
"""Generate PDF from input content. Invoked by Claude Code skill.

This script parses Markdown or HTML into StructuredContent and then renders
the sections to a PDF using reportlab (if available) or falls back to a
lightweight HTML-to-PDF pipeline.
"""
import argparse
import io
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.parsers.markdown_parser import MarkdownParser
from src.generators.base import GenerationMetadata, StructuredContent


def _render_pdf_reportlab(structured: StructuredContent, metadata: GenerationMetadata) -> bytes:
    """Render a StructuredContent to PDF bytes using reportlab."""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    colors = {"primary": "2B579A", "text": "333333", "table_header": "2B579A", "table_alt": "F2F2F2"}
    colors.update(metadata.style.get("color_scheme", {}))

    page_size_name = metadata.options.get("page_size", metadata.style.get("page_size", "letter"))
    page_size = A4 if page_size_name.lower() == "a4" else letter

    orientation = metadata.options.get("orientation", metadata.style.get("orientation", "portrait"))
    if orientation.lower() == "landscape":
        page_size = (page_size[1], page_size[0])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        textColor=HexColor(f"#{colors['primary']}"),
        alignment=TA_CENTER,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        parent=styles["Normal"],
        fontSize=16,
        leading=20,
        textColor=HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=24,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=HexColor(f"#{colors['primary']}"),
        spaceBefore=18,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="SubHeading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        textColor=HexColor(f"#{colors['primary']}"),
        spaceBefore=12,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="BodyText11",
        parent=styles["Normal"],
        fontSize=11,
        leading=13,
        textColor=HexColor(f"#{colors['text']}"),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="CodeBlock",
        parent=styles["Code"],
        fontSize=9,
        leading=11,
        backColor=HexColor("#F5F5F5"),
        borderPadding=6,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="BulletItem",
        parent=styles["Normal"],
        fontSize=11,
        leading=13,
        leftIndent=24,
        bulletIndent=12,
        textColor=HexColor(f"#{colors['text']}"),
        spaceAfter=3,
    ))

    story = []

    # Title page
    if structured.title:
        story.append(Spacer(1, 2 * inch))
        story.append(Paragraph(structured.title, styles["DocTitle"]))
        if structured.subtitle:
            story.append(Paragraph(structured.subtitle, styles["DocSubtitle"]))
        if structured.author:
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph(structured.author, styles["DocSubtitle"]))
        story.append(PageBreak())

    # Sections
    for section in structured.sections:
        if section.title:
            story.append(Paragraph(section.title, styles["SectionHeading"]))

        for block in section.blocks:
            btype = block.type.value

            if btype == "heading":
                level = block.level
                style_name = "SubHeading" if level <= 2 else "BodyText11"
                story.append(Paragraph(f"<b>{block.content}</b>", styles[style_name]))

            elif btype == "text":
                if block.content:
                    story.append(Paragraph(block.content, styles["BodyText11"]))

            elif btype in ("bullet_list", "numbered_list"):
                for idx, item in enumerate(block.items):
                    prefix = f"{idx + 1}. " if btype == "numbered_list" else "\u2022 "
                    story.append(Paragraph(f"{prefix}{item}", styles["BulletItem"]))
                story.append(Spacer(1, 4))

            elif btype == "table" and block.rows:
                header_color = HexColor(f"#{colors['table_header']}")
                alt_color = HexColor(f"#{colors.get('table_alt', 'F2F2F2')}")
                table_data = [row for row in block.rows]
                t = Table(table_data, repeatRows=1)
                table_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), header_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
                # Alternating row colors
                for row_idx in range(1, len(table_data)):
                    if row_idx % 2 == 0:
                        table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), alt_color))
                t.setStyle(TableStyle(table_style))
                story.append(t)
                story.append(Spacer(1, 8))

            elif btype == "code":
                if block.content:
                    story.append(Preformatted(block.content, styles["CodeBlock"]))

            elif btype == "image":
                # Placeholder for images
                story.append(Paragraph(
                    f"<i>[Image: {block.content or block.metadata.get('url', 'image')}]</i>",
                    styles["BodyText11"],
                ))

    if not story:
        story.append(Paragraph("Empty document", styles["BodyText11"]))

    doc.build(story)
    return buf.getvalue()


def _render_pdf_fallback(structured: StructuredContent, metadata: GenerationMetadata) -> bytes:
    """Minimal fallback PDF renderer when reportlab is not available.

    Generates a very simple PDF with plain text content. This is intended as a
    last resort; install reportlab for full-featured PDF output.
    """
    lines = []
    if structured.title:
        lines.append(structured.title)
        lines.append("=" * len(structured.title))
        lines.append("")
    if structured.subtitle:
        lines.append(structured.subtitle)
        lines.append("")
    if structured.author:
        lines.append(f"Author: {structured.author}")
        lines.append("")

    for section in structured.sections:
        if section.title:
            lines.append("")
            lines.append(section.title)
            lines.append("-" * len(section.title))
        for block in section.blocks:
            btype = block.type.value
            if btype in ("text", "heading", "code"):
                lines.append(block.content)
            elif btype in ("bullet_list", "numbered_list"):
                for idx, item in enumerate(block.items):
                    prefix = f"  {idx + 1}. " if btype == "numbered_list" else "  * "
                    lines.append(f"{prefix}{item}")
            elif btype == "table" and block.rows:
                for row in block.rows:
                    lines.append(" | ".join(str(c) for c in row))
            lines.append("")

    text_content = "\n".join(lines)

    # Build a minimal valid PDF
    # This is a basic PDF 1.4 structure
    objects = []

    def add_obj(content: str) -> int:
        idx = len(objects) + 1
        objects.append(content)
        return idx

    catalog_id = add_obj("")
    pages_id = add_obj("")
    page_id = add_obj("")
    font_id = add_obj(f"{len(objects) + 1} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj")

    # Escape special PDF characters and encode text
    safe_text = text_content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    text_lines = safe_text.split("\n")

    # Build text stream with simple pagination
    page_height = 792  # Letter size in points
    margin = 72
    usable_height = page_height - 2 * margin
    line_height = 12
    lines_per_page = int(usable_height / line_height)

    pages_list = []
    for page_start in range(0, len(text_lines), lines_per_page):
        page_lines = text_lines[page_start:page_start + lines_per_page]
        stream_parts = [f"BT /F1 10 Tf {margin} {page_height - margin} Td {line_height} TL"]
        for tl in page_lines:
            stream_parts.append(f"({tl}) '")
        stream_parts.append("ET")
        stream_content = "\n".join(stream_parts)
        pages_list.append((stream_content, len(stream_content)))

    # Rebuild objects properly
    objects.clear()

    # obj 1: catalog
    add_obj("")
    # obj 2: pages
    add_obj("")
    # obj 3: font
    add_obj("")

    page_obj_ids = []
    for stream_content, stream_len in pages_list:
        # page object
        p_id = len(objects) + 1
        add_obj("")
        page_obj_ids.append(p_id)
        # stream object
        add_obj("")

    # Now write proper PDF
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")

    offsets = {}

    # Object 1: Catalog
    offsets[1] = output.tell()
    page_ref_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    output.write(f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n".encode())

    # Object 2: Pages
    offsets[2] = output.tell()
    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    output.write(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>\nendobj\n".encode())

    # Object 3: Font
    offsets[3] = output.tell()
    output.write(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    # Page + stream objects
    obj_counter = 4
    for stream_content, stream_len in pages_list:
        page_obj_id = obj_counter
        stream_obj_id = obj_counter + 1

        offsets[page_obj_id] = output.tell()
        output.write(
            f"{page_obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 {page_height}] "
            f"/Contents {stream_obj_id} 0 R "
            f"/Resources << /Font << /F1 3 0 R >> >> >>\n"
            f"endobj\n".encode()
        )

        offsets[stream_obj_id] = output.tell()
        encoded_stream = stream_content.encode("latin-1", errors="replace")
        output.write(
            f"{stream_obj_id} 0 obj\n"
            f"<< /Length {len(encoded_stream)} >>\n"
            f"stream\n".encode()
        )
        output.write(encoded_stream)
        output.write(b"\nendstream\nendobj\n")

        obj_counter += 2

    # Cross-reference table
    xref_offset = output.tell()
    total_objs = obj_counter
    output.write(f"xref\n0 {total_objs}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for obj_id in range(1, total_objs):
        output.write(f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode())

    # Trailer
    output.write(
        f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )

    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Generate PDF from content")
    parser.add_argument("--input", "-i", required=True, help="Input file path")
    parser.add_argument("--output", "-o", default="output.pdf", help="Output file path")
    parser.add_argument("--title", "-t", default="", help="Document title")
    parser.add_argument("--author", "-a", default="", help="Document author")
    parser.add_argument(
        "--format",
        "-f",
        default="markdown",
        choices=["markdown", "html"],
        help="Input content format (default: markdown)",
    )
    parser.add_argument(
        "--orientation",
        default="portrait",
        choices=["portrait", "landscape"],
        help="Page orientation (default: portrait)",
    )
    parser.add_argument(
        "--page-size",
        default="letter",
        choices=["letter", "a4"],
        help="Page size (default: letter)",
    )
    parser.add_argument(
        "--style",
        "-s",
        default=None,
        help="JSON string of style overrides",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    content_text = input_path.read_text(encoding="utf-8")

    # Parse based on input format
    if args.format == "html":
        from src.parsers.html_parser import HtmlParser
        html_parser = HtmlParser()
        structured = html_parser.parse(content_text)
    else:
        md_parser = MarkdownParser()
        structured = md_parser.parse(content_text)

    if args.title:
        structured.title = args.title
    if args.author:
        structured.author = args.author

    # Build metadata with optional style overrides
    style = {}
    if args.style:
        import json
        try:
            style = json.loads(args.style)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse style JSON: {e}", file=sys.stderr)

    style.setdefault("page_size", args.page_size)
    style.setdefault("orientation", args.orientation)

    metadata = GenerationMetadata(style=style)

    # Try reportlab first, fall back to minimal PDF
    try:
        result = _render_pdf_reportlab(structured, metadata)
        engine = "reportlab"
    except ImportError:
        print("Warning: reportlab not installed. Using fallback PDF renderer.", file=sys.stderr)
        print("Install reportlab for full-featured PDF output: pip install reportlab", file=sys.stderr)
        result = _render_pdf_fallback(structured, metadata)
        engine = "fallback"

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)
    print(
        f"Generated: {args.output} ({len(result):,} bytes, "
        f"{len(structured.sections)} sections, engine={engine})"
    )


if __name__ == "__main__":
    main()
