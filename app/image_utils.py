import io

from PIL import Image

TARGET_SIZE = 100 * 1024  # 100 KB


def compress_image(image_bytes: bytes, mime_type: str, target_size: int = TARGET_SIZE) -> tuple[bytes, str]:
    """Compress an image to approximately target_size bytes.

    Returns (compressed_bytes, mime_type). If the image is already under
    the target size or cannot be parsed, returns it unchanged.
    """
    if len(image_bytes) <= target_size:
        return image_bytes, mime_type

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return image_bytes, mime_type
    img = img.convert("RGB")  # ensure compatible with JPEG

    # Step 1: Scale down if very large
    max_dim = 1024
    while True:
        resized = img.copy()
        resized.thumbnail((max_dim, max_dim))

        # Step 2: Binary search on JPEG quality
        lo, hi = 20, 85
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=mid)
            size = buf.tell()
            if size <= target_size:
                best = (buf.getvalue(), size, mid)
                lo = mid + 1  # try higher quality
            else:
                hi = mid - 1

        if best is not None:
            return best[0], "image/jpeg"

        # Quality range exhausted at this resolution — shrink further
        max_dim = int(max_dim * 0.75)
        if max_dim < 64:
            # Fallback: return lowest quality at smallest size
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=20)
            return buf.getvalue(), "image/jpeg"
