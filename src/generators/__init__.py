"""Document generators for various output formats."""

from .base import (
    BaseGenerator,
    ContentBlock,
    ContentType,
    GenerationMetadata,
    SectionData,
    SlideData,
    StructuredContent,
)
from .docx_generator import DOCXGenerator
from .html_generator import HTMLGenerator
from .pdf_generator import PDFGenerator
from .pptx_generator import PPTXGenerator
from .xlsx_generator import XLSXGenerator

__all__ = [
    # Base classes
    "BaseGenerator",
    "ContentBlock",
    "ContentType",
    "GenerationMetadata",
    "SectionData",
    "SlideData",
    "StructuredContent",
    # Generators
    "DOCXGenerator",
    "HTMLGenerator",
    "PDFGenerator",
    "PPTXGenerator",
    "XLSXGenerator",
]
