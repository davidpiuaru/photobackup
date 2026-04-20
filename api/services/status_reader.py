"""Cititor cache-uit pentru /mnt/backup-ssd/status.json."""
import json
import logging
from pathlib import Path
from threading import Lock

from photobackup import config

log = logging.getLogger(__name__)

STATUS_FILE = config.SSD_MOUNT / "status.json"

_cache: dict | None = None
_cache_mtime: float = 0.0
_lock = Lock()

_EMPTY = {
    "backup": {"state": "idle", "files_copied": 0, "files_total": 0,
               "bytes_copied": 0, "bytes_total": 0, "speed_mbps": 0.0,
               "eta_seconds": 0, "current_file": None,
               "started_at": None, "session_id": None},
    "sync": {"state": "idle", "files_synced": 0, "files_total": 0,
             "bytes_synced": 0, "bytes_total": 0, "speed_mbps": 0.0,
             "eta_seconds": 0, "current_session": None},
    "sdcard": {"connected": False, "label": None, "filesystem": None,
               "size_bytes": 0, "used_bytes": 0, "mount_point": None},
    "notifications": [],
}


def read() -> dict:
    """Returneaza status.json; cache pe mtime (re-citim doar cand s-a schimbat)."""
    global _cache, _cache_mtime
    with _lock:
        if not STATUS_FILE.exists():
            return dict(_EMPTY)
        try:
            mtime = STATUS_FILE.stat().st_mtime
        except OSError:
            return _cache or dict(_EMPTY)
        if _cache is not None and mtime == _cache_mtime:
            return _cache
        try:
            _cache = json.loads(STATUS_FILE.read_text())
            _cache_mtime = mtime
        except (OSError, json.JSONDecodeError) as e:
            log.warning("Citire status.json esuata: %s", e)
            return _cache or dict(_EMPTY)
        return _cache
