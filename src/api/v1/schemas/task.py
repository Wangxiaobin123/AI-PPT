"""Request/response schemas for task plan inspection and execution."""

from pydantic import BaseModel


class TaskInfo(BaseModel):
    """Status summary for a single task inside a plan."""

    id: str
    skill_name: str
    status: str
    error: str | None = None


class TaskPlanResponse(BaseModel):
    """Serialised view of a TaskPlan suitable for the API consumer."""

    session_id: str
    tasks: list[TaskInfo]
    execution_order: list[list[str]]


class ExecuteRequest(BaseModel):
    """Request body to trigger execution of a previously created task plan."""

    session_id: str
