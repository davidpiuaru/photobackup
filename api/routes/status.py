"""GET /api/status + /api/storage/*."""
from fastapi import APIRouter

from ..models import (
    BackupState,
    DeviceStatus,
    DiskInfo,
    SDCardInfo,
    SyncState,
    SystemInfo,
    WiFiState,
)
from ..services import status_reader, system_info, wifi_state

router = APIRouter()


@router.get("/api/status", response_model=DeviceStatus)
def full_status() -> DeviceStatus:
    snap = status_reader.read()
    sdcard_raw = snap.get("sdcard", {})
    if sdcard_raw.get("connected") and sdcard_raw.get("mount_point"):
        total, used = system_info.sdcard_disk_info(sdcard_raw["mount_point"])
        sdcard_raw = {**sdcard_raw, "size_bytes": total, "used_bytes": used}

    wifi_raw = wifi_state.read_state()

    return DeviceStatus(
        backup=BackupState(**snap.get("backup", {})),
        sync=SyncState(**snap.get("sync", {})),
        sdcard=SDCardInfo(**sdcard_raw),
        ssd=DiskInfo(**system_info.ssd_disk_info()),
        wifi=WiFiState(**wifi_raw),
        system=SystemInfo(**system_info.cached_system_block()),
    )


@router.get("/api/storage/ssd", response_model=DiskInfo)
def ssd_info() -> DiskInfo:
    return DiskInfo(**system_info.ssd_disk_info())


@router.get("/api/storage/sdcard", response_model=SDCardInfo)
def sdcard_info() -> SDCardInfo:
    snap = status_reader.read()
    data = snap.get("sdcard", {})
    if data.get("connected") and data.get("mount_point"):
        total, used = system_info.sdcard_disk_info(data["mount_point"])
        data = {**data, "size_bytes": total, "used_bytes": used}
    return SDCardInfo(**data)
