# Codex work plan: Readwise Reader API parity

## Goal

Bring the repository reuteras/readwise-api to parity with the public Readwise Reader API documentation, ensuring that:

- Implemented features match documented API behavior
- README and CLI reflect actual supported functionality
- Undocumented or guessed features are not exposed without clear labeling
- Tests cover all public-facing functionality

Codex should treat:
- the repository source code as the implementation baseline
- the public Readwise Reader API documentation as the specification

---

## Phase 0 — Repository audit (mandatory)

### Tasks

1. Inspect the repository layout:
   - readwise/ (client code)
   - tests/
   - pyproject.toml
   - uv.lock
   - README.md

2. Identify and document:
   - Base API URL(s) used
   - Authentication header format
   - All HTTP endpoints currently called
   - Public Python functions
   - CLI commands and flags
   - Existing test coverage

3. Create a parity matrix file:

Create docs/parity-matrix.md with the following table structure:

| Feature | Endpoint | Python API | CLI | Supported | Notes |
|-------|----------|------------|-----|-----------|------|

Populate this table by inspecting the code, not by trusting the README.

---

## Phase 1 — Token validation

### Specification (public Reader API)

- Endpoint: GET https://readwise.io/api/v2/auth/
- Behavior:
  - HTTP 204 → token is valid
  - HTTP 401 or 403 → token is invalid

### Python API

Implement:

- validate_token(token: str | None = None) -> bool

Rules:
- Use READWISE_TOKEN environment variable if token is not provided
- Return True on HTTP 204
- Return False on HTTP 401 or 403
- Raise exception on other unexpected 4xx or 5xx responses

### CLI

Add command:

- readwise auth-check

Exit codes:
- 0 → token valid
- 1 → token invalid

### Tests

- Mock 204 response → returns True
- Mock 401 response → returns False
- Mock 5xx response → raises exception

---

## Phase 2 — Document listing parity

### Specification

The public Reader API explicitly supports fetching documents.

### Tasks

1. Identify the exact endpoint currently used for listing documents.
2. Verify whether that endpoint supports:
   - pagination
   - cursors
   - filtering
3. Only expose features that are actually supported by the endpoint in use.

### Python API

Extend or confirm:

- get_documents(...)

Optional additions (only if endpoint supports them):
- updated_after parameter
- pagination via limit and cursor
- iter_documents(...) generator that auto-paginates

Do not implement undocumented filters or parameters.

### CLI

Ensure existing commands are accurate, for example:
- readwise list new
- readwise list later
- readwise list archive

Do not add flags that are not backed by the API.

### Tests

- Verify correct query parameter construction
- Test pagination behavior if applicable

---

## Phase 3 — Document retrieval by ID

### Audit requirement

Determine whether:
- There is a documented Reader API endpoint to fetch a document by ID
- OR the current implementation is a client-side helper built on top of listing

### Action

If no official endpoint exists:
- Keep get_document_by_id as a helper
- Clearly document it as a convenience function, not API parity

Update README accordingly.

---

## Phase 4 — Document saving parity

### Specification

The public Reader API supports saving new documents.

### Python API

Extend save_document to support (only if confirmed supported by the endpoint):

- url (required unless html is provided)
- html (optional, if supported)
- Metadata fields only if verified:
  - title
  - author
  - tags
  - notes

Rules:
- Preserve backward compatibility:
  - save_document("https://example.com") must continue to work
- Validate invalid parameter combinations early

### CLI

Existing command:
- readwise save <url>

Optional flags (only if endpoint supports them):
- --html-file
- --title
- --author
- --tags

### Tests

- URL-only document save
- HTML-based save (if implemented)
- Metadata propagation
- Validation failures for invalid inputs

---

## Phase 5 — Error handling and rate limits

### Tasks

1. Normalize API error handling:
   - status code
   - error message
   - response body (if available)
   - Retry-After header on HTTP 429

2. Ensure all API calls raise consistent exceptions.

3. Do not auto-retry requests by default.

Optional:
- Provide retry_on_429 flag for advanced usage

### Tests

- HTTP 429 exposes Retry-After
- Distinguish 4xx vs 5xx behavior clearly

---

## Phase 6 — Documentation updates

### README.md

Update README to include:

- Truthful list of supported operations
- Authentication instructions
- Python and CLI usage examples
- Known limitations
- Clear distinction between:
  - documented API features
  - client-side helpers

### Code documentation

- Add type hints to all public functions
- Add docstrings explaining parameters and behavior
- Document environment variable usage

---

## Phase 7 — Test coverage requirements

### Requirements

- All public Python APIs must be tested
- CLI commands must have basic invocation tests
- No tests may call the real Readwise API

Recommended tools:
- pytest
- responses or requests-mock (use what the repo already prefers)

---

## Acceptance criteria

- All tests pass
- README accurately reflects behavior
- No undocumented API features are silently exposed
- Token validation works exactly as specified
- save_document and get_documents match public Reader API claims
- CLI behavior matches Python API

---

## Implementation rules for Codex

- Do not guess undocumented API behavior
- Prefer correctness over feature count
- Keep changes incremental and minimal
- If uncertain, document the limitation instead of implementing a guess
