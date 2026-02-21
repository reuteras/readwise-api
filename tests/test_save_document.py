"""Tests for save_document, token validation, document listing, and error handling in the Readwise API client."""

import os
from http import HTTPStatus
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from readwise.api import (
    ReadwiseAuthenticationError,
    ReadwiseClientError,
    ReadwiseRateLimitError,
    ReadwiseReader,
    ReadwiseServerError,
)
from readwise.cli import app
from readwise.model import DeleteResponse, Document, GetResponse, UpdateRequest, UpdateResponse


class TestSaveDocument:
    """Test cases for the save_document function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    def test_save_document_success(self, client: ReadwiseReader) -> None:
        """Test successful document save with 200 response."""
        with patch("readwise.api.requests.post") as mock_post:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {"id": "doc123", "url": "https://reader.readwise.io/doc/123"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is True
            assert response is not None
            assert response.id == "doc123"
            assert response.url == "https://reader.readwise.io/doc/123"

    def test_save_document_success_201(self, client: ReadwiseReader) -> None:
        """Test successful document save with 201 Created response."""
        with patch("readwise.api.requests.post") as mock_post:
            # Mock successful response with 201 Created
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.CREATED
            mock_response.json.return_value = {"id": "doc456", "url": "https://reader.readwise.io/doc/456"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is True
            assert response is not None
            assert response.id == "doc456"
            assert response.url == "https://reader.readwise.io/doc/456"

    def test_save_document_with_full_metadata(self, client: ReadwiseReader) -> None:
        """Test save_document with all optional fields."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {"id": "doc456", "url": "https://reader.readwise.io/doc/456"}
            mock_post.return_value = mock_response

            success, response = client.save_document(
                url="https://example.com/article",
                html="<html><body>Content</body></html>",
                title="Test Article",
                author="Test Author",
                summary="Test Summary",
                published_date="2024-01-01T00:00:00Z",
                image_url="https://example.com/image.jpg",
                location="archive",
                category="article",
                saved_using="test-tool",
                tags=["tag1", "tag2"],
                notes="Test notes",
                should_clean_html=True,
            )

            assert success is True
            assert response is not None
            assert response.id == "doc456"

            # Verify the request was made with correct payload
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["url"] == "https://readwise.io/api/v3/save/"
            assert call_kwargs["headers"] == {"Authorization": "Token test-token"}

            payload = call_kwargs["json"]
            assert payload["url"] == "https://example.com/article"
            assert payload["html"] == "<html><body>Content</body></html>"
            assert payload["title"] == "Test Article"
            assert payload["author"] == "Test Author"
            assert payload["tags"] == ["tag1", "tag2"]

    def test_save_document_auth_error(self, client: ReadwiseReader) -> None:
        """Test save_document with 401 Unauthorized response."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.UNAUTHORIZED
            mock_response.json.return_value = {"error": "Invalid token"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is False
            assert response is None

    def test_save_document_bad_request(self, client: ReadwiseReader) -> None:
        """Test save_document with 400 Bad Request response."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.BAD_REQUEST
            mock_response.json.return_value = {"error": "Invalid URL format"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="invalid-url")

            assert success is False
            assert response is None

    def test_save_document_server_error(self, client: ReadwiseReader) -> None:
        """Test save_document with 500 Internal Server Error response."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            mock_response.json.return_value = {"error": "Internal server error"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is False
            assert response is None

    def test_save_document_invalid_json_response(self, client: ReadwiseReader) -> None:
        """Test save_document when response body is not valid JSON."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is False
            assert response is None

    def test_save_document_rate_limit(self, client: ReadwiseReader) -> None:
        """Test save_document handles rate limiting (429 Too Many Requests)."""
        with patch("readwise.api.requests.post") as mock_post, patch("readwise.api.sleep") as mock_sleep:
            # First call returns rate limit, second returns success
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = HTTPStatus.TOO_MANY_REQUESTS
            rate_limit_response.headers = {"Retry-After": "1"}

            success_response = MagicMock()
            success_response.status_code = HTTPStatus.OK
            success_response.json.return_value = {"id": "doc789", "url": "https://reader.readwise.io/doc/789"}

            mock_post.side_effect = [rate_limit_response, success_response]

            success, response = client.save_document(url="https://example.com", retry_on_429=True)

            assert success is True
            assert response is not None
            assert response.id == "doc789"
            mock_sleep.assert_called_once_with(1)

    def test_save_document_minimal_fields(self, client: ReadwiseReader) -> None:
        """Test save_document with only required URL field."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {"id": "doc_minimal", "url": "https://reader.readwise.io/doc/minimal"}
            mock_post.return_value = mock_response

            success, response = client.save_document(url="https://example.com")

            assert success is True
            assert response is not None

            # Verify the request was made with correct URL
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            assert payload["url"] == "https://example.com"

    def test_save_document_with_html_only(self, client: ReadwiseReader) -> None:
        """Test save_document with HTML content only (no URL)."""
        with patch("readwise.api.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {"id": "doc_html", "url": "https://reader.readwise.io/doc/html"}
            mock_post.return_value = mock_response

            success, response = client.save_document(html="<html><body>Test</body></html>")

            assert success is True
            assert response is not None

            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            assert payload["html"] == "<html><body>Test</body></html>"
            assert "url" not in payload or payload["url"] is None

    def test_save_document_validation_no_url_or_html(self, client: ReadwiseReader) -> None:
        """Test save_document raises ValueError when neither url nor html is provided."""
        with pytest.raises(ValueError, match="Either 'url' or 'html' must be provided"):
            client.save_document()

    def test_save_document_validation_should_clean_html_without_html(self, client: ReadwiseReader) -> None:
        """Test save_document raises ValueError when should_clean_html is used without html."""
        with pytest.raises(ValueError, match="'should_clean_html' can only be used when 'html' is provided"):
            client.save_document(url="https://example.com", should_clean_html=True)

    def test_save_document_validation_invalid_location(self, client: ReadwiseReader) -> None:
        """Test save_document raises ValueError for invalid location."""
        with pytest.raises(ValueError, match="Parameter 'location' cannot be of value 'invalid'"):
            client.save_document(url="https://example.com", location="invalid")

    def test_save_document_validation_invalid_category(self, client: ReadwiseReader) -> None:
        """Test save_document raises ValueError for invalid category."""
        with pytest.raises(ValueError, match="Parameter 'category' cannot be of value 'invalid'"):
            client.save_document(url="https://example.com", category="invalid")


class TestDeleteDocument:
    """Test cases for the delete_document function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    def test_delete_document_success(self, client: ReadwiseReader) -> None:
        """Test successful document deletion with 200 response."""
        with patch("readwise.api.requests.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {"success": True, "message": "Document deleted"}
            mock_delete.return_value = mock_response

            success, response = client.delete_document(document_id="doc123")

            assert success is True
            assert response is not None

    def test_delete_document_success_204(self, client: ReadwiseReader) -> None:
        """Test successful document deletion with 204 No Content response."""
        with patch("readwise.api.requests.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.NO_CONTENT
            mock_response.text = ""
            mock_delete.return_value = mock_response

            success, response = client.delete_document(document_id="doc123")

            assert success is True
            assert response is not None
            response_obj = cast(DeleteResponse, response)
            assert response_obj.success is True

    def test_delete_document_not_found(self, client: ReadwiseReader) -> None:
        """Test delete_document with 404 Not Found response."""
        with patch("readwise.api.requests.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.NOT_FOUND
            mock_response.json.return_value = {"error": "Document not found"}
            mock_delete.return_value = mock_response

            success, response = client.delete_document(document_id="nonexistent")

            assert success is False
            assert response is None

    def test_delete_document_invalid_json(self, client: ReadwiseReader) -> None:
        """Test delete_document when response body is not valid JSON."""
        with patch("readwise.api.requests.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_delete.return_value = mock_response

            success, response = client.delete_document(document_id="doc123")

            assert success is False
            assert response is None

    def test_delete_document_no_params(self, client: ReadwiseReader) -> None:
        """Test delete_document with neither URL nor document_id raises error."""
        success, response = client.delete_document()

        assert success is False
        assert response == {"error": "Either url or document_id must be provided"}


class TestValidateToken:
    """Test cases for the validate_token function."""

    def test_validate_token_success(self) -> None:
        """Test successful token validation (204 response)."""
        with patch("readwise.api.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.NO_CONTENT
            mock_get.return_value = mock_response

            client = ReadwiseReader(token="test-token")
            result = client.validate_token("test-token")

            assert result is True
            mock_get.assert_called_once_with(
                url="https://readwise.io/api/v2/auth/",
                headers={"Authorization": "Token test-token"},
                timeout=30,
            )

    def test_validate_token_invalid_401(self) -> None:
        """Test token validation with 401 Unauthorized response."""
        with patch("readwise.api.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.UNAUTHORIZED
            mock_get.return_value = mock_response

            client = ReadwiseReader(token="test-token")
            result = client.validate_token("test-token")

            assert result is False

    def test_validate_token_invalid_403(self) -> None:
        """Test token validation with 403 Forbidden response."""
        with patch("readwise.api.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.FORBIDDEN
            mock_get.return_value = mock_response

            client = ReadwiseReader(token="test-token")
            result = client.validate_token("test-token")

            assert result is False

    def test_validate_token_unexpected_error(self) -> None:
        """Test token validation with unexpected 5xx response raises exception."""
        with patch("readwise.api.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            client = ReadwiseReader(token="test-token")

            with pytest.raises(Exception, match="Unexpected response from auth endpoint"):
                client.validate_token("test-token")

    def test_validate_token_uses_env_var(self) -> None:
        """Test validate_token uses READWISE_TOKEN env var when no token provided."""
        with patch("readwise.api.requests.get") as mock_get, patch.dict("os.environ", {"READWISE_TOKEN": "env-token"}):
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.NO_CONTENT
            mock_get.return_value = mock_response

            client = ReadwiseReader()  # No token provided
            result = client.validate_token()  # Should use env var

            assert result is True
            mock_get.assert_called_once_with(
                url="https://readwise.io/api/v2/auth/",
                headers={"Authorization": "Token env-token"},
                timeout=30,
            )

    def test_validate_token_no_token_raises_error(self) -> None:
        """Test validate_token raises ValueError when no token available."""
        with patch.dict("os.environ", {}, clear=True):
            client = ReadwiseReader()  # No token provided

            with pytest.raises(ValueError, match="Token is required"):
                client.validate_token()


class TestGetDocuments:
    """Test cases for the get_documents function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    @pytest.fixture
    def mock_document(self) -> Document:
        """Create a mock document for testing."""
        return Document(
            id="doc123",
            url="https://example.com",
            title="Test Document",
            author="Test Author",
            source="Test Source",
            category="article",
            location="new",
            tags={},
            site_name="Test Site",
            word_count=100,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            notes="",
            published_date="2023-01-01",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
            content="Test content",
            source_url="https://example.com/source",
            parent_id=None,
            saved_at="2023-01-01T00:00:00Z",
            last_moved_at="2023-01-01T00:00:00Z",
            reading_progress=0.5,
            first_opened_at="2023-01-01T00:00:00Z",
            last_opened_at="2023-01-01T00:00:00Z",
        )

    def test_get_documents_basic(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test basic get_documents functionality."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = client.get_documents()

            assert len(documents) == 1
            assert documents[0].id == "doc123"
            mock_get.assert_called_once()

    def test_get_documents_with_limit(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_documents with limit parameter."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = client.get_documents(limit=10)

            assert len(documents) == 1
            assert documents[0].id == "doc123"
            # Check that limit was passed in the request
            call_args = mock_get.call_args[0][0]  # First positional arg is params dict
            assert call_args["limit"] == 10

    def test_get_documents_limit_validation(self, client: ReadwiseReader) -> None:
        """Test get_documents validates limit parameter."""
        with pytest.raises(ValueError, match="Parameter 'limit' must be between 1 and 100"):
            client.get_documents(limit=0)

        with pytest.raises(ValueError, match="Parameter 'limit' must be between 1 and 100"):
            client.get_documents(limit=101)

    def test_get_documents_with_tag(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_documents with tag parameter."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = client.get_documents(tag="test-tag")

            assert len(documents) == 1
            call_args = mock_get.call_args[0][0]
            assert call_args["tag"] == "test-tag"

    def test_get_documents_with_raw_source_url(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_documents with with_raw_source_url parameter."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = client.get_documents(with_raw_source_url=True)

            assert len(documents) == 1
            call_args = mock_get.call_args[0][0]
            assert call_args["withRawSourceUrl"] is True

    def test_get_documents_pagination(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_documents handles pagination correctly."""
        doc1 = mock_document
        doc2 = mock_document.model_copy(update={"id": "doc456"})

        # First call returns doc1 with next cursor
        response1 = GetResponse(count=1, nextPageCursor="cursor123", results=[doc1])
        # Second call returns doc2 with no cursor
        response2 = GetResponse(count=1, nextPageCursor=None, results=[doc2])

        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = [response1, response2]

            documents = client.get_documents()  # No limit = auto-paginate

            assert len(documents) == 2
            assert documents[0].id == "doc123"
            assert documents[1].id == "doc456"

            # Should have made 2 calls
            assert mock_get.call_count == 2

    def test_get_documents_limit_no_pagination(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_documents with limit doesn't paginate."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor="cursor123", results=[mock_document])
            mock_get.return_value = mock_response

            documents = client.get_documents(limit=10)

            assert len(documents) == 1
            # Should have made only 1 call despite next_page_cursor being present
            assert mock_get.call_count == 1


class TestIterDocuments:
    """Test cases for the iter_documents generator function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    @pytest.fixture
    def mock_document(self) -> Document:
        """Create a mock document for testing."""
        return Document(
            id="doc123",
            url="https://example.com",
            title="Test Document",
            author="Test Author",
            source="Test Source",
            category="article",
            location="new",
            tags={},
            site_name="Test Site",
            word_count=100,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            notes="",
            published_date="2023-01-01",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
            content="Test content",
            source_url="https://example.com/source",
            parent_id=None,
            saved_at="2023-01-01T00:00:00Z",
            last_moved_at="2023-01-01T00:00:00Z",
            reading_progress=0.5,
            first_opened_at="2023-01-01T00:00:00Z",
            last_opened_at="2023-01-01T00:00:00Z",
        )

    def test_iter_documents_basic(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test basic iter_documents functionality."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = list(client.iter_documents())

            assert len(documents) == 1
            assert documents[0].id == "doc123"

    def test_iter_documents_pagination(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test iter_documents handles pagination correctly."""
        doc1 = mock_document
        doc2 = mock_document.model_copy(update={"id": "doc456"})

        response1 = GetResponse(count=1, nextPageCursor="cursor123", results=[doc1])
        response2 = GetResponse(count=1, nextPageCursor=None, results=[doc2])

        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = [response1, response2]

            documents = list(client.iter_documents())

            assert len(documents) == 2
            assert documents[0].id == "doc123"
            assert documents[1].id == "doc456"

    def test_iter_documents_with_parameters(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test iter_documents passes parameters correctly."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            documents = list(client.iter_documents(location="archive", tag="test-tag"))

            assert len(documents) == 1
            call_args = mock_get.call_args[0][0]
            assert call_args["location"] == "archive"
            assert call_args["tag"] == "test-tag"


class TestUpdateDocumentLocation:
    """Test cases for the update_document_location function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    def test_update_document_location_success(self, client: ReadwiseReader) -> None:
        """Test successful document location update."""
        with patch.object(client, "_make_update_request") as mock_update:
            mock_response = (True, UpdateResponse(success=True, message="Document updated successfully"))
            mock_update.return_value = mock_response

            success, response = client.update_document_location("doc123", "archive")

            assert success is True
            assert isinstance(response, UpdateResponse)
            assert response.success is True
            assert response.message == "Document updated successfully"

            expected_payload = UpdateRequest(id="doc123", location="archive")
            mock_update.assert_called_once_with(expected_payload, retry_on_429=False)

    def test_update_document_location_failure(self, client: ReadwiseReader) -> None:
        """Test failed document location update."""
        with patch.object(client, "_make_update_request") as mock_update:
            mock_response = (False, UpdateResponse(success=False, message="Update failed"))
            mock_update.return_value = mock_response

            success, response = client.update_document_location("doc123", "archive")

            assert success is False
            assert isinstance(response, UpdateResponse)
            assert response.success is False
            assert response.message == "Update failed"

    def test_update_document_location_with_retry(self, client: ReadwiseReader) -> None:
        """Test update_document_location with retry_on_429 enabled."""
        with patch.object(client, "_make_update_request") as mock_update:
            mock_response = (True, UpdateResponse(success=True, message="Document updated successfully"))
            mock_update.return_value = mock_response

            success, _response = client.update_document_location("doc123", "archive", retry_on_429=True)

            assert success is True

            expected_payload = UpdateRequest(id="doc123", location="archive")
            mock_update.assert_called_once_with(expected_payload, retry_on_429=True)


class TestSearchDocument:
    """Test cases for the search_document function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    @pytest.fixture
    def mock_document(self) -> Document:
        """Create a mock document for testing."""
        return Document(
            id="doc123",
            url="https://example.com",
            title="Test Document",
            author="Test Author",
            source="Test Source",
            category="article",
            location="new",
            tags={},
            site_name="Test Site",
            word_count=100,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            notes="",
            published_date="2023-01-01",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
            content="Test content",
            source_url="https://example.com/source",
            parent_id=None,
            saved_at="2023-01-01T00:00:00Z",
            last_moved_at="2023-01-01T00:00:00Z",
            reading_progress=0.5,
            first_opened_at="2023-01-01T00:00:00Z",
            last_opened_at="2023-01-01T00:00:00Z",
        )

    def test_search_document_found(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test search_document when document is found."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            success, result = client.search_document("https://example.com")

            assert success is True
            assert isinstance(result, Document)
            assert result.id == "doc123"
            mock_get.assert_called_once_with(params={"url": "https://example.com"}, retry_on_429=False)

    def test_search_document_not_found(self, client: ReadwiseReader) -> None:
        """Test search_document when document is not found."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=0, nextPageCursor=None, results=[])
            mock_get.return_value = mock_response

            success, result = client.search_document("https://example.com")

            assert success is False
            assert result == {"error": "No document found with URL https://example.com"}
            mock_get.assert_called_once_with(params={"url": "https://example.com"}, retry_on_429=False)

    def test_search_document_with_retry(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test search_document with retry_on_429 enabled."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            success, result = client.search_document("https://example.com", retry_on_429=True)

            assert success is True
            assert isinstance(result, Document)
            assert result.id == "doc123"
            mock_get.assert_called_once_with(params={"url": "https://example.com"}, retry_on_429=True)


class TestCLI:
    """Test cases for CLI commands."""

    def test_cli_list_help(self) -> None:
        """Test that list command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "--help"])

        assert result.exit_code == 0
        assert "List documents" in result.output
        assert "--location" in result.output
        assert "--category" in result.output

    def test_cli_get_help(self) -> None:
        """Test that get command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["get", "--help"])

        assert result.exit_code == 0
        assert "Get a single document" in result.output

    def test_cli_save_help(self) -> None:
        """Test that save command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["save", "--help"])

        assert result.exit_code == 0
        assert "Save a document" in result.output
        assert "--url" in result.output
        assert "--html-file" in result.output

    def test_cli_auth_check_help(self) -> None:
        """Test that auth-check command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["auth-check", "--help"])

        assert result.exit_code == 0
        assert "Check if the Readwise token is valid" in result.output

    def test_cli_main_help(self) -> None:
        """Test that main CLI help shows all commands."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "save" in result.output
        assert "auth-check" in result.output

    def test_cli_list_no_token(self) -> None:
        """Test that CLI commands fail gracefully without token."""
        # Remove token from environment
        old_token = os.environ.get("READWISE_TOKEN")
        if "READWISE_TOKEN" in os.environ:
            del os.environ["READWISE_TOKEN"]

        try:
            runner = CliRunner()
            result = runner.invoke(app, ["list"])

            # Should fail with exit code 1 due to missing token
            assert result.exit_code == 1
        finally:
            # Restore token
            if old_token:
                os.environ["READWISE_TOKEN"] = old_token


class TestErrorHandling:
    """Test cases for error handling and rate limiting."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    def test_get_documents_rate_limit_error_without_retry(self, client: ReadwiseReader) -> None:
        """Test that rate limit errors are raised when retry_on_429 is False."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = ReadwiseRateLimitError(
                "Rate limit exceeded",
                status_code=429,
                response_body="Too Many Requests",
                retry_after=30,
            )

            with pytest.raises(ReadwiseRateLimitError) as exc_info:
                client.get_documents(retry_on_429=False)

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 30

    def test_get_documents_server_error(self, client: ReadwiseReader) -> None:
        """Test that server errors are raised."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = ReadwiseServerError(
                "Internal server error",
                status_code=500,
                response_body="Server Error",
            )

            with pytest.raises(ReadwiseServerError) as exc_info:
                client.get_documents()

            assert exc_info.value.status_code == 500

    def test_get_documents_auth_error(self, client: ReadwiseReader) -> None:
        """Test that authentication errors are raised."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = ReadwiseAuthenticationError(
                "Authentication failed",
                status_code=401,
                response_body="Invalid token",
            )

            with pytest.raises(ReadwiseAuthenticationError) as exc_info:
                client.get_documents()

            assert exc_info.value.status_code == 401

    def test_get_documents_client_error(self, client: ReadwiseReader) -> None:
        """Test that client errors are raised."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_get.side_effect = ReadwiseClientError(
                "Bad request",
                status_code=400,
                response_body="Invalid parameter",
            )

            with pytest.raises(ReadwiseClientError) as exc_info:
                client.get_documents()

            assert exc_info.value.status_code == 400

    def test_save_document_rate_limit_error_without_retry(self, client: ReadwiseReader) -> None:
        """Test that POST rate limit errors are raised when retry_on_429 is False."""
        with patch.object(client, "_make_post_request") as mock_post:
            mock_post.side_effect = ReadwiseRateLimitError(
                "Rate limit exceeded",
                status_code=429,
                response_body="Too Many Requests",
                retry_after=30,
            )

            with pytest.raises(ReadwiseRateLimitError) as exc_info:
                client.save_document(url="https://example.com", retry_on_429=False)

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 30

    def test_save_document_server_error(self, client: ReadwiseReader) -> None:
        """Test that POST server errors are raised."""
        with patch.object(client, "_make_post_request") as mock_post:
            mock_post.side_effect = ReadwiseServerError(
                "Internal server error",
                status_code=500,
                response_body="Server Error",
            )

            with pytest.raises(ReadwiseServerError) as exc_info:
                client.save_document(url="https://example.com")

            assert exc_info.value.status_code == 500

    def test_get_documents_retry_on_429_enabled(self, client: ReadwiseReader) -> None:
        """Test that retry_on_429=True causes automatic retry on rate limits."""
        mock_document = Document(
            id="doc123",
            url="https://example.com",
            title="Test Document",
            author="Test Author",
            source="Test Source",
            category="article",
            location="new",
            tags={},
            site_name="Test Site",
            word_count=100,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            notes="",
            published_date="2023-01-01",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
            content="Test content",
            source_url="https://example.com/source",
            parent_id=None,
            saved_at="2023-01-01T00:00:00Z",
            last_moved_at="2023-01-01T00:00:00Z",
            reading_progress=0.5,
            first_opened_at="2023-01-01T00:00:00Z",
            last_opened_at="2023-01-01T00:00:00Z",
        )

        with patch("readwise.api.requests.get") as mock_get, patch("readwise.api.sleep") as mock_sleep:
            # First request returns 429, second returns success
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {"Retry-After": "1"}
            rate_limit_response.text = "Rate limited"

            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "count": 1,
                "nextPageCursor": None,
                "results": [mock_document.model_dump()],
            }

            mock_get.side_effect = [rate_limit_response, success_response]

            documents = client.get_documents(retry_on_429=True)

            assert len(documents) == 1
            assert documents[0].id == "doc123"
            mock_sleep.assert_called_once_with(1)
            assert mock_get.call_count == 2


class TestGetDocumentById:
    """Test cases for the get_document_by_id function."""

    @pytest.fixture
    def client(self) -> ReadwiseReader:
        """Create a ReadwiseReader client with a test token."""
        return ReadwiseReader(token="test-token")

    @pytest.fixture
    def mock_document(self) -> Document:
        """Create a mock document for testing."""
        return Document(
            id="doc123",
            url="https://example.com",
            title="Test Document",
            author="Test Author",
            source="Test Source",
            category="article",
            location="new",
            tags={},
            site_name="Test Site",
            word_count=100,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            notes="",
            published_date="2023-01-01",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
            content="Test content",
            source_url="https://example.com/source",
            parent_id=None,
            saved_at="2023-01-01T00:00:00Z",
            last_moved_at="2023-01-01T00:00:00Z",
            reading_progress=0.5,
            first_opened_at="2023-01-01T00:00:00Z",
            last_opened_at="2023-01-01T00:00:00Z",
        )

    def test_get_document_by_id_found(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_document_by_id when document is found."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=1, nextPageCursor=None, results=[mock_document])
            mock_get.return_value = mock_response

            result = client.get_document_by_id("doc123")

            assert result is not None
            assert result.id == "doc123"
            assert result.title == "Test Document"
            mock_get.assert_called_once_with(params={"id": "doc123"}, retry_on_429=False)

    def test_get_document_by_id_not_found(self, client: ReadwiseReader) -> None:
        """Test get_document_by_id when document is not found."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=0, nextPageCursor=None, results=[])
            mock_get.return_value = mock_response

            result = client.get_document_by_id("nonexistent")

            assert result is None
            mock_get.assert_called_once_with(params={"id": "nonexistent"}, retry_on_429=False)

    def test_get_document_by_id_multiple_results(self, client: ReadwiseReader, mock_document: Document) -> None:
        """Test get_document_by_id when somehow multiple results are returned (shouldn't happen)."""
        with patch.object(client, "_make_get_request") as mock_get:
            mock_response = GetResponse(count=2, nextPageCursor=None, results=[mock_document, mock_document])
            mock_get.return_value = mock_response

            result = client.get_document_by_id("doc123")

            assert result is None  # Should return None if count != 1
            mock_get.assert_called_once_with(params={"id": "doc123"}, retry_on_429=False)
