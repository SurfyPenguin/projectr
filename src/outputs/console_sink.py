"""Trivial sink proving the output interface is transport-agnostic."""

from __future__ import annotations

from src.core.models import Slide


class ConsoleSink:
    def on_new_slide(self, slide: Slide) -> None:
        print(f"[SLIDE {slide.slide_num:02d}] new  {slide.timestamp}  {slide.image_path}")

    def on_update_slide(self, index: int, slide: Slide) -> None:
        print(f"[SLIDE {index + 1:02d}] updated  {slide.timestamp}  {slide.image_path}")

    def on_status(self, *, status: str, message: str = "", mode: str = "") -> None:
        detail = mode or message
        print(f"[STATUS] {status}{f'  {detail}' if detail else ''}")
