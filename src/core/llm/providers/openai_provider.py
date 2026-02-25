"""OpenAI provider for the LLM client abstraction.

Wraps the ``openai`` SDK to expose the standard ``complete`` and
``complete_json`` interface expected by :class:`~src.core.llm.client.LLMClient`.
"""

from __future__ import annotations

import json
import re

from src.utils.exceptions import LLMError
from src.utils.logging import get_logger

logger = get_logger("llm.openai")


class OpenAIProvider:
    """Provider implementation for OpenAI models.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    model:
        Model identifier, e.g. ``"gpt-4o"``.
    """

    MAX_TOKENS = 4096

    def __init__(self, api_key: str, model: str):
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "openai",
                "The 'openai' package is not installed. "
                "Install it with: pip install openai",
            ) from exc

        if not api_key:
            raise LLMError("openai", "API key is required but was empty.")

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        """Call the OpenAI chat completions API and return the text response."""
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
            logger.error("openai_complete_error", error=str(exc))
            raise LLMError("openai", str(exc)) from exc

    async def complete_json(self, system: str, user: str) -> dict:
        """Call OpenAI and parse the response as JSON.

        Uses ``response_format`` when available to request structured JSON
        output.  Falls back to manual extraction otherwise.
        """
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
            logger.error("openai_json_parse_error", error=str(exc))
            raise LLMError(
                "openai",
                f"Failed to parse LLM response as JSON: {exc}",
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            logger.error("openai_complete_json_error", error=str(exc))
            raise LLMError("openai", str(exc)) from exc

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Best-effort JSON extraction from LLM output.

        Handles responses that are plain JSON as well as those wrapped in
        markdown ```json ... ``` fences.
        """
        text = text.strip()
        # Try direct parse first.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code fences.
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        # Try to find first { ... } block.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

        raise json.JSONDecodeError("No JSON object found in response", text, 0)
