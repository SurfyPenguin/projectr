"""In-memory lecture deck: owns slide numbering, timestamps, and replacement."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterator

from src.core.models import Diagram, Slide

TimestampProvider = Callable[[], str]


def _default_timestamp() -> str:
    return datetime.now().strftime("%I:%M %p")


class SlideDeck:
    """Chronological deck. The single owner of slide state for the application."""

    def __init__(self, clock: TimestampProvider | None = None) -> None:
        self._slides: list[Slide] = []
        self._clock = clock or _default_timestamp

    def __len__(self) -> int:
        return len(self._slides)

    def __iter__(self) -> Iterator[Slide]:
        return iter(self._slides)

    def __getitem__(self, index: int) -> Slide:
        return self._slides[index]

    @property
    def slides(self) -> tuple[Slide, ...]:
        return tuple(self._slides)

    @property
    def latest_index(self) -> int | None:
        return len(self._slides) - 1 if self._slides else None

    def add(
        self,
        *,
        image_path: str,
        latex: str,
        diagrams: list[Diagram] | None = None,
    ) -> Slide:
        slide = Slide(
            slide_num=len(self._slides) + 1,
            timestamp=self._clock(),
            image_path=image_path,
            latex=latex,
            diagrams=list(diagrams or []),
        )
        self._slides.append(slide)
        return slide

    def replace(
        self,
        index: int,
        *,
        image_path: str,
        latex: str,
        diagrams: list[Diagram] | None = None,
    ) -> Slide:
        existing = self._slides[index]  # IndexError propagates to the caller
        slide = Slide(
            slide_num=existing.slide_num,
            timestamp=self._clock(),
            image_path=image_path,
            latex=latex,
            diagrams=list(diagrams or []),
        )
        self._slides[index] = slide
        return slide

    def to_dicts(self) -> list[dict]:
        """Template/socket payload shape (kept identical to the pre-refactor dicts)."""
        return [slide.to_dict() for slide in self._slides]
