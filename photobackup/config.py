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
