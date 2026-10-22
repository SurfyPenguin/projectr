"""File-based frame source and the shared test_images/ scanner."""

from __future__ import annotations

import glob
import os

import cv2

from src.core.errors import FrameSourceError
from src.core.models import Frame

IMAGE_EXTENSIONS = ("*.jpeg", "*.jpg", "*.png", "*.webp")


def list_available_images(directory: str = "test_images") -> list[str]:
    """Real images in ``directory``, newest first; debug_* artifacts are excluded."""
    os.makedirs(directory, exist_ok=True)
    files: list[str] = []
    for extension in IMAGE_EXTENSIONS:
        for path in glob.glob(os.path.join(directory, extension)):
            if not os.path.basename(path).startswith("debug_"):
                files.append(path.replace("\\", "/"))
    files.sort(key=os.path.getmtime, reverse=True)
    return files


class FileImageSource:
    """Reads an explicit image, falling back to the newest file in the directory."""

    def __init__(self, image_path: str | None = None, *, directory: str = "test_images"):
        self.directory = directory
        self._path = self._resolve(image_path)

    def _resolve(self, requested: str | None) -> str | None:
        if requested and os.path.exists(requested):
            return requested.replace("\\", "/")
        available = list_available_images(self.directory)
        return available[0] if available else None

    @property
    def source_id(self) -> str:
        return self._path or f"{self.directory}/*"

    def get_frame(self) -> Frame:
        if self._path is None:
            raise FrameSourceError(f"No images found in {self.directory}/")
        frame = cv2.imread(self._path)
        if frame is None:
            raise FrameSourceError(f"Could not read {self._path}")
        return Frame(image=frame, source_id=self._path)
