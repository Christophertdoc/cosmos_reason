import io
import os
import tempfile

import cv2
from PIL import Image

from app import config

TARGET_SIZE = 40 * 1024  # 40 KB — smaller frames = faster vision encoder


def _compress_frame(frame_bgr, target_size: int = TARGET_SIZE) -> tuple[bytes, str]:
    """Compress a single BGR frame to approximately target_size JPEG bytes."""
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)

    # Scale down — 512px is sufficient for the 2B model's vision encoder
    max_dim = 512
    while True:
        resized = img.copy()
        resized.thumbnail((max_dim, max_dim))

        # Binary search on JPEG quality
        lo, hi = 20, 85
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=mid)
            size = buf.tell()
            if size <= target_size:
                best = (buf.getvalue(), size, mid)
                lo = mid + 1
            else:
                hi = mid - 1

        if best is not None:
            return best[0], "image/jpeg"

        max_dim = int(max_dim * 0.75)
        if max_dim < 64:
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=20)
            return buf.getvalue(), "image/jpeg"


def extract_frames(video_bytes: bytes) -> list[tuple[bytes, str]]:
    """Extract frames from video bytes at VIDEO_FPS rate.

    Returns list of (jpeg_bytes, mime_type) tuples.
    Raises ValueError for duration/format errors.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
    try:
        os.write(tmp_fd, video_bytes)
        os.close(tmp_fd)

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file. Unsupported or corrupted format.")

        source_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if source_fps <= 0:
            cap.release()
            raise ValueError("Could not determine video frame rate.")

        duration = frame_count / source_fps
        if duration > config.MAX_VIDEO_DURATION_SECONDS:
            cap.release()
            raise ValueError(
                f"Video duration ({duration:.1f}s) exceeds the "
                f"{config.MAX_VIDEO_DURATION_SECONDS}s limit."
            )

        # Seek directly to each target frame instead of reading every frame
        frame_interval = source_fps / config.VIDEO_FPS
        frames: list[tuple[bytes, str]] = []

        target_idx = 0.0
        while target_idx < frame_count and len(frames) < config.MAX_FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_idx))
            ret, frame = cap.read()
            if not ret:
                break
            jpeg_bytes, mime = _compress_frame(frame)
            frames.append((jpeg_bytes, mime))
            target_idx += frame_interval

        cap.release()

        if not frames:
            raise ValueError("No frames could be extracted from the video.")

        return frames
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
