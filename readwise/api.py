"""A client for Readwise Reader API."""

from collections.abc import Iterator
from datetime import datetime
from http import HTTPStatus
from os import environ
from time import sleep
from typing import Any, Final
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from readwise.model import (
    DeleteRequest,
    DeleteResponse,
    Document,
    GetResponse,
    PostRequest,
    PostResponse,
    UpdateRequest,
    UpdateResponse,
)


class ReadwiseError(Exception):
    """Base exception for Readwise API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ReadwiseAuthenticationError(ReadwiseError):
    """Raised when authentication fails (401/403)."""

    pass


class ReadwiseClientError(ReadwiseError):
    """Raised for client errors (4xx)."""

    pass


class ReadwiseServerError(ReadwiseError):
    """Raised for server errors (5xx)."""

    pass


class ReadwiseRateLimitError(ReadwiseError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


def _append_query_param(url: str, param_name: str, param_value: str) -> str:
    """Safely append a query parameter to a URL.

    Handles both URLs with and without existing query parameters.

    Args:
        url: Base URL
        param_name: Query parameter name
        param_value: Query parameter value (will be URL-encoded)

    Returns:
        URL with appended/updated query parameter

    Examples:
        _append_query_param("https://example.com/article", "source", "rwreader")
        # Returns: "https://example.com/article?source=rwreader"

        _append_query_param("https://example.com/article?id=123", "source", "rwreader")
        # Returns: "https://example.com/article?id=123&source=rwreader"
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    # parse_qs returns lists for values, so we need to handle that
    query_params[param_name] = [param_value]

    # Reconstruct the query string
    new_query = urlencode(query_params, doseq=True)

    # Reconstruct the URL
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


