"""Tests for input parsers."""
import pytest
from src.generators.base import ContentType


class TestMarkdownParser:
    def test_parse_basic(self, sample_markdown):
        from src.parsers.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        result = parser.parse(sample_markdown)
        assert result.title == "Test Presentation"
        assert len(result.slides) > 0

    def test_parse_headings(self):
        from src.parsers.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        result = parser.parse("# Title\n\n## Section 1\n\nSome text.\n\n## Section 2\n\nMore text.")
        assert result.title == "Title"

    def test_parse_bullets(self):
        from src.parsers.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        result = parser.parse("# Slide\n\n- Item 1\n- Item 2\n- Item 3")
        assert len(result.slides) > 0


class TestHtmlParser:
    def test_parse_basic(self, sample_html):
        from src.parsers.html_parser import HtmlParser
        parser = HtmlParser()
        result = parser.parse(sample_html)
        assert result.title == "Test Document"

    def test_parse_table(self, sample_html):
        from src.parsers.html_parser import HtmlParser
        parser = HtmlParser()
        result = parser.parse(sample_html)
        has_table = any(
            b.type == ContentType.TABLE
            for section in result.sections
            for b in section.blocks
        )
        assert has_table


class TestCsvParser:
    def test_parse_basic(self, sample_csv):
        from src.parsers.csv_parser import CsvParser
        parser = CsvParser()
        result = parser.parse(sample_csv)
        assert len(result.sheets) > 0

    def test_parse_headers(self, sample_csv):
        from src.parsers.csv_parser import CsvParser
        parser = CsvParser()
        result = parser.parse(sample_csv)
        sheet = result.sheets[0]
        assert "headers" in sheet
        assert "Name" in sheet["headers"]


class TestJsonParser:
    def test_parse_array(self, sample_json):
        from src.parsers.json_parser import JsonParser
        parser = JsonParser()
        result = parser.parse(sample_json)
        assert len(result.sheets) > 0

    def test_parse_structured(self):
        import json
        from src.parsers.json_parser import JsonParser
        parser = JsonParser()
        data = json.dumps({"title": "Report", "sections": [{"title": "Intro", "content": "Hello"}]})
        result = parser.parse(data)
        assert result.title == "Report"


class TestTextParser:
    def test_parse_basic(self, sample_text):
        from src.parsers.text_parser import TextParser
        parser = TextParser()
        result = parser.parse(sample_text)
        assert result.title != ""
        assert len(result.sections) > 0
