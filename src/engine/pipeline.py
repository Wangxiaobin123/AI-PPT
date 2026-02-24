"""Execution pipeline -- orchestrates tasks, rendering, and result aggregation.

The :class:`ExecutionPipeline` consumes a :class:`TaskPlan` and:

1. Iterates through the ``execution_order`` groups sequentially.
2. Within each group, runs tasks in parallel via :func:`asyncio.gather`.
3. After each successful task, renders the output file to disk.
4. Collects all results into a :class:`PipelineResult`.
"""

from __future__ import annotations

import asyncio
import uuid

from pydantic import BaseModel

from src.core.task.models import Task, TaskPlan, TaskStatus
from src.engine.executor import TaskExecutor, TaskResult
from src.engine.renderer import FileRenderer, RenderedFile
from src.utils.logging import get_logger

logger = get_logger("engine.pipeline")


class PipelineResult(BaseModel):
    """Aggregated result of running an entire :class:`TaskPlan`.

    Attributes:
        task_results: Mapping of task ID -> :class:`TaskResult`.
        rendered_files: List of all files successfully written to disk.
        success: ``True`` only when *every* task completed successfully.
        total_tasks: Total number of tasks in the plan.
        completed_tasks: Number of tasks that succeeded.
        failed_tasks: Number of tasks that failed.
    """

    task_results: dict[str, TaskResult] = {}
    rendered_files: list[RenderedFile] = []
    success: bool = True
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class ExecutionPipeline:
    """Top-level orchestrator for running a task plan.

    Parameters
    ----------
    executor:
        The :class:`TaskExecutor` responsible for executing individual tasks.
    renderer:
        The :class:`FileRenderer` responsible for writing outputs to disk.
    """

    def __init__(
        self,
        executor: TaskExecutor,
        renderer: FileRenderer,
    ) -> None:
        self.executor = executor
        self.renderer = renderer
        self.logger = get_logger("engine.pipeline")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, plan: TaskPlan) -> PipelineResult:
        """Execute all tasks in *plan* respecting ``execution_order``.

        Tasks within the same group are launched concurrently; groups are
        executed one after another so that dependencies across groups are
        honoured.

        Returns
        -------
        PipelineResult
            Complete summary of task outcomes and rendered files.
        """
        self.logger.info(
            "pipeline_start",
            session_id=plan.session_id,
            total_tasks=len(plan.tasks),
            groups=len(plan.execution_order),
        )

        task_results: dict[str, TaskResult] = {}
        rendered_files: list[RenderedFile] = []

        # Build a quick lookup from task ID to Task object.
        task_map: dict[str, Task] = {t.id: t for t in plan.tasks}

        # Determine the execution groups.  If execution_order is empty,
        # fall back to running all tasks sequentially (one per group).
        groups = plan.execution_order
        if not groups:
            groups = [[t.id] for t in plan.tasks]

        for group_idx, group_ids in enumerate(groups):
            self.logger.info(
                "pipeline_group_start",
                group=group_idx,
                task_ids=group_ids,
            )

            # Filter out task IDs that aren't in the plan (defensive).
            valid_ids = [tid for tid in group_ids if tid in task_map]
            if not valid_ids:
                self.logger.warning("pipeline_group_empty", group=group_idx)
                continue

            # Check that all dependencies have completed successfully.
            for tid in valid_ids:
                task = task_map[tid]
                for dep_id in task.dependencies:
                    dep_result = task_results.get(dep_id)
                    if dep_result is None or not dep_result.success:
                        # Dependency not met -- skip this task.
                        self.logger.warning(
                            "dependency_not_met",
                            task_id=tid,
                            dependency_id=dep_id,
                        )
                        task.status = TaskStatus.FAILED
                        task.error = f"Dependency '{dep_id}' did not complete successfully"
                        task_results[tid] = TaskResult(
                            task_id=tid,
                            success=False,
                            error=task.error,
                        )
                        valid_ids = [x for x in valid_ids if x != tid]

            if not valid_ids:
                continue

            # Launch tasks in parallel within this group.
            coros = [self._run_and_render(task_map[tid]) for tid in valid_ids]
            group_outcomes: list[tuple[TaskResult, RenderedFile | None]] = (
                await asyncio.gather(*coros, return_exceptions=False)
            )

            for task_result, rendered_file in group_outcomes:
                task_results[task_result.task_id] = task_result
                if rendered_file is not None:
                    rendered_files.append(rendered_file)

            self.logger.info(
                "pipeline_group_complete",
                group=group_idx,
                succeeded=sum(1 for tr, _ in group_outcomes if tr.success),
                failed=sum(1 for tr, _ in group_outcomes if not tr.success),
            )

        # Aggregate final result.
        completed = sum(1 for r in task_results.values() if r.success)
        failed = sum(1 for r in task_results.values() if not r.success)

        pipeline_result = PipelineResult(
            task_results=task_results,
            rendered_files=rendered_files,
            success=(failed == 0 and completed > 0),
            total_tasks=len(plan.tasks),
            completed_tasks=completed,
            failed_tasks=failed,
        )

        self.logger.info(
            "pipeline_complete",
            session_id=plan.session_id,
            success=pipeline_result.success,
            completed=completed,
            failed=failed,
            files=len(rendered_files),
        )
        return pipeline_result

    async def run_single(
        self,
        skill_name: str,
        params: dict,
    ) -> PipelineResult:
        """Convenience method: build and execute a one-task plan.

        Creates a minimal :class:`TaskPlan` containing a single :class:`Task`
        and runs it through the pipeline.

        Parameters
        ----------
        skill_name:
            Registered skill name to invoke.
        params:
            Parameters forwarded to the skill.

        Returns
        -------
        PipelineResult
        """
        task = Task(
            id=uuid.uuid4().hex[:8],
            skill_name=skill_name,
            parameters=params,
        )
        plan = TaskPlan(
            tasks=[task],
            execution_order=[[task.id]],
        )
        return await self.run(plan)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _run_and_render(
        self,
        task: Task,
    ) -> tuple[TaskResult, RenderedFile | None]:
        """Execute a task and, on success, render its output to disk.

        Returns a ``(TaskResult, RenderedFile | None)`` tuple.  The rendered
        file will be ``None`` when execution fails or when there are no
        content bytes to persist.
        """
        task_result = await self.executor.execute_task(task)

        rendered_file: RenderedFile | None = None

        if task_result.success and task_result.output and task_result.output.content_bytes:
            try:
                prefix = task.skill_name.replace(" ", "_")
                rendered_file = await self.renderer.render(
                    task_result.output,
                    prefix=prefix,
                )
                self.logger.info(
                    "task_rendered",
                    task_id=task.id,
                    file=rendered_file.filename,
                )
            except Exception as exc:
                self.logger.error(
                    "render_error",
                    task_id=task.id,
                    error=str(exc),
                    exc_info=True,
                )
                # Rendering failure does not mark the task as failed --
                # the skill produced valid output; only the file write failed.

        return task_result, rendered_file
