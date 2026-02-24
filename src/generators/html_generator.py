"""HTML document generator using Jinja2 templates."""

import html as html_module
import io

from jinja2 import Environment

from .base import (
    BaseGenerator,
    ContentBlock,
    ContentType,
    GenerationMetadata,
    SectionData,
    StructuredContent,
)


DEFAULT_COLORS = {
    "primary": "#2B579A",
    "secondary": "#217346",
    "accent": "#B7472A",
    "background": "#FFFFFF",
    "text": "#333333",
    "subtitle": "#666666",
    "table_header": "#2B579A",
    "table_alt_row": "#F2F2F2",
    "code_bg": "#F5F5F5",
    "border": "#CCCCCC",
}

DEFAULT_FONTS = {
    "title": "'Segoe UI', Calibri, Arial, sans-serif",
    "body": "'Segoe UI', Calibri, Arial, sans-serif",
    "code": "'Consolas', 'Courier New', monospace",
}


def _resolve_colors(metadata: GenerationMetadata) -> dict[str, str]:
    colors = dict(DEFAULT_COLORS)
    user_scheme = metadata.style.get("color_scheme", {})
    # Ensure # prefix for HTML
    for k, v in user_scheme.items():
        if not v.startswith("#"):
            v = f"#{v}"
        colors[k] = v
    return colors


def _resolve_fonts(metadata: GenerationMetadata) -> dict[str, str]:
    fonts = dict(DEFAULT_FONTS)
    fonts.update(metadata.style.get("fonts", {}))
    return fonts


