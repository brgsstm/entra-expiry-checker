"""
Tests for the app_discovery module.
"""

from unittest.mock import MagicMock

import pytest

from entra_expiry_checker.services.app_discovery import AppDiscoveryService


class TestAppDiscoveryService:
    """Test the AppDiscoveryService class."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock Graph client."""
        return MagicMock()

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
    def discovery_service(self, mock_graph_client, mock_table_client, mock_settings):
        """Create an AppDiscoveryService instance."""
        return AppDiscoveryService(
            graph_client=mock_graph_client,
            table_client=mock_table_client,
            settings=mock_settings,
        )

    def test_discovery_service_initialization(self, mock_graph_client, mock_settings):
        """Test discovery service initialization."""
        service = AppDiscoveryService(
            graph_client=mock_graph_client, settings=mock_settings
        )

        assert service.graph_client == mock_graph_client
        assert service.settings == mock_settings
        assert service.table_client is None

    def test_discover_applications_invalid_mode(self, discovery_service):
        """Test discovery with invalid mode."""
        discovery_service.settings.MODE = "invalid"

        with pytest.raises(ValueError) as exc_info:
            discovery_service.discover_applications()
        assert "Invalid mode" in str(exc_info.value)

    def test_discover_from_storage(self, discovery_service, mock_table_client):
        """Test discovering applications from storage."""
        discovery_service.settings.MODE = "storage"
        discovery_service.table_client = mock_table_client

        from entra_expiry_checker.models import TableEntity

        table_entities = [
            TableEntity(
                email="owner@example.com",
                object_id="12345678-1234-1234-1234-123456789012",
            ),
            TableEntity(
                email="admin@example.com",
                object_id="87654321-4321-4321-4321-210987654321",
            ),
        ]

        mock_table_client.get_all_entities.return_value = table_entities
        discovery_service.graph_client.make_request.return_value = {
            "displayName": "Test App"
        }

        apps = discovery_service.discover_applications()

        assert len(apps) == 2
        assert apps[0]["email"] == "owner@example.com"
        assert apps[0]["object_id"] == "12345678-1234-1234-1234-123456789012"
        assert apps[0]["source"] == "storage"
        assert mock_table_client.get_all_entities.called

    def test_discover_from_storage_no_table_client(self, discovery_service):
        """Test discovering from storage without table client."""
        discovery_service.settings.MODE = "storage"
        discovery_service.table_client = None

        with pytest.raises(ValueError) as exc_info:
            discovery_service.discover_applications()
        assert "Table client is required" in str(exc_info.value)

    def test_discover_from_storage_display_name_fallback(
        self, discovery_service, mock_table_client
    ):
        """Test discovering from storage when display name fetch fails."""
        discovery_service.settings.MODE = "storage"
        discovery_service.table_client = mock_table_client

        from entra_expiry_checker.models import TableEntity

        table_entity = TableEntity(
            email="owner@example.com",
            object_id="12345678-1234-1234-1234-123456789012",
        )

        mock_table_client.get_all_entities.return_value = [table_entity]
        discovery_service.graph_client.make_request.side_effect = Exception("Not found")

        apps = discovery_service.discover_applications()

        assert len(apps) == 1
        assert apps[0]["display_name"] == "Unknown"

    def test_discover_from_tenant(self, discovery_service):
        """Test discovering applications from tenant."""
        discovery_service.settings.MODE = "tenant"

        # Mock Graph API responses
        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            },
            {
                "id": "app2-id",
                "displayName": "App 2",
            },
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps

        # Mock owners endpoint
        discovery_service.graph_client.make_request.side_effect = [
            {"value": [{"mail": "owner1@example.com"}]},  # App 1 owners
            {"value": [{"mail": "owner2@example.com"}]},  # App 2 owners
        ]

        apps = discovery_service.discover_applications()

        assert len(apps) == 2
        assert apps[0]["email"] == "owner1@example.com"
        assert apps[0]["object_id"] == "app1-id"
        assert apps[0]["display_name"] == "App 1"
        assert apps[0]["source"] == "tenant"

    def test_discover_from_tenant_no_owners_with_default_email(self, discovery_service):
        """Test discovering from tenant with no owners but default email."""
        discovery_service.settings.MODE = "tenant"
        discovery_service.settings.DEFAULT_NOTIFICATION_EMAIL = "default@example.com"

        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            }
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps
        discovery_service.graph_client.make_request.return_value = {
            "value": []
        }  # No owners

        apps = discovery_service.discover_applications()

        assert len(apps) == 1
        assert apps[0]["email"] == "default@example.com"

    def test_discover_from_tenant_no_owners_no_default(self, discovery_service):
        """Test discovering from tenant with no owners and no default email."""
        discovery_service.settings.MODE = "tenant"
        discovery_service.settings.DEFAULT_NOTIFICATION_EMAIL = None

        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            }
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps
        discovery_service.graph_client.make_request.return_value = {
            "value": []
        }  # No owners

        apps = discovery_service.discover_applications()

        assert len(apps) == 0  # App skipped because no notification email

    def test_discover_from_tenant_multiple_owners(self, discovery_service):
        """Test discovering from tenant with multiple owners."""
        discovery_service.settings.MODE = "tenant"

        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            }
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps
        discovery_service.graph_client.make_request.return_value = {
            "value": [
                {"mail": "owner1@example.com"},
                {"mail": "owner2@example.com"},
                {"userPrincipalName": "owner3@example.com"},  # No mail, use UPN
            ]
        }

        apps = discovery_service.discover_applications()

        assert len(apps) == 3  # One entry per owner
        emails = [app["email"] for app in apps]
        assert "owner1@example.com" in emails
        assert "owner2@example.com" in emails
        assert "owner3@example.com" in emails

    def test_discover_from_tenant_owner_fetch_error(self, discovery_service):
        """Test discovering from tenant when owner fetch fails."""
        discovery_service.settings.MODE = "tenant"
        discovery_service.settings.DEFAULT_NOTIFICATION_EMAIL = "default@example.com"

        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            }
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps
        discovery_service.graph_client.make_request.side_effect = Exception(
            "Error fetching owners"
        )

        apps = discovery_service.discover_applications()

        # Should fall back to default email
        assert len(apps) == 1
        assert apps[0]["email"] == "default@example.com"

    def test_discover_from_tenant_app_without_id(self, discovery_service):
        """Test discovering from tenant with app missing ID."""
        discovery_service.settings.MODE = "tenant"

        all_apps = [
            {
                "id": "app1-id",
                "displayName": "App 1",
            },
            {
                # Missing ID
                "displayName": "App Without ID",
            },
        ]

        discovery_service.graph_client.get_all_applications.return_value = all_apps
        discovery_service.graph_client.make_request.return_value = {
            "value": [{"mail": "owner@example.com"}]
        }

        apps = discovery_service.discover_applications()

        # Should only include app with ID
        assert len(apps) == 1
        assert apps[0]["object_id"] == "app1-id"
