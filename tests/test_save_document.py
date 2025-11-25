"""Tests for save_document and error handling in the Readwise API client."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from readwise.api import ReadwiseReader


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

            success, response = client.save_document(url="https://example.com")

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
            assert response.success is True

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
