"""Rute sesiuni backup: listare + detalii."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from photobackup import config

from ..models import PaginatedThumbnails, SessionDetail, SessionFile, SessionSummary, ThumbnailEntry

router = APIRouter(prefix="/api/sessions")


def _sync_completed_set() -> set[str]:
    try:
        data = json.loads(config.SYNC_STATE.read_text())
        return set(data.get("completed", []))
    except (OSError, json.JSONDecodeError):
        return set()


def _load_manifest(session_dir: Path) -> dict:
    m = session_dir / "manifest.json"
    if not m.exists():
        return {}
    try:
        return json.loads(m.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _session_summary(session_dir: Path, completed: set[str]) -> SessionSummary:
    name = session_dir.name
    manifest = _load_manifest(session_dir)
    files = manifest.get("files", [])
    bytes_total = int(manifest.get("copied_bytes") or sum(f.get("size", 0) for f in files))
    # parse "YYYY-MM-DD_HH-MM-SS_label"
    parts = name.split("_", 2)
    timestamp = "_".join(parts[:2]) if len(parts) >= 2 else name
    label = parts[2] if len(parts) >= 3 else ""
    return SessionSummary(
        id=name,
        timestamp=timestamp,
        label=label,
        files_count=len(files),
        bytes_total=bytes_total,
        synced=name in completed,
        incomplete=(session_dir / ".incomplete").exists(),
    )


@router.get("", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    if not config.BACKUPS_DIR.exists():
        return []
    completed = _sync_completed_set()
    dirs = sorted(
        (p for p in config.BACKUPS_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    return [_session_summary(d, completed) for d in dirs]


@router.get("/{session_id}", response_model=SessionDetail)
def session_detail(session_id: str) -> SessionDetail:
    session_dir = config.BACKUPS_DIR / session_id
    if not session_dir.is_dir():
        raise HTTPException(404, "Sesiune inexistenta")
    completed = _sync_completed_set()
    summary = _session_summary(session_dir, completed)
    manifest = _load_manifest(session_dir)
    files = [SessionFile(**f) for f in manifest.get("files", [])]
    return SessionDetail(**summary.model_dump(), files=files)


@router.get("/{session_id}/thumbnails", response_model=PaginatedThumbnails)
def session_thumbnails(session_id: str, page: int = 1, per_page: int = 50) -> PaginatedThumbnails:
    session_dir = config.BACKUPS_DIR / session_id
    if not session_dir.is_dir():
        raise HTTPException(404, "Sesiune inexistenta")
    manifest = _load_manifest(session_dir)
    files = manifest.get("files", [])
    # filtrare imagini
    IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".cr2", ".cr3",
                 ".arw", ".nef", ".raf", ".orf", ".rw2", ".dng"}
    images = [f for f in files if Path(f["path"]).suffix.lower() in IMAGE_EXT]
    total = len(images)
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    start = (page - 1) * per_page
    chunk = images[start:start + per_page]
    items = [
        ThumbnailEntry(
            filename=f["path"],
            size=int(f.get("size", 0)),
            url=f"/api/thumbnails/{session_id}/{f['path']}",
        )
        for f in chunk
    ]
    return PaginatedThumbnails(page=page, per_page=per_page, total=total, items=items)
