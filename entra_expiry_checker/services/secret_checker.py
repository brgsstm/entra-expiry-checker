"""
Service for checking expiring secrets and certificates on Azure AD app registrations.
"""

import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import requests
    from azure.core.exceptions import ResourceNotFoundError
except ImportError as e:
    print(f"Missing required dependency: {e}")
    sys.exit(1)

from ..clients.graph_client import MicrosoftGraphClient
from ..models import AppRegistration, Certificate, ExpiryCheckResult, Secret


class CredentialCheckerService:
    """Service for checking expiring secrets and certificates on app registrations."""

    def __init__(self, graph_client: MicrosoftGraphClient):
        self.graph_client = graph_client

    def get_app_registration(self, object_id: str) -> dict:
        """
        Get app registration details by object ID.

        Args:
            object_id: The object ID of the app registration

        Returns:
            App registration data
        """
        endpoint = f"/applications/{object_id}"
        return self.graph_client.make_request(endpoint)

    def get_app_secrets(self, object_id: str) -> list:
        """
        Get secrets for an app registration.

        Args:
            object_id: The object ID of the app registration

        Returns:
            List of secrets with their expiry information
        """
        endpoint = f"/applications/{object_id}/passwordCredentials"
        response = self.graph_client.make_request(endpoint)
        return response.get("value", [])

    def get_app_certificates(self, object_id: str) -> list:
        """
        Get certificates for an app registration.

        Args:
            object_id: The object ID of the app registration

        Returns:
            List of certificates with their expiry information
        """
        endpoint = f"/applications/{object_id}/keyCredentials"
        response = self.graph_client.make_request(endpoint)
        return response.get("value", [])

    def check_expiring_credentials(
        self, object_id: str, days_threshold: int = 30
    ) -> Optional[ExpiryCheckResult]:
        """
        Check for secrets and certificates that are expiring soon.

        Args:
            object_id: The object ID of the app registration
            days_threshold: Number of days to consider as "expiring soon"

        Returns:
            ExpiryCheckResult with app info and expiring credentials, or None if app not found or error occurs
        """
        try:
            # Get app registration details
            app_info = self.get_app_registration(object_id)

            # Get secrets and certificates
            secrets_data = self.get_app_secrets(object_id)
            certificates_data = self.get_app_certificates(object_id)

            # Check for expiring secrets
            expiring_secrets = self._check_expiring_secrets(
                secrets_data, days_threshold
            )

            # Check for expiring certificates
            expiring_certificates = self._check_expiring_certificates(
                certificates_data, days_threshold
            )

            # Create app registration model
            app_registration = AppRegistration(
                app_id=app_info.get("appId"),
                display_name=app_info.get("displayName"),
                object_id=object_id,
                total_secrets=len(secrets_data),
                total_certificates=len(certificates_data),
            )

            return ExpiryCheckResult(
                app_registration=app_registration,
                expiring_secrets=expiring_secrets,
                expiring_certificates=expiring_certificates,
                days_threshold=days_threshold,
            )

        except ResourceNotFoundError:
            print(
                f"⚠️  Warning: App registration with Object ID '{object_id}' not found (may have been deleted)"
            )
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP error checking app registration {object_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"❌ Network error checking app registration {object_id}: {e}")
            return None
        except Exception as e:
            print(
                f"❌ Unexpected error checking app registration {object_id}: {e}")
            return None

    def _check_expiring_secrets(self, secrets_data: list, days_threshold: int) -> list:
        """Check for expiring secrets."""
        expiring_secrets = []
        current_time = datetime.now(timezone.utc)
        threshold_date = current_time + timedelta(days=days_threshold)

        for secret_data in secrets_data:
            if "endDateTime" in secret_data:
                end_date = datetime.fromisoformat(
                    secret_data["endDateTime"].replace("Z", "+00:00")
                )

                if end_date <= threshold_date:
                    days_until_expiry = (end_date - current_time).days
                    secret = Secret(
                        key_id=secret_data.get("keyId", "Unknown"),
                        display_name=secret_data.get("displayName", "Unnamed"),
                        end_date=end_date,
                        days_until_expiry=days_until_expiry,
                        is_expired=days_until_expiry < 0,
                    )
                    expiring_secrets.append(secret)

        return expiring_secrets

    def _check_expiring_certificates(
        self, certificates_data: list, days_threshold: int
    ) -> list:
        """Check for expiring certificates."""
        expiring_certificates = []
        current_time = datetime.now(timezone.utc)
        threshold_date = current_time + timedelta(days=days_threshold)

        for cert_data in certificates_data:
            if "endDateTime" in cert_data:
                end_date = datetime.fromisoformat(
                    cert_data["endDateTime"].replace("Z", "+00:00")
                )

                if end_date <= threshold_date:
                    days_until_expiry = (end_date - current_time).days
                    certificate = Certificate(
                        key_id=cert_data.get("keyId", "Unknown"),
                        display_name=cert_data.get("displayName", "Unnamed"),
                        end_date=end_date,
                        days_until_expiry=days_until_expiry,
                        is_expired=days_until_expiry < 0,
                        thumbprint=cert_data.get("customKeyIdentifier"),
                    )
                    expiring_certificates.append(certificate)

        return expiring_certificates

    # Keep the old method name for backward compatibility
    def check_expiring_secrets(
        self, object_id: str, days_threshold: int = 30
    ) -> Optional[ExpiryCheckResult]:
        """Alias for check_expiring_credentials for backward compatibility."""
        return self.check_expiring_credentials(object_id, days_threshold)
