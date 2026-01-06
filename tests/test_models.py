"""
Tests for the models module.
"""

from datetime import datetime, timedelta, timezone

from entra_expiry_checker.models import (
    AppRegistration,
    Certificate,
    ExpiryCheckResult,
    ProcessingResult,
    Secret,
    TableEntity,
)


class TestAppRegistration:
    """Test the AppRegistration model."""

    def test_app_registration_creation(self):
        """Test creating an AppRegistration."""
        app = AppRegistration(
            app_id="12345678-1234-1234-1234-123456789012",
            display_name="Test App",
            object_id="87654321-4321-4321-4321-210987654321",
            total_secrets=2,
            total_certificates=1,
        )

        assert app.app_id == "12345678-1234-1234-1234-123456789012"
        assert app.display_name == "Test App"
        assert app.object_id == "87654321-4321-4321-4321-210987654321"
        assert app.total_secrets == 2
        assert app.total_certificates == 1


class TestSecret:
    """Test the Secret model."""

    def test_secret_creation(self):
        """Test creating a Secret."""
        end_date = datetime.now(timezone.utc) + timedelta(days=30)
        secret = Secret(
            key_id="secret-key-123",
            display_name="Test Secret",
            end_date=end_date,
            days_until_expiry=30,
            is_expired=False,
        )

        assert secret.key_id == "secret-key-123"
        assert secret.display_name == "Test Secret"
        assert secret.end_date == end_date
        assert secret.days_until_expiry == 30
        assert secret.is_expired is False

    def test_secret_expired(self):
        """Test creating an expired Secret."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        secret = Secret(
            key_id="secret-key-456",
            display_name="Expired Secret",
            end_date=past_date,
            days_until_expiry=-5,
            is_expired=True,
        )

        assert secret.is_expired is True
        assert secret.days_until_expiry == -5


class TestCertificate:
    """Test the Certificate model."""

    def test_certificate_creation(self):
        """Test creating a Certificate."""
        end_date = datetime.now(timezone.utc) + timedelta(days=60)
        cert = Certificate(
            key_id="cert-key-123",
            display_name="Test Certificate",
            end_date=end_date,
            days_until_expiry=60,
            is_expired=False,
            thumbprint="ABC123DEF456",
        )

        assert cert.key_id == "cert-key-123"
        assert cert.display_name == "Test Certificate"
        assert cert.end_date == end_date
        assert cert.days_until_expiry == 60
        assert cert.is_expired is False
        assert cert.thumbprint == "ABC123DEF456"

    def test_certificate_without_thumbprint(self):
        """Test creating a Certificate without thumbprint."""
        end_date = datetime.now(timezone.utc) + timedelta(days=30)
        cert = Certificate(
            key_id="cert-key-789",
            display_name="Certificate Without Thumbprint",
            end_date=end_date,
            days_until_expiry=30,
            is_expired=False,
            thumbprint=None,
        )

        assert cert.thumbprint is None


class TestExpiryCheckResult:
    """Test the ExpiryCheckResult model."""

    def test_expiry_check_result_creation(
        self, sample_app_registration, sample_secret_expiring
    ):
        """Test creating an ExpiryCheckResult."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[sample_secret_expiring],
            expiring_certificates=[],
            days_threshold=30,
        )

        assert result.app_registration == sample_app_registration
        assert len(result.expiring_secrets) == 1
        assert len(result.expiring_certificates) == 0
        assert result.days_threshold == 30

    def test_expiry_check_result_with_multiple_credentials(
        self,
        sample_app_registration,
        sample_secret_expiring,
        sample_secret_expired,
        sample_certificate_expiring,
    ):
        """Test ExpiryCheckResult with multiple expiring credentials."""
        result = ExpiryCheckResult(
            app_registration=sample_app_registration,
            expiring_secrets=[sample_secret_expiring, sample_secret_expired],
            expiring_certificates=[sample_certificate_expiring],
            days_threshold=30,
        )

        assert len(result.expiring_secrets) == 2
        assert len(result.expiring_certificates) == 1


class TestProcessingResult:
    """Test the ProcessingResult model."""

    def test_processing_result_creation(self):
        """Test creating a ProcessingResult."""
        result = ProcessingResult(
            total_entities=10,
            processed=10,
            successful_checks=8,
            emails_sent=5,
            not_found=2,
            errors=["Error 1", "Error 2"],
        )

        assert result.total_entities == 10
        assert result.processed == 10
        assert result.successful_checks == 8
        assert result.emails_sent == 5
        assert result.not_found == 2
        assert len(result.errors) == 2

    def test_processing_result_no_errors(self):
        """Test ProcessingResult with no errors."""
        result = ProcessingResult(
            total_entities=5,
            processed=5,
            successful_checks=5,
            emails_sent=3,
            not_found=0,
            errors=[],
        )

        assert len(result.errors) == 0


class TestTableEntity:
    """Test the TableEntity model."""

    def test_table_entity_creation(self):
        """Test creating a TableEntity."""
        timestamp = datetime.now(timezone.utc)
        entity = TableEntity(
            email="test@example.com",
            object_id="12345678-1234-1234-1234-123456789012",
            timestamp=timestamp,
            etag="etag-123",
        )

        assert entity.email == "test@example.com"
        assert entity.object_id == "12345678-1234-1234-1234-123456789012"
        assert entity.timestamp == timestamp
        assert entity.etag == "etag-123"

    def test_table_entity_optional_fields(self):
        """Test TableEntity with optional fields as None."""
        entity = TableEntity(
            email="test@example.com",
            object_id="12345678-1234-1234-1234-123456789012",
        )

        assert entity.timestamp is None
        assert entity.etag is None
