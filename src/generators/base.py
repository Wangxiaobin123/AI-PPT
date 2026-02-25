"""Base classes and data models for all document generators."""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel


class ContentType(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    CHART = "chart"


class ContentBlock(BaseModel):
    type: ContentType
    content: str = ""
    level: int = 1  # heading level or nesting level
    items: list[str] = []  # for lists
    rows: list[list[str]] = []  # for tables (first row = header)
    metadata: dict = {}  # extra info (image url, chart data, etc.)


class SlideData(BaseModel):
    title: str = ""
    subtitle: str = ""
    blocks: list[ContentBlock] = []
    layout: str = "content"  # "title", "content", "two_column", "image", "blank"
    notes: str = ""


class SectionData(BaseModel):
    title: str = ""
    blocks: list[ContentBlock] = []


class StructuredContent(BaseModel):
    title: str = ""
    subtitle: str = ""
    author: str = ""
    slides: list[SlideData] = []  # for PPTX
    sections: list[SectionData] = []  # for DOCX/PDF/HTML
    sheets: list[dict] = []  # for XLSX: [{"name": "Sheet1", "headers": [...], "rows": [...]}]
    metadata: dict = {}


class GenerationMetadata(BaseModel):
    template: str = "default"
    style: dict = {}  # color_scheme, fonts, etc.
    options: dict = {}  # format-specific options


class BaseGenerator(ABC):
    @abstractmethod
    async def generate(self, content: StructuredContent, metadata: GenerationMetadata) -> bytes:
        ...
