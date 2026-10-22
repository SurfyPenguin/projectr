# app_server.py
"""Thin Flask + Socket.IO adapter: composes sources, service, and sinks."""

import base64
import io
import socket

import qrcode
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from src.core.scan_service import ScanService
from src.core.slide_deck import SlideDeck
from src.engine.pipeline import WhiteboardEngine
from src.inputs.file_source import list_available_images
from src.inputs.triggers import HttpTrigger
from src.outputs.socketio_sink import SocketIOSink

HOST = "0.0.0.0"
PORT = 5000


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def create_app(
    *,
    engine=None,
    deck: SlideDeck | None = None,
    source_directory: str = "test_images",
):
    """Composition root for the web adapter. Tests inject a fake engine/deck."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "whiteboard-secret-key"
    socketio = SocketIO(app, cors_allowed_origins="*")

    if deck is None:
        deck = SlideDeck()
    if engine is None:
        engine = WhiteboardEngine()
    scan_service = ScanService(deck, engine)
    scan_service.add_sink(SocketIOSink(socketio))
    http_trigger = HttpTrigger(scan_service, directory=source_directory)

    @app.route("/")
    def projector_view():
        student_url = f"http://{get_local_ip()}:{PORT}/student"
        return render_template(
            "projector.html",
            qr_b64=generate_qr_base64(student_url),
            student_url=student_url,
            slides=deck.to_dicts(),
            images=list_available_images(source_directory),
        )

    @app.route("/student")
    def student_view():
        return render_template("student_notes.html", slides=deck.to_dicts())

    @app.route("/api/images", methods=["GET"])
    def get_images():
        return jsonify({"images": list_available_images(source_directory)})

    @app.route("/api/scan", methods=["POST"])
    def trigger_scan():
        outcome = http_trigger.handle(request.get_json(silent=True) or {})
        return jsonify(outcome.to_response()), outcome.http_status

    return app, socketio


app, socketio = create_app()


if __name__ == "__main__":
    ip = get_local_ip()
    print("\n=======================================================")
    print(f" Projector UI:   http://localhost:{PORT}")
    print(f" Student UI:     http://{ip}:{PORT}/student")
    print("=======================================================\n")
    socketio.run(app, host=HOST, port=PORT, debug=True)
