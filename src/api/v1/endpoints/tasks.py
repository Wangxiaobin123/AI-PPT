"""Task plan inspection and execution endpoints.

Provides a lightweight in-memory store of task plans keyed by session ID.
Plans are created by the ``/intent`` endpoint and can be executed or
inspected here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.generate import FileInfo, GenerateResponse
from src.api.v1.schemas.task import ExecuteRequest, TaskInfo, TaskPlanResponse
from src.core.task.models import TaskPlan, TaskStatus
from src.dependencies import get_output_manager, get_pipeline
from src.output.manager import OutputManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory task plan store.  In a production system this would be backed
# by a database or distributed cache.
# ---------------------------------------------------------------------------
_plans: dict[str, TaskPlan] = {}


def store_plan(plan: TaskPlan) -> None:
    """Persist a plan so it can be retrieved / executed later."""
    _plans[plan.session_id] = plan


def get_plan(session_id: str) -> TaskPlan | None:
    return _plans.get(session_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/tasks/{session_id}",
    response_model=TaskPlanResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get task plan status",
    description="Retrieve the current status of all tasks in a session's plan.",
)
async def get_task_status(session_id: str) -> TaskPlanResponse:
    plan = get_plan(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan found for session: {session_id}")

    tasks = [
        TaskInfo(
            id=t.id,
            skill_name=t.skill_name,
            status=t.status.value,
            error=t.error,
        )
        for t in plan.tasks
    ]
    return TaskPlanResponse(
        session_id=plan.session_id,
        tasks=tasks,
        execution_order=plan.execution_order,
    )


@router.post(
    "/tasks/execute",
    response_model=GenerateResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Execute a task plan",
    description=(
        "Trigger execution of a previously created task plan.  "
        "Tasks are run according to the plan's execution order."
    ),
)
async def execute_plan(
    request: ExecuteRequest,
    pipeline=Depends(get_pipeline),
    output_manager: OutputManager = Depends(get_output_manager),
) -> GenerateResponse:
    plan = get_plan(request.session_id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=f"No plan found for session: {request.session_id}",
        )

    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Execution pipeline is not available.  Check that required modules are installed.",
        )

    # ------------------------------------------------------------------
    # Execute the pipeline
    # ------------------------------------------------------------------
    try:
        results = await pipeline.run(plan)
    except Exception as exc:
        logger.error("pipeline_execution_failed", session_id=request.session_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Collect results and store output files
    # ------------------------------------------------------------------
    files: list[FileInfo] = []
    errors: list[str] = []

    for task in plan.tasks:
        if task.status == TaskStatus.FAILED:
            errors.append(f"Task {task.id} ({task.skill_name}) failed: {task.error}")
            continue

        if task.result:
            content_bytes = task.result.get("content_bytes")
            file_path = task.result.get("file_path")
            output_format = task.result.get("output_format", "bin")

            try:
                if content_bytes:
                    stored = await output_manager.store(
                        content_bytes if isinstance(content_bytes, bytes) else content_bytes.encode(),
                        format=output_format,
                        prefix=task.skill_name,
                    )
                elif file_path:
                    stored = await output_manager.store_from_path(file_path, format=output_format)
                else:
                    continue

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
                logger.error("result_storage_failed", task_id=task.id, error=str(exc))
                errors.append(f"Failed to store output for task {task.id}: {exc}")

    return GenerateResponse(
        success=len(files) > 0 and len(errors) == 0,
        files=files,
        errors=errors,
    )
