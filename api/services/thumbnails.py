"""Generare thumbnail-uri / preview-uri JPEG, cache pe disk.

Suport: JPEG/PNG/HEIC (Pillow + pillow-heif) + RAW (rawpy, daca disponibil) —
decodarea e in `photobackup.imaging` (partajata cu scorer-ul AI).
Cache thumbnail (300px): /mnt/backup-ssd/.thumbnails/<session_id>/<path>.jpg
Cache preview  (1600px): /mnt/backup-ssd/.previews/<session_id>/<path>.jpg
"""
import logging
from pathlib import Path

from photobackup import config, imaging

from .safe_paths import safe_join

log = logging.getLogger(__name__)

THUMB_ROOT = config.SSD_MOUNT / ".thumbnails"
PREVIEW_ROOT = config.SSD_MOUNT / ".previews"
THUMB_SIZE = (300, 300)
PREVIEW_SIZE = (1600, 1600)


def _get_or_generate(session_id: str, rel_path: str, root: Path, size: tuple[int, int]) -> Path | None:
    """Intoarce calea imaginii cache-uite (sau o genereaza). None daca nu se poate."""
    # Validare anti path-traversal: ambele cai trebuie sa ramana in directoarele lor.
    src = safe_join(config.BACKUPS_DIR, session_id, rel_path)
    out = safe_join(root, session_id, rel_path + ".jpg")
    if src is None or out is None:
        log.warning("Cale imagine respinsa (traversal?): %s / %s", session_id, rel_path)
        return None

    if out.exists():
        return out

    if not src.is_file():
        return None

    try:
        img = imaging.load_image(src, half_size_raw=True)
    except Exception as e:
        log.warning("Randare imagine esuata pentru %s: %s", src, e)
        return None

    try:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(size)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, "JPEG", quality=85, optimize=True)
    except OSError as e:
        log.warning("Salvare imagine esuata: %s", e)
        return None
    return out


def get_or_generate(session_id: str, rel_path: str) -> Path | None:
    """Thumbnail 300px (grid galerie)."""
    return _get_or_generate(session_id, rel_path, THUMB_ROOT, THUMB_SIZE)


def get_preview(session_id: str, rel_path: str) -> Path | None:
    """Preview 1600px (vizualizare full-screen cu zoom)."""
    return _get_or_generate(session_id, rel_path, PREVIEW_ROOT, PREVIEW_SIZE)