# ------------------------------------------------------------------ #
#  Jinja2 string template
# ------------------------------------------------------------------ #

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title | e }}</title>
    <style>
        /* ---- Reset & Base ---- */
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html {
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
        }

        body {
            font-family: {{ fonts.body }};
            color: {{ colors.text }};
            background-color: {{ colors.background }};
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }

        /* ---- Title Page ---- */
        .title-page {
            text-align: center;
            padding: 4rem 1rem 3rem;
            border-bottom: 3px solid {{ colors.primary }};
            margin-bottom: 2.5rem;
        }

        .title-page h1 {
            font-family: {{ fonts.title }};
            font-size: 2.5rem;
            color: {{ colors.primary }};
            margin-bottom: 0.5rem;
            line-height: 1.2;
        }

        .title-page .subtitle {
            font-size: 1.25rem;
            color: {{ colors.subtitle }};
            margin-bottom: 0.75rem;
        }

        .title-page .author {
            font-size: 1rem;
            color: {{ colors.text }};
            font-style: italic;
            margin-top: 1rem;
        }

        /* ---- Sections ---- */
        .section {
            margin-bottom: 2.5rem;
        }

        .section + .section {
            border-top: 1px solid {{ colors.border }};
            padding-top: 2rem;
        }

        /* ---- Headings ---- */
        h1, h2, h3, h4 {
            font-family: {{ fonts.title }};
            color: {{ colors.primary }};
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }

        h1 { font-size: 2rem; }
        h2 { font-size: 1.6rem; }
        h3 { font-size: 1.3rem; }
        h4 { font-size: 1.1rem; }

        /* ---- Paragraphs ---- */
        p {
            margin-bottom: 0.75rem;
        }

        /* ---- Lists ---- */
        ul, ol {
            margin: 0.5rem 0 1rem 1.5rem;
        }

        ul li, ol li {
            margin-bottom: 0.3rem;
        }

        /* ---- Tables ---- */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0 1.5rem;
            font-size: 0.95rem;
        }

        thead th {
            background-color: {{ colors.table_header }};
            color: #FFFFFF;
            font-weight: 600;
            text-align: center;
            padding: 0.6rem 0.75rem;
            border: 1px solid {{ colors.border }};
        }

        tbody td {
            padding: 0.5rem 0.75rem;
            border: 1px solid {{ colors.border }};
        }

        tbody tr:nth-child(even) {
            background-color: {{ colors.table_alt_row }};
        }

        /* ---- Code Blocks ---- */
        pre {
            background-color: {{ colors.code_bg }};
            border: 1px solid {{ colors.border }};
            border-radius: 4px;
            padding: 1rem;
            overflow-x: auto;
            margin: 0.75rem 0 1rem;
            font-family: {{ fonts.code }};
            font-size: 0.875rem;
            line-height: 1.5;
        }

        code {
            font-family: {{ fonts.code }};
            font-size: 0.875em;
        }

        /* ---- Image Placeholder ---- */
        .image-placeholder {
            text-align: center;
            color: #999;
            font-style: italic;
            padding: 2rem 1rem;
            border: 2px dashed {{ colors.border }};
            border-radius: 4px;
            margin: 1rem 0;
        }

        /* ---- Responsive ---- */
        @media (max-width: 600px) {
            body {
                padding: 1rem;
            }

            .title-page h1 {
                font-size: 1.8rem;
            }

            table {
                font-size: 0.85rem;
            }

            thead th, tbody td {
                padding: 0.4rem 0.5rem;
            }
        }

        /* ---- Print ---- */
        @media print {
            body {
                max-width: 100%;
                padding: 0;
            }

            .section {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
{% if title %}
    <header class="title-page">
        <h1>{{ title | e }}</h1>
        {% if subtitle %}<p class="subtitle">{{ subtitle | e }}</p>{% endif %}
        {% if author %}<p class="author">{{ author | e }}</p>{% endif %}
    </header>
{% endif %}

{% for section in sections %}
    <section class="section">
        {% if section.heading %}<h1>{{ section.heading | e }}</h1>{% endif %}
        {{ section.html_content }}
    </section>
{% endfor %}
</body>
</html>
"""


class HTMLGenerator(BaseGenerator):
    """Generates HTML documents from structured content using Jinja2."""

    def __init__(self):
        self._env = Environment(autoescape=False)

    async def generate(
        self, content: StructuredContent, metadata: GenerationMetadata
    ) -> bytes:
        """Generate an HTML file and return it as UTF-8 bytes."""
        colors = _resolve_colors(metadata)
        fonts = _resolve_fonts(metadata)

        # Build section data for the template
        sections_for_template = []
        for section in content.sections:
            section_html = self._render_section_blocks(section, colors)
            sections_for_template.append({
                "heading": section.title,
                "html_content": section_html,
            })

        template = self._env.from_string(HTML_TEMPLATE)
        html_output = template.render(
            title=content.title,
            subtitle=content.subtitle,
            author=content.author,
            colors=colors,
            fonts=fonts,
            sections=sections_for_template,
        )

        return html_output.encode("utf-8")

    # ------------------------------------------------------------------ #
    #  Block rendering (returns raw HTML strings)
    # ------------------------------------------------------------------ #

    def _render_section_blocks(self, section: SectionData, colors: dict) -> str:
        """Render all blocks in a section to an HTML string."""
        parts: list[str] = []
        for block in section.blocks:
            parts.append(self._render_block(block, colors))
        return "\n".join(parts)

    def _render_block(self, block: ContentBlock, colors: dict) -> str:
        """Render a single content block to HTML."""
        if block.type == ContentType.HEADING:
            return self._render_heading(block)
        elif block.type == ContentType.TEXT:
            return self._render_text(block)
        elif block.type == ContentType.BULLET_LIST:
            return self._render_bullet_list(block)
        elif block.type == ContentType.NUMBERED_LIST:
            return self._render_numbered_list(block)
        elif block.type == ContentType.TABLE:
            return self._render_table(block)
        elif block.type == ContentType.CODE:
            return self._render_code(block)
        elif block.type == ContentType.IMAGE:
            return self._render_image(block)
        elif block.type == ContentType.CHART:
            return self._render_chart_placeholder(block)
        else:
            if block.content:
                return f"<p>{self._esc(block.content)}</p>"
            return ""

    def _render_heading(self, block: ContentBlock) -> str:
        level = max(1, min(block.level, 4))
        tag = f"h{level}"
        return f"<{tag}>{self._esc(block.content)}</{tag}>"

    def _render_text(self, block: ContentBlock) -> str:
        if not block.content:
            return ""
        # Split on double newlines for separate paragraphs
        paragraphs = block.content.split("\n\n")
        parts = []
        for para in paragraphs:
            cleaned = para.strip()
            if cleaned:
                # Preserve single newlines as <br>
                cleaned = cleaned.replace("\n", "<br>")
                parts.append(f"<p>{self._esc_with_br(cleaned)}</p>")
        return "\n".join(parts)

    def _render_bullet_list(self, block: ContentBlock) -> str:
        if not block.items:
            return ""
        items_html = "\n".join(f"    <li>{self._esc(item)}</li>" for item in block.items)
        return f"<ul>\n{items_html}\n</ul>"

    def _render_numbered_list(self, block: ContentBlock) -> str:
        if not block.items:
            return ""
        items_html = "\n".join(f"    <li>{self._esc(item)}</li>" for item in block.items)
        return f"<ol>\n{items_html}\n</ol>"

    def _render_table(self, block: ContentBlock) -> str:
        rows = block.rows
        if not rows:
            return ""

        parts = ["<table>"]

        # Header row (first row)
        if rows:
            parts.append("  <thead>")
            parts.append("    <tr>")
            for cell in rows[0]:
                parts.append(f"      <th>{self._esc(str(cell))}</th>")
            parts.append("    </tr>")
            parts.append("  </thead>")

        # Body rows
        if len(rows) > 1:
            parts.append("  <tbody>")
            for row in rows[1:]:
                parts.append("    <tr>")
                for cell in row:
                    parts.append(f"      <td>{self._esc(str(cell))}</td>")
                parts.append("    </tr>")
            parts.append("  </tbody>")

        parts.append("</table>")
        return "\n".join(parts)

    def _render_code(self, block: ContentBlock) -> str:
        if not block.content:
            return ""
        lang = block.metadata.get("language", "")
        lang_attr = f' data-language="{self._esc(lang)}"' if lang else ""
        return f"<pre{lang_attr}><code>{self._esc(block.content)}</code></pre>"

    def _render_image(self, block: ContentBlock) -> str:
        url = block.metadata.get("url", "")
        alt = block.content or "Image"
        if url:
            return (
                f'<figure style="text-align: center; margin: 1rem 0;">'
                f'<img src="{self._esc(url)}" alt="{self._esc(alt)}" '
                f'style="max-width: 100%; height: auto;">'
                f"</figure>"
            )
        return f'<div class="image-placeholder">[Image: {self._esc(alt)}]</div>'

    def _render_chart_placeholder(self, block: ContentBlock) -> str:
        label = block.content or "Chart"
        return f'<div class="image-placeholder">[Chart: {self._esc(label)}]</div>'

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _esc(text: str) -> str:
        """HTML-escape a string."""
        return html_module.escape(str(text))

    @staticmethod
    def _esc_with_br(text: str) -> str:
        """HTML-escape but preserve <br> tags that were already inserted."""
        # First escape everything
        escaped = html_module.escape(str(text))
        # Restore <br> tags
        escaped = escaped.replace("&lt;br&gt;", "<br>")
        return escaped
