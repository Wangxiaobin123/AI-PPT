---
name: pdf
description: >
  Use this skill when creating, exporting, or converting PDF documents (.pdf).
  Triggers on: "PDF", ".pdf", "export to PDF", "print-ready", "printable".
  Two modes: direct generation (from HTML/Markdown) and conversion (from DOCX/PPTX).
---

# PDF Generation Skill

## Quick Start

Generate a PDF document by running:
```bash
cd /home/user/AI-PPT && python -m src.skills.public.pdf_skill --help
```

Or use the standalone script:
```bash
python .claude/skills/pdf/scripts/generate_pdf.py --input content.md --output output.pdf
```

## Modes of Operation

### Mode 1: Direct Generation

Create a PDF directly from Markdown or HTML content. The content is parsed into
structured sections and rendered to PDF using the built-in PDF engine.

```bash
python .claude/skills/pdf/scripts/generate_pdf.py \
  --input report.md \
  --output report.pdf \
  --format markdown
```

### Mode 2: Conversion

Convert an existing DOCX or PPTX file to PDF. This mode uses the document
generators as an intermediate step: the content is first parsed, then rendered
to PDF layout.

```bash
python .claude/skills/pdf/scripts/generate_pdf.py \
  --input document.md \
  --output printable.pdf \
  --format markdown \
  --orientation portrait
```

## Input Formats

- **Markdown** (preferred) -- Full Markdown support including headings, lists, tables, code blocks, and images
- **HTML** -- Parses semantic HTML elements (h1-h6, p, ul, ol, table, pre, img)
- **Plain text** -- Treated as a single-section document

## Document Structure

The PDF generator produces:
1. **Title page** -- Centered title, subtitle, and author
2. **Sections** -- Each H1 heading starts a new page
3. **Content blocks** -- Paragraphs, lists, tables, code blocks rendered with professional typography

## Design Guidelines

- Page size: A4 (210 x 297 mm) or Letter (8.5 x 11 in)
- Margins: 1 inch (72pt) on all sides
- Title font: 28pt bold, primary color
- Heading 1: 20pt bold, Heading 2: 16pt bold
- Body text: 11pt with 1.15 line spacing
- Code blocks: 9pt monospace with light gray background
- Tables: styled headers with alternating row colors
- Page numbers in the footer

## Style Overrides

Pass custom styles via JSON:
```json
{
  "color_scheme": {
    "primary": "1A73E8",
    "text": "202124",
    "table_header": "1A73E8"
  },
  "fonts": {
    "title": "Helvetica",
    "body": "Helvetica"
  },
  "page_size": "letter",
  "orientation": "portrait"
}
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pdf",
    "content": "# Annual Report\n\n## Financial Summary\n\nTotal revenue: $12.5M\n\n- Q1: $2.8M\n- Q2: $3.1M\n- Q3: $3.2M\n- Q4: $3.4M",
    "content_format": "markdown",
    "title": "Annual Report 2025"
  }'
```

## QA

After generation, verify the output by checking:
- PDF opens correctly in standard viewers (Adobe Reader, Preview, Chrome)
- Title page displays correctly with proper typography
- Page breaks occur at H1 section boundaries
- Tables do not overflow page margins
- Code blocks render with monospace font and background
- Lists are properly indented and styled
- Images or image placeholders are positioned correctly
- Page numbers are present and sequential
- Text is selectable (not rasterized)
- No content is truncated at page boundaries
