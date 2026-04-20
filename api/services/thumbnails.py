"""Generare thumbnail-uri JPEG 300px, cache pe disk.

Suport: JPEG/PNG/HEIC (Pillow) + RAW (rawpy, daca disponibil).
Cache: /mnt/backup-ssd/.thumbnails/<session_id>/<path>.jpg
"""
import logging
from pathlib import Path

from PIL import Image, ImageOps

from photobackup import config

log = logging.getLogger(__name__)

THUMB_ROOT = config.SSD_MOUNT / ".thumbnails"
THUMB_SIZE = (300, 300)

try:
    import rawpy  # type: ignore
    _RAW_OK = True
except ImportError:
    _RAW_OK = False
    log.warning("rawpy indisponibil — RAW-urile nu vor avea thumbnail")


RAW_EXT = {".cr2", ".cr3", ".arw", ".nef", ".raf", ".orf", ".rw2", ".dng"}


def _thumb_path(session_id: str, rel_path: str) -> Path:
    return THUMB_ROOT / session_id / (rel_path + ".jpg")


def _render_raw(src: Path) -> Image.Image:
    with rawpy.imread(str(src)) as raw:  # type: ignore
        rgb = raw.postprocess(half_size=True, use_camera_wb=True, no_auto_bright=False)
    return Image.fromarray(rgb)


def _render_standard(src: Path) -> Image.Image:
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    return img


def get_or_generate(session_id: str, rel_path: str) -> Path | None:
    """Intoarce path-ul thumbnail-ului (cache sau generat). None daca nu-l poate genera."""
    thumb = _thumb_path(session_id, rel_path)
    if thumb.exists():
        return thumb

    src = config.BACKUPS_DIR / session_id / rel_path
    if not src.is_file():
        return None

    ext = src.suffix.lower()
    try:
        if ext in RAW_EXT:
            if not _RAW_OK:
                return None
            img = _render_raw(src)
        else:
            img = _render_standard(src)
    except Exception as e:
        log.warning("Generare thumbnail esuata pentru %s: %s", src, e)
        return None

    try:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(THUMB_SIZE)
        thumb.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumb, "JPEG", quality=82, optimize=True)
    except OSError as e:
        log.warning("Salvare thumbnail esuata: %s", e)
        return None
    return thumb
