import logging
from logging.handlers import RotatingFileHandler

from . import config, monitor
from .copier import backup_card
from .led import LedFeedback
from .mounter import MountError, mount, unmount


def setup_logging():
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers = [
        RotatingFileHandler(config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5),
        logging.StreamHandler(),
    ]
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers)


log = logging.getLogger(__name__)


def main():
    setup_logging()
    led = LedFeedback()
    led.idle()
    log.info("PhotoBackup pornit — astept SD card")

    def handle(device_node: str, label: str):
        led.working()
        mount_point = None
        try:
            mount_point = mount(device_node)
            log.info("Card montat la %s", mount_point)
            result = backup_card(mount_point, label=label)
            if result["ok"]:
                led.idle()
            else:
                led.error()
        except MountError as e:
            log.error("Mount esuat: %s", e)
            led.error()
        except Exception as e:
            log.exception("Eroare neasteptata: %s", e)
            led.error()
        finally:
            try:
                unmount(device_node)
            except Exception as e:
                log.warning("Unmount esuat: %s", e)

    try:
        monitor.watch(handle)
    except KeyboardInterrupt:
        log.info("Oprire la cerere")
    finally:
        led.off()


if __name__ == "__main__":
    main()
