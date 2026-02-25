"""Execution engine -- orchestrates task execution, QA, rendering, and pipelines.

Public API::

    from src.engine import (
        ExecutionPipeline,
        FileRenderer,
        PipelineResult,
        QAValidator,
        RenderedFile,
        TaskExecutor,
        TaskResult,
    )
"""

from src.engine.executor import TaskExecutor, TaskResult
from src.engine.pipeline import ExecutionPipeline, PipelineResult
from src.engine.qa import QAValidator
from src.engine.renderer import FileRenderer, RenderedFile

__all__ = [
    "ExecutionPipeline",
    "FileRenderer",
    "PipelineResult",
    "QAValidator",
    "RenderedFile",
    "TaskExecutor",
    "TaskResult",
]
