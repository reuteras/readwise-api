"""A client for Readwise Reader API."""

from datetime import datetime
from http import HTTPStatus
from os import environ
from time import sleep
from typing import Final
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
    """A client for Readwise Reader API."""

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

    def _make_get_request(self, params: dict[str, str]) -> GetResponse:
        http_response: requests.Response = requests.get(
            url=f"{self.URL_BASE}/list/",
            headers={"Authorization": f"Token {self.token}"},
            params=params,
            timeout=30,
        )
        if http_response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
            return GetResponse(**http_response.json())

        # Respect rate limiting of maximum 20 requests per minute (https://readwise.io/reader_api).
        wait_time = int(http_response.headers["Retry-After"])
        print(f"Rate limited, waiting for {wait_time} seconds...")
        sleep(wait_time)
        return self._make_get_request(params=params)

    def _make_post_request(self, payload: PostRequest) -> tuple[bool, PostResponse | None]:
        http_response: requests.Response = requests.post(
            url=f"{self.URL_BASE}/save/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )
        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            # Respect rate limiting of maximum 20 requests per minute (https://readwise.io/reader_api).
            wait_time = int(http_response.headers["Retry-After"])
            sleep(wait_time)
            return self._make_post_request(payload)

        # Handle success responses (200 OK or 201 Created)
        if http_response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            try:
                return (True, PostResponse(**http_response.json()))
            except ValueError as e:
                # If JSON parsing/validation fails, log and return False
                print(f"Warning: Failed to parse PostResponse: {e}. Status code: {http_response.status_code}")
                return (False, None)
        else:
            # For non-success responses, log the error and return False
            error_msg = http_response.text[:500] if http_response.text else "No error details"
            print(f"Error: API returned status {http_response.status_code}: {error_msg}")
            return (False, None)

    def get_documents(
        self,
        location: str | None = None,
        category: str | None = None,
        updated_after: datetime | None = None,
        withHtmlContent: bool = False,
    ) -> list[Document]:
        """Get a list of documents from Readwise Reader.

        Params:
            location (str): The document's location, could be one of: new, later, shortlist, archive, feed
            category (str): The document's category, could be one of: article, email, rss, highlight, note, pdf, epub,
                tweet, video

        Returns:
            A list of `Document` objects.
        """
        params = {}
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

        results: list[Document] = []
        while (response := self._make_get_request(params)).next_page_cursor:
            results.extend(response.results)
            params["pageCursor"] = response.next_page_cursor
        # Make sure not to forget last response where `next_page_cursor` is None.
        results.extend(response.results)

        return results

    def get_document_by_id(self, id: str) -> Document | None:
        """Get a single documents from Readwise Reader by its ID.

        Params:
            id (str): The document's unique id. Using this parameter it will return just one document, if found.

        Returns:
            A `Document` object if a document with the given ID exists, or None otherwise.
        """
        response: GetResponse = self._make_get_request(params={"id": id})
        if response.count == 1:
            return response.results[0]
        return None

    def save_document(  # noqa: PLR0913
        self,
        url: str,
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
    ) -> tuple[bool, PostResponse | None]:
        """Save a document to Readwise Reader.

        Args:
            url: Document URL (required). Can include query parameters.
            html: Custom HTML content to save. If provided, Readwise uses this
                  instead of scraping the URL. Optional.
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

        Returns:
            Tuple of (success: bool, response: PostResponse)
            - success: True if document was saved successfully
            - response: PostResponse object with document_id and reader_url

        Raises:
            ReadwiseAuthenticationError: If authentication fails
            ReadwiseServerError: If Readwise server returns an error
        """
        payload_dict = {"url": url}

        # Add optional fields only if provided
        if html is not None:
            payload_dict["html"] = html
            payload_dict["should_clean_html"] = should_clean_html

        if title is not None:
            payload_dict["title"] = title
        if author is not None:
            payload_dict["author"] = author
        if summary is not None:
            payload_dict["summary"] = summary
        if published_date is not None:
            payload_dict["published_date"] = published_date
        if image_url is not None:
            payload_dict["image_url"] = image_url
        if location is not None:
            payload_dict["location"] = location
        if category is not None:
            payload_dict["category"] = category
        if saved_using is not None:
            payload_dict["saved_using"] = saved_using
        if tags is not None:
            payload_dict["tags"] = tags
        if notes is not None:
            payload_dict["notes"] = notes

        return self._make_post_request(payload=PostRequest(**payload_dict))

    def _make_delete_request(self, payload: DeleteRequest) -> tuple[bool, DeleteResponse | None]:
        """Make a DELETE request to the Readwise API."""
        http_response: requests.Response = requests.delete(
            url=f"{self.URL_BASE}/delete/{payload.id}/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )
        if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            # Respect rate limiting
            wait_time = int(http_response.headers["Retry-After"])
            print(f"Rate limited, waiting for {wait_time} seconds...")
            sleep(wait_time)
            return self._make_delete_request(payload)

        # Handle success responses (200 OK or 204 No Content)
        if http_response.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            try:
                # 204 No Content won't have a response body
                if http_response.status_code == HTTPStatus.NO_CONTENT:
                    return (True, DeleteResponse(success=True, message="Document deleted successfully"))
                return (True, DeleteResponse(**http_response.json()))
            except ValueError as e:
                # If JSON parsing/validation fails, log and return False
                print(f"Warning: Failed to parse DeleteResponse: {e}. Status code: {http_response.status_code}")
                return (False, None)
        else:
            # For non-success responses, log the error and return False
            error_msg = http_response.text[:500] if http_response.text else "No error details"
            print(f"Error: API returned status {http_response.status_code}: {error_msg}")
            return (False, None)

    def _make_update_request(self, payload: UpdateRequest) -> tuple[bool, UpdateResponse]:
        """Make an UPDATE request to the Readwise API using PATCH method.

        Args:
            payload: UpdateRequest object with document id and fields to update

        Returns:
            Tuple of (success, response)
        """
        try:
            http_response: requests.Response = requests.patch(
                url=f"{self.URL_BASE}/update/{payload.id}/",
                headers={"Authorization": f"Token {self.token}"},
                json=payload.model_dump(exclude={"id"}),  # Exclude id from payload as it's in the URL
                timeout=30,
            )

            if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                # Respect rate limiting
                wait_time = int(http_response.headers["Retry-After"])
                print(f"Rate limited, waiting for {wait_time} seconds...")
                sleep(wait_time)
                return self._make_update_request(payload)

            # Try to parse the response as JSON
            try:
                response_json = http_response.json()
                if http_response.status_code == HTTPStatus.OK:
                    return (True, UpdateResponse(success=True, message="Document updated successfully"))
                else:
                    return (False, UpdateResponse(success=False, message=f"API error: {response_json}"))
            except ValueError as json_error:
                # The response might not be JSON
                if http_response.status_code == HTTPStatus.OK:
                    # Successful but not JSON response
                    return (True, UpdateResponse(success=True, message="Document updated successfully"))
                else:
                    error_msg = f"Failed to parse API response: {json_error}. Status: {http_response.status_code}"
                    return (False, UpdateResponse(success=False, message=error_msg))

        except Exception as e:
            return (False, UpdateResponse(success=False, message=f"Request failed: {e}"))

    def delete_document(
        self, url: str | None = None, document_id: str | None = None
    ) -> tuple[bool, dict | DeleteResponse]:
        """Delete a document from Readwise Reader.

        Args:
            url: URL of the document to delete (either url or document_id must be provided)
            document_id: ID of the document to delete

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

        return self._make_delete_request(payload=DeleteRequest(id=str(document_id)))

    def update_document_location(self, document_id: str, location: str) -> tuple[bool, dict | UpdateResponse]:
        """Update a document's location in Readwise Reader.

        Args:
            document_id: ID of the document to update
            location: New location ('new' for inbox, 'later', 'archive')

        Returns:
            Tuple of (success, response)
                - success: Boolean indicating if the operation was successful
                - response: Response data or error information
        """
        if location not in ("new", "later", "archive"):
            return False, {"error": f"Invalid location: {location}. Must be one of: 'new', 'later', 'archive'"}

        try:
            # According to API docs: PATCH to https://readwise.io/api/v3/update/<document_id>/
            http_response: requests.Response = requests.patch(
                url=f"{self.URL_BASE}/update/{document_id}/",
                headers={"Authorization": f"Token {self.token}"},
                json={"location": location},
                timeout=30,
            )

            if http_response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                # Respect rate limiting
                wait_time = int(http_response.headers["Retry-After"])
                print(f"Rate limited, waiting for {wait_time} seconds...")
                sleep(wait_time)
                return self.update_document_location(document_id=document_id, location=location)

            # Try to parse the response as JSON
            try:
                response_json = http_response.json()
                if http_response.status_code == HTTPStatus.OK:
                    return (True, UpdateResponse(success=True, message=f"Location updated to {location}"))
                else:
                    return (False, {"error": f"API error: {http_response.status_code}", "details": response_json})
            except ValueError as json_error:
                error_msg = f"Failed to parse API response: {json_error}. Status code: {http_response.status_code}, Raw response: {http_response.text[:200]}"
                return (False, {"error": error_msg})

        except Exception as e:
            return (False, {"error": f"Request failed: {e}"})

    def search_document(self, url: str) -> tuple[bool, dict | Document]:
        """Search for a document by URL in Readwise Reader.

        Args:
            url: URL to search for

        Returns:
            Tuple of (success, document_data)
                - success: Boolean indicating if the document was found
                - document_data: Document information or error message
        """
        response: GetResponse = self._make_get_request(params={"url": url})
        if response.count > 0:
            return True, response.results[0]
        return False, {"error": f"No document found with URL {url}"}
