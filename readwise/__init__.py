"""Readwise API client for Python."""

from datetime import datetime

from readwise.api import ReadwiseReader
from readwise.model import DeleteRequest, DeleteResponse, Document, PostResponse, UpdateResponse
from readwise.version import __version__

__all__: list[str] = [
    "DeleteRequest",
    "DeleteResponse",
    "Document",
    "ReadwiseReader",
    "UpdateResponse",
    "__version__",
    "delete_document",
    "get_document_by_id",
    "get_documents",
    "save_document",
    "search_document",
    "update_document_location",
    "validate_token",
]


def validate_token(token: str | None = None) -> bool:
    """Validate a Readwise Reader API token.

    Args:
        token: The token to validate. If not provided, uses READWISE_TOKEN environment variable.

    Returns:
        True if token is valid, False otherwise.

    Raises:
        ValueError: If no token is provided and READWISE_TOKEN is not set.
    """
    reader = ReadwiseReader()
    return reader.validate_token(token)


def get_documents(  # noqa: PLR0913
    location: str | None = None,
    category: str | None = None,
    updated_after: datetime | None = None,
    withHtmlContent: bool = False,
    tag: str | None = None,
    limit: int | None = None,
    page_cursor: str | None = None,
    with_raw_source_url: bool = False,
    retry_on_429: bool = False,
) -> list[Document]:
    """Get a list of documents from Readwise Reader.

    Args:
        location: The document's location, could be one of: new, later, shortlist, archive, feed
        category: The document's category, could be one of: article, email, rss, highlight, note, pdf, epub,
            tweet, video
        updated_after: Filter documents updated after this date
        withHtmlContent: Include the html_content field in each document's data
        tag: The document's tag key. Pass a tag parameter to find documents having that tag.
        limit: The maximum number of documents to return (1-100). If None, returns all documents.
        page_cursor: A string returned by a previous request to get the next page of documents.
        with_raw_source_url: Include the raw_source_url field containing a direct Amazon S3 link.
        retry_on_429: Whether to automatically retry when rate limited (429).

    Returns:
        A list of Document objects.
    """
    reader = ReadwiseReader()
    return reader.get_documents(
        location=location,
        category=category,
        updated_after=updated_after,
        withHtmlContent=withHtmlContent,
        tag=tag,
        limit=limit,
        page_cursor=page_cursor,
        with_raw_source_url=with_raw_source_url,
        retry_on_429=retry_on_429,
    )


def get_document_by_id(id: str, retry_on_429: bool = False) -> Document | None:
    """Get a single document from Readwise Reader by its ID.

    Args:
        id: The document's unique ID.
        retry_on_429: Whether to automatically retry when rate limited (429).

    Returns:
        A Document object if a document with the given ID exists, or None otherwise.
    """
    reader = ReadwiseReader()
    return reader.get_document_by_id(id=id, retry_on_429=retry_on_429)


def save_document(  # noqa: PLR0913
    url: str | None = None,
    html: str | None = None,
    title: str | None = None,
    author: str | None = None,
    summary: str | None = None,
    published_date: str | None = None,
    image_url: str | None = None,
    location: str | None = None,
    category: str | None = None,
    saved_using: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
    should_clean_html: bool = False,
    retry_on_429: bool = False,
) -> tuple[bool, PostResponse | None]:
    """Save a document to Readwise Reader.

    Args:
        url: Document URL (required unless html is provided). Can include query parameters.
        html: Custom HTML content to save. If provided, Readwise uses this
              instead of scraping the URL. Either url or html must be provided.
        title: Override document title. Optional.
        author: Override document author. Optional.
        summary: Document summary/description. Optional.
        published_date: ISO 8601 formatted publication date. Optional.
        image_url: Cover/thumbnail image URL. Optional.
        location: Initial location in Readwise. One of: "new", "later",
                  "archive", "feed". Optional, defaults to "new".
        category: Document type. One of: "article", "email", "rss",
                  "highlight", "note", "pdf", "epub", "tweet", "video".
                  Optional.
        saved_using: String identifying the source/tool that saved this.
                     Example: "rwreader-html-redownload". Optional.
        tags: List of tag strings to apply. Optional.
        notes: Top-level document note. Optional.
        should_clean_html: Whether Readwise should auto-clean the provided HTML.
                          Only used if html is provided. Defaults to False.
        retry_on_429: Whether to automatically retry when rate limited (429).

    Returns:
        Tuple of (success: bool, response: PostResponse)
            - success: True if document was saved successfully
            - response: PostResponse object with document_id and reader_url

    Raises:
        ValueError: If neither url nor html is provided, or if invalid parameters are used.
    """
    reader = ReadwiseReader()
    return reader.save_document(
        url=url,
        html=html,
        title=title,
        author=author,
        summary=summary,
        published_date=published_date,
        image_url=image_url,
        location=location,
        category=category,
        saved_using=saved_using,
        tags=tags,
        notes=notes,
        should_clean_html=should_clean_html,
        retry_on_429=retry_on_429,
    )


def delete_document(
    url: str | None = None, document_id: str | None = None
) -> tuple[bool, dict | DeleteResponse | None]:
    """Delete a document from Readwise Reader.

    Args:
        url: URL of the document to delete (either url or document_id must be provided)
        document_id: ID of the document to delete

    Returns:
        Tuple of (success, response)
            - success: Boolean indicating if the operation was successful
            - response: Response data or error information
    """
    reader = ReadwiseReader()
    return reader.delete_document(url=url, document_id=document_id)


def update_document_location(document_id: str, location: str) -> tuple[bool, dict | UpdateResponse]:
    """Update a document's location in Readwise Reader.

    Args:
        document_id: ID of the document to update
        location: New location ('new' for inbox, 'later', 'archive')

    Returns:
        Tuple of (success, response)
            - success: Boolean indicating if the operation was successful
            - response: Response data or error information
    """
    reader = ReadwiseReader()
    return reader.update_document_location(document_id=document_id, location=location)


def search_document(url: str) -> tuple[bool, dict | Document]:
    """Search for a document by URL in Readwise Reader.

    Args:
        url: URL to search for

    Returns:
        Tuple of (success, document_data)
            - success: Boolean indicating if the document was found
            - document_data: Document information or error message
    """
    reader = ReadwiseReader()
    return reader.search_document(url=url)
