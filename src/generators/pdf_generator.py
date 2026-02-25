"""PDF document generator using ReportLab."""

import io

from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .base import (
    BaseGenerator,
    ContentBlock,
    ContentType,
    GenerationMetadata,
    SectionData,
    StructuredContent,
)


DEFAULT_COLORS = {
    "primary": "2B579A",
    "secondary": "217346",
    "accent": "B7472A",
    "text": "333333",
    "table_header": "2B579A",
    "table_alt_row": "F2F2F2",
    "code_bg": "F5F5F5",
}

DEFAULT_FONTS = {
    "title": "Helvetica-Bold",
    "body": "Helvetica",
    "code": "Courier",
}


def _hex_to_rl_color(hex_color: str) -> rl_colors.Color:
    """Convert a hex color string to a ReportLab Color."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return rl_colors.Color(r, g, b)


def _resolve_colors(metadata: GenerationMetadata) -> dict[str, str]:
    colors = dict(DEFAULT_COLORS)
    colors.update(metadata.style.get("color_scheme", {}))
    return colors


def _map_font_to_ps(font_name: str) -> str:
    """Map common font names to ReportLab PostScript font names.

    ReportLab only supports a limited set of built-in PostScript fonts.
    This maps user-friendly names to valid PostScript equivalents.
    """
    mapping = {
        # Sans-serif
        "arial": "Helvetica",
        "calibri": "Helvetica",
        "segoe ui": "Helvetica",
        "verdana": "Helvetica",
        "tahoma": "Helvetica",
        "trebuchet ms": "Helvetica",
        "helvetica": "Helvetica",
        # Serif
        "times new roman": "Times-Roman",
        "times": "Times-Roman",
        "georgia": "Times-Roman",
        "cambria": "Times-Roman",
        "garamond": "Times-Roman",
        # Monospace
        "consolas": "Courier",
        "courier new": "Courier",
        "courier": "Courier",
        "monospace": "Courier",
        # Bold variants
        "arial-bold": "Helvetica-Bold",
        "calibri-bold": "Helvetica-Bold",
        "helvetica-bold": "Helvetica-Bold",
        "times-bold": "Times-Bold",
    }
    lower = font_name.strip().lower()
    return mapping.get(lower, font_name)


def _resolve_fonts(metadata: GenerationMetadata) -> dict[str, str]:
    fonts = dict(DEFAULT_FONTS)
    user_fonts = metadata.style.get("fonts", {})
    for key, value in user_fonts.items():
        fonts[key] = _map_font_to_ps(value)
    return fonts


class _PageNumberCanvas:
    """Mixin-style helper to add page numbers via the onPage/onPageEnd callbacks."""

    @staticmethod
    def add_page_number(canvas, doc):
        """Draw page number at the bottom center of every page."""
        page_num = canvas.getPageNumber()
        text = f"- {page_num} -"
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(_hex_to_rl_color("999999"))
        canvas.drawCentredString(
            doc.pagesize[0] / 2.0,
            15 * mm,
            text,
        )
        canvas.restoreState()


def _build_styles(colors: dict[str, str], fonts: dict[str, str]) -> dict[str, ParagraphStyle]:
    """Build a dictionary of ParagraphStyles for the PDF."""
    base = getSampleStyleSheet()

    primary_color = _hex_to_rl_color(colors["primary"])
    text_color = _hex_to_rl_color(colors["text"])

    styles = {}

    styles["Title"] = ParagraphStyle(
        "CustomTitle",
        parent=base["Title"],
        fontName=fonts["title"],
        fontSize=36,
        leading=42,
        alignment=TA_CENTER,
        textColor=primary_color,
        spaceAfter=12,
    )

    styles["Subtitle"] = ParagraphStyle(
        "CustomSubtitle",
        parent=base["Normal"],
        fontName=fonts["body"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=_hex_to_rl_color("666666"),
        spaceAfter=6,
    )

    styles["Author"] = ParagraphStyle(
        "CustomAuthor",
        parent=base["Normal"],
        fontName=fonts["body"],
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=text_color,
        spaceBefore=24,
    )

    styles["Heading1"] = ParagraphStyle(
        "CustomH1",
        parent=base["Heading1"],
        fontName=fonts["title"],
        fontSize=24,
        leading=30,
        textColor=primary_color,
        spaceBefore=18,
        spaceAfter=10,
    )

    styles["Heading2"] = ParagraphStyle(
        "CustomH2",
        parent=base["Heading2"],
        fontName=fonts["title"],
        fontSize=20,
        leading=26,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
    )

    styles["Heading3"] = ParagraphStyle(
        "CustomH3",
        parent=base["Heading3"],
        fontName=fonts["title"],
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )

    styles["Heading4"] = ParagraphStyle(
        "CustomH4",
        parent=base["Heading4"],
        fontName=fonts["title"],
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4,
    )

    styles["BodyText"] = ParagraphStyle(
        "CustomBody",
        parent=base["Normal"],
        fontName=fonts["body"],
        fontSize=11,
        leading=15,
        textColor=text_color,
        spaceAfter=6,
    )

    styles["BulletItem"] = ParagraphStyle(
        "CustomBullet",
        parent=base["Normal"],
        fontName=fonts["body"],
        fontSize=11,
        leading=15,
        textColor=text_color,
        leftIndent=20,
        spaceAfter=3,
        bulletIndent=8,
        bulletFontName=fonts["body"],
    )

    styles["NumberedItem"] = ParagraphStyle(
        "CustomNumbered",
        parent=base["Normal"],
        fontName=fonts["body"],
        fontSize=11,
        leading=15,
        textColor=text_color,
        leftIndent=20,
        spaceAfter=3,
    )

    styles["Code"] = ParagraphStyle(
        "CustomCode",
        parent=base["Code"],
        fontName=fonts["code"],
        fontSize=9,
        leading=12,
        textColor=_hex_to_rl_color("333333"),
        backColor=_hex_to_rl_color(colors["code_bg"]),
        leftIndent=12,
        rightIndent=12,
        spaceBefore=6,
        spaceAfter=6,
        borderPadding=6,
    )

    return styles


class PDFGenerator(BaseGenerator):
    """Generates PDF documents from structured content."""

    async def generate(
        self, content: StructuredContent, metadata: GenerationMetadata
    ) -> bytes:
        """Generate a PDF file and return it as bytes."""
        buf = io.BytesIO()
        colors = _resolve_colors(metadata)
        fonts = _resolve_fonts(metadata)
        styles = _build_styles(colors, fonts)

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=1 * inch,
            rightMargin=1 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
            title=content.title,
            author=content.author,
        )

        story: list = []

        # Title page
        if content.title:
            self._add_title_page(story, content, styles)

        # Sections
        for idx, section in enumerate(content.sections):
            if idx > 0 or content.title:
                story.append(PageBreak())
            self._render_section(story, section, styles, colors, fonts)

        # Build with page numbers
        doc.build(
            story,
            onFirstPage=_PageNumberCanvas.add_page_number,
            onLaterPages=_PageNumberCanvas.add_page_number,
        )

        return buf.getvalue()

    # ------------------------------------------------------------------ #
    #  Title page
    # ------------------------------------------------------------------ #

    def _add_title_page(self, story: list, content: StructuredContent, styles: dict):
        """Add title page elements to the story."""
        # Vertical spacing to push title toward center
        story.append(Spacer(1, 2 * inch))

        # Title
        story.append(Paragraph(self._escape(content.title), styles["Title"]))

        # Subtitle
        if content.subtitle:
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph(self._escape(content.subtitle), styles["Subtitle"]))

        # Author
        if content.author:
            story.append(Spacer(1, 0.4 * inch))
            story.append(Paragraph(self._escape(content.author), styles["Author"]))

    # ------------------------------------------------------------------ #
    #  Section rendering
    # ------------------------------------------------------------------ #

    def _render_section(
        self,
        story: list,
        section: SectionData,
        styles: dict,
        colors: dict,
        fonts: dict,
    ):
        """Render a section heading and its content blocks."""
        if section.title:
            story.append(Paragraph(self._escape(section.title), styles["Heading1"]))

        for block in section.blocks:
            self._render_block(story, block, styles, colors, fonts)

    def _render_block(
        self,
        story: list,
        block: ContentBlock,
        styles: dict,
        colors: dict,
        fonts: dict,
    ):
        """Render a single content block into the story."""
        if block.type == ContentType.HEADING:
            self._render_heading(story, block, styles)
        elif block.type == ContentType.TEXT:
            self._render_text(story, block, styles)
        elif block.type == ContentType.BULLET_LIST:
            self._render_bullet_list(story, block, styles)
        elif block.type == ContentType.NUMBERED_LIST:
            self._render_numbered_list(story, block, styles)
        elif block.type == ContentType.TABLE:
            self._render_table(story, block, styles, colors, fonts)
        elif block.type == ContentType.CODE:
            self._render_code(story, block, styles)
        elif block.type == ContentType.IMAGE:
            self._render_image_placeholder(story, block, styles)
        else:
            if block.content:
                story.append(Paragraph(self._escape(block.content), styles["BodyText"]))

    def _render_heading(self, story, block, styles):
        level = max(1, min(block.level, 4))
        style_key = f"Heading{level}"
        story.append(Paragraph(self._escape(block.content), styles[style_key]))

    def _render_text(self, story, block, styles):
        if block.content:
            story.append(Paragraph(self._escape(block.content), styles["BodyText"]))

    def _render_bullet_list(self, story, block, styles):
        for item in block.items:
            bullet_text = f"\u2022  {self._escape(item)}"
            story.append(Paragraph(bullet_text, styles["BulletItem"]))
        story.append(Spacer(1, 4))

    def _render_numbered_list(self, story, block, styles):
        for idx, item in enumerate(block.items, start=1):
            numbered_text = f"{idx}.  {self._escape(item)}"
            story.append(Paragraph(numbered_text, styles["NumberedItem"]))
        story.append(Spacer(1, 4))

    def _render_table(self, story, block, styles, colors, fonts):
        rows_data = block.rows
        if not rows_data:
            return

        # Build table data as list of lists of Paragraph objects for wrapping
        body_style = ParagraphStyle(
            "TableCell",
            fontName=fonts["body"],
            fontSize=9,
            leading=12,
            textColor=_hex_to_rl_color(colors["text"]),
        )
        header_style = ParagraphStyle(
            "TableHeader",
            fontName=fonts["title"],
            fontSize=10,
            leading=13,
            textColor=rl_colors.white,
            alignment=TA_CENTER,
        )

        table_data = []
        for row_idx, row in enumerate(rows_data):
            processed_row = []
            for cell_val in row:
                s = header_style if row_idx == 0 else body_style
                processed_row.append(Paragraph(self._escape(str(cell_val)), s))
            table_data.append(processed_row)

        # Ensure all rows have the same number of columns
        max_cols = max(len(r) for r in table_data)
        for row in table_data:
            while len(row) < max_cols:
                row.append(Paragraph("", body_style))

        # Calculate available width
        page_width = A4[0] - 2 * inch
        col_width = page_width / max_cols

        tbl = Table(table_data, colWidths=[col_width] * max_cols)

        # Table style commands
        style_commands = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), _hex_to_rl_color(colors["table_header"])),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), fonts["title"]),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, _hex_to_rl_color(colors.get("border", "CCCCCC"))),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]

        # Alternating row colors
        for row_idx in range(1, len(table_data)):
            if row_idx % 2 == 0:
                style_commands.append(
                    ("BACKGROUND", (0, row_idx), (-1, row_idx),
                     _hex_to_rl_color(colors["table_alt_row"]))
                )

        tbl.setStyle(TableStyle(style_commands))
        story.append(tbl)
        story.append(Spacer(1, 8))

    def _render_code(self, story, block, styles):
        if block.content:
            # Replace newlines with <br/> for Paragraph
            escaped = self._escape(block.content)
            code_html = escaped.replace("\n", "<br/>")
            story.append(Paragraph(code_html, styles["Code"]))

    def _render_image_placeholder(self, story, block, styles):
        placeholder = f"<i>[Image: {self._escape(block.content or block.metadata.get('url', 'image'))}]</i>"
        style = ParagraphStyle(
            "ImagePlaceholder",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            textColor=_hex_to_rl_color("999999"),
        )
        story.append(Paragraph(placeholder, style))

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _escape(text: str) -> str:
        """Escape text for use in ReportLab Paragraphs (basic XML entities)."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text
