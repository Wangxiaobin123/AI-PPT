#!/usr/bin/env python3
"""Generate XLSX from input content. Invoked by Claude Code skill."""
import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.parsers.csv_parser import CsvParser
from src.parsers.markdown_parser import MarkdownParser
from src.generators.xlsx_generator import XLSXGenerator
from src.generators.base import GenerationMetadata, StructuredContent
import asyncio


def _load_json_sheets(text: str, title: str) -> StructuredContent:
    """Build StructuredContent from a JSON string.

    Supported formats:
    - {"sheets": [{"name": "...", "headers": [...], "rows": [[...], ...]}, ...]}
    - [{"col1": "val1", "col2": "val2"}, ...]  (array of objects)
    """
    data = json.loads(text)
    content = StructuredContent(title=title)

    if isinstance(data, dict) and "sheets" in data:
        content.sheets = data["sheets"]
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        # Array of objects -- derive headers from keys of the first object
        headers = list(data[0].keys())
        rows = [[str(obj.get(h, "")) for h in headers] for obj in data]
        content.sheets.append({"name": title or "Sheet1", "headers": headers, "rows": rows})
    else:
        print("Warning: Unrecognized JSON structure. Expected 'sheets' key or array of objects.",
              file=sys.stderr)
        content.sheets.append({"name": title or "Sheet1", "headers": [], "rows": []})

    return content


def main():
    parser = argparse.ArgumentParser(description="Generate XLSX from content")
    parser.add_argument("--input", "-i", required=True, help="Input file path")
    parser.add_argument("--output", "-o", default="output.xlsx", help="Output file path")
    parser.add_argument("--title", "-t", default="", help="Workbook/sheet title")
    parser.add_argument(
        "--format",
        "-f",
        default="csv",
        choices=["csv", "markdown", "json"],
        help="Input content format (default: csv)",
    )
    parser.add_argument(
        "--delimiter",
        "-d",
        default=",",
        help="CSV delimiter character (default: comma)",
    )
    parser.add_argument(
        "--sheet-name",
        default=None,
        help="Name for the worksheet (default: derived from filename or title)",
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
    sheet_name = args.sheet_name or args.title or input_path.stem

    # Parse based on input format
    if args.format == "json":
        structured = _load_json_sheets(content_text, title=args.title or sheet_name)
    elif args.format == "markdown":
        md_parser = MarkdownParser()
        structured = md_parser.parse(content_text)
    else:
        csv_parser = CsvParser()
        structured = csv_parser.parse(
            content_text,
            title=args.title or None,
            delimiter=args.delimiter,
            sheet_name=sheet_name,
        )

    if args.title:
        structured.title = args.title

    # Build metadata with optional style overrides
    style = {}
    if args.style:
        try:
            style = json.loads(args.style)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse style JSON: {e}", file=sys.stderr)

    metadata = GenerationMetadata(style=style)
    generator = XLSXGenerator()
    result = asyncio.run(generator.generate(structured, metadata))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)

    sheet_count = len(structured.sheets) if structured.sheets else 1
    print(f"Generated: {args.output} ({len(result):,} bytes, {sheet_count} sheet(s))")


if __name__ == "__main__":
    main()
