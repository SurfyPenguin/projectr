from pathlib import Path

import pytest

from src.core.errors import FrameSourceError
from src.inputs.file_source import FileImageSource, list_available_images
from src.inputs.upload_source import UploadSource

IMAGES = Path(__file__).resolve().parents[1] / "test_images"


def test_file_source_reads_explicit_image():
    path = IMAGES / "board1.jpeg"
    source = FileImageSource(str(path))

    frame = source.get_frame()

    assert source.source_id == str(path)
    assert frame.image.shape[0] > 0
    assert frame.source_id == str(path)


def test_file_source_falls_back_to_newest_image(tmp_path):
    (tmp_path / "old.jpeg").write_bytes((IMAGES / "board1.jpeg").read_bytes())
    (tmp_path / "new.jpeg").write_bytes((IMAGES / "board4.jpeg").read_bytes())

    source = FileImageSource(None, directory=str(tmp_path))

    assert source.source_id.endswith("new.jpeg")


def test_file_source_errors_when_directory_is_empty(tmp_path):
    source = FileImageSource(None, directory=str(tmp_path))

    with pytest.raises(FrameSourceError, match="No images found"):
        source.get_frame()


def test_scanner_skips_debug_files(tmp_path):
    (tmp_path / "board.jpeg").write_bytes(b"x")
    (tmp_path / "debug_flattened_cleaned.jpg").write_bytes(b"x")

    assert [Path(p).name for p in list_available_images(str(tmp_path))] == ["board.jpeg"]


def test_upload_source_decodes_bytes():
    data = (IMAGES / "board1.jpeg").read_bytes()

    frame = UploadSource(data, filename="board1.jpeg").get_frame()

    assert frame.source_id == "upload:board1.jpeg"
    assert frame.image.ndim == 3


def test_upload_source_rejects_garbage():
    with pytest.raises(FrameSourceError, match="Could not decode"):
        UploadSource(b"not-an-image", filename="broken.png").get_frame()
