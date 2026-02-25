"""Generic OpenAI-compatible provider for the LLM client abstraction.

Supports any LLM service that exposes an OpenAI-compatible chat completions
API, including:
  - Ollama (``http://localhost:11434/v1``)
  - vLLM (``http://localhost:8000/v1``)
  - Together AI (``https://api.together.xyz/v1``)
  - Groq (``https://api.groq.com/openai/v1``)
  - Moonshot / Kimi (``https://api.moonshot.cn/v1``)
  - Zhipu / GLM (``https://open.bigmodel.cn/api/paas/v4``)
  - Any other service with a compatible ``/chat/completions`` endpoint
"""

from __future__ import annotations

import json
import re

from src.utils.exceptions import LLMError
from src.utils.logging import get_logger

logger = get_logger("llm.openai_compatible")


class OpenAICompatibleProvider:
    """Provider for any OpenAI-compatible API endpoint.

    Parameters
    ----------
    api_key:
        API key (pass an empty string or ``"none"`` for services that do not
        require authentication, e.g. local Ollama).
    model:
        Model identifier.
    base_url:
        Base URL for the API (e.g. ``"http://localhost:11434/v1"``).
    provider_name:
        Human-readable name used in log messages and error reports.
    """

    MAX_TOKENS = 4096

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        provider_name: str = "openai_compatible",
    ):
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                provider_name,
                "The 'openai' package is required. "
                "Install it with: pip install openai",
            ) from exc

        if not base_url:
            raise LLMError(provider_name, "base_url is required but was empty.")

        # Some local services (e.g. Ollama) don't need a key.
        effective_key = api_key if api_key else "none"

        self.client = openai.OpenAI(api_key=effective_key, base_url=base_url)
        self.model = model
        self.provider_name = provider_name

    async def complete(self, system: str, user: str) -> str:
        """Call the remote API and return the assistant's text response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            choice = response.choices[0] if response.choices else None
            if choice and choice.message and choice.message.content:
                return choice.message.content
            return ""
        except Exception as exc:
            logger.error(
                "openai_compatible_complete_error",
                provider=self.provider_name,
                error=str(exc),
            )
            raise LLMError(self.provider_name, str(exc)) from exc

    async def complete_json(self, system: str, user: str) -> dict:
        """Call the remote API and parse the response as JSON.

        Attempts to use ``response_format`` if the server supports it;
        falls back to prompt-based JSON extraction otherwise.
        """
        json_system = (
            system + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown code fences or any other text."
        )
        try:
            # Try with response_format first.
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.MAX_TOKENS,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": json_system},
                        {"role": "user", "content": user},
                    ],
                )
            except Exception:
                # Some endpoints don't support response_format; fall back.
                logger.debug(
                    "openai_compatible_no_json_mode",
                    provider=self.provider_name,
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.MAX_TOKENS,
                    messages=[
                        {"role": "system", "content": json_system},
                        {"role": "user", "content": user},
                    ],
                )

            choice = response.choices[0] if response.choices else None
            raw = ""
            if choice and choice.message and choice.message.content:
                raw = choice.message.content
            return self._parse_json(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "openai_compatible_json_parse_error",
                provider=self.provider_name,
                error=str(exc),
            )
            raise LLMError(
                self.provider_name,
                f"Failed to parse LLM response as JSON: {exc}",
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            logger.error(
                "openai_compatible_complete_json_error",
                provider=self.provider_name,
                error=str(exc),
            )
            raise LLMError(self.provider_name, str(exc)) from exc

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Best-effort JSON extraction from LLM output."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

        raise json.JSONDecodeError("No JSON object found in response", text, 0)
