"""Request/response schemas for the intent analysis endpoint."""

from pydantic import BaseModel, Field


class IntentRequest(BaseModel):
    """User's natural-language request to be analysed by the intent engine."""

    text: str = Field(..., min_length=1, max_length=10000, description="Natural-language request")
    session_id: str | None = Field(
        default=None,
        description="Optional session ID for multi-turn conversations",
    )


class IntentResponse(BaseModel):
    """Result of intent analysis.

    * ``status="ready"`` means a :pyclass:`TaskPlan` was produced and is
      included in *plan*.
    * ``status="needs_clarification"`` means the engine needs more info;
      the follow-up question is in *clarification*.
    """

    status: str  # "ready" | "needs_clarification"
    plan: dict | None = None  # TaskPlan serialised as dict
    clarification: dict | None = None  # ClarificationResponse serialised as dict
