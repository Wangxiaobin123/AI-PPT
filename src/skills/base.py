"""Abstract base class for all skills in the content production system."""

from abc import ABC, abstractmethod

from src.skills.models import QACheck, QAReport, SkillMetadata, SkillResult


class BaseSkill(ABC):
    """Base class that every skill must inherit from.

    Skills are the units of work in the content production system.  Each skill
    declares its capabilities via ``metadata``, validates incoming parameters,
    executes the core transformation, and optionally runs quality-assurance
    checks on the result.
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return the skill's metadata (name, description, formats, etc.)."""
        ...

    @abstractmethod
    async def validate_params(self, params: dict) -> bool:
        """Validate that *params* contains everything this skill requires.

        Returns ``True`` when valid; raises or returns ``False`` otherwise.
        """
        ...

    @abstractmethod
    async def execute(self, params: dict, context: dict) -> SkillResult:
        """Run the skill and produce a :class:`SkillResult`.

        Parameters
        ----------
        params:
            User-supplied parameters (content, format hints, style, etc.).
        context:
            Execution context (e.g. output directory, request id).
        """
        ...

    async def qa_check(self, result: SkillResult) -> QAReport:
        """Run default quality-assurance checks on a skill result.

        Subclasses can override this to add format-specific checks.
        """
        checks: list[QACheck] = []

        # Check that the result has non-empty content bytes.
        if result.content_bytes:
            checks.append(
                QACheck(
                    name="non_empty",
                    passed=len(result.content_bytes) > 0,
                    detail=f"Size: {len(result.content_bytes)} bytes",
                )
            )

        # Check that the result was marked successful.
        checks.append(
            QACheck(
                name="success_flag",
                passed=result.success,
                detail=result.error if not result.success else "OK",
            )
        )

        return QAReport(
            checks=checks,
            passed=all(c.passed for c in checks),
        )
