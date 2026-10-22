"""Triggers translate operator intent into ScanService calls. They never call the engine."""

from __future__ import annotations

from typing import Callable

from src.core.interfaces import FrameSource
from src.core.models import ScanOutcome
from src.core.scan_service import ScanService
from src.inputs.file_source import FileImageSource

SourceFactory = Callable[[], FrameSource]


class HttpTrigger:
    """Translates a /api/scan JSON payload into a capture or recapture intent."""

    def __init__(self, service: ScanService, *, directory: str = "test_images"):
        self.service = service
        self.directory = directory

    def handle(self, payload: dict) -> ScanOutcome:
        replace_index = payload.get("replace_index")
        requested_path = payload.get("image_path")
        use_warp = bool(payload.get("use_warp", False))

        is_replace = (
            replace_index is not None and 0 <= replace_index < len(self.service.deck)
        )
        if is_replace and not requested_path:
            # Recapturing reuses the slide's original image unless a new one is chosen.
            requested_path = self.service.deck[replace_index].image_path

        source = FileImageSource(requested_path, directory=self.directory)
        if is_replace:
            return self.service.recapture(replace_index, source, use_warp=use_warp)
        return self.service.capture(source, use_warp=use_warp)


class KeyboardTrigger:
    """Kiosk/CLI key mapping mirroring the projector's C / R shortcuts."""

    def __init__(self, service: ScanService, source_factory: SourceFactory):
        self.service = service
        self.source_factory = source_factory

    def handle_key(self, key: str, *, use_warp: bool = False) -> ScanOutcome | None:
        key = key.lower()
        if key == "c":
            return self.service.capture(self.source_factory(), use_warp=use_warp)
        if key == "r" and self.service.deck.latest_index is not None:
            return self.service.recapture(
                self.service.deck.latest_index,
                self.source_factory(),
                use_warp=use_warp,
            )
        return None


class GpioTrigger:
    """Podium button stub: short press = capture, long press = recapture.

    Requires RPi.GPIO on the Raspberry Pi 5 node; a no-op everywhere else.
    """

    def __init__(
        self,
        service: ScanService,
        source_factory: SourceFactory,
        *,
        pin: int = 17,
        long_press_seconds: float = 0.6,
    ):
        self.service = service
        self.source_factory = source_factory
        self.pin = pin
        self.long_press_seconds = long_press_seconds
        self._pressed_at: float | None = None
        self._gpio = None

    def start(self) -> bool:
        try:
            import RPi.GPIO as GPIO  # type: ignore[import-not-found]
        except ImportError:
            print("[WARN] RPi.GPIO unavailable; GPIO trigger disabled.")
            return False

        import time

        self._gpio = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        def on_press(_channel):
            self._pressed_at = time.monotonic()

        def on_release(_channel):
            if self._pressed_at is None:
                return
            held = time.monotonic() - self._pressed_at
            self._pressed_at = None
            if held >= self.long_press_seconds:
                latest = self.service.deck.latest_index
                if latest is not None:
                    self.service.recapture(latest, self.source_factory())
            else:
                self.service.capture(self.source_factory())

        GPIO.add_event_detect(self.pin, GPIO.RISING, callback=on_press)
        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=on_release)
        return True

    def stop(self) -> None:
        if self._gpio is not None:
            self._gpio.cleanup(self.pin)
            self._gpio = None
