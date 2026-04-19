import logging
import re
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

MEDIA_ROOT = Path("/media/photobackup")
_SANITIZE = re.compile(r"[^A-Za-z0-9._-]+")


class MountError(Exception):
    pass


def _label_for_device(device: str) -> str:
    result = subprocess.run(
        ["lsblk", "-no", "LABEL", device],
        capture_output=True, text=True,
    )
    label = result.stdout.strip() or "UNLABELED"
    return _SANITIZE.sub("_", label) or "UNLABELED"


def _existing_mountpoint(device: str) -> Path | None:
    with open("/proc/mounts") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == device:
                return Path(parts[1].replace(r"\040", " "))
    return None


def mount(device: str) -> Path:
    """Monteaza partitia sub /media/photobackup/<LABEL>. Idempotent."""
    existing = _existing_mountpoint(device)
    if existing:
        log.info("%s deja montat la %s", device, existing)
        return existing

    label = _label_for_device(device)
    target = MEDIA_ROOT / label
    subprocess.run(["sudo", "mkdir", "-p", str(target)], check=True)

    uid = subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip()
    gid = subprocess.run(["id", "-g"], capture_output=True, text=True).stdout.strip()
    options = f"ro,uid={uid},gid={gid},umask=022"

    result = subprocess.run(
        ["sudo", "mount", "-o", options, device, str(target)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # exfat/ntfs uneori nu accepta uid/gid prin mount generic — incearca fara optiuni
        result = subprocess.run(
            ["sudo", "mount", "-o", "ro", device, str(target)],
            capture_output=True, text=True,
        )
    if result.returncode != 0:
        raise MountError(f"mount esuat pentru {device}: {result.stderr.strip()}")

    log.info("Montat %s la %s", device, target)
    return target


def unmount(device: str) -> None:
    if not _existing_mountpoint(device):
        return
    result = subprocess.run(
        ["sudo", "umount", device],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # fortam daca nu se demonteaza clean
        result = subprocess.run(
            ["sudo", "umount", "-l", device],
            capture_output=True, text=True,
        )
    if result.returncode != 0:
        log.warning("umount esuat pentru %s: %s", device, result.stderr.strip())
    else:
        log.info("Demontat %s", device)
