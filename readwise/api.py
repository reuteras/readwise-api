"""A client for Readwise Reader API."""

from datetime import datetime
from http import HTTPStatus
from os import environ
from time import sleep
from typing import Final

import requests

from readwise.model import Document, GetResponse, PostRequest, PostResponse


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
        withHtmlContent: bool = False
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

    def get_document_by_id(self, doc_id: str) -> Document | None:
        """Get a single documents from Readwise Reader by its ID.

        Params:
            doc_id (str): The document's unique id. Using this parameter it will return just one document, if found.

        Returns:
            A `Document` object if a document with the given ID exists, or None otherwise.
        """
        response: GetResponse = self._make_get_request(params={"id": doc_id})
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
