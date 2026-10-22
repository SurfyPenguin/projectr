import numpy as np
import pytest

from src.core.errors import FrameSourceError
from src.core.models import EngineResult, Frame, Slide
from src.core.scan_service import ScanService
from src.core.slide_deck import SlideDeck


class FakeSource:
    def __init__(self, source_id="test_images/fake.jpeg", error=None):
        self._source_id = source_id
        self._error = error
        self.calls = 0

    @property
    def source_id(self):
        return self._source_id

    def get_frame(self):
        self.calls += 1
        if self._error:
            raise FrameSourceError(self._error)
        return Frame(np.zeros((8, 8, 3), dtype=np.uint8), self._source_id)


class FakeEngine:
    def __init__(self, result=None):
        self.result = result or EngineResult(status="success", latex="$x$")
        self.calls = []

    def process(self, frame, *, retry=False, use_warp=False):
        self.calls.append({"shape": frame.shape, "retry": retry, "use_warp": use_warp})
        return self.result


class RecordingSink:
    def __init__(self, with_status=True):
        self.new_slides: list[Slide] = []
        self.updates: list[tuple[int, Slide]] = []
        self.statuses: list[dict] = []
        if with_status:
            self.on_status = self._on_status

    def _on_status(self, *, status, message="", mode=""):
        self.statuses.append({"status": status, "message": message, "mode": mode})

    def on_new_slide(self, slide):
        self.new_slides.append(slide)

    def on_update_slide(self, index, slide):
        self.updates.append((index, slide))


def make_service(result=None, times=("10:00 AM", "10:01 AM", "10:02 AM")):
    stamps = iter(times)
    deck = SlideDeck(clock=lambda: next(stamps))
    engine = FakeEngine(result)
    service = ScanService(deck, engine)
    sink = RecordingSink()
    service.add_sink(sink)
    return service, deck, engine, sink


def test_capture_publishes_new_slide_and_stores_it():
    service, deck, engine, sink = make_service()
    source = FakeSource()

    outcome = service.capture(source)

    assert outcome.status == "success"
    assert outcome.replaced is False
    assert outcome.index == 0
    assert len(deck) == 1
    assert deck[0].image_path == "test_images/fake.jpeg"
    assert sink.new_slides == [deck[0]]
    assert sink.updates == []
    assert engine.calls == [{"shape": (8, 8, 3), "retry": False, "use_warp": False}]
    assert sink.statuses[0] == {
        "status": "scanning",
        "message": "",
        "mode": "scanning (fake.jpeg)",
    }


def test_capture_forwards_warp_flag():
    service, _, engine, _ = make_service()

    service.capture(FakeSource(), use_warp=True)

    assert engine.calls[0]["use_warp"] is True


def test_recapture_updates_in_place_with_retry_temperature():
    service, deck, engine, sink = make_service()
    source = FakeSource()

    service.capture(source)
    outcome = service.recapture(0, source)

    assert outcome.replaced is True
    assert outcome.index == 0
    assert len(deck) == 1
    assert deck[0].slide_num == 1
    assert deck[0].timestamp == "10:01 AM"
    assert sink.updates == [(0, deck[0])]
    assert [call["retry"] for call in engine.calls] == [False, True]
    assert sink.statuses[-1]["mode"] == "recapturing (fake.jpeg)"


def test_recapture_rejects_out_of_range_index():
    service, _, engine, sink = make_service()

    outcome = service.recapture(5, FakeSource())

    assert outcome.status == "error"
    assert outcome.http_status == 400
    assert engine.calls == []
    assert sink.statuses[-1]["status"] == "error"


def test_engine_error_returns_error_outcome_and_no_slide_events():
    failed = EngineResult(status="error", latex=None, error="quota exceeded")
    service, deck, _, sink = make_service(failed)

    outcome = service.capture(FakeSource())

    assert outcome.status == "error"
    assert outcome.http_status == 500
    assert outcome.to_response() == {"status": "error", "message": "quota exceeded"}
    assert len(deck) == 0
    assert sink.new_slides == []
    assert sink.statuses[-1] == {
        "status": "error",
        "message": "quota exceeded",
        "mode": "",
    }


def test_source_error_returns_400():
    service, deck, engine, _ = make_service()

    outcome = service.capture(FakeSource(error="No images found in test_images/"))

    assert outcome.status == "error"
    assert outcome.http_status == 400
    assert outcome.error == "No images found in test_images/"
    assert engine.calls == []
    assert len(deck) == 0


def test_sinks_without_status_support_are_supported():
    deck = SlideDeck(clock=lambda: "10:00 AM")
    service = ScanService(deck, FakeEngine())
    sink = RecordingSink(with_status=False)
    service.add_sink(sink)

    outcome = service.capture(FakeSource())

    assert outcome.status == "success"
    assert sink.new_slides[0].slide_num == 1


def test_success_response_shape():
    service, _, _, _ = make_service()

    payload = service.capture(FakeSource()).to_response()

    assert payload["status"] == "success"
    assert payload["replaced"] is False
    assert payload["slide"]["slide_num"] == 1
    assert set(payload) == {"status", "slide", "replaced"}
