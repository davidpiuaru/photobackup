"""Sincronizare backup-uri locale catre Google Drive (via rclone).

Rulat periodic de un timer systemd. Sare folderele marcate `.incomplete`
si pe cele deja sincronizate (urmarite in sync_state.json).
"""
import json
import logging
import socket
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler

from . import config

log = logging.getLogger(__name__)


def setup_logging():
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers = [
        RotatingFileHandler(
            config.LOGS_DIR / "sync.log", maxBytes=5 * 1024 * 1024, backupCount=3
        ),
        logging.StreamHandler(),
    ]
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers)


def has_internet(timeout: float = 3.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        with socket.create_connection(("1.1.1.1", 53)):
            return True
    except OSError:
        return False


def load_state() -> dict:
    if config.SYNC_STATE.exists():
        try:
            return json.loads(config.SYNC_STATE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"completed": []}


def save_state(state: dict) -> None:
    config.SYNC_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.SYNC_STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(config.SYNC_STATE)


def sync_folder(local_dir, remote_subpath: str) -> bool:
    cmd = [
        "rclone", "copy",
        str(local_dir),
        f"{config.RCLONE_REMOTE}/{remote_subpath}",
        "--transfers", "2",
        "--checkers", "4",
        "--log-level", "INFO",
    ]
    log.info("rclone: %s -> %s/%s", local_dir, config.RCLONE_REMOTE, remote_subpath)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("rclone failed: %s", result.stderr.strip())
        return False
    if result.stderr.strip():
        log.info("rclone stderr: %s", result.stderr.strip()[:500])
    return True


def main():
    setup_logging()
    if not has_internet():
        log.info("Fara internet — skip sync")
        return 0

    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    completed = set(state.get("completed", []))

    candidates = sorted(p for p in config.BACKUPS_DIR.iterdir() if p.is_dir())
    if not candidates:
        log.info("Niciun backup local — nimic de sincronizat")
        return 0

    for backup in candidates:
        if (backup / ".incomplete").exists():
            log.info("Skip %s (incomplete)", backup.name)
            continue
        if backup.name in completed:
            continue
        if sync_folder(backup, backup.name):
            completed.add(backup.name)
            state["completed"] = sorted(completed)
            state["last_sync"] = datetime.now().isoformat(timespec="seconds")
            save_state(state)
            log.info("Sync OK: %s", backup.name)
        else:
            log.warning("Sync esuat pentru %s — voi reincerca la urmatorul ciclu", backup.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
