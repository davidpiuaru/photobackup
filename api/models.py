"""Pydantic schemas pentru raspunsurile API."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DiskInfo(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    mounted: bool = True


class SDCardInfo(BaseModel):
    connected: bool
    label: Optional[str] = None
    filesystem: Optional[str] = None
    size_bytes: int = 0
    used_bytes: int = 0
    mount_point: Optional[str] = None


class BackupState(BaseModel):
    state: Literal["idle", "copying", "completed", "error", "cancelled"] = "idle"
    current_file: Optional[str] = None
    files_copied: int = 0
    files_total: int = 0
    bytes_copied: int = 0
    bytes_total: int = 0
    speed_mbps: float = 0.0
    eta_seconds: int = 0
    started_at: Optional[str] = None
    session_id: Optional[str] = None


class SyncState(BaseModel):
    state: Literal["idle", "syncing", "paused", "completed", "error",
                   "waiting_internet", "cancelled"] = "idle"
    files_synced: int = 0
    files_total: int = 0
    bytes_synced: int = 0
    bytes_total: int = 0
    speed_mbps: float = 0.0
    eta_seconds: int = 0
    current_session: Optional[str] = None


class WiFiState(BaseModel):
    mode: Literal["ap", "client", "unknown"] = "unknown"
    ap_ssid: str
    ap_password: str
    ap_ip: str
    client_ssid: Optional[str] = None
    client_ip: Optional[str] = None
    has_internet: bool = False
    last_change: Optional[str] = None


class SystemInfo(BaseModel):
    uptime_seconds: int
    cpu_temp_c: Optional[float] = None
    hostname: str


class DeviceStatus(BaseModel):
    backup: BackupState
    sync: SyncState
    sdcard: SDCardInfo
    ssd: DiskInfo
    wifi: WiFiState
    system: SystemInfo


class WiFiNetwork(BaseModel):
    ssid: str
    signal: int
    security: str
    in_use: bool = False


class WiFiConnectRequest(BaseModel):
    ssid: str
    password: Optional[str] = None


class APSettingsRequest(BaseModel):
    ssid: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=8, max_length=63)


class SessionFile(BaseModel):
    path: str
    size: int
    sha256: Optional[str] = None


class SessionSummary(BaseModel):
    id: str
    timestamp: str
    label: str
    files_count: int
    bytes_total: int
    synced: bool
    incomplete: bool


class SessionDetail(SessionSummary):
    files: list[SessionFile]


class ThumbnailEntry(BaseModel):
    filename: str
    url: str
    size: int


class PaginatedThumbnails(BaseModel):
    page: int
    per_page: int
    total: int
    items: list[ThumbnailEntry]


class Notification(BaseModel):
    id: int
    type: Literal["info", "success", "warning", "error"]
    message: str
    timestamp: str
