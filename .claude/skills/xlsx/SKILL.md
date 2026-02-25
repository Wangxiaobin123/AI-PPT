---
name: xlsx
description: >
  Use this skill when creating, editing, or converting Excel spreadsheets (.xlsx).
  Triggers on: "spreadsheet", "Excel", ".xlsx", "data table", "workbook".
  Can create from CSV, JSON, markdown tables, or structured data input.
---

# XLSX Generation Skill

## Quick Start

Generate an Excel spreadsheet by running:
```bash
cd /home/user/AI-PPT && python -m src.skills.public.xlsx_skill --help
```

Or use the standalone script:
```bash
python .claude/skills/xlsx/scripts/generate_xlsx.py --input data.csv --output output.xlsx
```

## Input Formats

### CSV (preferred for tabular data)

Standard comma-separated values. The first row is treated as column headers.
```csv
Name,Department,Salary
Alice,Engineering,95000
Bob,Marketing,78000
Carol,Sales,82000
```

### Markdown tables

Pipe-delimited tables from Markdown input:
```markdown
| Name  | Department  | Salary  |
|-------|-------------|---------|
| Alice | Engineering | 95,000  |
| Bob   | Marketing   | 78,000  |
```

### JSON

Array of objects or explicit sheet structure:
```json
{
  "sheets": [
    {
      "name": "Employees",
      "headers": ["Name", "Department", "Salary"],
      "rows": [
        ["Alice", "Engineering", "95000"],
        ["Bob", "Marketing", "78000"]
      ]
    }
  ]
}
```

## Features

- **Multiple sheets** -- Provide multiple CSV files or JSON sheet entries to create a multi-sheet workbook
- **Auto column widths** -- Columns are automatically sized to fit content (min 8, max 50 characters)
- **Header formatting** -- Bold white text on colored background with centered alignment
- **Alternating row colors** -- Odd/even row shading for readability
- **Auto-filter** -- Filter dropdowns added to header row automatically
- **Frozen header row** -- Header row stays visible when scrolling
- **Number formatting** -- Percentages, currency, and decimal numbers are auto-detected and formatted
- **Value coercion** -- String values that look like numbers or percentages are converted to proper numeric types

## Design Guidelines

- Header row: bold white text on primary color background (default: #2B579A)
- Body text: 10pt Calibri
- Alternating rows: light gray (#F2F2F2) on even data rows
- Borders: thin light gray (#CCCCCC) on all cells
- Column width: auto-calculated from content, clamped to 8-50 characters

## Style Overrides

Pass custom styles via JSON:
```json
{
  "color_scheme": {
    "primary": "1A73E8",
    "header_bg": "1A73E8",
    "header_font": "FFFFFF",
    "alt_row": "E8F0FE",
    "border": "DADCE0",
    "text": "202124"
  },
  "fonts": {
    "header": "Arial",
    "body": "Arial"
  }
}
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "xlsx",
    "content": "Name,Department,Salary\nAlice,Engineering,95000\nBob,Marketing,78000\nCarol,Sales,82000",
    "content_format": "csv",
    "title": "Employee Data"
  }'
```

## QA

After generation, verify the output by checking:
- Correct number of sheets created
- All headers present and styled
- Data rows match input count
- Numeric values properly formatted (not stored as text)
- Percentage values display with % symbol
- Column widths are reasonable (no truncation, no excessive width)
- Auto-filter is active on header row
- Header row is frozen
- File opens correctly in Microsoft Excel, Google Sheets, and LibreOffice Calc
