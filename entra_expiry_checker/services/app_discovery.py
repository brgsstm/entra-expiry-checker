"""
Service for discovering applications to check for credential expiry.
"""

from typing import List, Optional

from ..clients.graph_client import MicrosoftGraphClient
from ..clients.table_client import TableStorageClient
from ..config import Settings


class AppDiscoveryService:
    """Service for discovering applications to check for credential expiry."""

    def __init__(
        self,
        graph_client: MicrosoftGraphClient,
        table_client: Optional[TableStorageClient] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize the app discovery service.

        Args:
            graph_client: Microsoft Graph client for API calls
            table_client: Table Storage client (optional, only needed for storage mode)
            settings: Settings instance (optional, will create new one if not provided)
        """
        self.graph_client = graph_client
        self.table_client = table_client
        self.settings = settings or Settings()

    def discover_applications(self) -> List[dict]:
        """
        Discover applications based on the configured mode.

        Returns:
            List of application entities with email and object_id
        """
        if self.settings.MODE == "storage":
            return self._discover_from_storage()
        elif self.settings.MODE == "tenant":
            return self._discover_from_tenant()
        else:
            raise ValueError(f"Invalid mode: {self.settings.MODE}")

    def _discover_from_storage(self) -> List[dict]:
        """Discover applications from Azure Table Storage."""
        if not self.table_client:
            raise ValueError("Table client is required for storage mode")

        print("🔍 Discovering applications from Azure Table Storage...")
        entities = self.table_client.get_all_entities()

        # Convert TableEntity objects to dictionaries
        applications = []
        for entity in entities:
            # Fetch display name from Graph API since it's not stored in Table Storage
            display_name = self._get_app_display_name(entity.object_id)

            applications.append(
                {
                    "email": entity.email,
                    "object_id": entity.object_id,
                    "display_name": display_name,
                    "source": "storage",
                }
            )

        print(f"✅ Discovered {len(applications)} applications from storage")
        return applications

    def _get_app_display_name(self, object_id: str) -> str:
        """
        Get the display name of an application from Graph API.

        Args:
            object_id: The application's object ID

        Returns:
            The display name of the application, or "Unknown" if not found
        """
        try:
            endpoint = f"/applications/{object_id}"
            response = self.graph_client.make_request(endpoint)
            return response.get("displayName", "Unknown")
        except Exception as e:
            print(
                f"⚠️  Warning: Could not get display name for app {object_id}: {e}")
            return "Unknown"

    def _discover_from_tenant(self) -> List[dict]:
        """Discover all applications from the tenant."""
        print("🔍 Discovering all applications from tenant...")

        # Get all applications from Graph API
        all_apps = self.graph_client.get_all_applications()

        applications = []
        total_notifications = 0

        for app in all_apps:
            object_id = app.get("id")
            display_name = app.get("displayName", "Unknown")

            if not object_id:
                continue

            # Determine emails for notifications
            emails = self._determine_notification_emails(app)

            if emails:
                # Create an entry for each email
                for email in emails:
                    applications.append(
                        {
                            "email": email,
                            "object_id": object_id,
                            "display_name": display_name,
                            "source": "tenant",
                        }
                    )
                total_notifications += len(emails)

        print(
            f"✅ Found {len(all_apps)} applications with {total_notifications} total notification recipients"
        )
        return applications

    def _determine_notification_emails(self, app: dict) -> List[str]:
        """
        Determine the notification emails for an application.

        Args:
            app: Application data from Graph API

        Returns:
            List of email addresses for notifications
        """
        emails = set()  # Use set to avoid duplicates

        # Try to get emails from app owners first
        owners = self._get_app_owners(app.get("id"))
        if owners:
            for owner in owners:
                email = owner.get("mail") or owner.get("userPrincipalName")
                if email:
                    emails.add(email)

        # If no owner emails found, use default notification email
        if not emails:
            if self.settings.DEFAULT_NOTIFICATION_EMAIL:
                emails.add(self.settings.DEFAULT_NOTIFICATION_EMAIL)

        return list(emails)

    def _get_app_owners(self, object_id: str) -> List[dict]:
        """
        Get the owners of an application.

        Args:
            object_id: The application's object ID

        Returns:
            List of owner objects
        """
        try:
            endpoint = f"/applications/{object_id}/owners"
            response = self.graph_client.make_request(endpoint)
            return response.get("value", [])
        except Exception as e:
            print(
                f"⚠️  Warning: Could not get owners for app {object_id}: {e}")
            return []
