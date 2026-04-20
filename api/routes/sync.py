"""Rute sync rclone: status, start, pause, resume, cancel."""
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..models import SyncState
from ..services import status_reader

router = APIRouter(prefix="/api/sync")

_CONTROL_FILE = Path("/tmp/photobackup-sync.control")


@router.get("/status", response_model=SyncState)
def sync_status() -> SyncState:
    return SyncState(**status_reader.read().get("sync", {}))


@router.post("/start")
def sync_start() -> dict:
    # Declanseaza manual timer-ul systemd (oneshot)
    r = subprocess.run(
        ["systemctl", "start", "photobackup-sync.service"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise HTTPException(500, f"systemctl failed: {r.stderr.strip()}")
    return {"ok": True}


@router.post("/pause")
def sync_pause() -> dict:
    try:
        _CONTROL_FILE.write_text("pause")
    except OSError as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.post("/resume")
def sync_resume() -> dict:
    try:
        _CONTROL_FILE.write_text("resume")
    except OSError as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.post("/cancel")
def sync_cancel() -> dict:
    try:
        _CONTROL_FILE.write_text("cancel")
    except OSError as e:
        raise HTTPException(500, str(e))
    return {"ok": True}
