"""Rute rating AI: declanseaza evaluarea unei sesiuni + status progres."""
import logging
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

from photobackup import config

from ..models import RatingStatus
from ..services import status_reader
from ..services.safe_paths import safe_join, valid_session_id

log = logging.getLogger(__name__)

router = APIRouter()
# api/routes/rating.py -> repo root (pentru a porni `python -m photobackup.rater`)
_REPO_ROOT = Path(__file__).resolve().parents[2]


@router.post("/api/sessions/{session_id}/rate", status_code=202)
def rate_session(session_id: str) -> dict:
    if not valid_session_id(session_id):
        raise HTTPException(404, "Sesiune inexistenta")
    session_dir = safe_join(config.BACKUPS_DIR, session_id)
    if session_dir is None or not session_dir.is_dir():
        raise HTTPException(404, "Sesiune inexistenta")

    rating = status_reader.read().get("rating", {})
    if rating.get("state") == "rating" and rating.get("session_id") == session_id:
        raise HTTPException(409, "Evaluare deja in curs pentru aceasta sesiune")

    # Proces separat: nu blocheaza API-ul, ruleaza ca acelasi user (fara sudo).
    subprocess.Popen(
        [sys.executable, "-m", "photobackup.rater", session_id],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log.info("Evaluare pornita pentru sesiunea %s", session_id)
    return {"ok": True, "session_id": session_id}


@router.get("/api/rating/status", response_model=RatingStatus)
def rating_status() -> RatingStatus:
    return RatingStatus(**status_reader.read().get("rating", {}))
