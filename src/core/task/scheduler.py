"""Task scheduling with topological sort.

Takes a list of :class:`~src.core.task.models.Task` objects (potentially with
inter-task dependencies) and produces a :class:`~src.core.task.models.TaskPlan`
whose ``execution_order`` groups independent tasks together for parallel
execution while respecting dependency ordering.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque

from src.core.task.models import Task, TaskPlan
from src.utils.logging import get_logger

logger = get_logger("task.scheduler")


class CyclicDependencyError(Exception):
    """Raised when the task dependency graph contains a cycle."""


class TaskScheduler:
    """Produces an execution plan from a list of tasks.

    The scheduler performs a topological sort (Kahn's algorithm) on the task
    dependency graph and groups tasks into *waves* -- lists of task IDs that
    can be executed in parallel.
    """

    def schedule(
        self,
        tasks: list[Task],
        session_id: str = "",
    ) -> TaskPlan:
        """Build a :class:`TaskPlan` from the supplied *tasks*.

        Parameters
        ----------
        tasks:
            The tasks to schedule.  Each task may list dependency IDs in its
            ``dependencies`` field.
        session_id:
            An optional session ID to attach to the plan.  If empty, one is
            generated automatically.
        """
        if not session_id:
            session_id = uuid.uuid4().hex[:12]

        if not tasks:
            return TaskPlan(session_id=session_id, tasks=[], execution_order=[])

        # Build lookup and validate dependencies.
        task_map: dict[str, Task] = {t.id: t for t in tasks}
        self._validate_dependencies(task_map)

        # Topological sort into waves.
        execution_order = self._topological_sort(tasks, task_map)

        logger.info(
            "schedule_complete",
            session_id=session_id,
            total_tasks=len(tasks),
            waves=len(execution_order),
        )

        return TaskPlan(
            session_id=session_id,
            tasks=tasks,
            execution_order=execution_order,
        )

    # ----- Internal helpers -------------------------------------------------

    @staticmethod
    def _validate_dependencies(task_map: dict[str, Task]) -> None:
        """Ensure every referenced dependency exists in the task set."""
        for task in task_map.values():
            for dep_id in task.dependencies:
                if dep_id not in task_map:
                    logger.warning(
                        "unknown_dependency",
                        task_id=task.id,
                        missing_dep=dep_id,
                    )
                    # Remove the dangling dependency so scheduling can proceed.
                    task.dependencies = [
                        d for d in task.dependencies if d in task_map
                    ]

    @staticmethod
    def _topological_sort(
        tasks: list[Task],
        task_map: dict[str, Task],
    ) -> list[list[str]]:
        """Return waves of task IDs via Kahn's algorithm.

        Each wave is a ``list[str]`` of task IDs that have no unmet
        dependencies and can therefore run concurrently.  Waves are
        returned in execution order.

        Raises :class:`CyclicDependencyError` if the graph has a cycle.
        """
        # Compute in-degree for every task.
        in_degree: dict[str, int] = {t.id: 0 for t in tasks}
        dependents: dict[str, list[str]] = defaultdict(list)

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    in_degree[task.id] += 1
                    dependents[dep_id].append(task.id)

        # Seed the first wave with zero-in-degree tasks.
        current_wave: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )

        waves: list[list[str]] = []
        processed = 0

        while current_wave:
            wave = sorted(current_wave)  # deterministic ordering
            waves.append(wave)
            next_wave: deque[str] = deque()
            for tid in wave:
                processed += 1
                for dependent_id in dependents[tid]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_wave.append(dependent_id)
            current_wave = next_wave

        if processed != len(tasks):
            raise CyclicDependencyError(
                f"Cyclic dependency detected among tasks: "
                f"processed {processed}/{len(tasks)}."
            )

        return waves
