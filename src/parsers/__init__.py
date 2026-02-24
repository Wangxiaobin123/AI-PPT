"""Input parsers that convert various formats into StructuredContent.

Supported formats:
- Markdown (.md)
- HTML (.html, .htm)
- CSV (.csv)
- JSON (.json)
- Plain text (.txt)
- Office files (.pptx, .docx, .xlsx)
"""

from src.parsers.markdown_parser import MarkdownParser
from src.parsers.html_parser import HtmlParser
from src.parsers.csv_parser import CsvParser
from src.parsers.json_parser import JsonParser
from src.parsers.text_parser import TextParser
from src.parsers.office_parser import OfficeParser

__all__ = [
    "MarkdownParser",
    "HtmlParser",
    "CsvParser",
    "JsonParser",
    "TextParser",
    "OfficeParser",
]
