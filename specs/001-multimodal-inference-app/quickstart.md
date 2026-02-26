# Quickstart: Cosmos Reason2 Multimodal Inference Web Application

**Branch**: `001-multimodal-inference-app`

## Prerequisites

- macOS with Apple Silicon (M3 Pro or similar)
- Python 3.11+
- llama.cpp b7480+ compiled with Metal support
- ~6 GB disk space for model files
- `huggingface-cli` installed (`pip install huggingface-hub`)

## 1. Download Model Files

```bash
./scripts/download_models.sh
```

This downloads to `./models/`:
- `Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf` (~2.7 GB)
- `Cosmos-Reason2-2B-BF16-split-00002-of-00002.gguf` (~1.4 GB)
- `mmproj-Cosmos-Reason2-2B-BF16.gguf` (~0.9 GB)

## 2. Start llama-server

```bash
./scripts/start_llama_server.sh
```

Default settings: port 8080, 99 GPU layers (Metal), 8192 context, 6 threads.

Customize with environment variables:
```bash
MODEL_PATH=./models/custom.gguf PORT=9090 ./scripts/start_llama_server.sh
```

Verify it's running:
```bash
curl http://localhost:8080/health
```

## 3. Install Python Dependencies

```bash
pip install -e ".[dev]"
```

## 4. Start the Web Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5. Use the Application

1. Open `http://localhost:8000` in your browser
2. Drag and drop an image (JPEG, PNG, or WebP, up to 8 MB)
3. Enter a prompt (e.g., "Describe what you see in this image")
4. Click **Analyze**
5. Wait for the model response and latency display

## 6. Verify with curl

```bash
# Health check
curl http://localhost:8000/healthz

# Analyze an image
curl -F "prompt=Describe the scene" \
     -F "image=@examples/sample_image.jpg" \
     http://localhost:8000/api/analyze
```

## 7. Run Tests

```bash
pytest
```

Tests run with mocked llama-server — no model required.

## Environment Variables

| Variable              | Default                | Description                    |
| --------------------- | ---------------------- | ------------------------------ |
| LLAMA_SERVER_URL      | http://localhost:8080   | llama-server base URL          |
| MAX_UPLOAD_MB         | 8                      | Max image upload size (MB)     |
| MAX_PROMPT_LENGTH     | 2000                   | Max prompt characters          |
| MODEL_TIMEOUT_SECONDS | 120                    | llama-server request timeout   |
| MAX_GENERATION_TOKENS | 4096                   | Max tokens for model output    |
| ALLOWED_ORIGINS       | http://localhost:8000   | CORS allowed origins (comma-separated) |
