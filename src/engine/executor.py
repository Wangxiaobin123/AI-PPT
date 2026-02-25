"""Task executor -- resolves a skill for each task and runs it.

The :class:`TaskExecutor` is the bridge between the task plan (produced by
the intent engine) and the skills registry.  For every :class:`Task` it:

1. Looks up the skill by name.
2. Validates the task parameters.
3. Calls :meth:`BaseSkill.execute`.
4. Runs QA checks via :class:`QAValidator`.
5. Returns a :class:`TaskResult` summarising the outcome.
"""

from __future__ import annotations

import time
import traceback

from pydantic import BaseModel

from src.core.task.models import Task, TaskStatus
from src.engine.qa import QAValidator
from src.skills.models import QAReport, SkillResult
from src.skills.registry import SkillRegistry
from src.utils.exceptions import SkillExecutionError, SkillNotFoundError
from src.utils.logging import get_logger


class TaskResult(BaseModel):
    """Outcome of executing a single :class:`Task`.

    Attributes:
        task_id: The originating task's identifier.
        output: The skill's raw result, if execution succeeded.
        qa_report: Quality-assurance report, if QA ran.
        success: Whether the task completed without errors.
        error: Human-readable error message on failure.
        duration_seconds: Wall-clock time taken to execute.
    """

    task_id: str
    output: SkillResult | None = None
    qa_report: QAReport | None = None
    success: bool = False
    error: str = ""
    duration_seconds: float = 0.0


class TaskExecutor:
    """Execute individual tasks by delegating to the skills registry.

    Parameters
    ----------
    registry:
        The populated :class:`SkillRegistry` from which skills are resolved.
    qa_validator:
        Optional :class:`QAValidator`; one is created automatically when not
        provided.
    context:
        Extra context dict forwarded to every ``skill.execute()`` call
        (e.g. output directory, session id).
    """

    def __init__(
        self,
        registry: SkillRegistry,
        qa_validator: QAValidator | None = None,
        context: dict | None = None,
    ) -> None:
        self.registry = registry
        self.qa_validator = qa_validator or QAValidator()
        self.context = context or {}
        self.logger = get_logger("engine.executor")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a single *task* end-to-end.

        The method is safe to call for any task; errors are caught and
        returned inside the :class:`TaskResult` rather than propagated.
        """
        start = time.monotonic()
        self.logger.info("task_start", task_id=task.id, skill=task.skill_name)

        # Mark as running
        task.status = TaskStatus.RUNNING

        try:
            # 1. Resolve skill
            skill = self._resolve_skill(task)

            # 2. Validate parameters
            await self._validate_params(skill, task)

            # 3. Execute skill
            skill_result = await self._execute_skill(skill, task)

            # 4. Run QA checks
            qa_report = await self._run_qa(skill, skill_result)

            # 5. Build the success result
            duration = time.monotonic() - start

            # Populate the task model fields
            task.status = TaskStatus.COMPLETED
            task.result = skill_result.model_dump()

            result = TaskResult(
                task_id=task.id,
                output=skill_result,
                qa_report=qa_report,
                success=True,
                duration_seconds=round(duration, 4),
            )
            self.logger.info(
                "task_complete",
                task_id=task.id,
                duration=result.duration_seconds,
                qa_passed=qa_report.passed if qa_report else None,
            )
            return result

        except SkillNotFoundError as exc:
            return self._fail(task, str(exc), start)

        except SkillExecutionError as exc:
            return self._fail(task, str(exc), start)

        except Exception as exc:
            # Catch-all so we never crash the pipeline.
            tb = traceback.format_exc()
            self.logger.error(
                "task_unexpected_error",
                task_id=task.id,
                error=str(exc),
                traceback=tb,
            )
            return self._fail(task, f"Unexpected error: {exc}", start)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_skill(self, task: Task):
        """Look up the skill from the registry."""
        self.logger.debug("resolve_skill", skill_name=task.skill_name)
        return self.registry.get(task.skill_name)

    async def _validate_params(self, skill, task: Task) -> None:
        """Call the skill's parameter validation.

        Raises :class:`SkillExecutionError` when validation fails.
        """
        try:
            valid = await skill.validate_params(task.parameters)
            if valid is False:
                raise SkillExecutionError(
                    task.skill_name,
                    "Parameter validation returned False",
                )
        except SkillExecutionError:
            raise
        except Exception as exc:
            raise SkillExecutionError(
                task.skill_name,
                f"Parameter validation error: {exc}",
            ) from exc

    async def _execute_skill(self, skill, task: Task) -> SkillResult:
        """Call the skill's execute method.

        Raises :class:`SkillExecutionError` when execution fails.
        """
        try:
            result = await skill.execute(task.parameters, self.context)
        except Exception as exc:
            raise SkillExecutionError(
                task.skill_name,
                f"Execution raised: {exc}",
            ) from exc

        if not result.success:
            raise SkillExecutionError(
                task.skill_name,
                result.error or "Skill reported failure without error message",
            )
        return result

    async def _run_qa(self, skill, skill_result: SkillResult) -> QAReport:
        """Run QA through both the skill's own check and the global validator.

        Returns the combined QA report from the global :class:`QAValidator`.
        The skill's own ``qa_check`` is invoked first for its side-effects
        (logging, metrics); the authoritative report is from the validator.
        """
        # Skill-level QA (optional, best-effort)
        try:
            await skill.qa_check(skill_result)
        except Exception:
            self.logger.warning("skill_qa_check_error", exc_info=True)

        # Global QA validator
        qa_report = await self.qa_validator.validate(skill_result)
        return qa_report

    def _fail(self, task: Task, error_msg: str, start: float) -> TaskResult:
        """Mark a task as failed and return a failure :class:`TaskResult`."""
        duration = time.monotonic() - start
        task.status = TaskStatus.FAILED
        task.error = error_msg
        self.logger.error(
            "task_failed",
            task_id=task.id,
            error=error_msg,
            duration=round(duration, 4),
        )
        return TaskResult(
            task_id=task.id,
            success=False,
            error=error_msg,
            duration_seconds=round(duration, 4),
        )
