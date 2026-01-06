"""
Shared test fixtures for pytest.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from entra_expiry_checker.models import (
    AppRegistration,
    Certificate,
    ExpiryCheckResult,
    Secret,
)


@pytest.fixture
def sample_app_registration():
    """Create a sample AppRegistration for testing."""
    return AppRegistration(
        app_id="12345678-1234-1234-1234-123456789012",
        display_name="Test App",
        object_id="87654321-4321-4321-4321-210987654321",
        total_secrets=2,
        total_certificates=1,
    )


@pytest.fixture
def sample_secret_expiring():
    """Create a sample Secret that is expiring soon."""
    future_date = datetime.now(timezone.utc) + timedelta(days=15)
    return Secret(
        key_id="secret-key-123",
        display_name="Test Secret",
        end_date=future_date,
        days_until_expiry=15,
        is_expired=False,
    )


@pytest.fixture
def sample_secret_expired():
    """Create a sample Secret that is expired."""
    past_date = datetime.now(timezone.utc) - timedelta(days=5)
    return Secret(
        key_id="secret-key-456",
        display_name="Expired Secret",
        end_date=past_date,
        days_until_expiry=-5,
        is_expired=True,
    )


@pytest.fixture
def sample_certificate_expiring():
    """Create a sample Certificate that is expiring soon."""
    future_date = datetime.now(timezone.utc) + timedelta(days=20)
    return Certificate(
        key_id="cert-key-123",
        display_name="Test Certificate",
        end_date=future_date,
        days_until_expiry=20,
        is_expired=False,
        thumbprint="ABC123DEF456",
    )


@pytest.fixture
def sample_certificate_expired():
    """Create a sample Certificate that is expired."""
    past_date = datetime.now(timezone.utc) - timedelta(days=10)
    return Certificate(
        key_id="cert-key-456",
        display_name="Expired Certificate",
        end_date=past_date,
        days_until_expiry=-10,
        is_expired=True,
        thumbprint="XYZ789UVW012",
    )


@pytest.fixture
def sample_expiry_check_result(
    sample_app_registration, sample_secret_expiring, sample_certificate_expiring
):
    """Create a sample ExpiryCheckResult for testing."""
    return ExpiryCheckResult(
        app_registration=sample_app_registration,
        expiring_secrets=[sample_secret_expiring],
        expiring_certificates=[sample_certificate_expiring],
        days_threshold=30,
    )


@pytest.fixture
def sample_expiry_check_result_no_expiring(sample_app_registration):
    """Create a sample ExpiryCheckResult with no expiring credentials."""
    return ExpiryCheckResult(
        app_registration=sample_app_registration,
        expiring_secrets=[],
        expiring_certificates=[],
        days_threshold=30,
    )


@pytest.fixture
def mock_graph_client():
    """Create a mock MicrosoftGraphClient."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_table_client():
    """Create a mock TableStorageClient."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_email_service():
    """Create a mock EmailService."""
    mock_service = MagicMock()
    mock_service.send_expiry_notification.return_value = True
    return mock_service
