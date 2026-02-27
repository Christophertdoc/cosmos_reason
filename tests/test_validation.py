from app import config


def test_allowed_mime_types():
    assert "image/jpeg" in config.ALLOWED_MIME_TYPES
    assert "image/png" in config.ALLOWED_MIME_TYPES
    assert "image/webp" in config.ALLOWED_MIME_TYPES
    assert "image/gif" not in config.ALLOWED_MIME_TYPES
    assert "image/bmp" not in config.ALLOWED_MIME_TYPES
    assert "application/pdf" not in config.ALLOWED_MIME_TYPES


def test_max_upload_size():
    assert config.MAX_UPLOAD_MB == 8
    assert config.MAX_UPLOAD_BYTES == 8 * 1024 * 1024


def test_max_prompt_length():
    assert config.MAX_PROMPT_LENGTH == 2000


def test_llama_server_url_default():
    assert config.LLAMA_SERVER_URL == "http://localhost:8080"


def test_model_timeout_default():
    assert config.MODEL_TIMEOUT_SECONDS == 120


def test_max_generation_tokens_default():
    assert config.MAX_GENERATION_TOKENS == 1024


def test_allowed_origins_default():
    assert "http://localhost:8000" in config.ALLOWED_ORIGINS
