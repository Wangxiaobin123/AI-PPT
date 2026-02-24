#!/usr/bin/env python3
"""Generate PPTX from input content. Invoked by Claude Code skill."""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.parsers.markdown_parser import MarkdownParser
from src.generators.pptx_generator import PPTXGenerator
from src.generators.base import GenerationMetadata
import asyncio


def main():
    parser = argparse.ArgumentParser(description="Generate PPTX from content")
    parser.add_argument("--input", "-i", required=True, help="Input file path")
    parser.add_argument("--output", "-o", default="output.pptx", help="Output file path")
    parser.add_argument("--title", "-t", default="", help="Presentation title")
    parser.add_argument(
        "--format",
        "-f",
        default="markdown",
        choices=["markdown", "html", "csv"],
        help="Input content format (default: markdown)",
    )
    parser.add_argument(
        "--style",
        "-s",
        default=None,
        help="JSON string of style overrides, e.g. '{\"color_scheme\": {\"primary\": \"1A73E8\"}}'",
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
    elif args.format == "csv":
        from src.parsers.csv_parser import CsvParser
        csv_parser = CsvParser()
        structured = csv_parser.parse(content_text, title=args.title or None)
    else:
        md_parser = MarkdownParser()
        structured = md_parser.parse(content_text)

    if args.title:
        structured.title = args.title

    # Build metadata with optional style overrides
    style = {}
    if args.style:
        import json
        try:
            style = json.loads(args.style)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse style JSON: {e}", file=sys.stderr)

    metadata = GenerationMetadata(style=style)
    generator = PPTXGenerator()
    result = asyncio.run(generator.generate(structured, metadata))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)
    print(f"Generated: {args.output} ({len(result):,} bytes, {len(structured.slides)} slides)")


if __name__ == "__main__":
    main()
