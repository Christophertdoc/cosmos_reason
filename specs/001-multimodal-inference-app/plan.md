# Implementation Plan: Cosmos Reason2 Multimodal Inference Web Application

**Branch**: `001-multimodal-inference-app` | **Date**: 2026-02-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-multimodal-inference-app/spec.md`

## Summary

Build a FastAPI web application that accepts image uploads and text prompts, forwards them to a locally-running llama-server instance (Cosmos-Reason2-2B GGUF model with Metal acceleration), and returns the model's natural language analysis response. The frontend is vanilla HTML/CSS/JS with drag-and-drop upload, image preview, and loading state management. The llama-server is managed independently via shell scripts and communicates over HTTP using the OpenAI-compatible `/v1/chat/completions` endpoint with base64-encoded images.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, uvicorn, httpx, python-multipart
**Storage**: N/A (stateless — no persistence required)
**Testing**: pytest with FastAPI TestClient, httpx mocking
**Target Platform**: macOS (Apple Silicon, M3 Pro, 18GB RAM)
**Project Type**: web-service (API + static frontend)
**Performance Goals**: Single-user sequential requests; inference response within 120 seconds; 3+ sequential requests without degradation
**Constraints**: Model ~4 GB BF16; context window limited to 8192–16384 tokens on 18GB RAM; llama.cpp b7480+ required for qwen3vl architecture
**Scale/Scope**: Single concurrent user, 1 page, 2 API endpoints, 1 external dependency (llama-server)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is unconfigured (template placeholders only). No gates to enforce. Proceeding with standard engineering best practices.

**Post-Phase 1 re-check**: No violations. Project structure is minimal and appropriate for scope.

## Project Structure

### Documentation (this feature)

```text
specs/001-multimodal-inference-app/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # HTTP API contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py              # FastAPI application, routes, static file serving
├── config.py            # Environment-based configuration
└── llama_client.py      # HTTP client for llama-server communication

app/static/
├── index.html           # Single-page UI
├── app.js               # Client-side logic (upload, validation, fetch)
└── styles.css           # Styling

tests/
├── __init__.py
├── test_api.py          # Integration tests for API endpoints
├── test_validation.py   # Unit tests for input validation logic
└── test_llama_client.py # Unit tests for llama client (mocked)

scripts/
├── start_llama_server.sh  # Launch llama-server with recommended settings
└── download_models.sh     # Download model + mmproj from HuggingFace

examples/
└── sample_image.jpg     # Sample image for smoke testing

pyproject.toml           # Project metadata and dependencies
README.md                # Setup, usage, and troubleshooting guide
```

**Structure Decision**: Single project with `app/` package for backend, `app/static/` for frontend assets, `tests/` at root level. This matches the spec's prescribed layout and is appropriate for a single-service application with vanilla JS frontend (no build step needed).

## Complexity Tracking

No complexity violations to track. The project is minimal by design.
