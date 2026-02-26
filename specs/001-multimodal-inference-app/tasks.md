# Tasks: Cosmos Reason2 Multimodal Inference Web Application

**Input**: Design documents from `/specs/001-multimodal-inference-app/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested in feature specification (pytest, FastAPI TestClient, mocked llama client).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and tooling scripts

- [ ] T001 Create project directory structure: `app/`, `app/static/`, `tests/`, `scripts/`, `examples/` with `__init__.py` files in `app/` and `tests/`
- [ ] T002 Create `pyproject.toml` with project metadata and dependencies: fastapi, uvicorn[standard], httpx, python-multipart, pytest, httpx (dev)
- [ ] T003 [P] Create `scripts/download_models.sh` that downloads Cosmos-Reason2-2B-GGUF files (both split model files + mmproj) from HuggingFace to `./models/` using `huggingface-cli download` per research.md R1
- [ ] T004 [P] Create `scripts/start_llama_server.sh` that launches llama-server with configurable MODEL_PATH, MMPROJ_PATH, PORT (default 8080), `-ngl 99 -c 8192 -t 6 -b 512` per research.md R4, requires llama.cpp b7480+ per R2
- [ ] T005 [P] Add `examples/sample_image.jpg` — a small sample JPEG image for smoke testing curl commands

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend modules that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement configuration module in `app/config.py` — load all environment variables from data-model.md Configuration Entity table: LLAMA_SERVER_URL, MAX_UPLOAD_MB, MAX_PROMPT_LENGTH, MODEL_TIMEOUT_SECONDS, MAX_GENERATION_TOKENS, ALLOWED_ORIGINS with documented defaults
- [ ] T007 Implement llama client module in `app/llama_client.py` — async function that accepts image bytes, MIME type, and prompt text; base64-encodes the image; sends OpenAI-compatible `/v1/chat/completions` request per contracts/api.md Internal section; returns answer text; handles `httpx.ConnectError` and `httpx.TimeoutException` per research.md R3, R6, R7
- [ ] T008 Create FastAPI application skeleton in `app/main.py` — initialize FastAPI app, configure CORS middleware with ALLOWED_ORIGINS from config, mount `app/static` directory for static file serving, add GET `/` route that serves `app/static/index.html`, add global exception handler that returns structured JSON errors without stack traces

**Checkpoint**: Foundation ready — config loads, llama client can communicate, FastAPI serves static files

---

## Phase 3: User Story 1 — Analyze an Image with a Text Prompt (Priority: P1) 🎯 MVP

**Goal**: Users upload an image, enter a prompt, click Analyze, and receive the model's natural language response with latency display.

**Independent Test**: Upload a JPEG image, enter "Describe what you see," click Analyze, verify response text and latency_ms appear.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Write llama client unit tests in `tests/test_llama_client.py` — mock httpx responses: successful completion response (extract answer from choices[0].message.content), timeout exception (raise httpx.TimeoutException), connection error (raise httpx.ConnectError), unexpected response shape
- [ ] T010 [P] [US1] Write API integration tests for POST `/api/analyze` in `tests/test_api.py` — using FastAPI TestClient with mocked llama_client: valid JPEG image + prompt returns 200 with answer/latency_ms/model/backend/llama_server_url fields per contracts/api.md; llama-server unavailable returns 503 with structured error

### Implementation for User Story 1

- [ ] T011 [US1] Implement POST `/api/analyze` endpoint in `app/main.py` — accept multipart form data (image: UploadFile, prompt: str), read image bytes, measure latency with time.monotonic, call llama_client, return AnalysisResponse JSON per contracts/api.md; catch llama client errors and return 503
- [ ] T012 [US1] Create HTML page in `app/static/index.html` — page title, upload zone div (with click-to-upload via hidden file input), multi-line textarea for prompt, "Analyze" submit button, results display area (answer text + latency), error display area
- [ ] T013 [P] [US1] Create base CSS in `app/static/styles.css` — responsive desktop layout, upload zone styling, textarea styling, button styling, results area styling, basic typography
- [ ] T014 [US1] Implement form submission in `app/static/app.js` — on Analyze click: build FormData with image file and prompt text, POST to `/api/analyze`, on success render answer text and latency_ms in results area, on error render error message

**Checkpoint**: Core analysis flow works end-to-end — User Story 1 is fully functional and independently testable

---

## Phase 4: User Story 2 — Input Validation and Error Feedback (Priority: P2)

**Goal**: Users receive clear inline validation messages for invalid inputs (missing image, empty prompt, wrong file type, oversized file, prompt too long) before the request is sent.

**Independent Test**: Attempt each invalid input scenario and verify the correct inline error message appears without page reload.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US2] Write validation unit tests in `tests/test_validation.py` — test MIME type validation (accept jpeg/png/webp, reject gif/bmp/pdf), file size validation (accept under limit, reject over limit), prompt validation (reject empty/whitespace, reject over max length, accept valid), configuration values applied correctly
- [ ] T016 [P] [US2] Write API validation integration tests in `tests/test_api.py` — POST `/api/analyze` with: missing image returns 400, missing prompt returns 400, unsupported file type returns 400 with field:"image", oversized image returns 400 with field:"image", prompt too long returns 400 with field:"prompt" — all per contracts/api.md error response format

### Implementation for User Story 2

- [ ] T017 [US2] Add server-side input validation to POST `/api/analyze` in `app/main.py` — validate image content_type against allowed MIME types, validate image size against MAX_UPLOAD_MB, validate prompt non-empty and length against MAX_PROMPT_LENGTH, return 400 with `{"error": "...", "field": "..."}` per contracts/api.md error format
- [ ] T018 [US2] Add client-side validation in `app/static/app.js` — before form submission: check image selected (show "Please upload an image"), check prompt non-empty (show "Please enter a prompt"), check file type on selection (show "Unsupported file type. Please use JPEG, PNG, or WebP"), check file size on selection (show "File size exceeds the 8 MB limit"), check prompt length (show max length message); display errors inline near relevant input
- [ ] T019 [US2] Add validation error styling in `app/static/styles.css` — inline error message styling (color, positioning near input fields), error state borders on inputs

**Checkpoint**: All validation scenarios produce correct inline messages — User Story 2 independently testable

---

## Phase 5: User Story 3 — Loading State and Response Display (Priority: P2)

**Goal**: Users see a loading indicator and disabled button during processing, and clear response/latency display or error message on completion.

**Independent Test**: Submit a valid request, observe button disables + loading indicator appears, then response and latency render on completion.

### Implementation for User Story 3

- [ ] T020 [US3] Implement loading state management in `app/static/app.js` — on submit: disable Analyze button, show loading spinner/indicator, hide previous results; on success: hide spinner, re-enable button, display answer and latency_ms; on error (503/timeout): hide spinner, re-enable button, display "Service temporarily unavailable" message
- [ ] T021 [US3] Add loading state CSS in `app/static/styles.css` — spinner animation, disabled button styles (opacity, cursor), latency display formatting

**Checkpoint**: Loading states work correctly for success, error, and timeout — User Story 3 independently testable

---

## Phase 6: User Story 4 — Image Preview (Priority: P3)

**Goal**: Users see a thumbnail preview of their selected image immediately after drag-and-drop or file picker selection.

**Independent Test**: Drag an image onto the upload zone or click to select — preview renders immediately; select a different image — preview updates.

### Implementation for User Story 4

- [ ] T022 [US4] Implement drag-and-drop and image preview in `app/static/app.js` — add dragover/dragleave/drop event handlers to upload zone, read dropped/selected file with FileReader.readAsDataURL, render preview img element in upload zone, update preview on re-selection, set file reference for form submission
- [ ] T023 [US4] Add drag-and-drop and preview styling in `app/static/styles.css` — drop zone hover/active state (border highlight), image preview sizing and containment, drop zone visual affordance ("Drag image here or click to upload" text)

**Checkpoint**: Image preview works for both drag-and-drop and click-to-upload — User Story 4 independently testable

---

## Phase 7: User Story 5 — System Health Verification (Priority: P3)

**Goal**: Operators can check a health endpoint to verify both FastAPI and llama-server are operational.

**Independent Test**: GET `/healthz` returns JSON with fastapi_ok, llama_server_ok, and llama_server_url fields.

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T024 [P] [US5] Write health endpoint tests in `tests/test_api.py` — GET `/healthz` with mocked llama-server healthy returns `{"fastapi_ok": true, "llama_server_ok": true, "llama_server_url": "..."}`, with mocked llama-server unreachable returns `{"fastapi_ok": true, "llama_server_ok": false, "llama_server_url": "..."}`

### Implementation for User Story 5

- [ ] T025 [US5] Implement GET `/healthz` endpoint in `app/main.py` — check llama-server reachability (GET to llama-server health or /v1/models), return HealthStatus JSON per contracts/api.md, always return 200 (even if llama-server is down)

**Checkpoint**: Health endpoint returns accurate status — User Story 5 independently testable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, comprehensive error handling tests, and final validation

- [ ] T026 [P] Write error handling integration tests in `tests/test_api.py` — confirm 400 for all validation errors, 503 when llama-server unreachable, verify no stack traces in any error response (SC-004)
- [ ] T027 [P] Create `README.md` with: prerequisites (Python 3.11+, llama.cpp b7480+, Apple Silicon), model download steps, llama-server startup instructions, FastAPI startup command, running tests, example curl commands per quickstart.md, troubleshooting section, Apple Silicon performance tuning notes per research.md R4
- [ ] T028 Run full test suite (`pytest`) and validate all tests pass, verify quickstart.md steps work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational phase completion
  - US1 (P1) should complete first as MVP
  - US2 and US3 (both P2) can proceed after US1 or in parallel
  - US4 and US5 (both P3) can proceed independently after Foundational
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Phase 2 — Adds validation to the endpoint and UI built in US1, but is independently testable
- **User Story 3 (P2)**: Can start after Phase 2 — Adds loading states to the UI built in US1, but is independently testable
- **User Story 4 (P3)**: Can start after Phase 2 — Adds preview to the upload zone built in US1, but is independently testable
- **User Story 5 (P3)**: Can start after Phase 2 — Fully independent (new endpoint, no UI dependency)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend before frontend (when both exist in a story)
- Core implementation before styling
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004, T005 can run in parallel (different script files)
- T009, T010 can run in parallel (different test files)
- T012, T013 can run in parallel (HTML and CSS are independent)
- T015, T016 can run in parallel (different test files)
- T026, T027 can run in parallel (tests and docs are independent)
- US5 can run in parallel with US2, US3, or US4 (fully independent endpoint)

---

## Parallel Example: User Story 1

```text
# Launch tests in parallel:
Task: "Write llama client unit tests in tests/test_llama_client.py" (T009)
Task: "Write API integration tests for POST /api/analyze in tests/test_api.py" (T010)

# Launch HTML and CSS in parallel (after tests):
Task: "Create HTML page in app/static/index.html" (T012)
Task: "Create base CSS in app/static/styles.css" (T013)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T008)
3. Complete Phase 3: User Story 1 (T009–T014)
4. **STOP and VALIDATE**: Upload an image, enter a prompt, click Analyze, verify response
5. Deploy/demo if ready — core analysis works

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP!
3. Add User Story 2 → Validation protects inputs
4. Add User Story 3 → Loading states improve UX
5. Add User Story 4 → Image preview adds polish
6. Add User Story 5 → Health monitoring for operators
7. Polish → README, comprehensive tests, final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `app/static/app.js` is touched by US1, US2, US3, and US4 — implement incrementally within each story (additions, not rewrites)
