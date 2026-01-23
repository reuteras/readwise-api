# Readwise API

![logo](https://github.com/floscha/readwise-api/raw/main/logo.png)

A comprehensive Python client for the [Readwise Reader API](https://readwise.io/reader_api), providing full parity with the official API documentation.

## Installation

```bash
pip install readwise-api
```

## Authentication

First, obtain a [Readwise access token](https://readwise.io/access_token). Then set it as an environment variable:

```bash
export READWISE_TOKEN="your_token_here"
```

Or store it in a `.env` file in your project directory.

### Verify Authentication

```python
from readwise import ReadwiseReader

reader = ReadwiseReader()
if reader.validate_token():
    print("Token is valid!")
```

Or via CLI:

```bash
readwise auth-check
```

## Python API

### Initialization

```python
from readwise import ReadwiseReader

# Uses READWISE_TOKEN environment variable
reader = ReadwiseReader()

# Or pass token explicitly
reader = ReadwiseReader(token="your_token")
```

### Document Operations

#### List Documents

```python
# Get all documents
documents = reader.get_documents()

# Filter by location
new_docs = reader.get_documents(location="new")
later_docs = reader.get_documents(location="later")
archive_docs = reader.get_documents(location="archive")

# Filter by category
articles = reader.get_documents(category="article")
emails = reader.get_documents(category="email")

# Filter by date
from datetime import datetime
recent = reader.get_documents(updated_after=datetime(2024, 1, 1))

# Limit results
first_50 = reader.get_documents(limit=50)

# Combine filters
filtered = reader.get_documents(
    location="new",
    category="article",
    updated_after=datetime(2024, 1, 1),
    limit=100
)
```

#### Iterate Documents (Memory Efficient)

```python
# Process large numbers of documents without loading all into memory
for doc in reader.iter_documents(location="archive"):
    print(f"Processing: {doc.title}")
```

#### Get Single Document

```python
doc = reader.get_document_by_id("document_id")
if doc:
    print(f"Title: {doc.title}")
    print(f"Author: {doc.author}")
```

#### Search by URL

```python
success, result = reader.search_document("https://example.com/article")
if success:
    print(f"Found: {result.title}")
```

#### Save Document

```python
# From URL (Readwise will scrape the content)
success, response = reader.save_document("https://example.com/article")

# With metadata
success, response = reader.save_document(
    url="https://example.com/article",
    title="Custom Title",
    author="Custom Author",
    tags=["tag1", "tag2"],
    category="article"
)

# From HTML content
success, response = reader.save_document(
    html="<html><body>Custom content</body></html>",
    title="Custom Article",
    author="Author Name"
)
```

#### Update Document

```python
# Change location
success, response = reader.update_document_location(
    document_id="doc_id",
    location="archive"  # new, later, or archive
)
```

#### Delete Document

```python
# By document ID
success, response = reader.delete_document(document_id="doc_id")

# By URL (searches first, then deletes)
success, response = reader.delete_document(url="https://example.com/article")
```

### Error Handling

The library provides structured error handling:

```python
from readwise import (
    ReadwiseAuthenticationError,
    ReadwiseClientError,
    ReadwiseServerError,
    ReadwiseRateLimitError,
)

try:
    documents = reader.get_documents()
except ReadwiseAuthenticationError:
    print("Invalid token")
except ReadwiseRateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except ReadwiseServerError:
    print("Server error - try again later")
except ReadwiseClientError as e:
    print(f"Client error: {e.status_code}")
```

### Rate Limiting

By default, the library does not automatically retry on rate limits. You can enable retries:

```python
# Enable automatic retry on rate limits
documents = reader.get_documents(retry_on_429=True)
doc = reader.get_document_by_id("id", retry_on_429=True)
success, response = reader.save_document("url", retry_on_429=True)
```

Rate limits are 20 requests per minute per token for most operations, 50 for save/update operations.

## CLI

### List Documents

```bash
# List all documents
readwise list

# Filter by location
readwise list --location new
readwise list --location later
readwise list --location archive

# Filter by category
readwise list --category article
readwise list --category email

# Filter by date
readwise list --updated-after 2024-01-01

# Limit results
readwise list --number 50

# Combine filters
readwise list --location new --category article --number 25

# Save to file
readwise list --location archive > archived_docs.json
```

### Get Single Document

```bash
readwise get <document_id>
```

### Save Document

```bash
# From URL
readwise save --url "https://example.com/article"

# From HTML file
readwise save --html-file content.html

# With metadata
readwise save --url "https://example.com/article" \
    --title "Custom Title" \
    --author "Author Name" \
    --tags "tag1,tag2"
```

### Authentication Check

```bash
readwise auth-check
```

## Advanced Usage

### Custom Error Handling

```python
try:
    documents = reader.get_documents(location="invalid")
except ReadwiseClientError as e:
    print(f"API error {e.status_code}: {e.response_body}")
```

### Large Dataset Processing

```python
# Process all archived documents efficiently
count = 0
for doc in reader.iter_documents(location="archive"):
    count += 1
    # Process document...
print(f"Processed {count} documents")
```

### Batch Operations

```python
# Save multiple documents
urls = ["url1", "url2", "url3"]
for url in urls:
    success, response = reader.save_document(url)
    if success:
        print(f"Saved: {response.url}")
```

## API Coverage

### ✅ Fully Supported
- **Authentication**: Token validation
- **Document Listing**: Full filtering, pagination, iteration
- **Document Retrieval**: By ID and URL search
- **Document Saving**: URL and HTML content with full metadata
- **Document Updates**: Location changes
- **Document Deletion**: By ID or URL
- **Rate Limiting**: Configurable retry behavior
- **Error Handling**: Structured exceptions with detailed information

### 📋 Known Limitations
- Webhook functionality not implemented (not in Reader API)
- Tag management endpoints not implemented
- Bulk operations not available in API

## Contributing

This library aims for complete parity with the Readwise Reader API. If you find any discrepancies or missing features, please open an issue.
