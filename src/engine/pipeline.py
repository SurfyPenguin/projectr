"""Engine facade: preprocess a frame, then transcribe it with the VLM cascade."""

from __future__ import annotations

from typing import Any

from src.core.models import EngineResult
from src.engine.latex_engine import LatexConverterEngine
from src.engine.whiteboard_cv import WhiteboardPreprocessor


class WhiteboardEngine:
    """Image/frame in, structured transcription out.

    Owns the preprocessing policy (including the guardrail that calibration is
    only applied when ``use_warp=True``) and the retry/temperature policy lives
    in the converter.
    """

    def __init__(
        self,
        preprocessor: WhiteboardPreprocessor | None = None,
        converter: LatexConverterEngine | None = None,
    ) -> None:
        self.preprocessor = preprocessor or WhiteboardPreprocessor()
        self.converter = converter or LatexConverterEngine()

    def process(
        self, frame: Any, *, retry: bool = False, use_warp: bool = False
    ) -> EngineResult:
        # Guardrail: never apply calibration_config.json blindly.
        self.preprocessor.set_warp(use_warp)

        height, width = frame.shape[:2]
        cleaned = self.preprocessor.process_whiteboard(
            frame, out_width=width, out_height=height
        )
        return self.converter.convert(
            cleaned, retry=retry, preprocessor=self.preprocessor
        )
