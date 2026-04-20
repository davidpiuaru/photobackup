import hashlib
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from . import config, status
from .tracker import Tracker

log = logging.getLogger(__name__)

_HASH_CHUNK = 1024 * 1024
_CANCEL_FILE = Path("/tmp/photobackup-backup.control")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_HASH_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _walk_source(root: Path) -> list[tuple[Path, str, int, int]]:
    """Returneaza (abs_path, rel_path, size, mtime_int) pentru toate fisierele utile."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in config.EXCLUDED_NAMES]
        for fname in filenames:
            if fname in config.EXCLUDED_NAMES:
                continue
            abs_path = Path(dirpath) / fname
            try:
                st = abs_path.stat()
            except OSError:
                continue
            rel = str(abs_path.relative_to(root))
            result.append((abs_path, rel, st.st_size, int(st.st_mtime)))
    return result


def _cancel_requested() -> bool:
    try:
        return _CANCEL_FILE.exists() and _CANCEL_FILE.read_text().strip() == "cancel"
    except OSError:
        return False


def _clear_cancel() -> None:
    try:
        _CANCEL_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def backup_card(source: Path, label: str = "card") -> dict:
    """Copiaza fisierele noi de pe SD card pe SSD. Returneaza un sumar."""
    _clear_cancel()
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_id = f"{timestamp}_{label}"
    dest_dir = config.BACKUPS_DIR / session_id
    dest_dir.mkdir(parents=True)
    incomplete_marker = dest_dir / ".incomplete"
    incomplete_marker.touch()

    tracker = Tracker()
    all_files = _walk_source(source)
    new_files = [t for t in all_files if not tracker.is_known(t[1], t[2], t[3])]
    total_bytes = sum(t[2] for t in new_files)

    log.info(
        "Card %s: %d fisiere total, %d noi (skip %d duplicate)",
        label, len(all_files), len(new_files), len(all_files) - len(new_files),
    )

    status.update_sdcard(
        connected=True,
        label=label,
        mount_point=str(source),
    )

    if not new_files:
        log.info("Niciun fisier nou — sterg folder gol %s", dest_dir)
        shutil.rmtree(dest_dir)
        status.update_backup(
            force=True, state="idle", current_file=None,
            files_copied=0, files_total=0, bytes_copied=0, bytes_total=0,
            speed_mbps=0.0, eta_seconds=0, session_id=None, started_at=None,
        )
        status.add_notification("info", f"Card {label}: fara fisiere noi")
        return {"new_files": 0, "total_files": len(all_files), "dest": None, "ok": True}

    status.update_backup(
        force=True,
        state="copying",
        current_file=None,
        files_copied=0,
        files_total=len(new_files),
        bytes_copied=0,
        bytes_total=total_bytes,
        speed_mbps=0.0,
        eta_seconds=0,
        started_at=datetime.now().isoformat(timespec="seconds"),
        session_id=session_id,
    )

    summary = {
        "card_label": label,
        "started_at": timestamp,
        "source": str(source),
        "files": [],
    }

    copied_bytes = 0
    copied_count = 0
    errors = []
    cancelled = False

    # fereastra alunecatoare pentru calcul viteza
    window: list[tuple[float, int]] = [(time.monotonic(), 0)]

    for abs_path, rel, size, mtime in new_files:
        if _cancel_requested():
            cancelled = True
            log.warning("Backup anulat la cerere")
            break
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(abs_path, target)
            sha = _sha256(target)
            src_sha = _sha256(abs_path)
            if sha != src_sha:
                raise IOError(f"checksum mismatch: src={src_sha} dest={sha}")
            tracker.record(rel, size, mtime, sha, str(dest_dir))
            summary["files"].append({"path": rel, "size": size, "sha256": sha})
            copied_bytes += size
            copied_count += 1

            now = time.monotonic()
            window.append((now, copied_bytes))
            # pastreaza doar ultimele 3s
            while window and (now - window[0][0]) > 3.0:
                window.pop(0)
            if len(window) >= 2:
                dt = window[-1][0] - window[0][0]
                dbytes = window[-1][1] - window[0][1]
                speed_mbps = (dbytes / dt / 1024 / 1024) if dt > 0 else 0.0
            else:
                speed_mbps = 0.0
            remaining = max(total_bytes - copied_bytes, 0)
            eta = int(remaining / (speed_mbps * 1024 * 1024)) if speed_mbps > 0.1 else 0

            status.update_backup(
                current_file=rel,
                files_copied=copied_count,
                bytes_copied=copied_bytes,
                speed_mbps=round(speed_mbps, 2),
                eta_seconds=eta,
            )
        except (OSError, IOError) as e:
            log.error("Eroare la copiere %s: %s", rel, e)
            errors.append({"path": rel, "error": str(e)})

    summary["copied_bytes"] = copied_bytes
    summary["errors"] = errors
    summary["finished_at"] = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2))

    if cancelled:
        status.update_backup(force=True, state="cancelled", current_file=None, speed_mbps=0.0, eta_seconds=0)
        status.add_notification("warning", f"Backup {label} anulat ({copied_count}/{len(new_files)} fisiere)")
        _clear_cancel()
        return {"new_files": copied_count, "total_files": len(all_files),
                "dest": str(dest_dir), "ok": False, "cancelled": True}

    if errors:
        log.warning("Backup %s incheiat cu %d erori — pastrez .incomplete", dest_dir, len(errors))
        status.update_backup(force=True, state="error", current_file=None, speed_mbps=0.0, eta_seconds=0)
        status.add_notification("error", f"Backup {label}: {len(errors)} erori")
        return {"new_files": len(new_files), "total_files": len(all_files),
                "dest": str(dest_dir), "ok": False, "errors": len(errors)}

    incomplete_marker.unlink()
    tracker.save()
    log.info("Backup OK: %s (%d fisiere, %.1f MB)", dest_dir, len(new_files), copied_bytes / 1024 / 1024)
    status.update_backup(
        force=True, state="completed", current_file=None,
        files_copied=copied_count, speed_mbps=0.0, eta_seconds=0,
    )
    status.add_notification(
        "success",
        f"Backup complet: {copied_count} fisiere, {copied_bytes / 1024 / 1024:.1f} MB",
    )
    return {"new_files": len(new_files), "total_files": len(all_files),
            "dest": str(dest_dir), "ok": True, "bytes": copied_bytes}
