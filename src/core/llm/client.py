"""High-level LLM client abstraction.

Provides a unified interface for interacting with different LLM providers
through a single ``LLMClient`` class.  Supported providers:

  - ``anthropic`` — Anthropic Claude
  - ``openai`` — OpenAI GPT
  - ``deepseek`` — DeepSeek (OpenAI-compatible at api.deepseek.com)
  - ``ollama`` — Ollama local models (OpenAI-compatible at localhost:11434)
  - ``openai_compatible`` — Any OpenAI-compatible API with a custom base_url

The concrete provider is selected at initialisation time based on the
``provider`` string.
"""

from __future__ import annotations

import json

from src.utils.logging import get_logger
from src.utils.exceptions import LLMError

# Well-known OpenAI-compatible providers and their default base URLs.
_KNOWN_COMPATIBLE_PROVIDERS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com",
    "ollama": "http://localhost:11434/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


class LLMClient:
    """Unified LLM client that delegates to a provider-specific backend.

    Parameters
    ----------
    provider:
        Provider name — ``"anthropic"``, ``"openai"``, ``"deepseek"``,
        ``"ollama"``, ``"openai_compatible"``, or any key in the
        well-known providers registry.
    api_key:
        API key for the chosen provider.
    model:
        Model identifier (e.g. ``"claude-sonnet-4-20250514"``, ``"gpt-4o"``,
        ``"deepseek-chat"``, ``"llama3"``).
    base_url:
        Optional base URL.  Required for ``openai_compatible``; ignored for
        ``anthropic`` and ``openai``; overrides the default for well-known
        compatible providers.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.logger = get_logger("llm")
        self._provider_client = self._init_provider()

    def _init_provider(self):
        """Instantiate the appropriate provider backend."""
        if self.provider == "anthropic":
            from src.core.llm.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(self.api_key, self.model)

        if self.provider == "openai":
            from src.core.llm.providers.openai_provider import OpenAIProvider

            return OpenAIProvider(self.api_key, self.model)

        if self.provider == "deepseek":
            from src.core.llm.providers.deepseek_provider import DeepSeekProvider

            return DeepSeekProvider(self.api_key, self.model)

        # Check if it's a well-known compatible provider or explicit
        # openai_compatible.
        if self.provider in _KNOWN_COMPATIBLE_PROVIDERS or self.provider == "openai_compatible":
            from src.core.llm.providers.openai_compatible_provider import (
                OpenAICompatibleProvider,
            )

            base_url = self.base_url or _KNOWN_COMPATIBLE_PROVIDERS.get(self.provider, "")
            if not base_url:
                raise LLMError(
                    self.provider,
                    "base_url is required for openai_compatible provider. "
                    "Set LLM_BASE_URL in your .env file.",
                )
            return OpenAICompatibleProvider(
                api_key=self.api_key,
                model=self.model,
                base_url=base_url,
                provider_name=self.provider,
            )

        raise LLMError(
            self.provider,
            f"Unknown provider: {self.provider}. "
            f"Supported: anthropic, openai, deepseek, ollama, "
            f"{', '.join(_KNOWN_COMPATIBLE_PROVIDERS.keys())}, openai_compatible",
        )

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
