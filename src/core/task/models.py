"""Task-related data models for the content production system.

Defines the core structures used to represent individual tasks, their
statuses, and the overall execution plan produced by the intent engine.
"""

from enum import Enum

from pydantic import BaseModel, Field

import uuid


class TaskStatus(str, Enum):
    """Lifecycle states for a single task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A single unit of work to be executed by a skill.

    Attributes:
        id: Short unique identifier for the task.
        skill_name: The registered skill responsible for execution.
        parameters: Skill-specific parameters extracted from the user request.
        dependencies: List of task IDs that must complete before this one.
        status: Current lifecycle state.
        result: Output payload populated after successful execution.
        error: Error message populated if the task fails.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    skill_name: str
    parameters: dict = {}
    dependencies: list[str] = []
    status: TaskStatus = TaskStatus.PENDING
    result: dict | None = None
    error: str | None = None


class TaskPlan(BaseModel):
    """An ordered collection of tasks forming a complete execution plan.

    Attributes:
        session_id: Identifier linking the plan back to a conversation session.
        tasks: All tasks in the plan.
        execution_order: Groups of task IDs; tasks within the same group can
            run in parallel, groups are executed sequentially.
    """

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    tasks: list[Task] = []
    execution_order: list[list[str]] = []

    def get_task(self, task_id: str) -> Task | None:
        """Look up a task by its ID.  Returns ``None`` when not found."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Return all tasks that currently have the given *status*."""
        return [t for t in self.tasks if t.status == status]

    def all_completed(self) -> bool:
        """Return ``True`` when every task has completed or failed."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in self.tasks
        )
