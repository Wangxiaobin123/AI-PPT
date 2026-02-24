"""Anthropic Claude provider for the LLM client abstraction.

Wraps the ``anthropic`` SDK to expose the standard ``complete`` and
``complete_json`` interface expected by :class:`~src.core.llm.client.LLMClient`.
"""

from __future__ import annotations

import json
import re

from src.utils.exceptions import LLMError
from src.utils.logging import get_logger

logger = get_logger("llm.anthropic")


class AnthropicProvider:
    """Provider implementation for Anthropic Claude models.

    Parameters
    ----------
    api_key:
        Anthropic API key.
    model:
        Model identifier, e.g. ``"claude-sonnet-4-20250514"``.
    """

    MAX_TOKENS = 4096

    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "anthropic",
                "The 'anthropic' package is not installed. "
                "Install it with: pip install anthropic",
            ) from exc

        if not api_key:
            raise LLMError("anthropic", "API key is required but was empty.")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        """Call Claude and return the assistant's text response."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # Extract text from the first content block.
            if message.content and len(message.content) > 0:
                return message.content[0].text
            return ""
        except Exception as exc:
            logger.error("anthropic_complete_error", error=str(exc))
            raise LLMError("anthropic", str(exc)) from exc

    async def complete_json(self, system: str, user: str) -> dict:
        """Call Claude and parse the response as JSON.

        Instructs the model to return valid JSON via the system prompt and
        attempts to extract a JSON object from the response even if it is
        wrapped in markdown code fences.
        """
        json_system = (
            system + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown code fences or any other text."
        )
        try:
            raw = await self.complete(json_system, user)
            return self._parse_json(raw)
        except json.JSONDecodeError as exc:
            logger.error("anthropic_json_parse_error", raw=raw[:500], error=str(exc))
            raise LLMError(
                "anthropic",
                f"Failed to parse LLM response as JSON: {exc}",
            ) from exc

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
