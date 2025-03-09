"""A client for Readwise Reader API."""

from datetime import datetime
from http import HTTPStatus
from os import environ
from time import sleep
from typing import Final

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

    def _make_post_request(self, payload: PostRequest) -> tuple[bool, PostResponse]:
        http_response: requests.Response = requests.post(
            url=f"{self.URL_BASE}/save/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )
        if http_response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
            return (http_response.status_code == HTTPStatus.OK, PostResponse(**http_response.json()))

        # Respect rate limiting of maximum 20 requests per minute (https://readwise.io/reader_api).
        wait_time = int(http_response.headers["Retry-After"])
        sleep(wait_time)
        return self._make_post_request(payload)

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

    def save_document(self, url: str) -> tuple[bool, PostResponse]:
        """Save a document to Readwise Reader.

        Returns:
            int: Status code of 201 or 200 if document already exist.
            PostResponse: An object containing ID and Reader URL of the saved document.
        """
        return self._make_post_request(payload=PostRequest(url=url))

    def _make_delete_request(self, payload: DeleteRequest) -> tuple[bool, DeleteResponse]:
        """Make a DELETE request to the Readwise API."""
        http_response: requests.Response = requests.delete(
            url=f"{self.URL_BASE}/delete/",
            headers={"Authorization": f"Token {self.token}"},
            json=payload.model_dump(),
            timeout=30,
        )
        if http_response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
            return (http_response.status_code == HTTPStatus.OK, DeleteResponse(**http_response.json()))

        # Respect rate limiting
        wait_time = int(http_response.headers["Retry-After"])
        print(f"Rate limited, waiting for {wait_time} seconds...")
        sleep(wait_time)
        return self._make_delete_request(payload)

    def _make_update_request(self, payload: UpdateRequest) -> tuple[bool, dict | UpdateResponse]:
        """Make an UPDATE request to the Readwise API."""
        try:
            http_response: requests.Response = requests.post(
                url=f"{self.URL_BASE}/update/",
                headers={"Authorization": f"Token {self.token}"},
                json=payload.model_dump(),
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
                    return (True, UpdateResponse(**response_json))
                else:
                    return (False, {"error": f"API error: {http_response.status_code}", "details": response_json})
            except ValueError as json_error:
                # Log the raw response for debugging
                error_msg = f"Failed to parse API response: {json_error}. Raw response: {http_response.text[:200]}"
                return (False, {"error": error_msg})
        
        except Exception as e:
            return (False, {"error": f"Request failed: {e}"})

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
            document_id = result.id # type: ignore

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

        return self._make_update_request(payload=UpdateRequest(id=document_id, location=location))

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
