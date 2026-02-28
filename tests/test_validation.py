from app import config


def test_allowed_mime_types():
    assert "video/mp4" in config.ALLOWED_MIME_TYPES
    assert "video/webm" in config.ALLOWED_MIME_TYPES
    assert "video/quicktime" in config.ALLOWED_MIME_TYPES
    assert "image/jpeg" not in config.ALLOWED_MIME_TYPES
    assert "image/png" not in config.ALLOWED_MIME_TYPES
    assert "image/gif" not in config.ALLOWED_MIME_TYPES


def test_max_upload_size():
    assert config.MAX_UPLOAD_MB == 50
    assert config.MAX_UPLOAD_BYTES == 50 * 1024 * 1024


def test_video_settings():
    assert config.MAX_VIDEO_DURATION_SECONDS == 120
    assert config.MAX_FRAMES == 40
    assert config.VIDEO_FPS == 4


def test_max_prompt_length():
    assert config.MAX_PROMPT_LENGTH == 2000


def test_llama_server_url_default():
    assert config.LLAMA_SERVER_URL == "http://localhost:8080"


def test_model_timeout_default():
    assert config.MODEL_TIMEOUT_SECONDS == 120


def test_max_generation_tokens_default():
    assert config.MAX_GENERATION_TOKENS == 4096


def test_allowed_origins_default():
    assert "http://localhost:8000" in config.ALLOWED_ORIGINS
