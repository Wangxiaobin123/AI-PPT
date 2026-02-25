"""Request/response schemas for the direct file-generation endpoint."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request body for a direct document generation call."""

    format: str = Field(
        ...,
        description="Target output format: pptx, docx, xlsx, pdf, or html",
    )
    content: str = Field(..., min_length=1, description="Raw content to transform")
    content_format: str = Field(
        default="markdown",
        description="Format of the incoming content (e.g. markdown, html, plain)",
    )
    title: str = Field(default="", description="Document title")
    template: str = Field(default="default", description="Template name to apply")
    style: dict = Field(default_factory=dict, description="Style overrides (colours, fonts, etc.)")


class FileInfo(BaseModel):
    """Metadata about a single generated file."""

    file_id: str
    filename: str
    format: str
    size_bytes: int
    download_url: str


class GenerateResponse(BaseModel):
    """Response returned after a generation request completes."""

    success: bool
    files: list[FileInfo] = []
    errors: list[str] = []
