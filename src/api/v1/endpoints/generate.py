"""Direct file-generation endpoint -- bypasses intent analysis and runs a
single skill to produce an output file.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.generate import FileInfo, GenerateRequest, GenerateResponse
from src.dependencies import get_output_manager, get_pipeline, get_skills_registry
from src.output.manager import OutputManager
from src.skills.registry import SkillRegistry
from src.utils.exceptions import SkillExecutionError, SkillNotFoundError
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "No matching skill"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate a document",
    description=(
        "Submit content and a target format to generate a document directly.  "
        "The system selects the appropriate skill, runs it, stores the output, "
        "and returns download information."
    ),
)
async def generate_file(
    request: GenerateRequest,
    registry: SkillRegistry = Depends(get_skills_registry),
    output_manager: OutputManager = Depends(get_output_manager),
    pipeline=Depends(get_pipeline),
) -> GenerateResponse:
    # ------------------------------------------------------------------
    # 1. Resolve a matching skill
    # ------------------------------------------------------------------
    try:
        skill = registry.match(
            request.format,
            {"content_format": request.content_format},
        )
    except SkillNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No skill available for format: {request.format}",
        )

    # ------------------------------------------------------------------
    # 2. Build the parameter dict expected by the skill
    # ------------------------------------------------------------------
    params = {
        "content": request.content,
        "content_format": request.content_format,
        "title": request.title,
        "template": request.template,
        "style": request.style,
        "format": request.format,
    }
    context = {
        "output_dir": str(output_manager.output_dir),
    }

    # ------------------------------------------------------------------
    # 3. Execute the skill
    # ------------------------------------------------------------------
    try:
        result = await skill.execute(params, context)
    except SkillExecutionError as exc:
        logger.error("skill_execution_failed", skill=skill.metadata.name, error=str(exc))
        return GenerateResponse(success=False, errors=[str(exc)])
    except Exception as exc:
        logger.error("unexpected_generation_error", error=str(exc))
        return GenerateResponse(success=False, errors=[f"Unexpected error: {exc}"])

    if not result.success:
        return GenerateResponse(success=False, errors=[result.error or "Unknown skill error"])

    # ------------------------------------------------------------------
    # 4. Store the output and build the response
    # ------------------------------------------------------------------
    files: list[FileInfo] = []
    errors: list[str] = []

    try:
        if result.content_bytes:
            stored = await output_manager.store(
                result.content_bytes,
                format=result.output_format,
                prefix=request.title or "output",
            )
        elif result.file_path:
            stored = await output_manager.store_from_path(
                result.file_path,
                format=result.output_format,
            )
        else:
            return GenerateResponse(
                success=False,
                errors=["Skill produced no output content"],
            )

        files.append(
            FileInfo(
                file_id=stored.file_id,
                filename=stored.filename,
                format=stored.format,
                size_bytes=stored.size_bytes,
                download_url=f"/api/v1/files/{stored.file_id}",
            )
        )
    except Exception as exc:
        logger.error("file_storage_failed", error=str(exc))
        errors.append(f"File storage failed: {exc}")

    return GenerateResponse(
        success=len(files) > 0,
        files=files,
        errors=errors,
    )
