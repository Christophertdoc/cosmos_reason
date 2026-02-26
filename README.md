# Cosmos Reason2 Multimodal Inference

A web application for multimodal image analysis powered by [Cosmos-Reason2-2B](https://huggingface.co/robertzty/Cosmos-Reason2-2B-GGUF) running via llama.cpp.

Upload an image, enter a text prompt, and receive a natural language response from the model.

## Prerequisites

- **macOS** with Apple Silicon (M3 Pro or similar, 18 GB+ RAM)
- **Python 3.11+**
- **llama.cpp b7480+** compiled with Metal support (required for `qwen3vl` architecture) — install with `brew install llama.cpp`
- **huggingface-cli** (`pip install huggingface-hub`)
- ~6 GB disk space for model files

## Setup

### 1. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" huggingface-hub
```

### 2. Download Model Files

```bash
./scripts/download_models.sh
```

Downloads to `./models/`:
- `Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf` (~2.7 GB)
- `Cosmos-Reason2-2B-BF16-split-00002-of-00002.gguf` (~1.4 GB)
- `mmproj-Cosmos-Reason2-2B-BF16.gguf` (~0.9 GB)

llama-server handles split GGUF files natively — no merge required.

### 3. Start llama-server

```bash
./scripts/start_llama_server.sh
```

Default settings optimized for M3 Pro 18 GB:
- Port 8080
- 99 GPU layers (full Metal offload)
- 8192 context length
- 6 threads (M3 Pro performance cores)
- 512 batch size

Customize with environment variables:

```bash
MODEL_PATH=./models/custom.gguf PORT=9090 ./scripts/start_llama_server.sh
```

Verify it's running:

```bash
curl http://localhost:8080/health
```

### 4. Start the Web Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

## Usage

1. Drag and drop an image (JPEG, PNG, or WebP, up to 8 MB) or click to upload
2. Enter a prompt (e.g., "Describe what you see in this image")
3. Click **Analyze**
4. View the model's response and request latency

## Running Tests

```bash
pytest
```

Tests run with a mocked llama-server — no model download required.

## Example curl Commands

```bash
# Health check
curl http://localhost:8000/healthz

# Analyze an image
curl -F "prompt=Describe the scene" \
     -F "image=@examples/sample_image.jpg" \
     http://localhost:8000/api/analyze
```

## Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `LLAMA_SERVER_URL` | `http://localhost:8080` | llama-server base URL |
| `MAX_UPLOAD_MB` | `8` | Max image upload size (MB) |
| `MAX_PROMPT_LENGTH` | `2000` | Max prompt characters |
| `MODEL_TIMEOUT_SECONDS` | `120` | llama-server request timeout (seconds) |
| `MAX_GENERATION_TOKENS` | `4096` | Max tokens for model output |
| `ALLOWED_ORIGINS` | `http://localhost:8000` | CORS allowed origins (comma-separated) |

## Troubleshooting

**llama-server not found**
Install llama.cpp b7480+ from https://github.com/ggml-org/llama.cpp. Ensure `llama-server` is in your PATH.

**Model fails to load**
The Cosmos-Reason2-2B model uses the `qwen3vl` architecture, which requires llama.cpp b7480 or later. Check your version with `llama-server --version`.

**503 Service Unavailable from /api/analyze**
The FastAPI app cannot reach llama-server. Verify it's running on the expected port:
```bash
curl http://localhost:8080/health
```

**Slow responses**
Ensure all GPU layers are offloaded (default: `-ngl 99`). First request may be slower due to model warmup.

**Out of memory**
Reduce context size: `CTX_SIZE=4096 ./scripts/start_llama_server.sh`

## Apple Silicon Performance Tuning

- **GPU offload**: Use `-ngl 99` to offload all layers to Metal (default)
- **Threads**: Set to match your performance core count (6 for M3 Pro, 8 for M3 Max)
- **Context size**: 8192 is safe for 18 GB; reduce to 4096 if running other memory-intensive apps
- **Batch size**: 512 is a good default; increase to 1024 if you have headroom
- The 2B BF16 model (~4 GB) fits comfortably in 18 GB unified memory with ample room for KV cache

## Project Structure

```
app/
  main.py            # FastAPI application and endpoints
  config.py          # Environment variable configuration
  llama_client.py    # Async HTTP client for llama-server
  static/
    index.html       # Web UI
    app.js           # Frontend logic
    styles.css       # Styling
tests/
  test_api.py        # API integration tests
  test_validation.py # Configuration validation tests
  test_llama_client.py # Llama client unit tests
scripts/
  download_models.sh # Model download script
  start_llama_server.sh # llama-server launcher
examples/
  sample_image.jpg   # Sample image for smoke testing
```

## Frontend Manual Test Checklist

- [ ] Drag and drop image onto upload zone works
- [ ] Click-to-upload via file picker works
- [ ] Image preview renders immediately after selection
- [ ] Loading spinner appears during request
- [ ] Analyze button disables during request
- [ ] Model answer renders correctly on success
- [ ] Latency displays in milliseconds
- [ ] Inline error for missing image
- [ ] Inline error for empty prompt
- [ ] Inline error for unsupported file type
- [ ] Inline error for oversized file
- [ ] Error message displays on server error (503)
