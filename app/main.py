import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import httpx

from app import config
from app.image_utils import compress_image
from app.llama_client import LlamaClientError, analyze_image

logger = logging.getLogger(__name__)

app = FastAPI(title="Cosmos Reason2 Inference")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/healthz")
async def healthz() -> JSONResponse:
    llama_ok = False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{config.LLAMA_SERVER_URL}/health")
            llama_ok = resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        llama_ok = False

    return JSONResponse(
        content={
            "fastapi_ok": True,
            "llama_server_ok": llama_ok,
            "llama_server_url": config.LLAMA_SERVER_URL,
        }
    )


@app.post("/api/analyze")
async def analyze(image: UploadFile, prompt: str = Form("")) -> JSONResponse:
    # Validate image MIME type
    if image.content_type not in config.ALLOWED_MIME_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported file type. Allowed: {', '.join(sorted(config.ALLOWED_MIME_TYPES))}",
                "field": "image",
            },
        )

    # Read and validate image size
    image_bytes = await image.read()
    if len(image_bytes) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"File size exceeds the {config.MAX_UPLOAD_MB} MB limit",
                "field": "image",
            },
        )

    # Validate prompt
    prompt = prompt.strip()
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Prompt is required", "field": "prompt"},
        )
    if len(prompt) > config.MAX_PROMPT_LENGTH:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Prompt exceeds maximum length of {config.MAX_PROMPT_LENGTH} characters",
                "field": "prompt",
            },
        )

    # Compress image if over 100 KB
    image_bytes, mime_type = compress_image(image_bytes, image.content_type)

    # Call llama-server
    start = time.monotonic()
    try:
        answer = await analyze_image(image_bytes, mime_type, prompt)
    except LlamaClientError:
        return JSONResponse(
            status_code=503,
            content={"error": "Inference backend is temporarily unavailable"},
        )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    return JSONResponse(
        content={
            "answer": answer,
            "latency_ms": elapsed_ms,
            "model": "Cosmos-Reason2-2B-GGUF",
            "backend": "llama.cpp",
            "llama_server_url": config.LLAMA_SERVER_URL,
        }
    )
