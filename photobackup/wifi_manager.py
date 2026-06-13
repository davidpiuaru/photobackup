"""Wi-Fi manager — comutare automata AP (hotspot) <-> Client.

Foloseste NetworkManager (`nmcli`) exclusiv. Niciun hostapd/dnsmasq separat.

La boot:
  1. Daca vreo conexiune salvata e in range sau se poate conecta => mod client.
  2. Altfel (dupa timeout) => activeaza hotspot-ul `PhotoBackup-AP`.

Monitorizare continua:
  - Mod client: daca se pierde conexiunea > 60s => revine la AP.
  - Mod AP: asculta comenzi din /tmp/photobackup-wifi.cmd (scris de API).

Comenzi suportate (coada de fisiere JSON in /tmp/photobackup-wifi.cmd.d/,
fiecare {"cmd": ...}):
  {"cmd":"connect","ssid":..,"password":..}  -> opreste AP, conecteaza client
  {"cmd":"disconnect"}                       -> deconecteaza client, revine la AP
  {"cmd":"start-ap"}                         -> forteaza pornirea AP
  {"cmd":"rescan"}                           -> rescan Wi-Fi (util pentru API)
  {"cmd":"set-ap","ssid":..,"password":..}   -> modifica setari AP (persistent)
  {"cmd":"delete-saved","ssid":..}           -> sterge o retea salvata

State publicat in /tmp/wifi_state.json:
  {"mode":"ap"|"client", "ap_ssid":..., "ap_password":..., "ap_ip":...,
   "client_ssid":..., "client_ip":..., "has_internet":bool, "last_change":...}
"""
import json
import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

log = logging.getLogger("wifi_manager")

WLAN_IFACE = "wlan0"
AP_CONN_NAME = "PhotoBackup-AP"
AP_IP = "10.42.0.1"
DEFAULT_AP_SSID = "PhotoBackup-AP"
DEFAULT_AP_PASSWORD = "photobackup123"

STATE_FILE = Path("/tmp/wifi_state.json")
CMD_DIR = Path("/tmp/photobackup-wifi.cmd.d")
CONFIG_DIR = Path("/etc/photobackup")
CONFIG_FILE = CONFIG_DIR / "wifi.conf"
LOG_FILE = Path("/var/log/photobackup-wifi.log")

CLIENT_BOOT_TIMEOUT = 30  # secunde
CLIENT_LOST_TIMEOUT = 180  # secunde (3 min — toleram DHCP hiccups)
# Daca nu exista nicio retea salvata, nu pornim niciodata AP automat
# (user-ul nu ne-a dat credentiale — AP e sensul cand avem dar n-ajunge)
REQUIRE_SAVED_FOR_AUTO_AP = True


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3))
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


# ──────────────────────── config AP ────────────────────────


def load_ap_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (OSError, json.JSONDecodeError) as e:
            log.warning("wifi.conf corupt (%s) — folosesc default", e)
    return {"ap_ssid": DEFAULT_AP_SSID, "ap_password": DEFAULT_AP_PASSWORD}


