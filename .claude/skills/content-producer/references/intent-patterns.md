# Intent Patterns Reference

This document maps common user intent patterns to the appropriate skill in the
AI Content Production System. The orchestrator (`content-producer`) uses these
patterns to route requests to the correct format-specific skill.

---

## Pattern Format

Each pattern entry includes:
- **Pattern** -- Example user phrases (case-insensitive matching)
- **Skill** -- Target skill name
- **Output** -- Expected output format
- **Notes** -- Additional routing context

---

## Presentation Patterns (pptx)

| Pattern | Skill | Output |
|---------|-------|--------|
| "Make me a presentation about X" | pptx | .pptx |
| "Create a slide deck for X" | pptx | .pptx |
| "Build slides about X" | pptx | .pptx |
| "Generate a PowerPoint on X" | pptx | .pptx |
| "I need a PPT for X" | pptx | .pptx |
| "Prepare a deck for my talk on X" | pptx | .pptx |
| "Turn this into a presentation" | pptx | .pptx |
| "Make a pitch deck for X" | pptx | .pptx |
| "Create slides for my meeting about X" | pptx | .pptx |
| "I need to present X to my team" | pptx | .pptx |

**Trigger keywords**: slides, deck, presentation, PowerPoint, PPT, pitch, talk, keynote

---

## Document Patterns (docx)

| Pattern | Skill | Output |
|---------|-------|--------|
| "Create a report on X" | docx | .docx |
| "Write a document about X" | docx | .docx |
| "Generate a Word document for X" | docx | .docx |
| "Draft a memo about X" | docx | .docx |
| "Write a letter to X" | docx | .docx |
| "Create a proposal for X" | docx | .docx |
| "Build a business plan for X" | docx | .docx |
| "Generate a white paper on X" | docx | .docx |
| "Write up the meeting notes from X" | docx | .docx |
| "Create a policy document for X" | docx | .docx |
| "Draft an executive summary of X" | docx | .docx |

**Trigger keywords**: document, Word, report, letter, memo, proposal, plan, paper,
write-up, notes, summary, brief, draft, .docx

---

## Spreadsheet Patterns (xlsx)

| Pattern | Skill | Output |
|---------|-------|--------|
| "Build a spreadsheet with X data" | xlsx | .xlsx |
| "Create an Excel file for X" | xlsx | .xlsx |
| "Make a data table of X" | xlsx | .xlsx |
| "Generate a workbook for X" | xlsx | .xlsx |
| "Organize this data into a spreadsheet" | xlsx | .xlsx |
| "Create a budget spreadsheet for X" | xlsx | .xlsx |
| "Build a tracking sheet for X" | xlsx | .xlsx |
| "Put this data into Excel" | xlsx | .xlsx |
| "Make a pivot table from X" | xlsx | .xlsx |
| "Create a financial model for X" | xlsx | .xlsx |

**Trigger keywords**: spreadsheet, Excel, data table, workbook, .xlsx, budget,
tracker, ledger, inventory, financial model, pivot

---

## PDF Patterns (pdf)

| Pattern | Skill | Output |
|---------|-------|--------|
| "Generate a PDF of X" | pdf | .pdf |
| "Export X to PDF" | pdf | .pdf |
| "Create a print-ready version of X" | pdf | .pdf |
| "Make a PDF report on X" | pdf | .pdf |
| "Convert this to PDF" | pdf | .pdf |
| "I need a printable version of X" | pdf | .pdf |
| "Create a PDF handout for X" | pdf | .pdf |
| "Generate a certificate for X" | pdf | .pdf |
| "Make this document print-ready" | pdf | .pdf |

**Trigger keywords**: PDF, .pdf, export, print-ready, printable, handout, certificate

---

## HTML/Web Patterns (html-design)

| Pattern | Skill | Output |
|---------|-------|--------|
| "Design a web page for X" | html-design | .html |
| "Create a landing page for X" | html-design | .html |
| "Build an HTML page about X" | html-design | .html |
| "Make a website for X" | html-design | .html |
| "Design a responsive page for X" | html-design | .html |
| "Create an email template for X" | html-design | .html |
| "Build a dashboard page for X" | html-design | .html |
| "Generate a static site for X" | html-design | .html |
| "Make a newsletter template" | html-design | .html |

**Trigger keywords**: web page, HTML, landing page, website, responsive, email template,
static site, dashboard, newsletter, .html

---

## Conversion Patterns

When users ask to convert between formats, the output format determines the skill:

| Pattern | Skill | Output |
|---------|-------|--------|
| "Convert X to PowerPoint" | pptx | .pptx |
| "Convert X to Word" | docx | .docx |
| "Convert X to Excel" | xlsx | .xlsx |
| "Convert X to PDF" | pdf | .pdf |
| "Convert X to HTML" | html-design | .html |
| "Turn this CSV into a spreadsheet" | xlsx | .xlsx |
| "Turn this document into slides" | pptx | .pptx |
| "Export these slides as a PDF" | pdf | .pdf |
| "Make a Word version of this" | docx | .docx |

**Routing rule**: The **output** format always determines the skill, regardless of
the input format.

---

## Ambiguous Patterns

These patterns require content analysis or clarification:

| Pattern | Resolution Strategy |
|---------|-------------------|
| "Create something with this data" | Analyze data structure: tabular -> xlsx, narrative -> docx |
| "Make a file about X" | Ask user to specify format, default to docx for text content |
| "Generate a document from this" | Default to docx; if input is CSV/tabular, suggest xlsx |
| "Build this for my meeting" | Likely pptx (presentation context), confirm with user |
| "Format this nicely" | Analyze content length: short -> pptx, long -> docx |

### Content-Based Heuristics

When the intent is ambiguous, analyze the input content:

1. **Mostly tabular data** (CSV, TSV, tables) -> `xlsx`
2. **Short bullet points** (< 500 words, list-heavy) -> `pptx`
3. **Long-form prose** (> 500 words, paragraphs) -> `docx`
4. **Mixed content with data emphasis** -> `xlsx` + `docx`
5. **"Print" or "share" mentioned** -> `pdf`
6. **"Online" or "link" mentioned** -> `html-design`

---

## Multi-Output Patterns

Some requests imply multiple outputs:

| Pattern | Skills | Outputs |
|---------|--------|---------|
| "Create a presentation and handout" | pptx + pdf | .pptx + .pdf |
| "Build a report with supporting data" | docx + xlsx | .docx + .xlsx |
| "Make slides and a web version" | pptx + html-design | .pptx + .html |
| "Generate all formats" | all skills | .pptx + .docx + .xlsx + .pdf + .html |

---

## Confidence Scoring

The orchestrator assigns a confidence score (0.0 to 1.0) to each skill match:

| Confidence | Meaning | Action |
|-----------|---------|--------|
| >= 0.9 | Explicit format match | Proceed directly |
| 0.7 - 0.9 | Strong keyword match | Proceed with format noted |
| 0.5 - 0.7 | Moderate match, some ambiguity | Proceed, mention assumption |
| < 0.5 | Weak match or multiple candidates | Ask user to clarify |
