"""
Tests for the secret_checker module.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from entra_expiry_checker.models import AppRegistration, Certificate
from entra_expiry_checker.services.secret_checker import CredentialCheckerService


class TestCredentialCheckerService:
    """Test the CredentialCheckerService class."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock Graph client."""
        return MagicMock()

    @pytest.fixture
    def checker_service(self, mock_graph_client):
        """Create a CredentialCheckerService instance."""
        return CredentialCheckerService(mock_graph_client)

    def test_get_app_registration(self, checker_service, mock_graph_client):
        """Test getting app registration details."""
        mock_response = {
            "id": "12345678-1234-1234-1234-123456789012",
            "appId": "app-id-123",
            "displayName": "Test App",
        }
        mock_graph_client.make_request.return_value = mock_response

        result = checker_service.get_app_registration(
            "12345678-1234-1234-1234-123456789012"
        )

        assert result == mock_response
        mock_graph_client.make_request.assert_called_once_with(
            "/applications/12345678-1234-1234-1234-123456789012"
        )

    def test_get_app_secrets(self, checker_service, mock_graph_client):
        """Test getting app secrets."""
        mock_response = {
            "value": [
                {
                    "keyId": "secret-1",
                    "displayName": "Secret 1",
                    "endDateTime": (
                        datetime.now(timezone.utc) + timedelta(days=30)
                    ).isoformat(),
                }
            ]
        }
        mock_graph_client.make_request.return_value = mock_response

        result = checker_service.get_app_secrets("12345678-1234-1234-1234-123456789012")

        assert len(result) == 1
        assert result[0]["keyId"] == "secret-1"
        mock_graph_client.make_request.assert_called_once_with(
            "/applications/12345678-1234-1234-1234-123456789012/passwordCredentials"
        )

    def test_get_app_certificates(self, checker_service, mock_graph_client):
        """Test getting app certificates."""
        mock_response = {
            "value": [
                {
                    "keyId": "cert-1",
                    "displayName": "Cert 1",
                    "endDateTime": (
                        datetime.now(timezone.utc) + timedelta(days=60)
                    ).isoformat(),
                    "customKeyIdentifier": "thumbprint-123",
                }
            ]
        }
        mock_graph_client.make_request.return_value = mock_response

        result = checker_service.get_app_certificates(
            "12345678-1234-1234-1234-123456789012"
        )

        assert len(result) == 1
        assert result[0]["keyId"] == "cert-1"
        mock_graph_client.make_request.assert_called_once_with(
            "/applications/12345678-1234-1234-1234-123456789012/keyCredentials"
        )

    def test_check_expiring_credentials_success(
        self, checker_service, mock_graph_client
    ):
        """Test checking expiring credentials successfully."""
        future_date = datetime.now(timezone.utc) + timedelta(days=15)
        past_date = datetime.now(timezone.utc) - timedelta(days=5)

        # Mock app registration
        mock_graph_client.make_request.side_effect = [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "appId": "app-id-123",
                "displayName": "Test App",
            },
            {
                "value": [
                    {
                        "keyId": "secret-1",
                        "displayName": "Expiring Secret",
                        "endDateTime": future_date.isoformat(),
                    },
                    {
                        "keyId": "secret-2",
                        "displayName": "Expired Secret",
                        "endDateTime": past_date.isoformat(),
                    },
                ]
            },
            {"value": []},
        ]

        result = checker_service.check_expiring_credentials(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        assert result is not None
        assert isinstance(result.app_registration, AppRegistration)
        assert result.app_registration.display_name == "Test App"
        assert len(result.expiring_secrets) == 2
        assert len(result.expiring_certificates) == 0
        assert result.days_threshold == 30

        # Check first secret (expiring soon)
        assert result.expiring_secrets[0].key_id == "secret-1"
        assert result.expiring_secrets[0].is_expired is False
        assert result.expiring_secrets[0].days_until_expiry > 0

        # Check second secret (expired)
        assert result.expiring_secrets[1].key_id == "secret-2"
        assert result.expiring_secrets[1].is_expired is True
        assert result.expiring_secrets[1].days_until_expiry < 0

    def test_check_expiring_credentials_with_certificates(
        self, checker_service, mock_graph_client
    ):
        """Test checking expiring credentials including certificates."""
        future_date = datetime.now(timezone.utc) + timedelta(days=20)

        mock_graph_client.make_request.side_effect = [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "appId": "app-id-123",
                "displayName": "Test App",
            },
            {"value": []},
            {
                "value": [
                    {
                        "keyId": "cert-1",
                        "displayName": "Expiring Cert",
                        "endDateTime": future_date.isoformat(),
                        "customKeyIdentifier": "thumbprint-123",
                    }
                ]
            },
        ]

        result = checker_service.check_expiring_credentials(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        assert result is not None
        assert len(result.expiring_secrets) == 0
        assert len(result.expiring_certificates) == 1
        assert isinstance(result.expiring_certificates[0], Certificate)
        assert result.expiring_certificates[0].thumbprint == "thumbprint-123"

    def test_check_expiring_credentials_not_found(
        self, checker_service, mock_graph_client
    ):
        """Test checking credentials for non-existent app."""
        mock_graph_client.make_request.side_effect = ResourceNotFoundError(
            "App not found"
        )

        result = checker_service.check_expiring_credentials(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        assert result is None

    def test_check_expiring_credentials_no_expiring(
        self, checker_service, mock_graph_client
    ):
        """Test checking credentials with none expiring."""
        far_future_date = datetime.now(timezone.utc) + timedelta(days=100)

        mock_graph_client.make_request.side_effect = [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "appId": "app-id-123",
                "displayName": "Test App",
            },
            {
                "value": [
                    {
                        "keyId": "secret-1",
                        "displayName": "Not Expiring Secret",
                        "endDateTime": far_future_date.isoformat(),
                    }
                ]
            },
            {"value": []},
        ]

        result = checker_service.check_expiring_credentials(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        assert result is not None
        assert len(result.expiring_secrets) == 0
        assert len(result.expiring_certificates) == 0

    def test_check_expiring_secrets_backward_compatibility(
        self, checker_service, mock_graph_client
    ):
        """Test backward compatibility method check_expiring_secrets."""
        future_date = datetime.now(timezone.utc) + timedelta(days=15)

        mock_graph_client.make_request.side_effect = [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "appId": "app-id-123",
                "displayName": "Test App",
            },
            {
                "value": [
                    {
                        "keyId": "secret-1",
                        "displayName": "Expiring Secret",
                        "endDateTime": future_date.isoformat(),
                    }
                ]
            },
            {"value": []},
        ]

        result = checker_service.check_expiring_secrets(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        # Both methods should return the same type (ExpiryCheckResult or None)
        assert result is not None
        from entra_expiry_checker.models import ExpiryCheckResult

        assert isinstance(result, ExpiryCheckResult)

    def test_check_expiring_secrets_without_end_date(
        self, checker_service, mock_graph_client
    ):
        """Test checking secrets without endDateTime."""
        mock_graph_client.make_request.side_effect = [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "appId": "app-id-123",
                "displayName": "Test App",
            },
            {
                "value": [
                    {
                        "keyId": "secret-1",
                        "displayName": "Secret Without End Date",
                        # No endDateTime field
                    }
                ]
            },
            {"value": []},
        ]

        result = checker_service.check_expiring_credentials(
            "12345678-1234-1234-1234-123456789012", days_threshold=30
        )

        assert result is not None
        assert len(result.expiring_secrets) == 0
