import base64
import json
from collections.abc import AsyncGenerator

import httpx

from app import config


class LlamaClientError(Exception):
    """Raised when the llama-server is unreachable or returns an error."""


SYSTEM_PROMPT = "You are a helpful assistant."

# NVIDIA's documented format to trigger chain-of-thought reasoning
# Matches the exact wording from the API docs curl example
REASONING_SUFFIX = (
    " \nAnswer the question in the following format: "
    "<think>\nyour reasoning\n</think>\n\n"
    "<answer>\nyour answer\n</answer>."
)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.MODEL_TIMEOUT_SECONDS),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


def _build_payload(image_bytes: bytes, mime_type: str, prompt: str, *, stream: bool = False) -> dict:
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{image_b64}"

    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt + REASONING_SUFFIX},
                ],
            },
        ],
        "max_tokens": config.MAX_GENERATION_TOKENS,
        "temperature": 0.3,
        "top_p": 0.3,
        "stream": stream,
    }


async def analyze_image(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Send an image and prompt to llama-server and return the model's response text."""
    payload = _build_payload(image_bytes, mime_type, prompt)

    try:
        client = _get_client()
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


async def stream_analyze_image(
    image_bytes: bytes, mime_type: str, prompt: str
) -> AsyncGenerator[dict, None]:
    """Stream tokens from llama-server as an async generator.

    Yields dicts: {"type": "thinking"|"content", "token": "..."}
    With --reasoning-format deepseek, llama.cpp puts thinking tokens in
    delta.reasoning_content and answer tokens in delta.content.
    Without it, everything comes through delta.content with inline tags.
    """
    payload = _build_payload(image_bytes, mime_type, prompt, stream=True)
    url = f"{config.LLAMA_SERVER_URL}/v1/chat/completions"

    try:
        client = _get_client()
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choice = chunk.get("choices", [{}])[0]
                if choice.get("finish_reason") == "stop":
                    return
                delta = choice.get("delta", {})
                reasoning = delta.get("reasoning_content")
                content = delta.get("content")
                if reasoning:
                    yield {"type": "thinking", "token": reasoning}
                if content:
                    yield {"type": "content", "token": content}
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise LlamaClientError("Inference backend is temporarily unavailable") from exc
    except httpx.HTTPStatusError as exc:
        raise LlamaClientError("Inference backend returned an error") from exc
