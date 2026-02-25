"""Skills introspection endpoint -- lists all registered skills."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.v1.schemas.skill import SkillInfo, SkillsListResponse
from src.dependencies import get_skills_registry
from src.skills.registry import SkillRegistry

router = APIRouter()


@router.get(
    "/skills",
    response_model=SkillsListResponse,
    summary="List available skills",
    description="Return metadata for every skill currently registered in the system.",
)
async def list_skills(
    registry: SkillRegistry = Depends(get_skills_registry),
) -> SkillsListResponse:
    all_metadata = registry.list_all()
    skills = [
        SkillInfo(
            name=m.name,
            description=m.description,
            input_formats=m.input_formats,
            output_format=m.output_format,
            version=m.version,
        )
        for m in all_metadata
    ]
    return SkillsListResponse(skills=skills, total=len(skills))
