"""File download endpoint -- serves previously generated output files."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.api.v1.schemas.common import ErrorResponse
from src.dependencies import get_output_manager
from src.output.delivery import DeliveryService
from src.output.manager import OutputManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/files/{file_id}",
    response_class=FileResponse,
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="Download a generated file",
    description="Retrieve a previously generated file by its unique ID.",
)
async def download_file(
    file_id: str,
    output_manager: OutputManager = Depends(get_output_manager),
) -> FileResponse:
    delivery = DeliveryService(output_manager)
    try:
        return await delivery.get_download_response(file_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_id}",
        )


@router.get(
    "/files",
    summary="List all stored files",
    description="Return metadata for every file currently held by the output manager.",
)
async def list_files(
    output_manager: OutputManager = Depends(get_output_manager),
) -> dict:
    files = output_manager.list_files()
    return {
        "files": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "format": f.format,
                "size_bytes": f.size_bytes,
                "download_url": f"/api/v1/files/{f.file_id}",
            }
            for f in files
        ],
        "total": len(files),
    }
