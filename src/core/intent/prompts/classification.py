"""Prompt templates for intent classification.

These templates are consumed by :class:`~src.core.intent.classifier.IntentClassifier`
to ask the LLM to classify a user request into one of the predefined
intent categories.
"""

INTENT_CATEGORIES: list[str] = [
    "create_pptx",
    "create_docx",
    "create_xlsx",
    "create_pdf",
    "create_html",
    "convert",
    "edit",
    "batch",
    "unknown",
]

CLASSIFICATION_SYSTEM_PROMPT: str = """You are an intent classifier for a content production system.
Given a user request, classify the intent into one of these categories:
{categories}

Category descriptions:
- create_pptx: Create a new PowerPoint presentation (.pptx)
- create_docx: Create a new Word document (.docx)
- create_xlsx: Create a new Excel spreadsheet (.xlsx)
- create_pdf: Create a new PDF document
- create_html: Create a new HTML page or site
- convert: Convert a file from one format to another
- edit: Edit or modify an existing file
- batch: Process multiple files or create multiple outputs at once
- unknown: The request does not match any known intent

Return JSON: {{"intent_type": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
"""

CLASSIFICATION_USER_TEMPLATE: str = (
    "User request: {user_input}\n"
    "Available skills: {available_skills}"
)
