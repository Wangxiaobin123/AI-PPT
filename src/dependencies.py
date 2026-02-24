"""FastAPI dependency functions for injection into endpoint handlers.

Each function retrieves or constructs a service object that endpoints
need.  Dependencies that are expensive to create (e.g. the skills
registry) are stored on ``app.state`` during the lifespan and simply
looked up here.  Lighter objects (e.g. ``OutputManager``) are created
per-call but remain cheap because they are thin wrappers.
"""

from __future__ import annotations

from fastapi import Request

from src.config import settings
from src.output.manager import OutputManager
from src.skills.registry import SkillRegistry
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Skills registry (initialised during app lifespan)
# ---------------------------------------------------------------------------

def get_skills_registry(request: Request) -> SkillRegistry:
    """Return the global skills registry stored on ``app.state``."""
    return request.app.state.skills_registry


# ---------------------------------------------------------------------------
# LLM client (optional -- returns None when no API key is configured)
# ---------------------------------------------------------------------------

def get_llm_client():
    """Build an LLM client if API keys are available.

    Returns ``None`` when neither ``anthropic_api_key`` nor
    ``openai_api_key`` are set, allowing the system to degrade
    gracefully (e.g. rule-based intent parsing only).
    """
    if not settings.anthropic_api_key and not settings.openai_api_key:
        return None

    # Lazy import -- the LLM module may not be fully built yet.
    try:
        from src.core.llm.client import LLMClient  # noqa: WPS433
    except ImportError:
        logger.warning("llm_client_unavailable", reason="LLMClient not importable")
        return None

    api_key = settings.anthropic_api_key or settings.openai_api_key
    return LLMClient(settings.llm_provider, api_key, settings.llm_model)


# ---------------------------------------------------------------------------
# Intent engine
# ---------------------------------------------------------------------------

def get_intent_engine(request: Request):
    """Construct an :class:`IntentEngine` wired to the current registry and LLM."""
    # Lazy import to tolerate the module not yet existing at import time.
    try:
        from src.core.intent.engine import IntentEngine  # noqa: WPS433
    except ImportError:
        logger.warning("intent_engine_unavailable", reason="IntentEngine not importable")
        return None

    registry = get_skills_registry(request)
    llm = get_llm_client()
    return IntentEngine(
        llm_client=llm,
        available_skills=[s.name for s in registry.list_all()],
    )


# ---------------------------------------------------------------------------
# Execution pipeline
# ---------------------------------------------------------------------------

def get_pipeline(request: Request):
    """Build an :class:`ExecutionPipeline` for running task plans.

    Returns ``None`` if the pipeline module is not yet available.
    """
    try:
        from src.engine.executor import TaskExecutor  # noqa: WPS433
        from src.engine.pipeline import ExecutionPipeline  # noqa: WPS433
        from src.engine.renderer import FileRenderer  # noqa: WPS433
    except ImportError:
        logger.warning("pipeline_unavailable", reason="Pipeline modules not importable")
        return None

    registry = get_skills_registry(request)
    executor = TaskExecutor(registry)
    renderer = FileRenderer(settings.output_dir)
    return ExecutionPipeline(executor, renderer)


# ---------------------------------------------------------------------------
# Output manager
# ---------------------------------------------------------------------------

def get_output_manager() -> OutputManager:
    """Return a fresh :class:`OutputManager` pointed at the configured output dir."""
    return OutputManager(settings.output_dir)
