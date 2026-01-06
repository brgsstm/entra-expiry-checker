"""
Tests for the graph_client module.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

from entra_expiry_checker.clients.graph_client import MicrosoftGraphClient


class TestMicrosoftGraphClient:
    """Test the MicrosoftGraphClient class."""

    @pytest.fixture
    def mock_credential(self):
        """Create a mock Azure credential."""
        mock_cred = MagicMock()
        mock_token = Mock()
        mock_token.token = "mock-access-token"
        mock_cred.get_token.return_value = mock_token
        return mock_cred

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    def test_client_initialization(self, mock_default_credential, mock_credential):
        """Test client initialization."""
        mock_default_credential.return_value = mock_credential

        client = MicrosoftGraphClient()

        assert client.base_url == "https://graph.microsoft.com/v1.0"
        assert client.credential == mock_credential

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_get_access_token_success(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test successful access token retrieval."""
        mock_default_credential.return_value = mock_credential

        client = MicrosoftGraphClient()
        token = client.get_access_token()

        assert token == "mock-access-token"
        mock_credential.get_token.assert_called_once_with(
            "https://graph.microsoft.com/.default"
        )

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    def test_get_access_token_failure(self, mock_default_credential):
        """Test access token retrieval failure."""
        mock_credential = MagicMock()
        mock_credential.get_token.side_effect = ClientAuthenticationError(
            "Authentication failed"
        )
        mock_default_credential.return_value = mock_credential

        client = MicrosoftGraphClient()

        with pytest.raises(SystemExit):
            client.get_access_token()

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_success(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test successful API request."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "displayName": "Test App"}
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()
        result = client.make_request("/applications/123")

        assert result == {"id": "123", "displayName": "Test App"}
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        assert call_args[0][1] == "https://graph.microsoft.com/v1.0/applications/123"
        assert "Authorization" in call_args[1]["headers"]

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_not_found_404(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with 404 Not Found."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock()  # Don't actually raise
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(ResourceNotFoundError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_invalid_object_id(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with invalid object ID (400 with specific error)."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": "Request_BadRequest",
                "message": "Invalid object identifier",
            }
        }
        mock_response.raise_for_status = Mock()  # Don't actually raise
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(ResourceNotFoundError):
            client.make_request("/applications/invalid")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_unauthorized(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with 401 Unauthorized."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 401
        # Make raise_for_status actually raise HTTPError
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized"
        )
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_forbidden(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with 403 Forbidden."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "403 Client Error: Forbidden"
        )
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_rate_limited(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with 429 Rate Limited."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Client Error: Too Many Requests"
        )
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_server_error(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with 500 Server Error."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()

        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_make_request_network_error(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test request with network error."""
        mock_default_credential.return_value = mock_credential

        mock_requests.request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        client = MicrosoftGraphClient()

        with pytest.raises(requests.exceptions.ConnectionError):
            client.make_request("/applications/123")

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_get_all_applications_single_page(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test getting all applications with single page."""
        mock_default_credential.return_value = mock_credential

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "app1", "displayName": "App 1"},
                {"id": "app2", "displayName": "App 2"},
            ]
        }
        mock_requests.request.return_value = mock_response

        client = MicrosoftGraphClient()
        apps = client.get_all_applications()

        assert len(apps) == 2
        assert apps[0]["id"] == "app1"
        assert apps[1]["id"] == "app2"

    @patch("entra_expiry_checker.clients.graph_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.graph_client.requests")
    def test_get_all_applications_multiple_pages(
        self, mock_requests, mock_default_credential, mock_credential
    ):
        """Test getting all applications with pagination."""
        mock_default_credential.return_value = mock_credential

        # First page
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "value": [{"id": "app1", "displayName": "App 1"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/applications?$skipToken=token123",
        }

        # Second page
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "value": [{"id": "app2", "displayName": "App 2"}]
        }

        mock_requests.request.side_effect = [mock_response_1, mock_response_2]

        client = MicrosoftGraphClient()
        apps = client.get_all_applications()

        assert len(apps) == 2
        assert mock_requests.request.call_count == 2
