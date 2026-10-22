"""End-to-end adapter test: real Flask routes, real sources, fake engine."""

import os
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from src.core.models import EngineResult  # noqa: E402
from app_server import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "test_images"


class FakeEngine:
    def __init__(self, result=None):
        self.result = result or EngineResult(status="success", latex="$$x = 1$$")
        self.calls = []

    def process(self, frame, *, retry=False, use_warp=False):
        self.calls.append({"retry": retry, "use_warp": use_warp})
        return self.result


def make_app(engine=None, directory=str(IMAGES)):
    app, socketio = create_app(engine=engine or FakeEngine(), source_directory=directory)
    return app.test_client(), socketio.test_client(app)


def event_names(client):
    return [event["name"] for event in client.get_received()]


def test_pages_render():
    http, _ = make_app()
    assert http.get("/").status_code == 200
    assert http.get("/student").status_code == 200


def test_api_images_skips_debug_artifacts(tmp_path):
    (tmp_path / "board1.jpeg").write_bytes((IMAGES / "board1.jpeg").read_bytes())
    (tmp_path / "debug_flattened_cleaned.jpg").write_bytes(b"debug")

    http, _ = make_app(directory=str(tmp_path))
    images = http.get("/api/images").get_json()["images"]

    assert images == [str(tmp_path / "board1.jpeg")]


def test_scan_capture_returns_slide_and_broadcasts():
    http, sio = make_app()

    response = http.post(
        "/api/scan", json={"image_path": str(IMAGES / "board1.jpeg")}
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["replaced"] is False
    assert payload["slide"]["slide_num"] == 1
    assert payload["slide"]["latex"] == "$$x = 1$$"
    assert payload["slide"]["image_path"].endswith("board1.jpeg")

    names = event_names(sio)
    assert "scan_status" in names
    assert "new_latex_slide" in names


def test_scan_recapture_updates_in_place():
    http, sio = make_app()
    http.post("/api/scan", json={"image_path": str(IMAGES / "board1.jpeg")})
    sio.get_received()

    response = http.post("/api/scan", json={"replace_index": 0})
    payload = response.get_json()

    assert payload["status"] == "success"
    assert payload["replaced"] is True
    assert payload["slide"]["slide_num"] == 1

    events = {event["name"]: event["args"][0] for event in sio.get_received()}
    assert events["update_latex_slide"]["index"] == 0
    assert events["update_latex_slide"]["slide"]["slide_num"] == 1


def test_scan_reports_engine_failure():
    failing = FakeEngine(EngineResult(status="error", error="model unavailable"))
    http, sio = make_app(engine=failing)

    response = http.post(
        "/api/scan", json={"image_path": str(IMAGES / "board1.jpeg")}
    )

    assert response.status_code == 500
    assert response.get_json() == {"status": "error", "message": "model unavailable"}
    events = {event["name"]: event["args"][0] for event in sio.get_received()}
    assert events["scan_status"] == {"status": "error", "message": "model unavailable"}


def test_scan_without_images_returns_400(tmp_path):
    http, _ = make_app(directory=str(tmp_path))

    response = http.post("/api/scan", json={})

    assert response.status_code == 400
    assert "No images found" in response.get_json()["message"]
