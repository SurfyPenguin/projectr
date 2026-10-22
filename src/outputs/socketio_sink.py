"""Socket.IO sink: broadcasts deck events to the projector and student views."""

from __future__ import annotations

from flask_socketio import SocketIO

from src.core.models import Slide


class SocketIOSink:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio

    def on_new_slide(self, slide: Slide) -> None:
        self.socketio.emit("new_latex_slide", slide.to_dict())

    def on_update_slide(self, index: int, slide: Slide) -> None:
        self.socketio.emit(
            "update_latex_slide", {"index": index, "slide": slide.to_dict()}
        )

    def on_status(self, *, status: str, message: str = "", mode: str = "") -> None:
        payload = {"status": status}
        if mode:
            payload["mode"] = mode
        if message:
            payload["message"] = message
        self.socketio.emit("scan_status", payload)
