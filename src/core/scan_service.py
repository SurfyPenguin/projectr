"""Orchestrates: source.get_frame -> engine.process -> deck mutation -> sink events."""

from __future__ import annotations

import os

from src.core.errors import FrameSourceError
from src.core.interfaces import EnginePort, FrameSource, OutputSink, StatusListener
from src.core.models import ScanOutcome
from src.core.slide_deck import SlideDeck


class ScanService:
    """Single entry point for capture/recapture. Knows nothing about HTTP or sockets."""

    def __init__(self, deck: SlideDeck, engine: EnginePort) -> None:
        self.deck = deck
        self.engine = engine
        self._sinks: list[OutputSink] = []

    def add_sink(self, sink: OutputSink) -> None:
        self._sinks.append(sink)

    def capture(self, source: FrameSource, *, use_warp: bool = False) -> ScanOutcome:
        return self._run(source, retry=False, replace_index=None, use_warp=use_warp)

    def recapture(
        self, index: int, source: FrameSource, *, use_warp: bool = False
    ) -> ScanOutcome:
        if not 0 <= index < len(self.deck):
            return self._fail(f"Slide index {index} is out of range.", http_status=400)
        return self._run(source, retry=True, replace_index=index, use_warp=use_warp)

    def _run(
        self,
        source: FrameSource,
        *,
        retry: bool,
        replace_index: int | None,
        use_warp: bool,
    ) -> ScanOutcome:
        label = os.path.basename(source.source_id)
        self._status(
            "scanning",
            mode=f"{'recapturing' if retry else 'scanning'} ({label})",
        )

        try:
            frame = source.get_frame()
        except FrameSourceError as exc:
            return self._fail(str(exc), http_status=400)

        if frame is None:
            return self._fail(f"Could not read {source.source_id}", http_status=400)

        print(
            f"\n[SCAN] Source: {frame.source_id} | Retry={retry} | Warp={use_warp}"
        )
        result = self.engine.process(frame.image, retry=retry, use_warp=use_warp)

        if result.status != "success":
            return self._fail(result.error or "Conversion failed", http_status=500)

        if replace_index is None:
            slide = self.deck.add(
                image_path=frame.source_id,
                latex=result.latex or "",
                diagrams=result.diagrams,
            )
            self._publish(lambda sink: sink.on_new_slide(slide))
            return ScanOutcome(
                status="success",
                slide=slide,
                index=len(self.deck) - 1,
                replaced=False,
            )

        slide = self.deck.replace(
            replace_index,
            image_path=frame.source_id,
            latex=result.latex or "",
            diagrams=result.diagrams,
        )
        self._publish(lambda sink: sink.on_update_slide(replace_index, slide))
        return ScanOutcome(
            status="success",
            slide=slide,
            index=replace_index,
            replaced=True,
        )

    def _publish(self, event) -> None:
        for sink in self._sinks:
            event(sink)

    def _status(self, status: str, *, message: str = "", mode: str = "") -> None:
        for sink in self._sinks:
            if isinstance(sink, StatusListener):
                sink.on_status(status=status, message=message, mode=mode)

    def _fail(self, message: str, *, http_status: int) -> ScanOutcome:
        self._status("error", message=message)
        return ScanOutcome(status="error", error=message, http_status=http_status)
