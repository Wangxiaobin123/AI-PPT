"""Task decomposition module.

Breaks down a classified intent and its extracted parameters into one or
more executable :class:`~src.core.task.models.Task` objects.  Simple
intents produce a single task; complex intents like ``convert`` or
``batch`` may produce a pipeline of dependent tasks.
"""

from __future__ import annotations

from src.core.task.models import Task
from src.utils.logging import get_logger

logger = get_logger("task.decomposer")


# ---------------------------------------------------------------------------
# Mapping from intent types to skill names
# ---------------------------------------------------------------------------

_INTENT_TO_SKILL: dict[str, str] = {
    "create_pptx": "pptx",
    "create_docx": "docx",
    "create_xlsx": "xlsx",
    "create_pdf": "pdf",
    "create_html": "html",
}


class TaskDecomposer:
    """Decomposes an intent + parameters into a list of :class:`Task` objects.

    The decomposer handles three categories of intents:

    1. **Simple creation** (``create_*``) -- produces a single generation task.
    2. **Conversion** (``convert``) -- produces a parse task followed by a
       generation task (the generation depends on the parse).
    3. **Batch** (``batch``) -- produces one generation task per item in the
       ``items`` list found in the parameters.
    """

    def decompose(self, intent_type: str, params) -> list[Task]:
        """Return a list of tasks for the given intent and parameters.

        Parameters
        ----------
        intent_type:
            The classified intent (e.g. ``"create_pptx"``).
        params:
            A :class:`~src.core.intent.parameter_extractor.GenerationParams`
            instance or a plain ``dict``.
        """
        # Normalise params to a dict.
        if hasattr(params, "model_dump"):
            param_dict = params.model_dump(exclude_none=True)
        elif isinstance(params, dict):
            param_dict = {k: v for k, v in params.items() if v is not None}
        else:
            param_dict = {}

        if intent_type == "convert":
            return self._decompose_convert(param_dict)
        elif intent_type == "batch":
            return self._decompose_batch(param_dict)
        elif intent_type == "edit":
            return self._decompose_edit(param_dict)
        elif intent_type in _INTENT_TO_SKILL:
            return self._decompose_create(intent_type, param_dict)
        else:
            # Unknown or unrecognised intent: create a single generic task.
            logger.warning(
                "unknown_intent_type",
                intent_type=intent_type,
            )
            return [
                Task(
                    skill_name="generic_handler",
                    parameters=param_dict,
                )
            ]

    # ----- Simple creation --------------------------------------------------

    def _decompose_create(
        self,
        intent_type: str,
        params: dict,
    ) -> list[Task]:
        """Single task: generate the requested file type."""
        skill = _INTENT_TO_SKILL[intent_type]

        # If content is provided and needs parsing, prepend a parse task.
        content_format = params.get("content_format")
        content = params.get("content")
        if content and content_format and content_format != "text":
            parse_task = Task(
                skill_name=f"{content_format}_parser",
                parameters={
                    "content": content,
                    "content_format": content_format,
                },
            )
            gen_task = Task(
                skill_name=skill,
                parameters=params,
                dependencies=[parse_task.id],
            )
            return [parse_task, gen_task]

        return [Task(skill_name=skill, parameters=params)]

    # ----- Conversion -------------------------------------------------------

    def _decompose_convert(self, params: dict) -> list[Task]:
        """Two-task pipeline: parse source -> generate target."""
        source_format = params.get("content_format", "text")
        target_format = params.get("output_format", "")

        parse_task = Task(
            skill_name=f"{source_format}_parser",
            parameters={
                "content": params.get("content", ""),
                "content_format": source_format,
            },
        )

        target_skill = _INTENT_TO_SKILL.get(
            f"create_{target_format}", f"{target_format}_generator",
        )
        gen_task = Task(
            skill_name=target_skill,
            parameters=params,
            dependencies=[parse_task.id],
        )

        return [parse_task, gen_task]

    # ----- Batch processing -------------------------------------------------

    def _decompose_batch(self, params: dict) -> list[Task]:
        """One task per batch item.  All tasks are independent."""
        items = params.get("items", [])
        output_format = params.get("output_format", "pptx")
        skill = _INTENT_TO_SKILL.get(
            f"create_{output_format}", f"{output_format}_generator",
        )

        if not items:
            # If no items list, treat as a single generation task.
            return [Task(skill_name=skill, parameters=params)]

        tasks: list[Task] = []
        for idx, item in enumerate(items):
            item_params = {**params, "item_index": idx}
            if isinstance(item, dict):
                item_params.update(item)
            elif isinstance(item, str):
                item_params["title"] = item
            tasks.append(Task(skill_name=skill, parameters=item_params))

        return tasks

    # ----- Editing ----------------------------------------------------------

    def _decompose_edit(self, params: dict) -> list[Task]:
        """Single edit task."""
        return [Task(skill_name="file_editor", parameters=params)]
