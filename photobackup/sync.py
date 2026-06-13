"""Sincronizare backup-uri locale catre Google Drive (via rclone).

Rulat periodic de un timer systemd. Sare folderele marcate `.incomplete`
si pe cele deja sincronizate (urmarite in sync_state.json).

Progres live scris in /mnt/backup-ssd/status.json (parse rclone --use-json-log).
Control externe (pause/resume/cancel) prin /tmp/photobackup-sync.control.
"""
import json
import logging
import os
import socket
import subprocess
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import config, status

log = logging.getLogger(__name__)

CONTROL_FILE = Path("/tmp/photobackup-sync.control")


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


def _read_control() -> str:
    try:
        if CONTROL_FILE.exists():
            return CONTROL_FILE.read_text().strip()
    except OSError:
        pass
    return ""


def _clear_control() -> None:
    try:
        CONTROL_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _folder_size(path: Path) -> tuple[int, int]:
    """Returneaza (numar_fisiere, total_bytes) excluzand manifest + .incomplete."""
    total = 0
    count = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f in (".incomplete", "manifest.json"):
                continue
            try:
                total += (Path(root) / f).stat().st_size
                count += 1
            except OSError:
                pass
    return count, total


def sync_folder(local_dir: Path, remote_subpath: str, session_id: str) -> bool:
    """Ruleaza rclone cu parsing progres + control pauza/cancel.

    Returneaza True daca a urcat complet, False la eroare/cancel.
    """
    files_total, bytes_total = _folder_size(local_dir)
    status.update_sync(
        force=True,
        state="syncing",
        current_session=session_id,
        files_synced=0,
        files_total=files_total,
        bytes_synced=0,
        bytes_total=bytes_total,
        speed_mbps=0.0,
        eta_seconds=0,
    )

    cmd = [
        "rclone", "copy",
        str(local_dir),
        f"{config.RCLONE_REMOTE}/{remote_subpath}",
        "--transfers", "2",
        "--checkers", "4",
        "--use-json-log",
        "--stats", "1s",
        "--stats-one-line",
        "--log-level", "INFO",
    ]
    log.info("rclone: %s -> %s/%s", local_dir, config.RCLONE_REMOTE, remote_subpath)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    paused_notified = False
    cancelled = False
    try:
        for raw_line in proc.stdout or []:
            line = raw_line.strip()
            # Control extern
            cmd_ctl = _read_control()
            if cmd_ctl == "cancel":
                cancelled = True
                log.warning("Sync anulat la cerere")
                proc.terminate()
                break
            while cmd_ctl == "pause":
                if not paused_notified:
                    status.update_sync(force=True, state="paused")
                    paused_notified = True
                time.sleep(1)
                cmd_ctl = _read_control()
                # NOTE: rclone continua sa rulaze, dar noi consideram ca e pauza.
                # pentru o pauza reala am avea nevoie de SIGSTOP/SIGCONT; evitam aici.
            if paused_notified and cmd_ctl != "pause":
                status.update_sync(force=True, state="syncing")
                paused_notified = False

            # Parse JSON log
            if not line or not line.startswith("{"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            stats = entry.get("stats") or {}
            if stats:
                transferred = int(stats.get("bytes", 0))
                speed = float(stats.get("speed", 0.0))  # bytes/sec
                eta = int(stats.get("eta") or 0)
                files_done = int(stats.get("transfers", 0))
                status.update_sync(
                    bytes_synced=transferred,
                    files_synced=files_done,
                    speed_mbps=round(speed / 1024 / 1024, 2),
                    eta_seconds=eta,
                )
    finally:
        proc.wait()

    if cancelled:
        status.update_sync(force=True, state="cancelled", speed_mbps=0.0, eta_seconds=0)
        _clear_control()
        return False

    if proc.returncode != 0:
        log.error("rclone failed (rc=%d)", proc.returncode)
        status.update_sync(force=True, state="error", speed_mbps=0.0, eta_seconds=0)
        return False

    return True


def main():
    setup_logging()
    # Curatam orice comanda de control veche (cancel/pause/resume) ramasa in /tmp
    # de la o rulare anterioara — altfel ar bloca sync-ul curent.
    _clear_control()
    if not has_internet():
        log.info("Fara internet — skip sync")
        status.update_sync(force=True, state="waiting_internet")
        return 0

    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    completed = set(state.get("completed", []))

    candidates = sorted(p for p in config.BACKUPS_DIR.iterdir() if p.is_dir())
    if not candidates:
        log.info("Niciun backup local — nimic de sincronizat")
        status.update_sync(force=True, state="idle")
        return 0

    pending = [b for b in candidates if not (b / ".incomplete").exists() and b.name not in completed]
    if not pending:
        status.update_sync(force=True, state="idle")
        log.info("Nimic de sincronizat (toate up-to-date)")
        return 0

    any_error = False
    for backup in candidates:
        if (backup / ".incomplete").exists():
            log.info("Skip %s (incomplete)", backup.name)
            continue
        if backup.name in completed:
            continue
        if _read_control() == "cancel":
            log.warning("Sync oprit la cerere externa")
            _clear_control()
            break
        if sync_folder(backup, backup.name, backup.name):
            completed.add(backup.name)
            state["completed"] = sorted(completed)
            state["last_sync"] = datetime.now().isoformat(timespec="seconds")
            save_state(state)
            log.info("Sync OK: %s", backup.name)
            status.add_notification("success", f"Sincronizat: {backup.name}")
        else:
            any_error = True
            log.warning("Sync esuat pentru %s — voi reincerca la urmatorul ciclu", backup.name)

    if not any_error:
        status.update_sync(force=True, state="idle", current_session=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
