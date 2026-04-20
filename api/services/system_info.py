"""Utilitare pentru informatii de sistem (CPU temp, uptime, disk)."""
import socket
import time
from pathlib import Path

try:
    import psutil
except ImportError:  # fallback daca psutil lipseste
    psutil = None  # type: ignore

from photobackup import config


def uptime_seconds() -> int:
    try:
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]))
    except OSError:
        return 0


def cpu_temperature() -> float | None:
    """Citeste /sys/class/thermal (specific Pi)."""
    paths = [
        Path("/sys/class/thermal/thermal_zone0/temp"),
    ]
    for p in paths:
        try:
            raw = p.read_text().strip()
            return round(int(raw) / 1000, 1)
        except (OSError, ValueError):
            continue
    return None


def hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "photobackup"


def ssd_disk_info() -> dict:
    """Returneaza {total_bytes, used_bytes, free_bytes, mounted} pentru /mnt/backup-ssd."""
    mount = config.SSD_MOUNT
    if not mount.exists():
        return {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "mounted": False}
    if psutil:
        try:
            u = psutil.disk_usage(str(mount))
            return {"total_bytes": u.total, "used_bytes": u.used,
                    "free_bytes": u.free, "mounted": True}
        except OSError:
            return {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "mounted": False}
    # fallback: os.statvfs
    import os
    try:
        st = os.statvfs(str(mount))
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return {"total_bytes": total, "used_bytes": total - free,
                "free_bytes": free, "mounted": True}
    except OSError:
        return {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "mounted": False}


def sdcard_disk_info(mount_point: str | None) -> tuple[int, int]:
    """Pentru SD card: returneaza (total_bytes, used_bytes) sau (0, 0)."""
    if not mount_point:
        return 0, 0
    import os
    try:
        st = os.statvfs(mount_point)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return total, total - free
    except OSError:
        return 0, 0


# timer de cache pentru request-uri frecvente
_cache: dict = {}
_cache_ts: float = 0.0


def cached_system_block(ttl: float = 2.0) -> dict:
    global _cache, _cache_ts
    now = time.monotonic()
    if _cache and (now - _cache_ts) < ttl:
        return _cache
    _cache = {
        "uptime_seconds": uptime_seconds(),
        "cpu_temp_c": cpu_temperature(),
        "hostname": hostname(),
    }
    _cache_ts = now
    return _cache
