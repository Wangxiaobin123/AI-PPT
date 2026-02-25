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

def _resolve_api_key() -> str:
    """Pick the API key for the configured provider.

    Resolution order:
      1. Provider-specific key (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``,
         ``DEEPSEEK_API_KEY``)
      2. Generic ``LLM_API_KEY``
      3. Fall back to any non-empty provider-specific key
    """
    provider = settings.llm_provider
    provider_keys: dict[str, str] = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
    }

    # 1. Exact match for the configured provider.
    if provider in provider_keys and provider_keys[provider]:
        return provider_keys[provider]

    # 2. Generic key.
    if settings.llm_api_key:
        return settings.llm_api_key

    # 3. Any non-empty key (for services like Ollama that accept anything).
    for key in provider_keys.values():
        if key:
            return key

    return ""


def get_llm_client():
    """Build an LLM client if API keys are available.

    Returns ``None`` when no usable API key is found **and** the provider
    requires one, allowing the system to degrade gracefully (e.g.
    rule-based intent parsing only).
    """
    api_key = _resolve_api_key()
    provider = settings.llm_provider

    # Ollama and some local providers don't require a key.
    local_providers = {"ollama"}
    if not api_key and provider not in local_providers:
        return None

    # Lazy import -- the LLM module may not be fully built yet.
    try:
        from src.core.llm.client import LLMClient  # noqa: WPS433
    except ImportError:
        logger.warning("llm_client_unavailable", reason="LLMClient not importable")
        return None

    base_url = settings.llm_base_url or None
    return LLMClient(provider, api_key, settings.llm_model, base_url=base_url)


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
