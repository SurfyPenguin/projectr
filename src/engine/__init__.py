"""CV + VLM engine. Knows nothing about Flask, sockets, templates, or input UI."""

from src.engine.pipeline import WhiteboardEngine

__all__ = ["WhiteboardEngine"]
