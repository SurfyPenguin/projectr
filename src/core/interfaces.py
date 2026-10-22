"""Ports that decouple the application core from inputs, outputs, and the engine."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.models import EngineResult, Frame, Slide


@runtime_checkable
class FrameSource(Protocol):
    """Anything that can hand back one whiteboard frame."""

    @property
    def source_id(self) -> str: ...

    def get_frame(self) -> Frame | None: ...


@runtime_checkable
class EnginePort(Protocol):
    """The CV + VLM pipeline: frame in, structured transcription out."""

    def process(
        self, frame, *, retry: bool = False, use_warp: bool = False
    ) -> EngineResult: ...


@runtime_checkable
class OutputSink(Protocol):
    """Destination for deck mutations."""

    def on_new_slide(self, slide: Slide) -> None: ...

    def on_update_slide(self, index: int, slide: Slide) -> None: ...


@runtime_checkable
class StatusListener(Protocol):
    """Optional sink capability for transient UI status (e.g. Socket.IO scan_status)."""

    def on_status(self, *, status: str, message: str = "", mode: str = "") -> None: ...