def save_ap_config(cfg: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    except OSError as e:
        log.error("Salvare wifi.conf esuata: %s", e)


# ──────────────────────── nmcli helpers ────────────────────────


def _nmcli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = ["nmcli", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def has_internet(timeout: float = 3.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        with socket.create_connection(("1.1.1.1", 53)):
            return True
    except OSError:
        return False


def saved_wifi_connections() -> list[str]:
    """Lista SSID-uri Wi-Fi salvate (excluzand AP_CONN_NAME)."""
    r = _nmcli("-t", "-f", "NAME,TYPE", "connection", "show")
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "802-11-wireless" and parts[0] != AP_CONN_NAME:
            out.append(parts[0])
    return out


def visible_ssids(rescan: bool = True) -> list[str]:
    if rescan:
        _nmcli("device", "wifi", "rescan", "ifname", WLAN_IFACE, timeout=15)
        time.sleep(2)
    r = _nmcli("-t", "-f", "SSID", "device", "wifi", "list", "ifname", WLAN_IFACE)
    if r.returncode != 0:
        return []
    return [line for line in r.stdout.splitlines() if line]


def list_networks(rescan: bool = True) -> list[dict]:
    """Lista completa retele Wi-Fi vizibile (pentru API)."""
    if rescan:
        _nmcli("device", "wifi", "rescan", "ifname", WLAN_IFACE, timeout=15)
        time.sleep(2)
    r = _nmcli("-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi",
               "list", "ifname", WLAN_IFACE)
    if r.returncode != 0:
        return []
    seen: dict[str, dict] = {}
    for line in r.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue
        ssid, signal, sec, in_use = parts[0], parts[1], parts[2], parts[3]
        if not ssid:
            continue
        try:
            signal_int = int(signal)
        except ValueError:
            signal_int = 0
        # pastreaza cea mai puternica per SSID
        if ssid not in seen or signal_int > seen[ssid]["signal"]:
            seen[ssid] = {
                "ssid": ssid,
                "signal": signal_int,
                "security": sec or "OPEN",
                "in_use": in_use == "*",
            }
    return sorted(seen.values(), key=lambda x: -x["signal"])


def current_client_state() -> tuple[str | None, str | None]:
    """Returneaza (ssid, ipv4) daca suntem in mod client, altfel (None, None)."""
    r = _nmcli("-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active")
    if r.returncode != 0:
        return None, None
    active_wifi = None
    for line in r.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "802-11-wireless" and parts[2] == WLAN_IFACE:
            if parts[0] != AP_CONN_NAME:
                active_wifi = parts[0]
                break
    if not active_wifi:
        return None, None
    ip = _iface_ipv4(WLAN_IFACE)
    return active_wifi, ip


def _iface_ipv4(iface: str) -> str | None:
    r = _nmcli("-t", "-f", "IP4.ADDRESS", "device", "show", iface)
    if r.returncode != 0:
        return None
    for line in r.stdout.splitlines():
        if line.startswith("IP4.ADDRESS"):
            _, _, val = line.partition(":")
            ip = val.split("/")[0].strip()
            if ip:
                return ip
    return None


def ap_active() -> bool:
    r = _nmcli("-t", "-f", "NAME", "connection", "show", "--active")
    return AP_CONN_NAME in (r.stdout or "").splitlines()


def start_ap(ssid: str, password: str) -> bool:
    log.info("Pornire hotspot: %s", ssid)
    # Sterge conexiunea veche daca exista (ca sa actualizam SSID/password)
    _nmcli("connection", "delete", AP_CONN_NAME, timeout=10)
    r = _nmcli(
        "device", "wifi", "hotspot",
        "ifname", WLAN_IFACE,
        "con-name", AP_CONN_NAME,
        "ssid", ssid,
        "password", password,
        timeout=30,
    )
    if r.returncode != 0:
        log.error("start_ap esuat: %s", r.stderr.strip())
        return False
    # Asiguram IP-ul static (NM gestioneaza DHCP pentru clienti automat in shared mode)
    _nmcli("connection", "modify", AP_CONN_NAME,
           "ipv4.addresses", f"{AP_IP}/24", "ipv4.method", "shared")
    _nmcli("connection", "up", AP_CONN_NAME, timeout=15)
    log.info("Hotspot activ: SSID=%s IP=%s", ssid, AP_IP)
    return True


def stop_ap() -> None:
    if not ap_active():
        return
    log.info("Oprire hotspot")
    _nmcli("connection", "down", AP_CONN_NAME, timeout=10)


def connect_client(ssid: str, password: str | None) -> bool:
    log.info("Incercare conectare client: %s", ssid)
    stop_ap()
    args = ["device", "wifi", "connect", ssid, "ifname", WLAN_IFACE]
    if password:
        args.extend(["password", password])
    r = _nmcli(*args, timeout=45)
    if r.returncode != 0:
        log.error("connect_client(%s) esuat: %s", ssid, r.stderr.strip())
        return False
    # Asteapta IP
    for _ in range(15):
        if _iface_ipv4(WLAN_IFACE):
            log.info("Conectat client: %s", ssid)
            return True
        time.sleep(1)
    return False


def disconnect_client() -> None:
    ssid, _ = current_client_state()
    if ssid:
        log.info("Deconectare client: %s", ssid)
        _nmcli("connection", "down", ssid, timeout=10)


def delete_saved(ssid: str) -> bool:
    r = _nmcli("connection", "delete", ssid, timeout=10)
    return r.returncode == 0


def try_autoconnect_client(timeout: int) -> bool:
    """Incearca sa se conecteze la orice retea cunoscuta care e in range."""
    saved = set(saved_wifi_connections())
    if not saved:
        log.info("Nu exista retele Wi-Fi salvate")
        return False
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        visible = set(visible_ssids(rescan=True))
        match = saved & visible
        if match:
            for ssid in match:
                r = _nmcli("connection", "up", ssid, timeout=30)
                if r.returncode == 0:
                    log.info("Conectat auto la %s", ssid)
                    # asteapta IP
                    for _ in range(10):
                        if _iface_ipv4(WLAN_IFACE):
                            return True
                        time.sleep(1)
                else:
                    log.warning("autoconnect %s esuat: %s", ssid, r.stderr.strip())
        time.sleep(2)
    return False


# ──────────────────────── state + commands ────────────────────────


def write_state(mode: str, ap_ssid: str, ap_password: str,
                client_ssid: str | None, client_ip: str | None,
                internet: bool) -> None:
    data = {
        "mode": mode,
        "ap_ssid": ap_ssid,
        "ap_password": ap_password,
        "ap_ip": AP_IP,
        "client_ssid": client_ssid,
        "client_ip": client_ip,
        "has_internet": internet,
        "last_change": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        tmp = STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(STATE_FILE)
    except OSError as e:
        log.warning("write_state esuat: %s", e)


def consume_command() -> dict | None:
    """Scoate cea mai veche comanda din coada (un fisier JSON per comanda)."""
    try:
        if not CMD_DIR.is_dir():
            return None
        files = sorted(f for f in CMD_DIR.iterdir() if f.suffix == ".json")
        if not files:
            return None
        path = files[0]
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            data = None
        path.unlink(missing_ok=True)
        return data if isinstance(data, dict) else None
    except OSError:
        return None


# ──────────────────────── main loop ────────────────────────


def main() -> int:
    setup_logging()
    ap_cfg = load_ap_config()
    ap_ssid = ap_cfg["ap_ssid"]
    ap_password = ap_cfg["ap_password"]

    log.info("wifi_manager pornit (iface=%s AP=%s)", WLAN_IFACE, ap_ssid)

    # 0) Daca NetworkManager deja ne-a conectat la boot, respecta asta.
    existing_ssid, existing_ip = current_client_state()
    if existing_ssid and existing_ip:
        log.info("Deja conectat la %s (%s) — raman in mod client", existing_ssid, existing_ip)
        mode = "client"
    elif try_autoconnect_client(CLIENT_BOOT_TIMEOUT):
        mode = "client"
    elif saved_wifi_connections() or not REQUIRE_SAVED_FOR_AUTO_AP:
        log.info("Retele salvate indisponibile — pornesc AP")
        start_ap(ap_ssid, ap_password)
        mode = "ap"
    else:
        log.warning("Nicio retea salvata — nu pornesc AP automat. Folositi 'start-ap' manual.")
        mode = "unknown"

    lost_since: float | None = None
    while True:
        # 1) comenzi externe (dict JSON din coada)
        cmd = consume_command()
        if cmd:
            action = cmd.get("cmd")
            log.info("Comanda primita: %s", action)
            try:
                if action == "connect":
                    ssid = cmd.get("ssid", "")
                    password = cmd.get("password") or None
                    if ssid and connect_client(ssid, password):
                        mode = "client"
                    else:
                        start_ap(ap_ssid, ap_password)
                        mode = "ap"
                elif action == "disconnect":
                    disconnect_client()
                    start_ap(ap_ssid, ap_password)
                    mode = "ap"
                elif action == "start-ap":
                    start_ap(ap_ssid, ap_password)
                    mode = "ap"
                elif action == "rescan":
                    _nmcli("device", "wifi", "rescan", "ifname", WLAN_IFACE, timeout=15)
                elif action == "set-ap":
                    ap_ssid = cmd.get("ssid") or ap_ssid
                    ap_password = cmd.get("password") or ap_password
                    save_ap_config({"ap_ssid": ap_ssid, "ap_password": ap_password})
                    if mode == "ap":
                        start_ap(ap_ssid, ap_password)
                elif action == "delete-saved":
                    ssid = cmd.get("ssid")
                    if ssid:
                        delete_saved(ssid)
            except Exception as e:
                log.exception("Eroare comanda %s: %s", cmd, e)

        # 2) verificare conexiune client
        client_ssid, client_ip = current_client_state()
        if mode == "client":
            if client_ssid and client_ip:
                lost_since = None
            else:
                if lost_since is None:
                    lost_since = time.monotonic()
                    log.warning("Client Wi-Fi pierdut — monitorizez")
                elif (time.monotonic() - lost_since) > CLIENT_LOST_TIMEOUT:
                    log.warning("Client pierdut > %ds — comut la AP", CLIENT_LOST_TIMEOUT)
                    start_ap(ap_ssid, ap_password)
                    mode = "ap"
                    lost_since = None

        internet = has_internet() if mode == "client" else False
        write_state(mode, ap_ssid, ap_password, client_ssid if mode == "client" else None,
                    client_ip if mode == "client" else None, internet)

        time.sleep(3)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("Oprire la cerere")
        sys.exit(0)
