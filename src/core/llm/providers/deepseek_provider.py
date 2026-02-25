"""DeepSeek provider for the LLM client abstraction.

DeepSeek exposes an OpenAI-compatible API at ``https://api.deepseek.com``.
This provider reuses the ``openai`` SDK with a custom ``base_url``.
"""

from __future__ import annotations

import json
import re

from src.utils.exceptions import LLMError
from src.utils.logging import get_logger

logger = get_logger("llm.deepseek")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider:
    """Provider implementation for DeepSeek models.

    Parameters
    ----------
    api_key:
        DeepSeek API key.
    model:
        Model identifier, e.g. ``"deepseek-chat"`` or ``"deepseek-reasoner"``.
    """

    MAX_TOKENS = 4096

    def __init__(self, api_key: str, model: str):
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "deepseek",
                "The 'openai' package is required for DeepSeek. "
                "Install it with: pip install openai",
            ) from exc

        if not api_key:
            raise LLMError("deepseek", "API key is required but was empty.")

        self.client = openai.OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        """Call DeepSeek and return the assistant's text response."""
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
            logger.error("deepseek_complete_error", error=str(exc))
            raise LLMError("deepseek", str(exc)) from exc

    async def complete_json(self, system: str, user: str) -> dict:
        """Call DeepSeek and parse the response as JSON."""
        json_system = (
            system + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown code fences or any other text."
        )
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
            choice = response.choices[0] if response.choices else None
            raw = ""
            if choice and choice.message and choice.message.content:
                raw = choice.message.content
            return self._parse_json(raw)
        except json.JSONDecodeError as exc:
            logger.error("deepseek_json_parse_error", error=str(exc))
            raise LLMError(
                "deepseek",
                f"Failed to parse LLM response as JSON: {exc}",
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            logger.error("deepseek_complete_json_error", error=str(exc))
            raise LLMError("deepseek", str(exc)) from exc

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
