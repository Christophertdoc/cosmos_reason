# Data Model: Cosmos Reason2 Multimodal Inference Web Application

**Date**: 2026-02-25
**Branch**: `001-multimodal-inference-app`

## Overview

This application is stateless — no persistent storage is used. All entities exist only for the duration of a single request-response cycle. This document defines the logical data structures exchanged between system components.

## Entities

### UploadedImage

Represents a user-uploaded image file received via multipart form data.

| Field         | Type   | Constraints                                      |
| ------------- | ------ | ------------------------------------------------ |
| content       | bytes  | Raw file bytes; max 8 MB (configurable)          |
| content_type  | string | Must be one of: image/jpeg, image/png, image/webp |
| filename      | string | Original filename from upload                    |

**Validation rules**:
- `content_type` must match allowed MIME types
- `len(content)` must not exceed configured max upload size
- Content is read once and held in memory for the request duration

### Prompt

Represents the user's text analysis instruction.

| Field  | Type   | Constraints                                      |
| ------ | ------ | ------------------------------------------------ |
| text   | string | Non-empty; max 2000 characters (configurable)    |

**Validation rules**:
- Must not be empty or whitespace-only
- Must not exceed configured max prompt length

### AnalysisResponse

Represents the system's response to a successful analysis request.

| Field            | Type   | Description                              |
| ---------------- | ------ | ---------------------------------------- |
| answer           | string | Model-generated natural language output  |
| latency_ms       | int    | Request processing time in milliseconds  |
| model            | string | Model identifier (e.g., "Cosmos-Reason2-2B-GGUF") |
| backend          | string | Backend identifier (e.g., "llama.cpp")   |
| llama_server_url | string | URL of the inference backend             |

### ValidationError

Represents a structured error response for invalid inputs.

| Field   | Type   | Description                          |
| ------- | ------ | ------------------------------------ |
| error   | string | Human-readable error message         |
| field   | string | Name of the invalid field (optional) |

### HealthStatus

Represents the system health check response.

| Field            | Type    | Description                               |
| ---------------- | ------- | ----------------------------------------- |
| fastapi_ok       | boolean | Whether the FastAPI service is operational |
| llama_server_ok  | boolean | Whether the llama-server is reachable      |
| llama_server_url | string  | Configured URL of the llama-server         |

## Relationships

```
User ──uploads──▶ UploadedImage ──┐
                                  ├──▶ llama-server ──▶ AnalysisResponse
User ──enters───▶ Prompt ─────────┘

User ──invalid input──▶ ValidationError
Operator ──GET /healthz──▶ HealthStatus
```

## State Transitions

No state transitions — all entities are ephemeral within a single HTTP request-response cycle. No data is persisted between requests.

## Configuration Entity

Environment-based configuration loaded at startup.

| Variable              | Type   | Default                  | Description                        |
| --------------------- | ------ | ------------------------ | ---------------------------------- |
| LLAMA_SERVER_URL      | string | http://localhost:8080     | llama-server base URL              |
| MAX_UPLOAD_MB         | int    | 8                        | Maximum image upload size in MB    |
| MAX_PROMPT_LENGTH     | int    | 2000                     | Maximum prompt character count     |
| MODEL_TIMEOUT_SECONDS | int    | 120                      | Timeout for llama-server requests  |
| MAX_GENERATION_TOKENS | int    | 4096                     | Max tokens for model output        |
| ALLOWED_ORIGINS       | string | http://localhost:8000     | Comma-separated CORS origins       |
