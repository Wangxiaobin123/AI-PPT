---
name: pptx
description: >
  Use this skill when creating, editing, or converting PowerPoint presentations (.pptx).
  Triggers on: "slides", "deck", "presentation", ".pptx", "PowerPoint", "PPT".
  Can create from scratch using markdown, HTML, CSV, JSON, or plain text input.
---

# PPTX Generation Skill

## Quick Start

Generate a PowerPoint presentation by running:
```bash
cd /home/user/AI-PPT && python -m src.skills.public.pptx_skill --help
```

Or use the standalone script:
```bash
python .claude/skills/pptx/scripts/generate_pptx.py --input content.md --output output.pptx
```

## Input Format

Markdown is the preferred input format. Structure your content with:
- `# Title` for slide titles
- `## Subtitle` for subtitles
- `-` bullet lists for slide content
- `![alt](url)` for images
- Tables (| header |) for data slides
- `---` for explicit slide breaks

## Design Guidelines

- Use bold, content-informed color palettes
- Vary layouts: two-column, image-heavy, data callouts
- Title font: 36-44pt, Body font: 14-16pt
- Maintain 0.5" minimum margins

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"format": "pptx", "content": "# My Presentation\n\n## Slide 1\n- Point 1\n- Point 2", "content_format": "markdown"}'
```

## QA

After generation, verify the output by reading the file and checking:
- Correct slide count
- No empty slides
- Text not truncated
- Consistent styling
