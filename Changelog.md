# Changelog

All notable changes to the Readwise API client will be documented in this file.

## [0.4.0] - 2025-01-23

Full parity with the official Readwise Reader API. No breaking changes.

### Added

- `validate_token(token=None) -> bool` and `readwise auth-check` CLI command.
- `get_documents()`: `location`, `category`, `updated_after`, `tag`, `limit`, `page_cursor`, `with_raw_source_url`, `retry_on_429` parameters.
- `iter_documents()` — generator for memory-efficient pagination through large document sets.
- `get_document_by_id()` confirmed against the official LIST-with-`id` endpoint; added `retry_on_429`.
- `save_document()`: full metadata support (`title`, `author`, `summary`, `published_date`, `image_url`, `location`, `category`, `saved_using`, `tags`, `notes`, `should_clean_html`, `retry_on_429`).
- CLI: `--location`/`-l`, `--category`/`-c`, `--updated-after`/`-u`, `--number`/`-n` on `list`; `--url`/`-u`, `--html-file`/`-f`, `--title`/`-t`, `--author`/`-a`, `--tags`/`-g` on `save`.
- Structured exceptions: `ReadwiseError` base, with `ReadwiseAuthenticationError` (401/403), `ReadwiseClientError` (4xx), `ReadwiseServerError` (5xx), `ReadwiseRateLimitError` (429, carries `retry_after`).
- Module-level convenience functions (`readwise.get_documents()` etc.) usable without instantiating a client.
- 57 tests covering all public methods and CLI commands, no live API calls (mocked).
- Full type hints, mypy-clean.

### Not implemented (outside Reader API scope)

Webhooks, tag management, bulk operations, document export — none of these exist in the Reader API itself.

### API endpoints covered

`GET /api/v2/auth/`, `GET /api/v3/list/` (list and get-by-id), `POST /api/v3/save/`, `PATCH /api/v3/update/{id}/`, `DELETE /api/v3/delete/{id}/`.

Rate limits: 20 req/min standard, 50 req/min for save/update; 100 docs/page; up to 5 tags per request.
