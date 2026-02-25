"""Request/response schemas for the skills introspection endpoint."""

from pydantic import BaseModel


class SkillInfo(BaseModel):
    """Public-facing description of a single registered skill."""

    name: str
    description: str
    input_formats: list[str]
    output_format: str
    version: str


class SkillsListResponse(BaseModel):
    """Response listing all available skills."""

    skills: list[SkillInfo]
    total: int
