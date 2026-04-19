import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class MountError(Exception):
    pass


def mount(device: str) -> Path:
    """Monteaza partitia prin udisksctl si returneaza mount point-ul."""
    result = subprocess.run(
        ["udisksctl", "mount", "-b", device, "--no-user-interaction"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "already mounted" in result.stderr.lower():
            return _find_mountpoint(device)
        raise MountError(f"udisksctl mount esuat: {result.stderr.strip()}")

    # Output tipic: "Mounted /dev/sda1 at /media/admin/UNTITLED."
    line = result.stdout.strip()
    if " at " in line:
        mp = line.split(" at ", 1)[1].rstrip(".")
        return Path(mp)
    return _find_mountpoint(device)


def unmount(device: str) -> None:
    result = subprocess.run(
        ["udisksctl", "unmount", "-b", device, "--no-user-interaction"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "not mounted" not in result.stderr.lower():
        log.warning("udisksctl unmount esuat pentru %s: %s", device, result.stderr.strip())


def _find_mountpoint(device: str) -> Path:
    with open("/proc/mounts") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == device:
                return Path(parts[1])
    raise MountError(f"Nu gasesc mount point pentru {device}")
