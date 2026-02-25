---
name: docx
description: >
  Use this skill when creating, editing, or converting Word documents (.docx).
  Triggers on: "document", "Word", ".docx", "report", "letter", "memo".
  Can create from scratch using markdown, HTML, or plain text input.
---

# DOCX Generation Skill

## Quick Start

Generate a Word document by running:
```bash
cd /home/user/AI-PPT && python -m src.skills.public.docx_skill --help
```

Or use the standalone script:
```bash
python .claude/skills/docx/scripts/generate_docx.py --input content.md --output output.docx
```

## Input Format

Markdown is the preferred input format. Structure your content with:
- `# Title` for the document title (creates a title page)
- `## Section Heading` for major sections (H1 boundaries create page breaks)
- `### Subsection` for subsections within a section
- `-` or `*` for bullet lists
- `1.` for numbered/ordered lists
- Tables using `| header | header |` pipe syntax
- Fenced code blocks with triple backticks
- `![alt](url)` for image placeholders

HTML input is also supported. The parser handles `<h1>`-`<h6>`, `<p>`, `<ul>`, `<ol>`, `<table>`, `<pre>`, and `<img>` tags.

## Document Structure

The generator produces:
1. **Title page** -- centered title, subtitle, and author (if provided)
2. **Sections** -- each H1 heading starts a new page with its content blocks
3. **Content blocks** -- paragraphs, lists, tables, code blocks, and image placeholders

## Design Guidelines

- Title font: 36pt bold, primary color
- Heading 1: 24pt, Heading 2: 20pt, Heading 3: 16pt, Heading 4: 14pt
- Body text: 11pt Calibri
- Tables: header row with colored background, alternating row shading
- Code blocks: Consolas 9pt with light gray background
- Maintain professional, clean formatting throughout

## Style Overrides

Pass custom styles via JSON:
```json
{
  "color_scheme": {
    "primary": "1A73E8",
    "secondary": "34A853",
    "accent": "EA4335",
    "text": "202124"
  },
  "fonts": {
    "title": "Georgia",
    "body": "Arial"
  }
}
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "docx",
    "content": "# Quarterly Report\n\n## Executive Summary\n\nRevenue grew 15% year-over-year.\n\n- North America: $4.2M\n- Europe: $2.8M\n- Asia: $1.5M",
    "content_format": "markdown",
    "title": "Q4 2025 Quarterly Report"
  }'
```

## QA

After generation, verify the output by checking:
- Title page renders with title, subtitle, and author
- Each H1 section starts on a new page
- Tables have styled headers and alternating row colors
- Lists use proper bullet/number styles
- Code blocks use monospace font with gray background
- No empty sections or orphaned headings
- Document opens correctly in Microsoft Word, Google Docs, and LibreOffice
