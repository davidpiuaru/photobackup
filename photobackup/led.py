import logging

from . import config

log = logging.getLogger(__name__)

try:
    from gpiozero import LED
    _GPIO_AVAILABLE = True
except Exception as e:  # ImportError sau erori de init pe non-Pi
    log.warning("gpiozero indisponibil (%s) — LED-urile vor fi no-op", e)
    _GPIO_AVAILABLE = False


class LedFeedback:
    def __init__(self):
        self._green = None
        self._red = None
        if _GPIO_AVAILABLE:
            try:
                self._green = LED(config.LED_GREEN_PIN)
                self._red = LED(config.LED_RED_PIN)
            except Exception as e:
                log.warning("Init GPIO esuat (%s) — fallback no-op", e)
                self._green = None
                self._red = None

    def idle(self):
        self._set(green=True, red=False)

    def working(self):
        if self._green:
            self._green.blink(on_time=0.25, off_time=0.25, background=True)
        if self._red:
            self._red.off()

    def error(self):
        self._set(green=False, red=True)

    def off(self):
        self._set(green=False, red=False)

    def _set(self, green: bool, red: bool):
        for led, state in ((self._green, green), (self._red, red)):
            if led is None:
                continue
            try:
                if state:
                    led.on()
                else:
                    led.off()
            except Exception as e:
                log.warning("Eroare LED: %s", e)
