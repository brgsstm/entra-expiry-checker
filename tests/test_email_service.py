"""
Tests for the email_service module.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from entra_expiry_checker.models import ExpiryCheckResult
from entra_expiry_checker.services.email_service import (
    EmailService,
    SMTPProvider,
    _build_expiry_email_body,
)

# Check if SendGrid is available
try:
    from entra_expiry_checker.services.email_service import SendGridProvider

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


class TestBuildExpiryEmailBody:
    """Test the _build_expiry_email_body function."""

    def test_build_email_body_with_secrets(
        self, sample_app_registration, sample_secret_expiring
    ):
        """Test building email body with expiring secrets."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[sample_secret_expiring],
            expiring_certificates=[],
            days_threshold=30,
        )

        html = _build_expiry_email_body(result)

        assert "Test App" in html
        assert "Expiring Secrets" in html
        assert "Test Secret" in html
        assert "secret-key-123" in html
        assert "Days Until Expiry" in html
        assert "15" in html

    def test_build_email_body_with_certificates(
        self, sample_app_registration, sample_certificate_expiring
    ):
        """Test building email body with expiring certificates."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[],
            expiring_certificates=[sample_certificate_expiring],
            days_threshold=30,
        )

        html = _build_expiry_email_body(result)

        assert "Test App" in html
        assert "Expiring Certificates" in html
        assert "Test Certificate" in html
        assert "cert-key-123" in html
        assert "ABC123DEF456" in html

    def test_build_email_body_with_expired_credentials(
        self, sample_app_registration, sample_secret_expired
    ):
        """Test building email body with expired credentials."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[sample_secret_expired],
            expiring_certificates=[],
            days_threshold=30,
        )

        html = _build_expiry_email_body(result)

        assert "EXPIRED" in html
        assert "Days Until Expiry" in html
        assert "-5" in html

    def test_build_email_body_no_expiring(self, sample_app_registration):
        """Test building email body with no expiring credentials."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[],
            expiring_certificates=[],
            days_threshold=30,
        )

        html = _build_expiry_email_body(result)

        assert "Test App" in html
        # When no expiring credentials, the sections won't be rendered
        # but the header still shows counts of 0
        assert "Expiring Secrets:</strong> 0" in html
        assert "Expiring Certificates:</strong> 0" in html


class TestSMTPProvider:
    """Test the SMTPProvider class."""

    def test_smtp_provider_initialization(self):
        """Test SMTPProvider initialization."""
        provider = SMTPProvider(
            host="smtp.example.com",
            port=587,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
            use_tls=True,
            use_ssl=False,
            verify_ssl=True,
        )

        assert provider.host == "smtp.example.com"
        assert provider.port == 587
        assert provider.user == "testuser"
        assert provider.password == "testpass"
        assert provider.from_email == "test@example.com"
        assert provider.use_tls is True
        assert provider.use_ssl is False
        assert provider.verify_ssl is True

    @patch("entra_expiry_checker.services.email_service.smtplib.SMTP")
    def test_smtp_send_email_success(self, mock_smtp, sample_expiry_check_result):
        """Test successful email sending via SMTP."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        provider = SMTPProvider(
            host="smtp.example.com",
            port=587,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
        )

        result = provider.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("testuser", "testpass")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("entra_expiry_checker.services.email_service.smtplib.SMTP_SSL")
    def test_smtp_send_email_with_ssl(self, mock_smtp_ssl, sample_expiry_check_result):
        """Test email sending via SMTP with SSL."""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        provider = SMTPProvider(
            host="smtp.example.com",
            port=465,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
            use_ssl=True,
            use_tls=False,
        )

        result = provider.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is True
        mock_smtp_ssl.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch("entra_expiry_checker.services.email_service.smtplib.SMTP")
    def test_smtp_send_email_failure(self, mock_smtp, sample_expiry_check_result):
        """Test email sending failure via SMTP."""
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Authentication failed")
        mock_smtp.return_value = mock_server

        provider = SMTPProvider(
            host="smtp.example.com",
            port=587,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
        )

        result = provider.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is False

    def test_smtp_provider_without_tls(self):
        """Test SMTPProvider without TLS."""
        provider = SMTPProvider(
            host="smtp.example.com",
            port=25,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
            use_tls=False,
            use_ssl=False,
        )

        assert provider.use_tls is False
        assert provider.use_ssl is False


