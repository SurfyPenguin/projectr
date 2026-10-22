from src.core.models import Diagram
from src.core.slide_deck import SlideDeck


def make_deck(times=("09:00 AM", "09:05 AM", "09:10 AM")):
    stamps = iter(times)
    return SlideDeck(clock=lambda: next(stamps))


def test_add_assigns_sequential_numbers_and_timestamps():
    deck = make_deck()

    first = deck.add(image_path="a.jpeg", latex="$a$")
    second = deck.add(image_path="b.jpeg", latex="$b$")

    assert [s.slide_num for s in deck] == [1, 2]
    assert first.timestamp == "09:00 AM"
    assert second.timestamp == "09:05 AM"
    assert len(deck) == 2
    assert deck.latest_index == 1


def test_replace_keeps_slide_num_but_updates_content_and_timestamp():
    deck = make_deck()
    deck.add(image_path="a.jpeg", latex="$wrong$")

    updated = deck.replace(
        0,
        image_path="a.jpeg",
        latex="$right$",
        diagrams=[Diagram(type="mermaid", label="FIG 01", content="graph TD; A-->B")],
    )

    assert updated.slide_num == 1
    assert updated.timestamp == "09:05 AM"
    assert deck[0].latex == "$right$"
    assert len(deck) == 1


def test_to_dicts_matches_frontend_contract():
    deck = make_deck()
    deck.add(
        image_path="board1.jpeg",
        latex="$$x^2$$",
        diagrams=[Diagram(type="image", label="FIG 01", content="data:image/png;base64,AA")],
    )

    payload = deck.to_dicts()[0]

    assert payload == {
        "slide_num": 1,
        "timestamp": "09:00 AM",
        "image_path": "board1.jpeg",
        "latex": "$$x^2$$",
        "diagrams": [
            {"type": "image", "label": "FIG 01", "content": "data:image/png;base64,AA"}
        ],
    }


def test_latest_index_is_none_when_empty():
    assert SlideDeck().latest_index is None


def test_replace_out_of_range_raises():
    deck = make_deck()
    try:
        deck.replace(0, image_path="x", latex="y")
    except IndexError:
        return
    raise AssertionError("expected IndexError")
