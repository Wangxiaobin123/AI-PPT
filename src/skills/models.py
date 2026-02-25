"""Data models for the skills registry system."""

from pydantic import BaseModel


class SkillMetadata(BaseModel):
    """Metadata describing a skill's capabilities and identity."""

    name: str
    description: str
    input_formats: list[str]
    output_format: str
    version: str = "1.0.0"
    tags: list[str] = []


class SkillResult(BaseModel):
    """Result returned after a skill execution."""

    success: bool
    output_format: str
    content_bytes: bytes = b""
    file_path: str = ""
    metadata: dict = {}
    error: str = ""


class QACheck(BaseModel):
    """A single quality-assurance check result."""

    name: str
    passed: bool
    detail: str = ""


class QAReport(BaseModel):
    """Aggregated QA report composed of individual checks."""

    checks: list[QACheck] = []
    passed: bool = True
