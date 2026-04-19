import json
import logging
from pathlib import Path
from typing import Iterable

from . import config

log = logging.getLogger(__name__)


def _key(rel_path: str, size: int, mtime: int) -> str:
    return f"{rel_path}|{size}|{mtime}"


class Tracker:
    """Manifest global de fișiere copiate, pentru deduplicare între insertii SD."""

    def __init__(self, manifest_path: Path = config.GLOBAL_MANIFEST):
        self.path = manifest_path
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            self._entries = {}
            return
        try:
            data = json.loads(self.path.read_text())
            self._entries = data.get("entries", {})
        except (json.JSONDecodeError, OSError) as e:
            log.error("Manifest corupt (%s) — incep cu unul gol", e)
            self._entries = {}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"entries": self._entries}, indent=2))
        tmp.replace(self.path)

    def is_known(self, rel_path: str, size: int, mtime: int) -> bool:
        return _key(rel_path, size, mtime) in self._entries

    def record(self, rel_path: str, size: int, mtime: int, sha256: str, backup_dir: str):
        self._entries[_key(rel_path, size, mtime)] = {
            "sha256": sha256,
            "backup_dir": backup_dir,
            "size": size,
            "mtime": mtime,
        }

    def filter_new(self, files: Iterable[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
        return [f for f in files if not self.is_known(*f)]
