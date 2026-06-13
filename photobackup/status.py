"""Status writer partajat intre daemon, sync si API FastAPI.

Scrie in /mnt/backup-ssd/status.json. Fiecare proces (daemon, sync) e
"proprietarul" doar al sectiunilor pe care le scrie; la fiecare flush facem un
read-modify-write real: recitim fisierul de pe disc, aplicam doar campurile
schimbate de noi, scriem atomic (tmp + rename). Pentru a evita lost-update-uri
intre procese, intregul read-modify-write e serializat printr-un lock de fisier
advisory (`fcntl.flock`) pe `.status.lock`.

Rate-limited la ~1/s pentru ca SSD-ul sa nu fie uzat la copieri de fisiere mici;
modificarile se acumuleaza in `_pending` si se scriu impreuna la urmatorul flush.
"""
import fcntl
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
LOCK_FILE = config.SSD_MOUNT / ".status.lock"
_MIN_INTERVAL = 1.0  # secunde intre flush-uri
_MAX_NOTIFS = 50

_lock = threading.Lock()
# Modificari acumulate, neflush-uite inca: sectiune -> {camp: valoare}.
_pending: dict[str, dict[str, Any]] = {}
_pending_notifs: list[dict[str, Any]] = []
_last_flush: float = 0.0

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
    "rating": {
        "state": "idle",
        "session_id": None,
        "current_file": None,
        "files_done": 0,
        "files_total": 0,
        "method": None,
        "started_at": None,
    },
    "notifications": [],
}


def _with_defaults(data: dict[str, Any]) -> dict[str, Any]:
    for key, default in _DEFAULT.items():
        if key not in data:
            data[key] = dict(default) if isinstance(default, dict) else list(default)
    return data


def _read_disk() -> dict[str, Any]:
    """Citeste status.json de pe disc (fara lock — apelat in interiorul lock-ului)."""
    try:
        data = json.loads(STATUS_FILE.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}
    return _with_defaults(data)


def _flush_locked(force: bool = False) -> None:
    """Read-modify-write serializat inter-proces. Presupune _lock detinut."""
    global _last_flush, _pending, _pending_notifs
    if not _pending and not _pending_notifs:
        return
    now = time.monotonic()
    if not force and (now - _last_flush) < _MIN_INTERVAL:
        return
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, "w") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                disk = _read_disk()
                for section, fields in _pending.items():
                    disk.setdefault(section, {}).update(fields)
                if _pending_notifs:
                    notifs = disk.setdefault("notifications", [])
                    notifs.extend(_pending_notifs)
                    if len(notifs) > _MAX_NOTIFS:
                        del notifs[: len(notifs) - _MAX_NOTIFS]
                tmp = STATUS_FILE.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(disk, indent=2))
                tmp.replace(STATUS_FILE)
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)
        _pending = {}
        _pending_notifs = []
        _last_flush = now
    except OSError as e:
        log.warning("flush status.json esuat: %s", e)


def _patch(section: str, fields: dict[str, Any], force: bool) -> None:
    with _lock:
        _pending.setdefault(section, {}).update(fields)
        _flush_locked(force=force)


def update_backup(force: bool = False, **fields: Any) -> None:
    _patch("backup", fields, force)


def update_sync(force: bool = False, **fields: Any) -> None:
    _patch("sync", fields, force)


def update_sdcard(force: bool = True, **fields: Any) -> None:
    _patch("sdcard", fields, force)


def update_rating(force: bool = False, **fields: Any) -> None:
    _patch("rating", fields, force)


def add_notification(type_: str, message: str, force: bool = True) -> None:
    notif = {
        "id": int(time.time() * 1000),
        "type": type_,
        "message": message,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    with _lock:
        _pending_notifs.append(notif)
        _flush_locked(force=force)


def flush() -> None:
    with _lock:
        _flush_locked(force=True)


def read_snapshot() -> dict[str, Any]:
    """Citeste direct fisierul (folosit de API-ul FastAPI din alt proces)."""
    if not STATUS_FILE.exists():
        return _with_defaults({})
    try:
        data = json.loads(STATUS_FILE.read_text())
        return _with_defaults(data if isinstance(data, dict) else {})
    except (OSError, json.JSONDecodeError):
        return _with_defaults({})
