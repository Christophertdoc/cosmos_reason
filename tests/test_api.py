import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_mp4():
    """A minimal bytes object pretending to be an MP4 for testing."""
    return io.BytesIO(b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100)


@pytest.fixture
def mock_extract_frames():
    """Patch extract_frames to return a single fake JPEG frame."""
    with patch("app.main.extract_frames") as mock:
        mock.return_value = [(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")]
        yield mock


# --- US1: Core analysis flow ---


def test_analyze_success(client, sample_mp4, mock_extract_frames):
    with patch("app.main.analyze_video", new_callable=AsyncMock) as mock:
        mock.return_value = "A person walking down a street."
        response = client.post(
            "/api/analyze",
            files={"video": ("test.mp4", sample_mp4, "video/mp4")},
            data={"prompt": "Describe what happens"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "A person walking down a street."
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
    assert data["model"] == "Cosmos-Reason2-2B-GGUF"
    assert data["backend"] == "llama.cpp"
    assert "llama_server_url" in data


def test_analyze_llama_unavailable(client, sample_mp4, mock_extract_frames):
    from app.llama_client import LlamaClientError

    with patch("app.main.analyze_video", new_callable=AsyncMock) as mock:
        mock.side_effect = LlamaClientError("unavailable")
        response = client.post(
            "/api/analyze",
            files={"video": ("test.mp4", sample_mp4, "video/mp4")},
            data={"prompt": "Describe what happens"},
        )

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert "temporarily unavailable" in data["error"]


# --- US2: Input validation ---


def test_analyze_missing_prompt(client, sample_mp4, mock_extract_frames):
    response = client.post(
        "/api/analyze",
        files={"video": ("test.mp4", sample_mp4, "video/mp4")},
        data={"prompt": ""},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "prompt"


def test_analyze_unsupported_file_type(client):
    gif_file = io.BytesIO(b"GIF89a" + b"\x00" * 100)
    response = client.post(
        "/api/analyze",
        files={"video": ("test.gif", gif_file, "image/gif")},
        data={"prompt": "Describe what happens"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "video"
    assert "Unsupported file type" in data["error"]


def test_analyze_oversized_video(client):
    large_file = io.BytesIO(b"\x00" * (51 * 1024 * 1024))
    response = client.post(
        "/api/analyze",
        files={"video": ("big.mp4", large_file, "video/mp4")},
        data={"prompt": "Describe what happens"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "video"
    assert "exceeds" in data["error"]


def test_analyze_prompt_too_long(client, sample_mp4, mock_extract_frames):
    long_prompt = "x" * 2001
    response = client.post(
        "/api/analyze",
        files={"video": ("test.mp4", sample_mp4, "video/mp4")},
        data={"prompt": long_prompt},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "prompt"
    assert "exceeds maximum length" in data["error"]


def test_analyze_video_duration_error(client, sample_mp4):
    with patch("app.main.extract_frames") as mock:
        mock.side_effect = ValueError("Video duration (15.0s) exceeds the 10s limit.")
        response = client.post(
            "/api/analyze",
            files={"video": ("test.mp4", sample_mp4, "video/mp4")},
            data={"prompt": "Describe what happens"},
        )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "video"
    assert "duration" in data["error"]


# --- US5: Health check ---


def test_healthz_all_healthy(client):
    mock_response = AsyncMock()
    mock_response.status_code = 200
    with patch("app.main.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["fastapi_ok"] is True
    assert data["llama_server_ok"] is True
    assert "llama_server_url" in data


def test_healthz_llama_unreachable(client):
    import httpx as _httpx

    with patch("app.main.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = _httpx.ConnectError("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["fastapi_ok"] is True
    assert data["llama_server_ok"] is False
    assert "llama_server_url" in data


# --- Error handling: no stack traces (SC-004) ---


def test_validation_errors_have_no_stack_trace(client, sample_mp4):
    """All 400 errors return structured JSON without stack traces."""
    cases = [
        # Unsupported file type
        {
            "files": {"video": ("test.gif", io.BytesIO(b"GIF89a\x00" * 10), "image/gif")},
            "data": {"prompt": "Hello"},
            "expected_status": 400,
        },
        # Oversized video
        {
            "files": {"video": ("big.mp4", io.BytesIO(b"\x00" * (51 * 1024 * 1024)), "video/mp4")},
            "data": {"prompt": "Hello"},
            "expected_status": 400,
        },
        # Empty prompt
        {
            "files": {"video": ("test.mp4", sample_mp4, "video/mp4")},
            "data": {"prompt": ""},
            "expected_status": 400,
        },
        # Prompt too long
        {
            "files": {"video": ("test.mp4", io.BytesIO(b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100), "video/mp4")},
            "data": {"prompt": "x" * 2001},
            "expected_status": 400,
        },
    ]
    for case in cases:
        resp = client.post("/api/analyze", files=case["files"], data=case["data"])
        assert resp.status_code == case["expected_status"]
        body = resp.json()
        assert "error" in body
        assert "field" in body
        # No stack trace indicators
        raw = resp.text
        assert "Traceback" not in raw
        assert "File \"" not in raw
        assert "raise " not in raw


def test_503_error_has_no_stack_trace(client, sample_mp4, mock_extract_frames):
    """503 when llama-server unreachable contains no stack trace."""
    from app.llama_client import LlamaClientError

    with patch("app.main.analyze_video", new_callable=AsyncMock) as mock:
        mock.side_effect = LlamaClientError("down")
        resp = client.post(
            "/api/analyze",
            files={"video": ("test.mp4", sample_mp4, "video/mp4")},
            data={"prompt": "Describe"},
        )

    assert resp.status_code == 503
    body = resp.json()
    assert "error" in body
    raw = resp.text
    assert "Traceback" not in raw
    assert "File \"" not in raw


def test_500_global_handler_no_stack_trace(sample_mp4, mock_extract_frames):
    """Unhandled exceptions return generic error without stack trace."""
    safe_client = TestClient(app, raise_server_exceptions=False)
    with patch("app.main.analyze_video", new_callable=AsyncMock) as mock:
        mock.side_effect = RuntimeError("unexpected boom")
        resp = safe_client.post(
            "/api/analyze",
            files={"video": ("test.mp4", sample_mp4, "video/mp4")},
            data={"prompt": "Describe"},
        )

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Internal server error"
    raw = resp.text
    assert "Traceback" not in raw
    assert "unexpected boom" not in raw
