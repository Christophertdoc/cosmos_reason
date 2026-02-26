from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.llama_client import LlamaClientError, analyze_image


@pytest.fixture
def successful_response():
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": "A scenic landscape."},
                "finish_reason": "stop",
            }
        ]
    }


@pytest.mark.asyncio
async def test_analyze_image_success(successful_response):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = successful_response
    mock_response.raise_for_status = Mock()

    with patch("app.llama_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await analyze_image(b"\xff\xd8\xff\xe0", "image/jpeg", "Describe this")

    assert result == "A scenic landscape."


@pytest.mark.asyncio
async def test_analyze_image_timeout():
    with patch("app.llama_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(LlamaClientError, match="temporarily unavailable"):
            await analyze_image(b"\xff\xd8\xff\xe0", "image/jpeg", "Describe this")


@pytest.mark.asyncio
async def test_analyze_image_connection_error():
    with patch("app.llama_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(LlamaClientError, match="temporarily unavailable"):
            await analyze_image(b"\xff\xd8\xff\xe0", "image/jpeg", "Describe this")


@pytest.mark.asyncio
async def test_analyze_image_unexpected_response():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"unexpected": "shape"}
    mock_response.raise_for_status = Mock()

    with patch("app.llama_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(LlamaClientError, match="Unexpected response"):
            await analyze_image(b"\xff\xd8\xff\xe0", "image/jpeg", "Describe this")
