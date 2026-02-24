"""Request / response logging middleware using structlog.

Logs each request with method, path, status code, and timing.
"""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with timing and response status."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        # Attach identifiers if present.
        request_id = request.headers.get("x-request-id", "")

        logger.info(
            "request_started",
            method=method,
            path=path,
            query=query,
            request_id=request_id,
        )

        response: Response | None = None
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request_failed",
                method=method,
                path=path,
                elapsed_ms=elapsed_ms,
                request_id=request_id,
            )
            raise
        else:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.status_code if response else 500

            log_fn = logger.info if status_code < 400 else logger.warning
            log_fn(
                "request_completed",
                method=method,
                path=path,
                status_code=status_code,
                elapsed_ms=elapsed_ms,
                request_id=request_id,
            )

        return response
