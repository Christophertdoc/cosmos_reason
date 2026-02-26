import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_jpeg():
    """A minimal valid JPEG file for testing."""
    return io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9")


# --- US1: Core analysis flow ---


def test_analyze_success(client, sample_jpeg):
    with patch("app.main.analyze_image", new_callable=AsyncMock) as mock:
        mock.return_value = "A scenic landscape with mountains."
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
            data={"prompt": "Describe the scene"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "A scenic landscape with mountains."
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
    assert data["model"] == "Cosmos-Reason2-2B-GGUF"
    assert data["backend"] == "llama.cpp"
    assert "llama_server_url" in data


def test_analyze_llama_unavailable(client, sample_jpeg):
    from app.llama_client import LlamaClientError

    with patch("app.main.analyze_image", new_callable=AsyncMock) as mock:
        mock.side_effect = LlamaClientError("unavailable")
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
            data={"prompt": "Describe the scene"},
        )

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert "temporarily unavailable" in data["error"]


# --- US2: Input validation ---


def test_analyze_missing_prompt(client, sample_jpeg):
    response = client.post(
        "/api/analyze",
        files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
        data={"prompt": ""},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "prompt"


def test_analyze_unsupported_file_type(client):
    gif_file = io.BytesIO(b"GIF89a" + b"\x00" * 100)
    response = client.post(
        "/api/analyze",
        files={"image": ("test.gif", gif_file, "image/gif")},
        data={"prompt": "Describe the scene"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "image"
    assert "Unsupported file type" in data["error"]


def test_analyze_oversized_image(client):
    large_file = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * (9 * 1024 * 1024))
    response = client.post(
        "/api/analyze",
        files={"image": ("big.jpg", large_file, "image/jpeg")},
        data={"prompt": "Describe the scene"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "image"
    assert "exceeds" in data["error"]


def test_analyze_prompt_too_long(client, sample_jpeg):
    long_prompt = "x" * 2001
    response = client.post(
        "/api/analyze",
        files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
        data={"prompt": long_prompt},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["field"] == "prompt"
    assert "exceeds maximum length" in data["error"]


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


def test_validation_errors_have_no_stack_trace(client, sample_jpeg):
    """All 400 errors return structured JSON without stack traces."""
    cases = [
        # Unsupported file type
        {
            "files": {"image": ("test.gif", io.BytesIO(b"GIF89a\x00" * 10), "image/gif")},
            "data": {"prompt": "Hello"},
            "expected_status": 400,
        },
        # Oversized image
        {
            "files": {"image": ("big.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * (9 * 1024 * 1024)), "image/jpeg")},
            "data": {"prompt": "Hello"},
            "expected_status": 400,
        },
        # Empty prompt
        {
            "files": {"image": ("test.jpg", sample_jpeg, "image/jpeg")},
            "data": {"prompt": ""},
            "expected_status": 400,
        },
        # Prompt too long
        {
            "files": {"image": ("test.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"), "image/jpeg")},
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


def test_503_error_has_no_stack_trace(client, sample_jpeg):
    """503 when llama-server unreachable contains no stack trace."""
    from app.llama_client import LlamaClientError

    with patch("app.main.analyze_image", new_callable=AsyncMock) as mock:
        mock.side_effect = LlamaClientError("down")
        resp = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
            data={"prompt": "Describe"},
        )

    assert resp.status_code == 503
    body = resp.json()
    assert "error" in body
    raw = resp.text
    assert "Traceback" not in raw
    assert "File \"" not in raw


def test_500_global_handler_no_stack_trace(sample_jpeg):
    """Unhandled exceptions return generic error without stack trace."""
    safe_client = TestClient(app, raise_server_exceptions=False)
    with patch("app.main.analyze_image", new_callable=AsyncMock) as mock:
        mock.side_effect = RuntimeError("unexpected boom")
        resp = safe_client.post(
            "/api/analyze",
            files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
            data={"prompt": "Describe"},
        )

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Internal server error"
    raw = resp.text
    assert "Traceback" not in raw
    assert "unexpected boom" not in raw
