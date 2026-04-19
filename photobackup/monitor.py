import logging
import time

import pyudev

from . import config

log = logging.getLogger(__name__)


def is_sd_card_partition(device: pyudev.Device) -> bool:
    """True daca device-ul este o partitie de pe card readerul nostru."""
    if device.get("DEVTYPE") != "partition":
        return False
    if device.get("ID_BUS") != "usb":
        return False
    if device.get("ID_VENDOR_ID") != config.SD_READER_VENDOR_ID:
        return False
    if device.get("ID_MODEL_ID") != config.SD_READER_MODEL_ID:
        return False
    return True


def card_label(device: pyudev.Device) -> str:
    return device.get("ID_FS_LABEL") or device.get("ID_FS_LABEL_ENC") or "UNTITLED"


def watch(on_card_inserted):
    """Loop blocking: apeleaza callback(device_node, label) la insertie SD card."""
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")
    monitor.start()

    log.info("Monitor pornit (vendor=%s model=%s)",
             config.SD_READER_VENDOR_ID, config.SD_READER_MODEL_ID)

    for action, device in monitor:
        if action != "add":
            continue
        if not is_sd_card_partition(device):
            continue
        log.info("SD card detectat: %s (%s)", device.device_node, card_label(device))
        # Mic delay ca udisks/kernel sa termine setup-ul
        time.sleep(1)
        try:
            on_card_inserted(device.device_node, card_label(device))
        except Exception as e:
            log.exception("Eroare in handler: %s", e)
