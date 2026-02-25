"""High-level LLM client abstraction.

Provides a unified interface for interacting with different LLM providers
(Anthropic, OpenAI) through a single ``LLMClient`` class.  The concrete
provider is selected at initialisation time based on the ``provider`` string.
"""

from __future__ import annotations

import json

from src.utils.logging import get_logger
from src.utils.exceptions import LLMError


class LLMClient:
    """Unified LLM client that delegates to a provider-specific backend.

    Parameters
    ----------
    provider:
        One of ``"anthropic"`` or ``"openai"``.
    api_key:
        API key for the chosen provider.
    model:
        Model identifier (e.g. ``"claude-sonnet-4-20250514"``, ``"gpt-4o"``).
    """

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.logger = get_logger("llm")
        self._provider_client = self._init_provider()

    def _init_provider(self):
        """Instantiate the appropriate provider backend."""
        if self.provider == "anthropic":
            from src.core.llm.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(self.api_key, self.model)
        elif self.provider == "openai":
            from src.core.llm.providers.openai_provider import OpenAIProvider

            return OpenAIProvider(self.api_key, self.model)
        else:
            raise LLMError(self.provider, f"Unknown provider: {self.provider}")

    async def complete(self, system: str, user: str) -> str:
        """Send a system + user message pair and return the text response.

        Raises :class:`LLMError` on provider failures.
        """
        self.logger.info(
            "llm_complete",
            provider=self.provider,
            model=self.model,
            system_len=len(system),
            user_len=len(user),
        )
        try:
            result = await self._provider_client.complete(system, user)
            self.logger.info(
                "llm_complete_success",
                response_len=len(result),
            )
            return result
        except LLMError:
            raise
        except Exception as exc:
            self.logger.error("llm_complete_error", error=str(exc))
            raise LLMError(self.provider, str(exc)) from exc

    async def complete_json(self, system: str, user: str) -> dict:
        """Send a system + user message pair and parse the response as JSON.

        The underlying provider is instructed to return valid JSON.  If the
        response cannot be parsed, a :class:`LLMError` is raised.
        """
        self.logger.info(
            "llm_complete_json",
            provider=self.provider,
            model=self.model,
        )
        try:
            result = await self._provider_client.complete_json(system, user)
            self.logger.info("llm_complete_json_success")
            return result
        except LLMError:
            raise
        except Exception as exc:
            self.logger.error("llm_complete_json_error", error=str(exc))
            raise LLMError(self.provider, str(exc)) from exc
