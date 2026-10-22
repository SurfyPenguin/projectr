"""Transport-agnostic domain models shared by the engine, inputs, core, and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Frame:
    """A single whiteboard image plus the identifier of where it came from."""

    image: Any  # numpy.ndarray (BGR); kept untyped so core stays CV-library agnostic
    source_id: str


@dataclass(frozen=True)
class Diagram:
    """A figure extracted from a slide: either a Mermaid block or a cropped image."""

    type: str  # "mermaid" | "image"
    label: str  # "FIG 01"
    content: str  # mermaid source or data:image PNG URI

    def to_dict(self) -> dict:
        return {"type": self.type, "label": self.label, "content": self.content}


@dataclass
class EngineResult:
    """Contract returned by the CV + VLM engine."""

    status: str  # "success" | "error"
    latex: str | None = None
    diagrams: list[Diagram] = field(default_factory=list)
    error: str | None = None


@dataclass
class Slide:
    """One entry of the lecture deck, serialized verbatim into the templates."""

    slide_num: int
    timestamp: str
    image_path: str
    latex: str
    diagrams: list[Diagram] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slide_num": self.slide_num,
            "timestamp": self.timestamp,
            "image_path": self.image_path,
            "latex": self.latex,
            "diagrams": [d.to_dict() for d in self.diagrams],
        }


@dataclass
class ScanOutcome:
    """Result of a capture/recapture request, ready for the HTTP adapter."""

    status: str
    slide: Slide | None = None
    index: int | None = None
    replaced: bool = False
    error: str | None = None
    http_status: int = 200

    def to_response(self) -> dict:
        if self.status == "success":
            return {
                "status": "success",
                "slide": self.slide.to_dict() if self.slide else None,
                "replaced": self.replaced,
            }
        return {"status": "error", "message": self.error}
