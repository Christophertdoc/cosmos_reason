import os


LLAMA_SERVER_URL: str = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080")
MAX_UPLOAD_MB: int = int(os.environ.get("MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
MAX_PROMPT_LENGTH: int = int(os.environ.get("MAX_PROMPT_LENGTH", "2000"))
MODEL_TIMEOUT_SECONDS: int = int(os.environ.get("MODEL_TIMEOUT_SECONDS", "120"))
MAX_GENERATION_TOKENS: int = int(os.environ.get("MAX_GENERATION_TOKENS", "4096"))
ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
    if origin.strip()
]

ALLOWED_MIME_TYPES: set[str] = {"video/mp4", "video/webm", "video/quicktime"}
MAX_VIDEO_DURATION_SECONDS: int = int(os.environ.get("MAX_VIDEO_DURATION_SECONDS", "10"))
MAX_FRAMES: int = int(os.environ.get("MAX_FRAMES", "40"))
VIDEO_FPS: int = int(os.environ.get("VIDEO_FPS", "4"))
