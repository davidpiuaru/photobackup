from pathlib import Path

SSD_MOUNT = Path("/mnt/backup-ssd")
BACKUPS_DIR = SSD_MOUNT / "backups"
LOGS_DIR = SSD_MOUNT / "logs"
SYNC_QUEUE_DIR = SSD_MOUNT / "sync_queue"
GLOBAL_MANIFEST = SYNC_QUEUE_DIR / "global_manifest.json"
SYNC_STATE = SYNC_QUEUE_DIR / "sync_state.json"
LOG_FILE = LOGS_DIR / "photobackup.log"

SSD_LABEL = "BACKUP_SSD"

SD_READER_VENDOR_ID = "05e3"
SD_READER_MODEL_ID = "0764"

LED_GREEN_PIN = 17
LED_RED_PIN = 27

RCLONE_REMOTE = "gdrive:PhotoBackup"

# ──────────────────────── rating AI (1-5 stele) ────────────────────────
# Extensii de imagine recunoscute (pentru galerie + rating).
RAW_EXT = {".cr2", ".cr3", ".arw", ".nef", ".raf", ".orf", ".rw2", ".dng"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif"} | RAW_EXT

# Model NIMA (ONNX) — pus manual pe Pi (vezi models/README.md). Daca lipseste,
# scorer-ul cade pe euristica.
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
NIMA_MODEL = MODELS_DIR / "nima.onnx"

# Mapare scor mediu NIMA (1-10) -> stele: <4.0=1, <4.75=2, <5.25=3, <5.75=4, else 5.
RATING_THRESHOLDS = [4.0, 4.75, 5.25, 5.75]

# Marker de lock per-sesiune cat ruleaza evaluarea (anti-dublare).
RATING_LOCK_NAME = ".rating.lock"

EXCLUDED_NAMES = {
    "System Volume Information",
    "$RECYCLE.BIN",
    ".Spotlight-V100",
    ".fseventsd",
    ".Trashes",
    ".TemporaryItems",
    ".bzvol",
    ".DS_Store",
    "Thumbs.db",
}
