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
    wifi_state.send_command({"cmd": "delete-saved", "ssid": ssid})
    return {"ok": True}


@router.post("/connect", status_code=202)
def connect(req: WiFiConnectRequest) -> dict:
    wifi_state.send_command({"cmd": "connect", "ssid": req.ssid, "password": req.password or ""})
    # Fire-and-forget: in mod AP, Pi-ul opreste hotspotul ca sa comute, deci
    # raspunsul nu ar mai ajunge la telefon daca am astepta. App-ul afiseaza
    # ecranul de tranzitie si face polling de reconectare pe noua retea.
    return {"ok": True, "switching_to": req.ssid}


@router.post("/disconnect")
def disconnect() -> dict:
    wifi_state.send_command({"cmd": "disconnect"})
    return {"ok": True}


@router.post("/start-ap")
def start_ap() -> dict:
    wifi_state.send_command({"cmd": "start-ap"})
    return {"ok": True}


@router.post("/rescan")
def rescan() -> dict:
    wifi_state.send_command({"cmd": "rescan"})
    return {"ok": True}


@router.post("/ap-settings")
def ap_settings(req: APSettingsRequest) -> dict:
    wifi_state.send_command({"cmd": "set-ap", "ssid": req.ssid, "password": req.password})
    return {"ok": True}
