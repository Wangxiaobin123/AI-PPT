"""Intent classification module.

Classifies a user's natural-language request into one of the predefined
intent categories.  When an LLM client is available the classification is
performed by the model; otherwise a keyword-based heuristic is used as a
fallback so the system remains functional without API keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.intent.prompts.classification import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_TEMPLATE,
    INTENT_CATEGORIES,
)
from src.utils.logging import get_logger

logger = get_logger("intent.classifier")


@dataclass
class IntentResult:
    """The outcome of classifying a user request.

    Attributes:
        intent_type: One of the values in ``INTENT_CATEGORIES``.
        confidence: How confident the classifier is (0.0 -- 1.0).
        reasoning: Human-readable explanation of the decision.
    """

    intent_type: str
    confidence: float
    reasoning: str


# ---------------------------------------------------------------------------
# Keyword mapping used by the fallback classifier
# ---------------------------------------------------------------------------

# Keywords are tuples of (keyword, weight).  Format-specific keywords
# (file extensions, application names) receive a higher weight than
# generic terms (e.g. "report", "document") to improve discrimination.

_KEYWORD_MAP: dict[str, list[tuple[str, int]]] = {
    "create_pptx": [
        ("ppt", 3), ("pptx", 3), ("powerpoint", 3),
        ("presentation", 2), ("slides", 2), ("slide deck", 2),
        ("slide show", 1), ("slideshow", 1),
    ],
    "create_docx": [
        ("doc", 3), ("docx", 3), ("word", 3),
        ("document", 1), ("report", 1), ("essay", 1), ("letter", 1),
        ("memo", 1), ("paper", 1),
    ],
    "create_xlsx": [
        ("xls", 3), ("xlsx", 3), ("excel", 3),
        ("spreadsheet", 2), ("workbook", 2),
        ("table", 1), ("csv data", 1), ("data sheet", 1),
    ],
    "create_pdf": [
        ("pdf", 3),
    ],
    "create_html": [
        ("html", 3),
        ("webpage", 2), ("web page", 2), ("website", 2), ("web site", 2),
        ("landing page", 2),
    ],
    "convert": [
        ("convert", 3), ("transform", 2), ("export to", 2), ("save as", 2),
        ("change format", 2),
        ("to pptx", 2), ("to docx", 2), ("to pdf", 2), ("to xlsx", 2),
        ("to html", 2),
    ],
    "edit": [
        ("edit", 3), ("modify", 2), ("update", 1), ("change", 1),
        ("revise", 2), ("fix", 1), ("adjust", 1),
        ("add slide", 2), ("remove slide", 2), ("replace", 1),
    ],
    "batch": [
        ("batch", 3), ("multiple", 1), ("bulk", 2), ("several files", 2),
        ("all files", 1), ("many", 1), ("mass produce", 2),
    ],
}


class IntentClassifier:
    """Classifies user input into an intent category.

    Parameters
    ----------
    llm_client:
        An optional :class:`~src.core.llm.client.LLMClient`.  When ``None``
        the classifier falls back to keyword matching.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def classify(
        self,
        user_input: str,
        available_skills: list[str] | None = None,
    ) -> IntentResult:
        """Classify *user_input* and return an :class:`IntentResult`.

        Tries the LLM first; falls back to keyword matching on any failure.
        """
        if available_skills is None:
            available_skills = []

        # Try LLM-based classification when a client is available.
        if self.llm is not None:
            try:
                return await self._llm_classify(user_input, available_skills)
            except Exception as exc:
                logger.warning(
                    "llm_classification_failed_falling_back",
                    error=str(exc),
                )

        # Keyword-based fallback.
        return self._keyword_fallback(user_input)

    # ----- LLM-based classification ----------------------------------------

    async def _llm_classify(
        self,
        user_input: str,
        available_skills: list[str],
    ) -> IntentResult:
        """Use the LLM to classify the user request."""
        system = CLASSIFICATION_SYSTEM_PROMPT.format(
            categories=", ".join(INTENT_CATEGORIES),
        )
        user_msg = CLASSIFICATION_USER_TEMPLATE.format(
            user_input=user_input,
            available_skills=", ".join(available_skills) if available_skills else "none",
        )
        data = await self.llm.complete_json(system, user_msg)

        intent_type = data.get("intent_type", "unknown")
        if intent_type not in INTENT_CATEGORIES:
            intent_type = "unknown"

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        reasoning = data.get("reasoning", "")

        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            reasoning=reasoning,
        )

    # ----- Keyword-based fallback -------------------------------------------

    def _keyword_fallback(self, user_input: str) -> IntentResult:
        """Simple keyword-based classification used when the LLM is unavailable.

        Scans *user_input* against the weighted keyword map and returns the
        category with the highest total weight.  Ties are broken by the order
        in ``_KEYWORD_MAP`` (first match wins).
        """
        text = user_input.lower()
        best_intent = "unknown"
        best_score = 0
        best_keywords: list[str] = []

        for intent, kw_weights in _KEYWORD_MAP.items():
            matched = [(kw, w) for kw, w in kw_weights if kw in text]
            score = sum(w for _, w in matched)
            if score > best_score:
                best_score = score
                best_intent = intent
                best_keywords = [kw for kw, _ in matched]

        # A score of 0 means no keywords matched at all.
        if best_score == 0:
            # Last-ditch: check if the word "create" or "make" or "generate"
            # appears alongside a recognisable format extension.
            create_words = re.findall(
                r"\b(create|make|generate|build|produce|write)\b", text,
            )
            format_words = re.findall(
                r"\b(pptx?|docx?|xlsx?|pdf|html)\b", text,
            )
            if create_words and format_words:
                fmt = format_words[0].rstrip("x")
                fmt_map = {
                    "ppt": "create_pptx",
                    "doc": "create_docx",
                    "xls": "create_xlsx",
                    "pdf": "create_pdf",
                    "htm": "create_html",
                    "html": "create_html",
                }
                best_intent = fmt_map.get(fmt, "unknown")
                best_score = 1
                best_keywords = create_words[:1] + format_words[:1]

        confidence = min(1.0, best_score * 0.3) if best_score > 0 else 0.1

        return IntentResult(
            intent_type=best_intent,
            confidence=confidence,
            reasoning=f"Keyword match: {', '.join(best_keywords)}" if best_keywords else "No keywords matched",
        )
