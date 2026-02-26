#!/usr/bin/env bash
# Download Cosmos-Reason2-2B GGUF model files from HuggingFace.
# Requires: huggingface-cli (pip install huggingface-hub)
#
# Model source: https://huggingface.co/robertzty/Cosmos-Reason2-2B-GGUF
# Files downloaded:
#   - Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf (language model part 1)
#   - Cosmos-Reason2-2B-BF16-split-00002-of-00002.gguf (language model part 2)
#   - mmproj-Cosmos-Reason2-2B-BF16.gguf (multimodal projector)

set -euo pipefail

MODEL_DIR="${MODEL_DIR:-./models}"
REPO_ID="robertzty/Cosmos-Reason2-2B-GGUF"

echo "=== Cosmos-Reason2-2B GGUF Model Download ==="
echo "Destination: ${MODEL_DIR}"
echo "Repository:  ${REPO_ID}"
echo ""

if command -v huggingface-cli &> /dev/null; then
    HF_CLI="huggingface-cli"
elif command -v hf &> /dev/null; then
    HF_CLI="hf"
else
    echo "ERROR: huggingface-cli (or hf) not found."
    echo "Install with: pip install huggingface-hub"
    exit 1
fi

mkdir -p "${MODEL_DIR}"

echo "Downloading model files (~4 GB total)..."
"${HF_CLI}" download "${REPO_ID}" --local-dir "${MODEL_DIR}"

echo ""
echo "=== Download complete ==="
echo "Model files in: ${MODEL_DIR}"
ls -lh "${MODEL_DIR}"/*.gguf 2>/dev/null || echo "WARNING: No .gguf files found in ${MODEL_DIR}"
