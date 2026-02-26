<!--
Sync Impact Report
===================
Version change: 0.0.0 (template) → 1.0.0 (initial ratification)
Modified principles: None (all new)
Added sections:
  - I. Simplicity First
  - II. Test-Driven Development
  - III. Secure by Default
  - IV. Stateless & Configurable
  - V. Contract Stability
  - Security & Input Handling (Section 2)
  - Development Workflow (Section 3)
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ No changes needed (generic constitution check)
  - .specify/templates/spec-template.md ✅ No changes needed (generic structure)
  - .specify/templates/tasks-template.md ✅ No changes needed (generic structure)
  - CLAUDE.md ✅ No changes needed (auto-generated, no constitution refs)
Follow-up TODOs: None
-->

# Cosmos Reason Constitution

## Core Principles

### I. Simplicity First

Every feature MUST start with the simplest viable implementation.
No abstractions, patterns, or layers beyond what the current requirement
demands. Prefer flat module structures over deep hierarchies. Prefer
inline logic over premature extraction. Add complexity only when a
concrete, present-tense problem requires it — never for hypothetical
future needs.

- YAGNI applies at all levels: code, architecture, dependencies.
- A new dependency MUST solve a problem that cannot be reasonably
  solved with the existing stack.
- Maximum one level of service indirection (e.g., route → client,
  not route → service → adapter → client).

### II. Test-Driven Development

Tests MUST be written before implementation for all backend logic.
The Red-Green-Refactor cycle is enforced: tests fail first, then
implementation makes them pass, then refactor if needed.

- All backend endpoints MUST have integration tests using
  FastAPI TestClient.
- External dependencies (llama-server) MUST be mocked in tests —
  tests MUST run without requiring the real model.
- Frontend behavior is validated via manual checklist (no
  mandatory JS test framework).
- Tests MUST be independently runnable with `pytest` and no
  external services.

### III. Secure by Default

User input MUST never be trusted. All external data MUST be validated
at system boundaries before processing.

- File uploads MUST be validated for MIME type and size before
  any processing occurs.
- Text inputs MUST be validated for length and content constraints.
- Error responses MUST use structured JSON and MUST NOT expose
  stack traces, internal paths, or system details.
- CORS MUST be restricted to explicitly configured origins.
- No user input MUST ever be interpolated into shell commands
  or system calls.

### IV. Stateless & Configurable

The application MUST be stateless — no data persists between
requests. All tunable values MUST be configurable via environment
variables with sensible defaults.

- Every environment variable MUST have a documented default value.
- Configuration MUST be loaded once at startup and immutable
  during runtime.
- No hardcoded URLs, ports, limits, or timeouts in application
  logic — all MUST reference the configuration module.

### V. Contract Stability

API contracts (request/response shapes, status codes, error formats)
defined in `contracts/` MUST be treated as commitments. Changes to
contracts MUST be reflected in tests before implementation.

- Endpoint response shapes MUST match the documented contract.
- Error responses MUST use the documented structured format
  (`{"error": "...", "field": "..."}` for validation, `{"error": "..."}`
  for service errors).
- Status codes MUST follow the contract: 200 for success, 400 for
  validation errors, 503 for backend unavailability.

## Security & Input Handling

All input validation MUST occur at two layers:

1. **Client-side** (JavaScript): Immediate feedback for UX; MUST NOT
   be relied upon for security.
2. **Server-side** (FastAPI): Authoritative validation; MUST reject
   invalid input regardless of client behavior.

File size limits MUST be enforced at the upload layer before reading
the full file body into memory. Structured logging MUST be used for
request tracing without dumping sensitive payloads (file contents,
full prompts).

## Development Workflow

- Features are specified via `/speckit.specify` before implementation.
- Implementation follows the task list in priority order (P1 → P2 → P3).
- Each user story MUST be independently testable at its checkpoint.
- Commits SHOULD be made after each completed task or logical group.
- The MVP (User Story 1) MUST be validated end-to-end before
  proceeding to subsequent stories.

## Governance

This constitution governs all development on the Cosmos Reason
project. All code changes MUST comply with these principles.

- Amendments require updating this file, incrementing the version,
  and propagating changes to dependent artifacts (plan, tasks).
- Complexity beyond what these principles allow MUST be justified
  in the plan's Complexity Tracking table.
- Constitution compliance SHOULD be verified during code review.

**Version**: 1.0.0 | **Ratified**: 2026-02-25 | **Last Amended**: 2026-02-25
