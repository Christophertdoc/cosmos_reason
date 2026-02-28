import json
import logging
import time
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

import httpx

from app import config
from app.video_utils import extract_frames
from app.llama_client import LlamaClientError, analyze_video, stream_analyze_video, close_client

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    yield
    await close_client()


app = FastAPI(title="Cosmos Reason2 Inference", lifespan=lifespan)

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
async def analyze(video: UploadFile, prompt: str = Form("")) -> JSONResponse:
    # Validate video MIME type
    if video.content_type not in config.ALLOWED_MIME_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported file type. Allowed: {', '.join(sorted(config.ALLOWED_MIME_TYPES))}",
                "field": "video",
            },
        )

    # Read and validate video size
    video_bytes = await video.read()
    if len(video_bytes) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"File size exceeds the {config.MAX_UPLOAD_MB} MB limit",
                "field": "video",
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

    # Extract frames from video
    try:
        frames = extract_frames(video_bytes)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "field": "video"},
        )

    # Call llama-server
    start = time.monotonic()
    try:
        answer = await analyze_video(frames, prompt)
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


@app.post("/api/analyze/stream")
async def analyze_stream(video: UploadFile, prompt: str = Form("")):
    # Validate video MIME type
    if video.content_type not in config.ALLOWED_MIME_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported file type. Allowed: {', '.join(sorted(config.ALLOWED_MIME_TYPES))}",
                "field": "video",
            },
        )

    # Read and validate video size
    video_bytes = await video.read()
    if len(video_bytes) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"File size exceeds the {config.MAX_UPLOAD_MB} MB limit",
                "field": "video",
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

    # Extract frames from video
    try:
        frames = extract_frames(video_bytes)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "field": "video"},
        )

    async def event_generator():
        start = time.monotonic()
        try:
            async for event in stream_analyze_video(frames, prompt):
                yield json.dumps(event)
        except LlamaClientError:
            yield json.dumps({"error": "Inference backend is temporarily unavailable"})
            return
        elapsed_ms = int((time.monotonic() - start) * 1000)
        yield json.dumps({"done": True, "latency_ms": elapsed_ms})

    return EventSourceResponse(event_generator())
