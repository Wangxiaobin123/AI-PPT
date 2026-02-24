#!/usr/bin/env python3
"""Generate DOCX from input content. Invoked by Claude Code skill."""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.parsers.markdown_parser import MarkdownParser
from src.generators.docx_generator import DOCXGenerator
from src.generators.base import GenerationMetadata
import asyncio


def main():
    parser = argparse.ArgumentParser(description="Generate DOCX from content")
    parser.add_argument("--input", "-i", required=True, help="Input file path")
    parser.add_argument("--output", "-o", default="output.docx", help="Output file path")
    parser.add_argument("--title", "-t", default="", help="Document title")
    parser.add_argument("--author", "-a", default="", help="Document author")
    parser.add_argument(
        "--format",
        "-f",
        default="markdown",
        choices=["markdown", "html"],
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
    else:
        md_parser = MarkdownParser()
        structured = md_parser.parse(content_text)

    if args.title:
        structured.title = args.title
    if args.author:
        structured.author = args.author

    # Build metadata with optional style overrides
    style = {}
    if args.style:
        import json
        try:
            style = json.loads(args.style)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse style JSON: {e}", file=sys.stderr)

    metadata = GenerationMetadata(style=style)
    generator = DOCXGenerator()
    result = asyncio.run(generator.generate(structured, metadata))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)
    print(f"Generated: {args.output} ({len(result):,} bytes, {len(structured.sections)} sections)")


if __name__ == "__main__":
    main()
