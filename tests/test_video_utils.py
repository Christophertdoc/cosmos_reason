from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from app.video_utils import extract_frames


def _make_mock_cap(fps=30.0, frame_count=60, frame_shape=(480, 640, 3)):
    """Create a mock cv2.VideoCapture that yields solid-color frames."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.side_effect = lambda prop: {
        # cv2.CAP_PROP_FPS = 5, cv2.CAP_PROP_FRAME_COUNT = 7
        5: fps,
        7: float(frame_count),
    }.get(prop, 0.0)

    frames_returned = 0

    def read_side_effect():
        nonlocal frames_returned
        if frames_returned >= frame_count:
            return False, None
        frames_returned += 1
        frame = np.zeros(frame_shape, dtype=np.uint8)
        frame[:] = (128, 64, 32)  # BGR color
        return True, frame

    cap.read.side_effect = read_side_effect
    return cap


@patch("app.video_utils.cv2.VideoCapture")
def test_extract_frames_basic(mock_video_capture):
    """Extract frames from a 2-second, 30fps video at 4fps → expect 8 frames."""
    mock_video_capture.return_value = _make_mock_cap(fps=30.0, frame_count=60)

    frames = extract_frames(b"\x00" * 100)

    assert len(frames) == 8
    for frame_bytes, mime in frames:
        assert mime == "image/jpeg"
        assert len(frame_bytes) > 0


@patch("app.video_utils.cv2.VideoCapture")
def test_extract_frames_caps_at_max(mock_video_capture):
    """Frames capped at MAX_FRAMES."""
    with patch("app.video_utils.config.MAX_FRAMES", 5):
        mock_video_capture.return_value = _make_mock_cap(fps=30.0, frame_count=300)
        frames = extract_frames(b"\x00" * 100)
        assert len(frames) == 5


@patch("app.video_utils.cv2.VideoCapture")
def test_extract_frames_duration_exceeded(mock_video_capture):
    """Raises ValueError when video is too long."""
    mock_video_capture.return_value = _make_mock_cap(fps=30.0, frame_count=600)

    with pytest.raises(ValueError, match="duration"):
        extract_frames(b"\x00" * 100)


@patch("app.video_utils.cv2.VideoCapture")
def test_extract_frames_cannot_open(mock_video_capture):
    """Raises ValueError when video can't be opened."""
    cap = MagicMock()
    cap.isOpened.return_value = False
    mock_video_capture.return_value = cap

    with pytest.raises(ValueError, match="Could not open"):
        extract_frames(b"\x00" * 100)


@patch("app.video_utils.cv2.VideoCapture")
def test_extract_frames_zero_fps(mock_video_capture):
    """Raises ValueError when FPS is zero."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.return_value = 0.0
    mock_video_capture.return_value = cap

    with pytest.raises(ValueError, match="frame rate"):
        extract_frames(b"\x00" * 100)
