# Research: Cosmos Reason2 Inference Web Application

**Date**: 2026-02-25
**Branch**: `001-multimodal-inference-app`

## R1: Model Files and Download

**Decision**: Use the split BF16 GGUF files directly (no merge required — llama-server handles split files natively via the first split file path).

**Rationale**: The repository provides `Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf`, `Cosmos-Reason2-2B-BF16-split-00002-of-00002.gguf`, and `mmproj-Cosmos-Reason2-2B-BF16.gguf`. llama-server automatically loads split GGUF files when pointed at the first part. Merging is optional and adds a manual step.

**Alternatives considered**:
- Merge into single file using `llama-gguf-split --merge`: Viable but unnecessary overhead for local development. Can be documented as optional in README.

## R2: llama.cpp Version Requirement

**Decision**: Require llama.cpp b7480 or later.

**Rationale**: The Cosmos-Reason2-2B model uses the `qwen3vl` architecture, which was added in llama.cpp b7480. Earlier versions will fail to load the model.

**Alternatives considered**: None — this is a hard requirement.

## R3: Multimodal Request Format

**Decision**: Use the OpenAI-compatible `/v1/chat/completions` endpoint with base64-encoded images in the `image_url` content part.

**Rationale**: llama-server exposes an OpenAI-compatible endpoint that accepts the standard vision message format. Images are sent as `data:image/{format};base64,{data}` in an `image_url` content part alongside a `text` content part. This is the same format used by OpenAI GPT-4V and is well-documented.

**Alternatives considered**:
- Direct file upload to llama-server: Not supported by the OpenAI-compatible endpoint.
- URL-based image reference: Requires the image to be hosted; base64 is simpler for local file uploads.

## R4: Recommended llama-server Parameters for M3 Pro (18GB)

**Decision**: Use the following default parameters:
- `-ngl 99` (offload all layers to Metal GPU)
- `-c 8192` (context length — safe default)
- `-t 6` (threads — matches M3 Pro performance cores)
- `-b 512` (batch size — default)
- `--port 8080`

**Rationale**: The 2B BF16 model is ~4 GB, fitting comfortably in 18GB unified memory with ample room for KV cache at 8192 context. Using 6 threads targets the M3 Pro's 6 performance cores for optimal throughput. All GPU layers offloaded for Metal acceleration.

**Alternatives considered**:
- `-c 16384`: Feasible but doubles KV cache memory; 8192 is sufficient for single image + prompt use case.
- `-t 8`: Slightly more threads; 6 is more conservative and avoids contention with efficiency cores.

## R5: Max Tokens for Model Output

**Decision**: Default `max_tokens` to 4096 (configurable via environment variable `MAX_GENERATION_TOKENS`).

**Rationale**: The model produces chain-of-thought reasoning responses that can be verbose. 4096 tokens provides sufficient room for detailed responses without risking premature truncation.

**Alternatives considered**:
- 1024: May truncate reasoning chains.
- 8192: Unnecessarily large for most single-image analysis tasks; wastes KV cache.

## R6: FastAPI-to-llama-server Communication

**Decision**: Use `httpx.AsyncClient` with configurable timeout (default 120 seconds).

**Rationale**: httpx is the recommended async HTTP client for FastAPI applications. It supports async/await natively, has clean timeout handling, and is already a project dependency. The 120-second timeout accommodates slow inference on complex prompts.

**Alternatives considered**:
- `aiohttp`: Viable but httpx has better ergonomics and is more commonly used with FastAPI.
- `requests`: Synchronous — would block the event loop.

## R7: Image Encoding Strategy

**Decision**: Read the uploaded image bytes in FastAPI, base64-encode them, and embed in the OpenAI-compatible request payload as `data:image/{mime};base64,{data}`.

**Rationale**: This is the format expected by llama-server's `/v1/chat/completions` endpoint. The image is already in memory from the multipart upload, so base64 encoding is straightforward with minimal overhead for images under 8 MB.

**Alternatives considered**:
- Save to disk and pass URL: Adds complexity and requires llama-server to have filesystem access to the same path.
