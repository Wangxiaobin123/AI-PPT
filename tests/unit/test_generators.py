"""Tests for document generators."""
import pytest
from src.generators.base import (
    StructuredContent,
    SlideData,
    SectionData,
    ContentBlock,
    ContentType,
    GenerationMetadata,
)


def _make_content():
    return StructuredContent(
        title="Test Document",
        subtitle="Subtitle",
        slides=[
            SlideData(title="Title Slide", subtitle="A subtitle", layout="title"),
            SlideData(
                title="Content Slide",
                blocks=[
                    ContentBlock(
                        type=ContentType.BULLET_LIST,
                        items=["Point 1", "Point 2", "Point 3"],
                    )
                ],
            ),
            SlideData(
                title="Table Slide",
                blocks=[
                    ContentBlock(
                        type=ContentType.TABLE,
                        rows=[
                            ["Name", "Value"],
                            ["A", "1"],
                            ["B", "2"],
                        ],
                    )
                ],
            ),
        ],
        sections=[
            SectionData(
                title="Introduction",
                blocks=[
                    ContentBlock(type=ContentType.TEXT, content="This is intro text."),
                    ContentBlock(
                        type=ContentType.BULLET_LIST,
                        items=["Item A", "Item B"],
                    ),
                ],
            ),
            SectionData(
                title="Data",
                blocks=[
                    ContentBlock(
                        type=ContentType.TABLE,
                        rows=[["Col1", "Col2"], ["a", "b"]],
                    )
                ],
            ),
        ],
        sheets=[
            {
                "name": "Sheet1",
                "headers": ["Name", "Age", "City"],
                "rows": [
                    ["Alice", "30", "NY"],
                    ["Bob", "25", "SF"],
                ],
            }
        ],
    )


@pytest.mark.asyncio
async def test_pptx_generator():
    from src.generators.pptx_generator import PPTXGenerator
    gen = PPTXGenerator()
    content = _make_content()
    result = await gen.generate(content, GenerationMetadata())
    assert isinstance(result, bytes)
    assert len(result) > 0
    # PPTX files start with PK (ZIP header)
    assert result[:2] == b"PK"


@pytest.mark.asyncio
async def test_docx_generator():
    from src.generators.docx_generator import DOCXGenerator
    gen = DOCXGenerator()
    content = _make_content()
    result = await gen.generate(content, GenerationMetadata())
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:2] == b"PK"


@pytest.mark.asyncio
async def test_xlsx_generator():
    from src.generators.xlsx_generator import XLSXGenerator
    gen = XLSXGenerator()
    content = _make_content()
    result = await gen.generate(content, GenerationMetadata())
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:2] == b"PK"


@pytest.mark.asyncio
async def test_pdf_generator():
    from src.generators.pdf_generator import PDFGenerator
    gen = PDFGenerator()
    content = _make_content()
    result = await gen.generate(content, GenerationMetadata())
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_html_generator():
    from src.generators.html_generator import HTMLGenerator
    gen = HTMLGenerator()
    content = _make_content()
    result = await gen.generate(content, GenerationMetadata())
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert b"<html" in result.lower() if isinstance(result, bytes) else "<html" in result.lower()
