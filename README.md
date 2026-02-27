# Cosmos Reason2 Inference

World models have some understanding of how the physical world works ... they're used for autonomous driving, robotics, and interactive virtual environments. But they typically require large amounts of compute to run.

This project lets you run [NVIDIA's Cosmos Reason](https://huggingface.co/nvidia/Cosmos-Reason2-2B) world model locally on consumer hardware. It uses [Tingyu Zhang's GGUF conversion](https://huggingface.co/robertzty/Cosmos-Reason2-2B-GGUF) of the model, paired with [llama.cpp](https://github.com/ggml-org/llama.cpp), a lightweight C++ engine that runs models locally without heavy GPU frameworks.

Upload an image, enter a text prompt, and receive a natural language response from the model ... all running on your own machine.

## Prerequisites

- **Python 3.11+**
- **llama.cpp b7480+** (required for `qwen3vl` architecture) — install with `brew install llama.cpp` on macOS or [build from source](https://github.com/ggml-org/llama.cpp)
- **16 GB+ RAM** (the 2B BF16 model is ~4 GB plus KV cache)
- ~6 GB disk space for model files

Default settings in `scripts/start_llama_server.sh` are tuned for Apple Silicon with Metal GPU offload. For other platforms, adjust `GPU_LAYERS` and `THREADS` via environment variables (see [Configuration](#configuration)).

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

Default settings:
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
| `MAX_GENERATION_TOKENS` | `1024` | Max tokens for model output |
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
Images over 100 KB are automatically compressed and resized server-side before inference. Ensure all GPU layers are offloaded (default: `-ngl 99`). First request may be slower due to model warmup.

**Out of memory**
Reduce context size: `CTX_SIZE=4096 ./scripts/start_llama_server.sh`
