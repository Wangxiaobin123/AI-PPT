"""Intent analysis endpoint -- accepts natural-language input and returns a
task plan or a clarification request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.intent import IntentRequest, IntentResponse
from src.dependencies import get_intent_engine
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/intent",
    response_model=IntentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Intent engine unavailable"},
    },
    summary="Analyse user intent",
    description=(
        "Submit a natural-language request.  The intent engine analyses the "
        "text and either returns a ready-to-execute TaskPlan or a "
        "ClarificationResponse asking the user for more information."
    ),
)
async def submit_intent(
    request: IntentRequest,
    engine=Depends(get_intent_engine),
) -> IntentResponse:
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Intent engine is not available.  Check that required modules are installed.",
        )

    try:
        result = await engine.process(request.text, request.session_id)
    except Exception as exc:
        logger.error("intent_processing_failed", error=str(exc), text=request.text[:200])
        raise HTTPException(status_code=500, detail=f"Intent processing failed: {exc}") from exc

    # Determine whether the engine returned a plan or a clarification.
    # We duck-type: ClarificationResponse has a ``question`` attribute;
    # TaskPlan has a ``tasks`` attribute.
    if hasattr(result, "question"):
        # ClarificationResponse
        return IntentResponse(
            status="needs_clarification",
            clarification=result.model_dump(),
        )

    # TaskPlan
    return IntentResponse(
        status="ready",
        plan=result.model_dump(),
    )
