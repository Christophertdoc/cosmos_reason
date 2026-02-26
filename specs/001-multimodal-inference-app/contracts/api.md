# API Contract: Cosmos Reason2 Multimodal Inference

**Date**: 2026-02-25
**Base URL**: `http://localhost:8000`

## Endpoints

### GET /

Serves the static HTML frontend.

**Response**: `200 OK` with `text/html` content.

---

### GET /healthz

Returns system health status.

**Response** `200 OK`:
```json
{
  "fastapi_ok": true,
  "llama_server_ok": true,
  "llama_server_url": "http://localhost:8080"
}
```

When llama-server is unreachable:
```json
{
  "fastapi_ok": true,
  "llama_server_ok": false,
  "llama_server_url": "http://localhost:8080"
}
```

---

### POST /api/analyze

Accepts an image and text prompt, returns model analysis.

**Request**: `multipart/form-data`

| Field  | Type   | Required | Constraints                          |
| ------ | ------ | -------- | ------------------------------------ |
| image  | file   | Yes      | JPEG, PNG, or WebP; max 8 MB         |
| prompt | string | Yes      | Non-empty; max 2000 characters       |

**Response** `200 OK`:
```json
{
  "answer": "The image shows a scenic mountain landscape with a lake in the foreground...",
  "latency_ms": 3421,
  "model": "Cosmos-Reason2-2B-GGUF",
  "backend": "llama.cpp",
  "llama_server_url": "http://localhost:8080"
}
```

**Error Responses**:

`400 Bad Request` — validation failure:
```json
{
  "error": "Unsupported file type. Allowed: image/jpeg, image/png, image/webp",
  "field": "image"
}
```

```json
{
  "error": "File size exceeds the 8 MB limit",
  "field": "image"
}
```

```json
{
  "error": "Prompt is required",
  "field": "prompt"
}
```

```json
{
  "error": "Prompt exceeds maximum length of 2000 characters",
  "field": "prompt"
}
```

`503 Service Unavailable` — llama-server unreachable or timed out:
```json
{
  "error": "Inference backend is temporarily unavailable"
}
```

---

## Internal: FastAPI → llama-server

**Endpoint**: `POST {LLAMA_SERVER_URL}/v1/chat/completions`

**Request**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe the scene"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
          }
        }
      ]
    }
  ],
  "max_tokens": 4096,
  "temperature": 0.6
}
```

**Response** (OpenAI-compatible):
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "The image shows..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

**Timeout**: 120 seconds (configurable via `MODEL_TIMEOUT_SECONDS`).
**Failure handling**: `httpx.ConnectError` or `httpx.TimeoutException` → return `503` to client.
