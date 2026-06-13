"""Servire thumbnail-uri JPEG."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..services import thumbnails

router = APIRouter(prefix="/api/thumbnails")
preview_router = APIRouter(prefix="/api/preview")


@router.get("/{session_id}/{filename:path}")
def get_thumbnail(session_id: str, filename: str):
    path = thumbnails.get_or_generate(session_id, filename)
    if path is None:
        raise HTTPException(404, "Thumbnail indisponibil")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=86400"},
    )


@preview_router.get("/{session_id}/{filename:path}")
def get_preview(session_id: str, filename: str):
    path = thumbnails.get_preview(session_id, filename)
    if path is None:
        raise HTTPException(404, "Preview indisponibil")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=86400"},
    )
