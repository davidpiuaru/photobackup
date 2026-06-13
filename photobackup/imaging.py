"""Loader imagine partajat: RAW (rawpy), HEIC/HEIF (pillow-heif), standard (PIL).

Folosit atat de generarea de thumbnail-uri (API), cat si de scorer-ul AI (rater),
ca sa nu duplicam logica de decodare. Inregistrarea pillow-heif se face o data,
la import.
"""
import logging
from pathlib import Path

from PIL import Image, ImageOps

from . import config

log = logging.getLogger(__name__)

try:
    import rawpy  # type: ignore
    _RAW_OK = True
except ImportError:
    _RAW_OK = False
    log.warning("rawpy indisponibil — RAW-urile nu pot fi incarcate")

try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except ImportError:
    log.warning("pillow-heif indisponibil — HEIC/HEIF nu pot fi incarcate")


def is_image(path: Path) -> bool:
    return path.suffix.lower() in config.IMAGE_EXT


def raw_supported() -> bool:
    return _RAW_OK


def load_image(path: Path, half_size_raw: bool = True) -> Image.Image:
    """Incarca o imagine ca PIL.Image (orientare EXIF aplicata).

    `half_size_raw` decodeaza RAW-ul la jumatate (mai rapid — suficient pentru
    thumbnail/scoring). Ridica exceptie daca nu poate fi incarcata.
    """
    ext = path.suffix.lower()
    if ext in config.RAW_EXT:
        if not _RAW_OK:
            raise RuntimeError("rawpy indisponibil pentru fisiere RAW")
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(half_size=half_size_raw, use_camera_wb=True, no_auto_bright=False)
        return Image.fromarray(rgb)
    img = Image.open(path)
    return ImageOps.exif_transpose(img)
