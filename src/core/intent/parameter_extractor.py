"""Parameter extraction module.

Extracts structured generation parameters from a user's natural-language
request once the intent has been classified.  Uses an LLM when available
and falls back to simple regex-based extraction otherwise.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from src.core.intent.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_TEMPLATE,
)
from src.utils.logging import get_logger

logger = get_logger("intent.extractor")


class GenerationParams(BaseModel):
    """Structured parameters extracted from a user request.

    All fields default to ``None`` (or empty string for ``output_format``)
    so that the extractor only populates what it can determine.
    """

    output_format: str = ""
    title: str | None = None
    content: str | None = None
    content_format: str | None = None
    template: str | None = None
    style: dict | None = None
    slide_count: int | None = None
    sections: list[str] | None = None
    additional_instructions: str | None = None


# ---------------------------------------------------------------------------
# Intent type -> default output format mapping
# ---------------------------------------------------------------------------

_FORMAT_FROM_INTENT: dict[str, str] = {
    "create_pptx": "pptx",
    "create_docx": "docx",
    "create_xlsx": "xlsx",
    "create_pdf": "pdf",
    "create_html": "html",
}


class ParameterExtractor:
    """Extracts :class:`GenerationParams` from a user request.

    Parameters
    ----------
    llm_client:
        An optional :class:`~src.core.llm.client.LLMClient`.  When ``None``
        the extractor falls back to regex-based heuristics.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def extract(
        self,
        user_input: str,
        intent_type: str,
    ) -> GenerationParams:
        """Extract parameters from *user_input* given the classified *intent_type*.

        Tries the LLM first; falls back to regex extraction on any failure.
        """
        if self.llm is not None:
            try:
                return await self._llm_extract(user_input, intent_type)
            except Exception as exc:
                logger.warning(
                    "llm_extraction_failed_falling_back",
                    error=str(exc),
                )

        return self._regex_fallback(user_input, intent_type)

    # ----- LLM-based extraction ---------------------------------------------

    async def _llm_extract(
        self,
        user_input: str,
        intent_type: str,
    ) -> GenerationParams:
        """Use the LLM to extract structured parameters."""
        system = EXTRACTION_SYSTEM_PROMPT
        user_msg = EXTRACTION_USER_TEMPLATE.format(
            intent_type=intent_type,
            user_input=user_input,
        )
        data = await self.llm.complete_json(system, user_msg)

        # Normalise the output_format.
        output_format = data.get("output_format", "")
        if not output_format:
            output_format = _FORMAT_FROM_INTENT.get(intent_type, "")

        # Ensure slide_count is an int or None.
        slide_count = data.get("slide_count")
        if slide_count is not None:
            try:
                slide_count = int(slide_count)
            except (TypeError, ValueError):
                slide_count = None

        # Ensure sections is a list or None.
        sections = data.get("sections")
        if sections is not None and not isinstance(sections, list):
            sections = None

        # Ensure style is a dict or None.
        style = data.get("style")
        if style is not None and not isinstance(style, dict):
            style = None

        return GenerationParams(
            output_format=output_format,
            title=data.get("title"),
            content=data.get("content"),
            content_format=data.get("content_format"),
            template=data.get("template"),
            style=style,
            slide_count=slide_count,
            sections=sections,
            additional_instructions=data.get("additional_instructions"),
        )

    # ----- Regex-based fallback ----------------------------------------------

    def _regex_fallback(
        self,
        user_input: str,
        intent_type: str,
    ) -> GenerationParams:
        """Basic regex extraction when the LLM is unavailable.

        Extracts:
        - ``output_format`` from the intent type.
        - ``slide_count`` from numbers near "slide" / "page".
        - ``title`` from quoted strings or "about ..." / "titled ..." phrases.
        - ``sections`` from comma-separated or bullet-list items.
        """
        text = user_input

        # Output format
        output_format = _FORMAT_FROM_INTENT.get(intent_type, "")
        if not output_format:
            fmt_match = re.search(
                r"\b(pptx?|docx?|xlsx?|pdf|html)\b",
                text,
                re.IGNORECASE,
            )
            if fmt_match:
                fmt = fmt_match.group(1).lower()
                norm = {"ppt": "pptx", "doc": "docx", "xls": "xlsx", "htm": "html"}
                output_format = norm.get(fmt, fmt)

        # Slide / page count (matches "10 slides", "10-slide", etc.)
        slide_count: int | None = None
        slide_match = re.search(
            r"(\d+)[\s-]*(?:slides?|pages?)", text, re.IGNORECASE,
        )
        if slide_match:
            slide_count = int(slide_match.group(1))

        # Title from quoted text or "about ..." / "titled ..."
        title: str | None = None
        title_match = re.search(
            r'(?:titled?|called|named|about)\s+["\u201c](.+?)["\u201d]',
            text,
            re.IGNORECASE,
        )
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Try a simpler quoted string.
            quote_match = re.search(r'["\u201c](.+?)["\u201d]', text)
            if quote_match:
                title = quote_match.group(1).strip()
            else:
                # Try "about <topic>" without quotes.
                about_match = re.search(
                    r"\babout\s+(.+?)(?:\.|,|$|\swith\b|\sin\b)",
                    text,
                    re.IGNORECASE,
                )
                if about_match:
                    title = about_match.group(1).strip()

        # Sections from enumerated items like "covering: A, B, and C"
        sections: list[str] | None = None
        section_match = re.search(
            r"(?:covering|including|sections?|topics?)[:\s]+(.+?)(?:\.|$)",
            text,
            re.IGNORECASE,
        )
        if section_match:
            raw_sections = section_match.group(1)
            # Split on commas (with optional trailing "and"), or standalone "and".
            parts = re.split(r"\s*,\s*(?:and\s+)?|\s+and\s+", raw_sections)
            sections = [s.strip() for s in parts if s.strip()]
            if len(sections) < 2:
                sections = None

        # Content format hinting
        content_format: str | None = None
        if re.search(r"\bmarkdown\b", text, re.IGNORECASE):
            content_format = "markdown"
        elif re.search(r"\bhtml\b", text, re.IGNORECASE) and intent_type != "create_html":
            content_format = "html"
        elif re.search(r"\bcsv\b", text, re.IGNORECASE):
            content_format = "csv"
        elif re.search(r"\bjson\b", text, re.IGNORECASE):
            content_format = "json"

        return GenerationParams(
            output_format=output_format,
            title=title,
            content=None,
            content_format=content_format,
            template=None,
            style=None,
            slide_count=slide_count,
            sections=sections,
            additional_instructions=None,
        )
