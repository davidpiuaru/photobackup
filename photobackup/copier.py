import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from . import config
from .tracker import Tracker

log = logging.getLogger(__name__)

_HASH_CHUNK = 1024 * 1024


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


def backup_card(source: Path, label: str = "card") -> dict:
    """Copiaza fisierele noi de pe SD card pe SSD. Returneaza un sumar."""
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_dir = config.BACKUPS_DIR / f"{timestamp}_{label}"
    dest_dir.mkdir(parents=True)
    incomplete_marker = dest_dir / ".incomplete"
    incomplete_marker.touch()

    tracker = Tracker()
    all_files = _walk_source(source)
    new_files = [t for t in all_files if not tracker.is_known(t[1], t[2], t[3])]

    log.info(
        "Card %s: %d fisiere total, %d noi (skip %d duplicate)",
        label, len(all_files), len(new_files), len(all_files) - len(new_files),
    )

    if not new_files:
        log.info("Niciun fisier nou — sterg folder gol %s", dest_dir)
        shutil.rmtree(dest_dir)
        return {"new_files": 0, "total_files": len(all_files), "dest": None, "ok": True}

    summary = {
        "card_label": label,
        "started_at": timestamp,
        "source": str(source),
        "files": [],
    }

    copied_bytes = 0
    errors = []

    for abs_path, rel, size, mtime in new_files:
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
        except (OSError, IOError) as e:
            log.error("Eroare la copiere %s: %s", rel, e)
            errors.append({"path": rel, "error": str(e)})

    summary["copied_bytes"] = copied_bytes
    summary["errors"] = errors
    summary["finished_at"] = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2))

    if errors:
        log.warning("Backup %s incheiat cu %d erori — pastrez .incomplete", dest_dir, len(errors))
        return {"new_files": len(new_files), "total_files": len(all_files),
                "dest": str(dest_dir), "ok": False, "errors": len(errors)}

    incomplete_marker.unlink()
    tracker.save()
    log.info("Backup OK: %s (%d fisiere, %.1f MB)", dest_dir, len(new_files), copied_bytes / 1024 / 1024)
    return {"new_files": len(new_files), "total_files": len(all_files),
            "dest": str(dest_dir), "ok": True, "bytes": copied_bytes}
