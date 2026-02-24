"""Common response schemas used across all API endpoints."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response returned by all endpoints on failure."""

    error: str
    detail: str = ""


class SuccessResponse(BaseModel):
    """Generic success response for simple operations."""

    message: str
    data: dict = {}
