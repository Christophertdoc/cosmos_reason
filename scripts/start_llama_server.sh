#!/usr/bin/env bash
# Start llama-server for Cosmos-Reason2-2B GGUF with Metal acceleration.
#
# Prerequisites:
#   - llama.cpp b7480 or later (required for qwen3vl architecture)
#   - Compiled with Metal support (default on macOS Apple Silicon)
#   - Model files downloaded via scripts/download_models.sh
#
# Recommended hardware: Apple Silicon M3 Pro or better, 18GB+ RAM
#
# Environment variables:
#   MODEL_PATH  - Path to the GGUF model file (first split)
#   MMPROJ_PATH - Path to the mmproj GGUF file
#   PORT        - Server port (default: 8080)
#   CTX_SIZE    - Context size (default: 8192)
#   THREADS     - Number of threads (default: 6, matches M3 Pro perf cores)
#   GPU_LAYERS  - GPU layers to offload (default: 99, all layers)
#   BATCH_SIZE  - Batch size (default: 512)

set -euo pipefail

MODEL_DIR="${MODEL_DIR:-./models}"
MODEL_PATH="${MODEL_PATH:-${MODEL_DIR}/Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-${MODEL_DIR}/mmproj-Cosmos-Reason2-2B-BF16.gguf}"
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-8192}"
THREADS="${THREADS:-6}"
GPU_LAYERS="${GPU_LAYERS:-99}"
BATCH_SIZE="${BATCH_SIZE:-512}"

echo "=== Cosmos-Reason2-2B llama-server ==="
echo "Model:    ${MODEL_PATH}"
echo "MMProj:   ${MMPROJ_PATH}"
echo "Port:     ${PORT}"
echo "Context:  ${CTX_SIZE}"
echo "Threads:  ${THREADS}"
echo "GPU Layers: ${GPU_LAYERS}"
echo "Batch:    ${BATCH_SIZE}"
echo ""

if ! command -v llama-server &> /dev/null; then
    echo "ERROR: llama-server not found in PATH."
    echo "Install llama.cpp b7480+ from: https://github.com/ggml-org/llama.cpp"
    exit 1
fi

if [ ! -f "${MODEL_PATH}" ]; then
    echo "ERROR: Model file not found: ${MODEL_PATH}"
    echo "Run scripts/download_models.sh first."
    exit 1
fi

if [ ! -f "${MMPROJ_PATH}" ]; then
    echo "ERROR: MMProj file not found: ${MMPROJ_PATH}"
    echo "Run scripts/download_models.sh first."
    exit 1
fi

echo "Starting llama-server..."
echo "Endpoint: http://localhost:${PORT}"
echo ""

exec llama-server \
    -m "${MODEL_PATH}" \
    --mmproj "${MMPROJ_PATH}" \
    -ngl "${GPU_LAYERS}" \
    -c "${CTX_SIZE}" \
    -t "${THREADS}" \
    -b "${BATCH_SIZE}" \
    --port "${PORT}"
