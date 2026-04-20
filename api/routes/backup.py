"""Rute backup: status + cancel."""
from pathlib import Path

from fastapi import APIRouter

from ..models import BackupState
from ..services import status_reader

router = APIRouter(prefix="/api/backup")

_CANCEL_FILE = Path("/tmp/photobackup-backup.control")


@router.get("/status", response_model=BackupState)
def backup_status() -> BackupState:
    return BackupState(**status_reader.read().get("backup", {}))


@router.post("/cancel")
def backup_cancel() -> dict:
    try:
        _CANCEL_FILE.write_text("cancel")
    except OSError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}
