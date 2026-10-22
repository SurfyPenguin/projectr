"""Live webcam adapter. Wired by the composition root once Track 2 lands."""

from __future__ import annotations

import cv2

from src.core.errors import FrameSourceError
from src.core.models import Frame


class LiveCameraSource:
    """Grabs one frame from ``cv2.VideoCapture(index)``; opens the device lazily."""

    def __init__(self, index: int = 0):
        self.index = index
        self._capture: cv2.VideoCapture | None = None

    @property
    def source_id(self) -> str:
        return f"camera:{self.index}"

    def get_frame(self) -> Frame:
        if self._capture is None:
            self._capture = cv2.VideoCapture(self.index)
        ok, frame = self._capture.read()
        if not ok:
            raise FrameSourceError(f"Could not read from camera {self.index}")
        return Frame(image=frame, source_id=self.source_id)

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
