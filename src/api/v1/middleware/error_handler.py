"""Global error-handling middleware.

Catches application-specific exceptions and translates them into
structured JSON error responses with appropriate HTTP status codes.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.utils.exceptions import (
    ContentProducerError,
    FileStorageError,
    GeneratorError,
    IntentError,
    LLMError,
    ParserError,
    QAValidationError,
    SkillExecutionError,
    SkillNotFoundError,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Map exception types to HTTP status codes.
_STATUS_MAP: dict[type, int] = {
    SkillNotFoundError: 404,
    IntentError: 400,
    ParserError: 422,
    GeneratorError: 500,
    SkillExecutionError: 500,
    LLMError: 502,
    QAValidationError: 422,
    FileStorageError: 500,
}


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that wraps every request in a try/except and converts
    known exceptions to JSON error responses.

    Unknown exceptions are logged and returned as HTTP 500.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)

        except ContentProducerError as exc:
            status_code = _STATUS_MAP.get(type(exc), 500)
            logger.warning(
                "handled_error",
                error_type=type(exc).__name__,
                status_code=status_code,
                detail=str(exc),
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status_code,
                content={"error": type(exc).__name__, "detail": str(exc)},
            )

        except Exception as exc:
            logger.error(
                "unhandled_error",
                error_type=type(exc).__name__,
                detail=str(exc),
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "detail": "An unexpected error occurred.  Please try again later.",
                },
            )
