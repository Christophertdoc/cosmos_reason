import base64

import httpx

from app import config


class LlamaClientError(Exception):
    """Raised when the llama-server is unreachable or returns an error."""


async def analyze_image(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Send an image and prompt to llama-server and return the model's response text.

    Raises LlamaClientError if the server is unreachable, times out, or returns
    an unexpected response.
    """
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{image_b64}"

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": config.MAX_GENERATION_TOKENS,
        "temperature": 0.6,
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(config.MODEL_TIMEOUT_SECONDS)
        ) as client:
            response = await client.post(
                f"{config.LLAMA_SERVER_URL}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise LlamaClientError("Inference backend is temporarily unavailable") from exc
    except httpx.HTTPStatusError as exc:
        raise LlamaClientError("Inference backend returned an error") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlamaClientError("Unexpected response from inference backend") from exc
