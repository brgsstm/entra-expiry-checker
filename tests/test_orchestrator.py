"""
Tests for the orchestrator module.
"""

from unittest.mock import MagicMock

import pytest

from entra_expiry_checker.models import ProcessingResult
from entra_expiry_checker.orchestrator import SecretExpiryOrchestrator


class TestSecretExpiryOrchestrator:
    """Test the SecretExpiryOrchestrator class."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock Graph client."""
        return MagicMock()

    @pytest.fixture
    def mock_email_service(self):
        """Create a mock Email service."""
        service = MagicMock()
        service.send_expiry_notification.return_value = True
        return service

    @pytest.fixture
    def mock_table_client(self):
        """Create a mock Table client."""
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        """Create a mock Settings."""
        settings = MagicMock()
        settings.MODE = "tenant"
        settings.DEFAULT_NOTIFICATION_EMAIL = None
        return settings

    @pytest.fixture
    def orchestrator(
        self, mock_graph_client, mock_email_service, mock_table_client, mock_settings
    ):
        """Create a SecretExpiryOrchestrator instance."""
        return SecretExpiryOrchestrator(
            graph_client=mock_graph_client,
            email_service=mock_email_service,
            table_client=mock_table_client,
            settings=mock_settings,
        )

    def test_orchestrator_initialization(
        self, mock_graph_client, mock_email_service, mock_settings
    ):
        """Test orchestrator initialization."""
        orchestrator = SecretExpiryOrchestrator(
            graph_client=mock_graph_client,
            email_service=mock_email_service,
            settings=mock_settings,
        )

        assert orchestrator.graph_client == mock_graph_client
        assert orchestrator.email_service == mock_email_service
        assert orchestrator.settings == mock_settings

    def test_process_all_app_registrations_no_apps(
        self, orchestrator, mock_email_service
    ):
        """Test processing when no applications are found."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.return_value = []

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 0
        assert result.processed == 0
        assert result.emails_sent == 0
        mock_email_service.send_expiry_notification.assert_not_called()

    def test_process_all_app_registrations_with_expiring_credentials(
        self, orchestrator, mock_email_service, sample_expiry_check_result
    ):
        """Test processing applications with expiring credentials."""
        orchestrator.app_discovery = MagicMock()
        # Setup discovery to return one app
        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            }
        ]

        # Setup credential checker to return expiring credentials
        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.return_value = (
            sample_expiry_check_result
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 1
        assert result.processed == 1
        assert result.successful_checks == 1
        assert result.emails_sent == 1
        assert result.not_found == 0
        mock_email_service.send_expiry_notification.assert_called_once()

    def test_process_all_app_registrations_no_expiring_credentials(
        self, orchestrator, mock_email_service, sample_expiry_check_result_no_expiring
    ):
        """Test processing applications with no expiring credentials."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            }
        ]

        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.return_value = (
            sample_expiry_check_result_no_expiring
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 1
        assert result.processed == 1
        assert result.successful_checks == 1
        assert result.emails_sent == 0  # No emails sent when nothing expiring
        mock_email_service.send_expiry_notification.assert_not_called()

    def test_process_all_app_registrations_app_not_found(
        self, orchestrator, mock_email_service
    ):
        """Test processing when app registration is not found."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            }
        ]

        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.return_value = None

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 1
        assert result.processed == 1
        assert result.successful_checks == 0
        assert result.not_found == 1
        assert result.emails_sent == 0
        mock_email_service.send_expiry_notification.assert_not_called()

    def test_process_all_app_registrations_multiple_recipients(
        self, orchestrator, mock_email_service, sample_expiry_check_result
    ):
        """Test processing with multiple notification recipients."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner1@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            },
            {
                "email": "owner2@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            },
        ]

        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.return_value = (
            sample_expiry_check_result
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 1  # One unique app
        assert result.emails_sent == 2  # Two emails sent
        assert mock_email_service.send_expiry_notification.call_count == 2

    def test_process_all_app_registrations_email_failure(
        self, orchestrator, sample_expiry_check_result
    ):
        """Test processing when email sending fails."""
        orchestrator.app_discovery = MagicMock()
        mock_email_service = MagicMock()
        mock_email_service.send_expiry_notification.return_value = False
        orchestrator.email_service = mock_email_service

        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            }
        ]

        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.return_value = (
            sample_expiry_check_result
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.emails_sent == 0
        assert len(result.errors) > 0

    def test_process_all_app_registrations_discovery_error(self, orchestrator):
        """Test processing when app discovery fails."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.side_effect = Exception(
            "Discovery failed"
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.total_entities == 0
        assert len(result.errors) > 0
        assert "Application discovery failed" in result.errors[0]

    def test_process_all_app_registrations_processing_error(
        self, orchestrator, mock_email_service
    ):
        """Test processing when credential check fails."""
        orchestrator.app_discovery = MagicMock()
        orchestrator.app_discovery.discover_applications.return_value = [
            {
                "email": "owner@example.com",
                "object_id": "12345678-1234-1234-1234-123456789012",
                "display_name": "Test App",
                "source": "tenant",
            }
        ]

        orchestrator.credential_checker = MagicMock()
        orchestrator.credential_checker.check_expiring_credentials.side_effect = (
            Exception("Check failed")
        )

        result = orchestrator.process_all_app_registrations(days_threshold=30)

        assert isinstance(result, ProcessingResult)
        assert result.processed == 1
        assert len(result.errors) > 0

    def test_print_summary(self, orchestrator, capsys):
        """Test printing summary of results."""
        result = ProcessingResult(
            total_entities=10,
            processed=10,
            successful_checks=8,
            emails_sent=5,
            not_found=2,
            errors=["Error 1"],
        )

        orchestrator.print_summary(result)

        captured = capsys.readouterr()
        assert "PROCESSING SUMMARY" in captured.out
        assert "Total Applications: 10" in captured.out
        assert "Processed: 10" in captured.out
        assert "Successful Checks: 8" in captured.out
        assert "Emails Sent: 5" in captured.out
        assert "Not Found: 2" in captured.out
        assert "Errors: 1" in captured.out
