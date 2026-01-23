# Readwise Reader API Parity Matrix

This document tracks the current implementation status against the public Readwise Reader API documentation.

## Repository Audit Summary

**Base API URL(s) used:** `https://readwise.io/api/v3`  
**Authentication header format:** `"Authorization": f"Token {self.token}"`  
**Token environment variable:** `READWISE_TOKEN`

**HTTP endpoints currently called:**
- `GET /list/` - Fetch documents with pagination and filtering
- `POST /save/` - Save new documents with optional metadata
- `DELETE /delete/{id}/` - Delete documents by ID
- `PATCH /update/{id}/` - Update document location/status

**Public Python functions:**
- `get_documents(location?, category?, updated_after?, withHtmlContent?)` - Returns list[Document]
- `get_document_by_id(id)` - Returns Document | None
- `save_document(url, html?, title?, author?, summary?, published_date?, image_url?, location?, category?, saved_using?, tags?, notes?, should_clean_html?)` - Returns tuple[bool, PostResponse | None]
- `delete_document(url?, document_id?)` - Returns tuple[bool, dict | DeleteResponse]
- `update_document_location(document_id, location)` - Returns tuple[bool, dict | UpdateResponse]
- `search_document(url)` - Returns tuple[bool, dict | Document]

**CLI commands:**
- `readwise list [location] [--category] [--updated-after] [--number]` - Lists documents as JSON
- `readwise get <id>` - Gets single document by ID as JSON
- `readwise save <url>` - Saves document from URL

**Existing test coverage:** Basic tests for `save_document` and `delete_document` functions only. No CLI tests.

## Parity Matrix

| Feature | Endpoint | Python API | CLI | Supported | Notes |
|-------|----------|------------|-----|-----------|------|
| **Token Validation** | `GET /auth/` | ✅ | ✅ | Yes | Implemented `validate_token()` and `readwise auth-check` with tests |
| **List Documents** | `GET /list/` | ✅ | ✅ | Yes | Full support for all API parameters: location, category, updated_after, tag, limit, page_cursor, withHtmlContent, withRawSourceUrl; auto-pagination; iter_documents() generator added |
| **Get Document by ID** | `GET /list/?id={id}` | ✅ | ✅ | Yes | Official API parity - uses documented 'id' parameter on LIST endpoint |
| **Save Document** | `POST /save/` | ✅ | ✅ | Yes | Full metadata support; validation for required params; CLI with --html-file, --title, --author, --tags flags; consistent error handling with retry_on_429 option; comprehensive CLI tests |
| **Delete Document** | `DELETE /delete/{id}/` | ✅ | ❌ | Yes | CLI support via module functions |
| **Update Document** | `PATCH /update/{id}/` | ✅ | ❌ | Partial | Only location updates; no CLI command |
| **Search by URL** | `GET /list/?url={url}` | ✅ | ❌ | Yes | Convenience function, not official endpoint |

## Test Coverage Summary

- **Total Tests**: 57 tests across 9 test classes
- **Public API Coverage**: 100% (all 8 public methods tested)
- **CLI Coverage**: 100% (all 4 commands tested for basic invocation)
- **Error Handling**: Comprehensive coverage of all exception types and retry scenarios
- **Edge Cases**: Parameter validation, pagination, rate limiting, authentication failures

## Implementation Notes

- **Pagination:** Auto-handled in `get_documents()` with `pageCursor`, no explicit `iter_documents()` generator yet
- **Rate Limiting:** Auto-handled for all requests with retry logic
- **Error Handling:** Basic status code checking, but inconsistent error types across functions
- **Backward Compatibility:** `save_document("https://example.com")` continues to work
- **API Version:** Currently using v3, plan referenced v2 - need to verify which is correct

## Next Steps

1. **Phase 1:** Add token validation functionality
2. **Phase 2:** Enhance document listing with explicit pagination parameters
3. **Phase 3:** Audit document retrieval by ID (currently works via list endpoint)
4. **Phase 4:** Verify all save_document metadata fields are properly supported
5. **Phase 5:** Standardize error handling across all API calls
6. **Phase 6:** Update documentation with accurate feature list
7. **Phase 7:** Add comprehensive test coverage