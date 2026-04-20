"""Rute Wi-Fi: mod curent, listare retele, connect/disconnect, AP settings."""
import logging

from fastapi import APIRouter, HTTPException

from ..models import APSettingsRequest, WiFiConnectRequest, WiFiNetwork, WiFiState
from ..services import wifi_state

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wifi")


@router.get("/mode")
def wifi_mode() -> dict:
    s = wifi_state.read_state()
    return {"mode": s.get("mode", "unknown")}


@router.get("/current", response_model=WiFiState)
def wifi_current() -> WiFiState:
    return WiFiState(**wifi_state.read_state())


@router.get("/networks", response_model=list[WiFiNetwork])
def list_networks() -> list[WiFiNetwork]:
    try:
        return [WiFiNetwork(**n) for n in wifi_state.list_networks()]
    except Exception as e:
        log.exception("list_networks esuat: %s", e)
        raise HTTPException(500, f"Scan Wi-Fi esuat: {e}")


@router.get("/saved")
def saved_networks() -> list[str]:
    return wifi_state.saved_networks()


@router.delete("/saved/{ssid}")
def delete_saved(ssid: str) -> dict:
    wifi_state.send_command(f"delete-saved:{ssid}")
    return {"ok": True}


@router.post("/connect")
def connect(req: WiFiConnectRequest) -> dict:
    pw = req.password or ""
    wifi_state.send_command(f"connect:{req.ssid}:{pw}")
    # Asteapta 20s ca wifi_manager sa actualizeze state-ul
    final = wifi_state.wait_for_state(
        lambda s: s.get("mode") == "client" and s.get("client_ssid") == req.ssid,
        timeout=30.0,
    )
    if final is None:
        raise HTTPException(504, "Conectarea nu a reusit in 30s")
    return {"ok": True, "state": final}


@router.post("/disconnect")
def disconnect() -> dict:
    wifi_state.send_command("disconnect")
    return {"ok": True}


@router.post("/start-ap")
def start_ap() -> dict:
    wifi_state.send_command("start-ap")
    return {"ok": True}


@router.post("/rescan")
def rescan() -> dict:
    wifi_state.send_command("rescan")
    return {"ok": True}


@router.post("/ap-settings")
def ap_settings(req: APSettingsRequest) -> dict:
    wifi_state.send_command(f"set-ap:{req.ssid}:{req.password}")
    return {"ok": True}
