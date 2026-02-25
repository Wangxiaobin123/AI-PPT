"""Prompt templates for parameter extraction.

These templates are consumed by
:class:`~src.core.intent.parameter_extractor.ParameterExtractor` to ask the LLM
to extract structured parameters from a user request once the intent has been
classified.
"""

EXTRACTION_SYSTEM_PROMPT: str = """You are a parameter extractor for a content production system.
Given a user request and intent type, extract structured parameters.

Return JSON with these fields:
- output_format: str (pptx, docx, xlsx, pdf, html)
- title: str or null
- content: str or null (the actual content text if provided inline)
- content_format: str or null (markdown, html, csv, json, text)
- template: str or null
- style: object or null (color_scheme, fonts, etc.)
- slide_count: int or null (for pptx)
- sections: list[str] or null
- additional_instructions: str or null

Rules:
- Only populate fields that are explicitly mentioned or clearly implied.
- Use null for any field that cannot be determined from the request.
- For output_format, infer from the intent_type if not stated explicitly.
- For slide_count, extract any number the user mentions in the context of slides or pages.
- For sections, extract any headings or topic areas the user lists.
"""

EXTRACTION_USER_TEMPLATE: str = (
    "Intent type: {intent_type}\n"
    "User request: {user_input}"
)
