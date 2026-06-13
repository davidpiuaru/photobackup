"""Evaluare AI a unei sesiuni de backup: scor 1-5 stele in metadata pozelor.

Rulat ca proces separat, declansat manual de API:
    python -m photobackup.rater <session_id>

Citeste/scrie DOAR copiile de pe SSD (detinute de `admin`) — fara sudo, fara
implicarea cardului SD. Scorul se scrie:
  - JPEG/PNG/HEIC: incorporat (XMP:Rating + EXIF:Rating) cu exiftool
  - RAW (CR3/ARW/NEF/…): sidecar .xmp (standard Adobe, nedistructiv)
  - manifest.json: camp `rating` per fisier (pentru API/iOS)
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import config, imaging, status
from .scoring import Scorer

log = logging.getLogger("photobackup.rater")

_exiftool_missing = False


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(
            config.LOGS_DIR / "rating.log", maxBytes=2 * 1024 * 1024, backupCount=3))
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def _load_manifest(session_dir: Path) -> dict | None:
    m = session_dir / "manifest.json"
    try:
        return json.loads(m.read_text())
    except (OSError, json.JSONDecodeError) as e:
        log.error("manifest.json invalid pentru %s: %s", session_dir.name, e)
        return None


def _save_manifest(session_dir: Path, manifest: dict) -> None:
    m = session_dir / "manifest.json"
    tmp = m.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(m)


def _write_metadata_rating(path: Path, stars: int) -> bool:
    """Scrie rating-ul cu exiftool. RAW -> sidecar .xmp; restul -> incorporat."""
    global _exiftool_missing
    if _exiftool_missing:
        return False
    ext = path.suffix.lower()
    if ext in config.RAW_EXT:
        sidecar = path.with_suffix(".xmp")
        if sidecar.exists():
            cmd = ["exiftool", "-overwrite_original", f"-XMP:Rating={stars}", str(sidecar)]
        else:
            cmd = ["exiftool", f"-XMP:Rating={stars}", "-o", str(sidecar), str(path)]
    else:
        cmd = ["exiftool", "-overwrite_original",
               f"-XMP:Rating={stars}", f"-EXIF:Rating={stars}", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        _exiftool_missing = True
        log.warning("exiftool indisponibil — scriu rating-ul doar in manifest")
        return False
    except subprocess.TimeoutExpired:
        log.warning("exiftool timeout pentru %s", path.name)
        return False
    if r.returncode != 0:
        log.warning("exiftool esuat pentru %s: %s", path.name, r.stderr.strip())
        return False
    return True


def _unmark_synced(session_id: str) -> None:
    """Scoate sesiunea din `completed` ca sync-ul sa reurce fisierele cu rating."""
    try:
        if not config.SYNC_STATE.exists():
            return
        state = json.loads(config.SYNC_STATE.read_text())
        completed = state.get("completed", [])
        if session_id in completed:
            state["completed"] = [c for c in completed if c != session_id]
            tmp = config.SYNC_STATE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(state, indent=2))
            tmp.replace(config.SYNC_STATE)
            log.info("Sesiune %s remarcata pentru re-sync (rating actualizat)", session_id)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Nu am putut remarca sesiunea pentru re-sync: %s", e)


def rate_session(session_id: str) -> int:
    session_dir = config.BACKUPS_DIR / session_id
    if not session_dir.is_dir():
        log.error("Sesiune inexistenta: %s", session_id)
        return 1

    lock = session_dir / config.RATING_LOCK_NAME
    if lock.exists() and (time.time() - lock.stat().st_mtime) < 7200:
        log.warning("Rating deja in curs pentru %s — ies", session_id)
        return 1

    manifest = _load_manifest(session_dir)
    if manifest is None:
        return 1
    files = manifest.get("files", [])
    images = [f for f in files if Path(f["path"]).suffix.lower() in config.IMAGE_EXT]
    if not images:
        log.info("Nicio imagine de evaluat in %s", session_id)
        status.update_rating(force=True, state="completed", session_id=session_id,
                             files_total=0, files_done=0)
        return 0

    try:
        lock.write_text(str(os.getpid()))
    except OSError as e:
        log.error("Nu pot crea lock-ul de rating: %s", e)
        return 1

    scorer = Scorer()
    log.info("Evaluez %s: %d imagini (metoda=%s)", session_id, len(images), scorer.method)
    status.update_rating(force=True, state="rating", session_id=session_id,
                         files_total=len(images), files_done=0, current_file=None,
                         method=scorer.method,
                         started_at=datetime.now().isoformat(timespec="seconds"))

    by_path = {f["path"]: f for f in files}
    done = 0
    errors = 0
    try:
        for entry in images:
            rel = entry["path"]
            src = session_dir / rel
            status.update_rating(current_file=rel, files_done=done)
            try:
                image = imaging.load_image(src, half_size_raw=True)
                stars, raw_score, method = scorer.score(image)
            except Exception as e:
                log.warning("Scor esuat pentru %s: %s", rel, e)
                errors += 1
                done += 1
                continue
            _write_metadata_rating(src, stars)
            tgt = by_path.get(rel, entry)
            tgt["rating"] = stars
            tgt["rating_score"] = round(float(raw_score), 2)
            tgt["rating_method"] = method
            done += 1

        manifest["rated_at"] = datetime.now().isoformat(timespec="seconds")
        _save_manifest(session_dir, manifest)
        _unmark_synced(session_id)

        status.update_rating(force=True, state="completed", current_file=None,
                             files_done=done, files_total=len(images))
        msg = f"Evaluare completa: {done} poze ({scorer.method})"
        if errors:
            msg += f", {errors} esuate"
        status.add_notification("success", msg)
        log.info(msg)
        return 0
    except Exception as e:
        log.exception("Eroare evaluare %s: %s", session_id, e)
        status.update_rating(force=True, state="error", current_file=None)
        status.add_notification("error", f"Evaluare esuata pentru {session_id}")
        return 1
    finally:
        lock.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m photobackup.rater <session_id>", file=sys.stderr)
        return 2
    return rate_session(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