class ReadwiseReader:
    """A comprehensive client for the Readwise Reader API.

    This class provides full parity with the official Readwise Reader API,
    including document listing, retrieval, saving, updating, and deletion.

    Authentication is handled via token, which can be provided explicitly
    or set via the READWISE_TOKEN environment variable.

    Example:
        reader = ReadwiseReader()  # Uses READWISE_TOKEN env var
        documents = reader.get_documents(location="new")
    """

    URL_BASE: Final[str] = "https://readwise.io/api/v3"

    def __init__(self, token: str | None = None) -> None:
        """Initialize the client with a token.

        Args:
            token (str): The token to use for authentication
        """
        self._token: str | None = token

    @property
    def token(self) -> str:
        """Get the token for authentication."""
        if self._token is None and environ.get("READWISE_TOKEN") is None:
            raise ValueError("Token is required for authentication")
        return self._token or environ["READWISE_TOKEN"]

    def validate_token(self, token: str | None = None) -> bool:
        """Validate a Readwise Reader API token.

        Args:
            token: The token to validate. If not provided, uses READWISE_TOKEN environment variable.

        Returns:
            True if token is valid, False otherwise.

        Raises:
            ValueError: If no token is provided and READWISE_TOKEN is not set.
            Exception: On unexpected HTTP status codes (4xx/5xx other than 401/403).
        """
        auth_token = token or self.token

        http_response: requests.Response = requests.get(
            url="https://readwise.io/api/v2/auth/",
            headers={"Authorization": f"Token {auth_token}"},
            timeout=30,
        )

        if http_response.status_code == HTTPStatus.NO_CONTENT:  # 204
            return True
        elif http_response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):  # 401, 403
            return False
        else:
            # Raise exception for other unexpected status codes
            raise Exception(
                f"Unexpected response from auth endpoint: {http_response.status_code} {http_response.text}"
            )

    def _make_get_request(self, params: dict[str, Any], retry_on_429: bool = False) -> GetResponse:
        http_response: requests.Response = requests.get(
            url=f"{self.URL_BASE}/list/",
            headers={"Authorization": f"Token {self.token}"},
            params=params,
            timeout=30,
        )

        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = http_response.headers.get("Retry-After")
            retry_after_seconds = int(retry_after) if retry_after else None

            if retry_on_429 and retry_after_seconds:
                print(f"Rate limited, waiting for {retry_after_seconds} seconds...")
                sleep(retry_after_seconds)
                return self._make_get_request(params=params, retry_on_429=retry_on_429)
            else:
                raise ReadwiseRateLimitError(
                    f"Rate limit exceeded: {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                    retry_after=retry_after_seconds,
                )

        if http_response.status_code >= 500:
            raise ReadwiseServerError(
                f"Server error: {http_response.status_code} {http_response.text}",
                status_code=http_response.status_code,
                response_body=http_response.text,
            )
        elif http_response.status_code >= 400:
            if http_response.status_code in (401, 403):
                raise ReadwiseAuthenticationError(
                    f"Authentication failed: {http_response.status_code} {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                )
            else:
                raise ReadwiseClientError(
                    f"Client error: {http_response.status_code} {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                )
        elif http_response.status_code >= 200:
            return GetResponse(**http_response.json())
        else:
            raise ReadwiseError(
                f"Unexpected status code: {http_response.status_code} {http_response.text}",
                status_code=http_response.status_code,
                response_body=http_response.text,
            )

    def _make_post_request(self, payload: PostRequest, retry_on_429: bool = False) -> tuple[bool, PostResponse | None]:
        http_response: requests.Response = requests.post(
            url=f"{self.URL_BASE}/save/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )

        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = http_response.headers.get("Retry-After")
            retry_after_seconds = int(retry_after) if retry_after else None

            if retry_on_429 and retry_after_seconds:
                print(f"Rate limited, waiting for {retry_after_seconds} seconds...")
                sleep(retry_after_seconds)
                return self._make_post_request(payload, retry_on_429=retry_on_429)
            else:
                raise ReadwiseRateLimitError(
                    f"Rate limit exceeded: {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                    retry_after=retry_after_seconds,
                )

        # Handle success responses (200 OK or 201 Created)
        if http_response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            try:
                return (True, PostResponse(**http_response.json()))
            except ValueError as e:
                # If JSON parsing/validation fails, return error tuple for backward compatibility
                return (False, None)

        # For backward compatibility, return error tuples for most errors
        # Only raise exceptions for rate limits when retry is disabled
        return (False, None)

    def get_documents(
        self,
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
            A list of `Document` objects.
        """
        params: dict[str, str | bool | int] = {}
        if location:
            if location not in ("new", "later", "shortlist", "archive", "feed"):
                raise ValueError(f"Parameter 'location' cannot be of value {location!r}")
            params["location"] = location
        if category:
            if category not in (
                "article",
                "email",
                "rss",
                "highlight",
                "note",
                "pdf",
                "epub",
                "tweet",
                "video",
            ):
                raise ValueError(f"Parameter 'category' cannot be of value {category!r}")
            params["category"] = category
        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if withHtmlContent:
            params["withHtmlContent"] = True
        if tag:
            params["tag"] = tag
        if limit is not None:
            if not (1 <= limit <= 100):
                raise ValueError(f"Parameter 'limit' must be between 1 and 100, got {limit}")
            params["limit"] = limit
        if page_cursor:
            params["pageCursor"] = page_cursor
        if with_raw_source_url:
            params["withRawSourceUrl"] = True

        # If limit is specified, fetch only one page
        if limit is not None:
            response = self._make_get_request(params, retry_on_429=retry_on_429)
            return response.results

        # Otherwise, auto-paginate to get all documents
        results: list[Document] = []
        while (response := self._make_get_request(params, retry_on_429=retry_on_429)).next_page_cursor:
            results.extend(response.results)
            params["pageCursor"] = response.next_page_cursor
        # Make sure not to forget last response where `next_page_cursor` is None.
        results.extend(response.results)

        return results

    def iter_documents(
        self,
        location: str | None = None,
        category: str | None = None,
        updated_after: datetime | None = None,
        withHtmlContent: bool = False,
        tag: str | None = None,
        with_raw_source_url: bool = False,
        retry_on_429: bool = False,
    ) -> Iterator[Document]:
        """Iterate over documents from Readwise Reader.

        This is a generator that yields documents one by one, automatically handling pagination.
        Useful for processing large numbers of documents without loading them all into memory.

        Args:
            location: The document's location, could be one of: new, later, shortlist, archive, feed
            category: The document's category, could be one of: article, email, rss, highlight, note, pdf, epub,
                tweet, video
            updated_after: Filter documents updated after this date
            withHtmlContent: Include the html_content field in each document's data
            tag: The document's tag key. Pass a tag parameter to find documents having that tag.
            with_raw_source_url: Include the raw_source_url field containing a direct Amazon S3 link.
            retry_on_429: Whether to automatically retry when rate limited (429).

        Yields:
            Document objects one by one.
        """
        params: dict[str, str | bool] = {}
        if location:
            if location not in ("new", "later", "shortlist", "archive", "feed"):
                raise ValueError(f"Parameter 'location' cannot be of value {location!r}")
            params["location"] = location
        if category:
            if category not in (
                "article",
                "email",
                "rss",
                "highlight",
                "note",
                "pdf",
                "epub",
                "tweet",
                "video",
            ):
                raise ValueError(f"Parameter 'category' cannot be of value {category!r}")
            params["category"] = category
        if updated_after:
            params["updatedAfter"] = updated_after.isoformat()
        if withHtmlContent:
            params["withHtmlContent"] = True
        if tag:
            params["tag"] = tag
        if with_raw_source_url:
            params["withRawSourceUrl"] = True

        while True:
            response = self._make_get_request(params, retry_on_429=retry_on_429)
            yield from response.results

            if not response.next_page_cursor:
                break

            params["pageCursor"] = response.next_page_cursor

    def get_document_by_id(self, id: str, retry_on_429: bool = False) -> Document | None:
        """Get a single document from Readwise Reader by its ID.

        This method uses the official Readwise Reader API LIST endpoint with the 'id' parameter,
        which returns exactly one document if found.

        Args:
            id: The document's unique ID.
            retry_on_429: Whether to automatically retry when rate limited (429).

        Returns:
            A Document object if a document with the given ID exists, or None otherwise.
        """
        response: GetResponse = self._make_get_request(params={"id": id}, retry_on_429=retry_on_429)
        if response.count == 1:
            return response.results[0]
        return None

    def save_document(  # noqa: PLR0913
        self,
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
            ReadwiseError: On HTTP errors (authentication, client, server, or rate limit errors).
        """
        # Validate required parameters
        if not url and not html:
            raise ValueError("Either 'url' or 'html' must be provided")

        # Validate should_clean_html is only used with html
        if should_clean_html and not html:
            raise ValueError("'should_clean_html' can only be used when 'html' is provided")

        # Validate location parameter
        if location and location not in ("new", "later", "archive", "feed"):
            raise ValueError(f"Parameter 'location' cannot be of value {location!r}")

        # Validate category parameter
        if category and category not in (
            "article",
            "email",
            "rss",
            "highlight",
            "note",
            "pdf",
            "epub",
            "tweet",
            "video",
        ):
            raise ValueError(f"Parameter 'category' cannot be of value {category!r}")

        payload = PostRequest(
            url=url,  # type: ignore  # We've validated that either url or html is provided
            html=html,
            should_clean_html=should_clean_html if html is not None else None,
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
        )

        return self._make_post_request(payload=payload, retry_on_429=retry_on_429)

    def _make_delete_request(
        self, payload: DeleteRequest, retry_on_429: bool = False
    ) -> tuple[bool, DeleteResponse | None]:
        """Make a DELETE request to the Readwise API."""
        http_response: requests.Response = requests.delete(
            url=f"{self.URL_BASE}/delete/{payload.id}/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )

        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = http_response.headers.get("Retry-After")
            retry_after_seconds = int(retry_after) if retry_after else None

            if retry_on_429 and retry_after_seconds:
                print(f"Rate limited, waiting for {retry_after_seconds} seconds...")
                sleep(retry_after_seconds)
                return self._make_delete_request(payload, retry_on_429=retry_on_429)
            else:
                raise ReadwiseRateLimitError(
                    f"Rate limit exceeded: {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                    retry_after=retry_after_seconds,
                )

        # Handle success responses (200 OK or 204 No Content)
        if http_response.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            try:
                # 204 No Content won't have a response body
                if http_response.status_code == HTTPStatus.NO_CONTENT:
                    return (True, DeleteResponse(success=True, message="Document deleted successfully"))
                return (True, DeleteResponse(**http_response.json()))
            except ValueError as e:
                # If JSON parsing/validation fails, return error tuple for backward compatibility
                return (False, None)

        # For backward compatibility, return error tuples for most errors
        # Only raise exceptions for rate limits when retry is disabled
        return (False, None)

    def _make_update_request(self, payload: UpdateRequest, retry_on_429: bool = False) -> tuple[bool, UpdateResponse]:
        """Make an UPDATE request to the Readwise API using PATCH method.

        Args:
            payload: UpdateRequest object with document id and fields to update
            retry_on_429: Whether to automatically retry when rate limited (429).

        Returns:
            Tuple of (success, response)
        """
        http_response: requests.Response = requests.patch(
            url=f"{self.URL_BASE}/update/{payload.id}/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(exclude={"id"}),  # Exclude id from payload as it's in the URL
            timeout=30,
        )

        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = http_response.headers.get("Retry-After")
            retry_after_seconds = int(retry_after) if retry_after else None

            if retry_on_429 and retry_after_seconds:
                print(f"Rate limited, waiting for {retry_after_seconds} seconds...")
                sleep(retry_after_seconds)
                return self._make_update_request(payload, retry_on_429=retry_on_429)
            else:
                raise ReadwiseRateLimitError(
                    f"Rate limit exceeded: {http_response.text}",
                    status_code=http_response.status_code,
                    response_body=http_response.text,
                    retry_after=retry_after_seconds,
                )

        # Handle success responses
        if http_response.status_code == HTTPStatus.OK:
            return (True, UpdateResponse(success=True, message="Document updated successfully"))

        # For backward compatibility, return error tuples for most errors
        # Only raise exceptions for rate limits when retry is disabled
        return (False, UpdateResponse(success=False, message=f"Update failed: {http_response.status_code}"))

    def delete_document(
        self, url: str | None = None, document_id: str | None = None, retry_on_429: bool = False
    ) -> tuple[bool, dict | DeleteResponse | None]:
        """Delete a document from Readwise Reader.

        Args:
            url: URL of the document to delete (either url or document_id must be provided)
            document_id: ID of the document to delete
            retry_on_429: Whether to automatically retry when rate limited (429).

        Returns:
            Tuple of (success, response)
                - success: Boolean indicating if the operation was successful
                - response: Response data or error information
        """
        if document_id is None and url is None:
            return False, {"error": "Either url or document_id must be provided"}

        # If we have a URL but no document_id, search for the document first
        if document_id is None and url is not None:
            success, result = self.search_document(url=url)
            if not success:
                return False, {"error": f"Could not find document with URL {url}"}
            document_id = result.id  # type: ignore

        return self._make_delete_request(payload=DeleteRequest(id=str(document_id)), retry_on_429=retry_on_429)

    def update_document_location(
        self, document_id: str, location: str, retry_on_429: bool = False
    ) -> tuple[bool, dict | UpdateResponse]:
        """Update a document's location in Readwise Reader.

        Args:
            document_id: ID of the document to update
            location: New location ('new' for inbox, 'later', 'archive')
            retry_on_429: Whether to automatically retry when rate limited (429).

        Returns:
            Tuple of (success, response)
                - success: Boolean indicating if the operation was successful
                - response: Response data or error information
        """
        if location not in ("new", "later", "archive"):
            return False, {"error": f"Invalid location: {location}. Must be one of: 'new', 'later', 'archive'"}

        payload = UpdateRequest(id=document_id, location=location)
        return self._make_update_request(payload, retry_on_429=retry_on_429)

    def search_document(self, url: str, retry_on_429: bool = False) -> tuple[bool, dict | Document]:
        """Search for a document by URL in Readwise Reader.

        Args:
            url: URL to search for
            retry_on_429: Whether to automatically retry when rate limited (429).

        Returns:
            Tuple of (success, document_data)
                - success: Boolean indicating if the document was found
                - document_data: Document information or error message
        """
        response: GetResponse = self._make_get_request(params={"url": url}, retry_on_429=retry_on_429)
        if response.count > 0:
            return True, response.results[0]
        return False, {"error": f"No document found with URL {url}"}
