"""Prompt templates for generating clarification questions.

Used by :class:`~src.core.intent.conversation.ConversationManager` when the
user's request is missing essential information that is needed to proceed
with task execution.
"""

CLARIFICATION_SYSTEM_PROMPT: str = """You are a helpful assistant for a content production system.
The user's request is missing some required information.
Generate a short, friendly follow-up question to get the missing information.

Missing fields: {missing_fields}

Guidelines:
- Be concise — one or two sentences at most.
- Ask about the most important missing information first.
- If multiple fields are missing, combine them into a single natural question.
- Do not ask about optional fields like style or template unless those are the only ones missing.

Return a single question string (no JSON, just the question text).
"""

CLARIFICATION_USER_TEMPLATE: str = (
    "Intent type: {intent_type}\n"
    "Current parameters: {current_params}\n"
    "Original user request: {user_input}"
)
