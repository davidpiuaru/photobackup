"""Status writer partajat intre daemon, sync si API FastAPI.

Scrie in /mnt/backup-ssd/status.json. Fuziune non-distructiva (citim JSON-ul
existent, actualizam doar cheile date, scriem atomic cu tmp + rename).
Rate-limited la ~1/s pentru ca SSD-ul sa nu fie uzat la copieri de fisiere mici.
"""
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config

log = logging.getLogger(__name__)

STATUS_FILE = config.SSD_MOUNT / "status.json"
_MIN_INTERVAL = 1.0  # secunde intre flush-uri

_lock = threading.Lock()
_cache: dict[str, Any] = {}
_last_flush: float = 0.0
_dirty = False

_DEFAULT: dict[str, Any] = {
    "backup": {
        "state": "idle",
        "current_file": None,
        "files_copied": 0,
        "files_total": 0,
        "bytes_copied": 0,
        "bytes_total": 0,
        "speed_mbps": 0.0,
        "eta_seconds": 0,
        "started_at": None,
        "session_id": None,
    },
    "sync": {
        "state": "idle",
        "files_synced": 0,
        "files_total": 0,
        "bytes_synced": 0,
        "bytes_total": 0,
        "speed_mbps": 0.0,
        "current_session": None,
        "eta_seconds": 0,
    },
    "sdcard": {
        "connected": False,
        "label": None,
        "filesystem": None,
        "size_bytes": 0,
        "used_bytes": 0,
        "mount_point": None,
    },
    "notifications": [],
}


def _ensure_loaded() -> None:
    global _cache
    if _cache:
        return
    if STATUS_FILE.exists():
        try:
            _cache = json.loads(STATUS_FILE.read_text())
        except (OSError, json.JSONDecodeError) as e:
            log.warning("status.json corupt (%s) — reinit", e)
            _cache = {}
    for key, default in _DEFAULT.items():
        if key not in _cache:
            _cache[key] = dict(default) if isinstance(default, dict) else list(default)


def _flush_locked(force: bool = False) -> None:
    global _last_flush, _dirty
    if not _dirty:
        return
    now = time.monotonic()
    if not force and (now - _last_flush) < _MIN_INTERVAL:
        return
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATUS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_cache, indent=2))
        tmp.replace(STATUS_FILE)
        _last_flush = now
        _dirty = False
    except OSError as e:
        log.warning("flush status.json esuat: %s", e)


def _patch(section: str, fields: dict[str, Any], force: bool) -> None:
    global _dirty
    with _lock:
        _ensure_loaded()
        _cache.setdefault(section, {}).update({k: v for k, v in fields.items() if v is not None or k in _cache[section]})
        _dirty = True
        _flush_locked(force=force)


def update_backup(force: bool = False, **fields: Any) -> None:
    _patch("backup", fields, force)


def update_sync(force: bool = False, **fields: Any) -> None:
    _patch("sync", fields, force)


def update_sdcard(force: bool = True, **fields: Any) -> None:
    _patch("sdcard", fields, force)


def add_notification(type_: str, message: str, force: bool = True) -> None:
    global _dirty
    with _lock:
        _ensure_loaded()
        notif = {
            "id": int(time.time() * 1000),
            "type": type_,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        notifs: list = _cache.setdefault("notifications", [])
        notifs.append(notif)
        # pastreaza ultimele 50
        if len(notifs) > 50:
            del notifs[: len(notifs) - 50]
        _dirty = True
        _flush_locked(force=force)


def flush() -> None:
    with _lock:
        _flush_locked(force=True)


def read_snapshot() -> dict[str, Any]:
    """Citeste direct fisierul (folosit de API-ul FastAPI din alt proces)."""
    if not STATUS_FILE.exists():
        return dict(_DEFAULT)
    try:
        return json.loads(STATUS_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT)