class TestSendGridProvider:
    """Test the SendGridProvider class."""

    @pytest.mark.skipif(
        not SENDGRID_AVAILABLE,
        reason="SendGrid package not available",
    )
    @patch("entra_expiry_checker.services.email_service.SendGridAPIClient")
    def test_sendgrid_provider_initialization(self, mock_sendgrid_client):
        """Test SendGridProvider initialization."""
        provider = SendGridProvider(
            api_key="SG.test_key",
            from_email="test@example.com",
            verify_ssl=True,
        )

        assert provider.from_email == "test@example.com"
        mock_sendgrid_client.assert_called_once_with(api_key="SG.test_key")

    @pytest.mark.skipif(
        not SENDGRID_AVAILABLE,
        reason="SendGrid package not available",
    )
    @patch("entra_expiry_checker.services.email_service.SendGridAPIClient")
    def test_sendgrid_send_email_success(
        self, mock_sendgrid_client, sample_expiry_check_result
    ):
        """Test successful email sending via SendGrid."""
        mock_client_instance = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-message-id"}
        mock_client_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_client_instance

        provider = SendGridProvider(
            api_key="SG.test_key",
            from_email="test@example.com",
        )

        result = provider.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is True
        mock_client_instance.send.assert_called_once()

    @pytest.mark.skipif(
        not SENDGRID_AVAILABLE,
        reason="SendGrid package not available",
    )
    @patch("entra_expiry_checker.services.email_service.SendGridAPIClient")
    def test_sendgrid_send_email_failure(
        self, mock_sendgrid_client, sample_expiry_check_result
    ):
        """Test email sending failure via SendGrid."""
        mock_client_instance = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.body = "Bad Request"
        mock_client_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_client_instance

        provider = SendGridProvider(
            api_key="SG.test_key",
            from_email="test@example.com",
        )

        result = provider.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is False


class TestEmailService:
    """Test the EmailService class."""

    def test_email_service_initialization(self):
        """Test EmailService initialization with a provider."""
        mock_provider = MagicMock()
        service = EmailService(mock_provider)

        assert service.provider == mock_provider

    def test_email_service_create_smtp(self):
        """Test creating EmailService with SMTP provider."""
        service = EmailService.create_smtp(
            host="smtp.example.com",
            port=587,
            user="testuser",
            password="testpass",
            from_email="test@example.com",
        )

        assert isinstance(service.provider, SMTPProvider)
        assert service.provider.host == "smtp.example.com"
        assert service.provider.port == 587

    @pytest.mark.skipif(
        not SENDGRID_AVAILABLE,
        reason="SendGrid package not available",
    )
    def test_email_service_create_sendgrid(self):
        """Test creating EmailService with SendGrid provider."""
        with patch("entra_expiry_checker.services.email_service.SendGridAPIClient"):
            service = EmailService.create_sendgrid(
                api_key="SG.test_key",
                from_email="test@example.com",
            )

            assert isinstance(service.provider, SendGridProvider)

    def test_email_service_send_notification(self, sample_expiry_check_result):
        """Test EmailService delegates to provider."""
        mock_provider = MagicMock()
        mock_provider.send_expiry_notification.return_value = True
        service = EmailService(mock_provider)

        result = service.send_expiry_notification(
            "recipient@example.com", sample_expiry_check_result
        )

        assert result is True
        mock_provider.send_expiry_notification.assert_called_once_with(
            "recipient@example.com", sample_expiry_check_result
        )
