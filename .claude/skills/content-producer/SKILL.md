---
name: content-producer
description: >
  Meta-skill / orchestrator for the AI Content Production System.
  Use this skill when the user wants to create, generate, make, produce, or build
  any type of document. This skill understands user intent, selects the appropriate
  format-specific skill, prepares input, generates output, runs QA, and delivers.
  Triggers on: "create", "generate", "make", "produce", "build" + any document type.
---

# Content Producer -- Orchestrator Skill

## Overview

The Content Producer is the top-level orchestrator that coordinates the full
document generation pipeline. When a user asks to "create a presentation" or
"build a report", this skill determines the correct format, delegates to the
appropriate format-specific skill, and ensures quality output.

## Workflow

```
User Request
    |
    v
1. UNDERSTAND INTENT
   - Parse the natural language request
   - Identify target format (pptx, docx, xlsx, pdf, html)
   - Extract content requirements, style preferences, constraints
    |
    v
2. SELECT SKILL
   - Map intent to the correct format skill
   - See references/intent-patterns.md for mapping rules
    |
    v
3. PREPARE INPUT
   - Structure raw content into the format expected by the skill
   - Markdown is the universal interchange format
   - Apply any content transformations (summarize, expand, restructure)
    |
    v
4. GENERATE
   - Invoke the format-specific generator
   - Pass style overrides and metadata
    |
    v
5. QA CHECK
   - Validate the output (file size, structure, content integrity)
   - Run format-specific checks (slide count, page count, sheet count)
    |
    v
6. DELIVER
   - Save the file to the output directory
   - Return file metadata (path, size, format, preview info)
```

## Skill Registry

| Skill          | Format | Trigger Keywords                                    |
|---------------|--------|-----------------------------------------------------|
| `pptx`        | .pptx  | slides, deck, presentation, PowerPoint, PPT         |
| `docx`        | .docx  | document, Word, report, letter, memo                |
| `xlsx`        | .xlsx  | spreadsheet, Excel, data table, workbook            |
| `pdf`         | .pdf   | PDF, export to PDF, print-ready, printable          |
| `html-design` | .html  | web page, HTML, landing page, website, responsive   |

## Intent Recognition

The orchestrator uses keyword matching and contextual analysis to determine
the user's desired output format. See `references/intent-patterns.md` for the
full pattern catalog.

### Priority Rules

1. **Explicit format** -- If the user names a format directly (e.g., "make a PPTX"),
   use that format without further analysis.
2. **Document type keywords** -- Match against trigger keywords in the skill registry.
3. **Content analysis** -- If intent is ambiguous, analyze the content:
   - Tabular data -> xlsx
   - Long-form text with sections -> docx
   - Short bullet points -> pptx
   - Data with charts -> xlsx or pptx
4. **Default** -- If still ambiguous, ask the user to clarify.

## API Usage

### Direct Generation Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pptx",
    "content": "# Quarterly Review\n\n## Revenue\n- Q1: $2.8M\n- Q2: $3.1M",
    "content_format": "markdown",
    "title": "Q2 2025 Review"
  }'
```

### Intent-Based Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/intent \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a presentation about our Q2 revenue growth",
    "context": {
      "data": "Q1: $2.8M, Q2: $3.1M, Q3: $3.2M projected"
    }
  }'
```

## Common Patterns

### Presentation from Bullet Points
```
User: "Make me a deck about our new product features"
Flow: content-producer -> pptx
Input: User provides bullet points or topic
Output: Styled PPTX with title slide, content slides, and summary
```

### Report from Data
```
User: "Create a quarterly report with these numbers"
Flow: content-producer -> docx
Input: User provides data points, metrics, narrative text
Output: Formatted DOCX with title page, sections, tables, and charts
```

### Spreadsheet from CSV
```
User: "Build a spreadsheet from this sales data"
Flow: content-producer -> xlsx
Input: User provides CSV data or table
Output: Formatted XLSX with headers, styling, and auto-filter
```

### PDF Export
```
User: "Generate a print-ready PDF of this report"
Flow: content-producer -> pdf
Input: User provides Markdown/HTML content
Output: PDF with proper typography, page breaks, and page numbers
```

### Landing Page
```
User: "Design a landing page for our product launch"
Flow: content-producer -> html-design
Input: User provides product info, features, pricing
Output: Responsive HTML page with hero, features section, CTA
```

## Multi-Format Workflows

The orchestrator can chain multiple skills for complex requests:

### Presentation + Handout
```
User: "Create a presentation and a PDF handout"
Flow: content-producer -> pptx (presentation) + pdf (handout)
```

### Report + Spreadsheet
```
User: "Build a report with the analysis and a spreadsheet with the raw data"
Flow: content-producer -> docx (report) + xlsx (data)
```

## Configuration

The orchestrator reads its configuration from the project settings. Key options:

| Setting                     | Default        | Description                           |
|----------------------------|----------------|---------------------------------------|
| `output_dir`               | `./output`     | Directory for generated files         |
| `default_template`         | `default`      | Template applied when none specified  |
| `qa_enabled`               | `true`         | Whether to run QA checks              |
| `max_file_size_mb`         | `50`           | Maximum output file size              |
| `default_style.color_scheme` | (blue theme) | Default color palette                 |
| `default_style.fonts`      | Calibri        | Default font family                   |

## QA Checks

After every generation, the orchestrator runs these checks:

1. **File integrity** -- Output file is non-empty and valid
2. **Format validation** -- File matches expected format (magic bytes)
3. **Content completeness** -- All input sections are represented in output
4. **Size sanity** -- File size is within expected bounds
5. **Style consistency** -- Fonts and colors match the requested theme

If any check fails, the orchestrator logs the issue and can optionally
retry generation with adjusted parameters.
