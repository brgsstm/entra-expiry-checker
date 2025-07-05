"""
Data models for the App Registration Secret Expiry Checker.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class AppRegistration:
    """Represents an Azure AD app registration."""

    app_id: str
    display_name: str
    object_id: str
    total_secrets: int
    total_certificates: int


@dataclass
class Secret:
    """Represents a secret/password credential for an app registration."""

    key_id: str
    display_name: str
    end_date: datetime
    days_until_expiry: int
    is_expired: bool


@dataclass
class Certificate:
    """Represents a certificate credential for an app registration."""

    key_id: str
    display_name: str
    end_date: datetime
    days_until_expiry: int
    is_expired: bool
    thumbprint: Optional[str] = None


@dataclass
class ExpiryCheckResult:
    """Result of checking for expiring secrets and certificates on an app registration."""

    app_registration: AppRegistration
    expiring_secrets: List[Secret]
    expiring_certificates: List[Certificate]
    days_threshold: int


@dataclass
class ProcessingResult:
    """Result of processing all app registrations."""

    total_entities: int
    processed: int
    successful_checks: int
    emails_sent: int
    not_found: int
    errors: List[str]


@dataclass
class TableEntity:
    """Represents an entity from Azure Table Storage."""

    email: str
    object_id: str
    timestamp: Optional[datetime] = None
    etag: Optional[str] = None
