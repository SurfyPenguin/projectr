"""In-memory upload adapter (browser file upload, clipboard, base64 payload)."""

from __future__ import annotations

import cv2
import numpy as np

from src.core.errors import FrameSourceError
from src.core.models import Frame


class UploadSource:
    """Decodes an uploaded image held in memory; nothing touches disk."""

    def __init__(self, data: bytes, *, filename: str = "upload.png"):
        self._data = data
        self.filename = filename

    @property
    def source_id(self) -> str:
        return f"upload:{self.filename}"

    def get_frame(self) -> Frame:
        buffer = np.frombuffer(self._data, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if frame is None:
            raise FrameSourceError(f"Could not decode upload {self.filename}")
        return Frame(image=frame, source_id=self.source_id)
