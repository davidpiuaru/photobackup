"""Adapter intre API-ul FastAPI si wifi_manager.py."""
import json
import logging
import socket
import subprocess
import time
from pathlib import Path

from photobackup import wifi_manager


def _probe_internet(timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        return False


def _current_wifi_ssid() -> str | None:
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=5,
        )
        for line in (r.stdout or "").splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "802-11-wireless":
                return parts[0]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None

log = logging.getLogger(__name__)

STATE_FILE = Path("/tmp/wifi_state.json")
CMD_FILE = Path("/tmp/photobackup-wifi.cmd")

_DEFAULT = {
    "mode": "unknown",
    "ap_ssid": wifi_manager.DEFAULT_AP_SSID,
    "ap_password": wifi_manager.DEFAULT_AP_PASSWORD,
    "ap_ip": wifi_manager.AP_IP,
    "client_ssid": None,
    "client_ip": None,
    "has_internet": False,
    "last_change": None,
}


def read_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, json.JSONDecodeError) as e:
            log.warning("wifi_state.json invalid: %s", e)
    # Fallback cand wifi_manager nu ruleaza: detectam direct
    ssid = _current_wifi_ssid()
    state = dict(_DEFAULT)
    if ssid and ssid != wifi_manager.AP_CONN_NAME:
        state["mode"] = "client"
        state["client_ssid"] = ssid
        state["has_internet"] = _probe_internet()
    return state


def send_command(cmd: str) -> None:
    """Scrie o comanda in /tmp/photobackup-wifi.cmd (wifi_manager o consuma)."""
    try:
        CMD_FILE.write_text(cmd)
    except OSError as e:
        log.error("Trimitere comanda Wi-Fi esuata: %s", e)
        raise


def wait_for_state(predicate, timeout: float = 30.0, poll: float = 1.0) -> dict | None:
    """Polling pe /tmp/wifi_state.json pana `predicate(state)` e True."""
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        state = read_state()
        if predicate(state):
            return state
        time.sleep(poll)
    return None


def list_networks() -> list[dict]:
    """Enumerare directa (subprocess nmcli)."""
    return wifi_manager.list_networks(rescan=True)


def saved_networks() -> list[str]:
    return wifi_manager.saved_wifi_connections()
