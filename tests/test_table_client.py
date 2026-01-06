"""
Tests for the table_client module.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from entra_expiry_checker.clients.table_client import TableStorageClient
from entra_expiry_checker.models import TableEntity


class TestTableStorageClient:
    """Test the TableStorageClient class."""

    @pytest.fixture
    def mock_table_service(self):
        """Create a mock TableServiceClient."""
        return MagicMock()

    @pytest.fixture
    def mock_table_client(self):
        """Create a mock table client."""
        return MagicMock()

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_client_initialization(
        self, mock_table_service_class, mock_default_credential, mock_table_service
    ):
        """Test client initialization."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = MagicMock()

        client = TableStorageClient("testaccount", "testtable")

        assert client.account_name == "testaccount"
        assert client.table_name == "testtable"
        mock_table_service_class.assert_called_once()
        mock_table_service.get_table_client.assert_called_once_with("testtable")

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_get_all_entities_success(
        self,
        mock_table_service_class,
        mock_default_credential,
        mock_table_service,
        mock_table_client,
    ):
        """Test successfully retrieving all entities."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = mock_table_client

        # Mock entities
        entity1 = {
            "PartitionKey": "email1@example.com",
            "RowKey": "object-id-1",
            "Timestamp": datetime.now(timezone.utc),
            "etag": "etag1",
        }
        entity2 = {
            "PartitionKey": "email2@example.com",
            "RowKey": "object-id-2",
            "Timestamp": datetime.now(timezone.utc),
            "etag": "etag2",
        }

        mock_table_client.list_entities.return_value = [entity1, entity2]

        client = TableStorageClient("testaccount", "testtable")
        entities = client.get_all_entities()

        assert len(entities) == 2
        assert isinstance(entities[0], TableEntity)
        assert entities[0].email == "email1@example.com"
        assert entities[0].object_id == "object-id-1"
        assert entities[1].email == "email2@example.com"
        assert entities[1].object_id == "object-id-2"

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_get_all_entities_empty(
        self,
        mock_table_service_class,
        mock_default_credential,
        mock_table_service,
        mock_table_client,
    ):
        """Test retrieving entities from empty table."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = mock_table_client

        mock_table_client.list_entities.return_value = []

        client = TableStorageClient("testaccount", "testtable")
        entities = client.get_all_entities()

        assert len(entities) == 0

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_get_all_entities_table_not_found(
        self,
        mock_table_service_class,
        mock_default_credential,
        mock_table_service,
        mock_table_client,
    ):
        """Test retrieving entities when table is not found."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = mock_table_client

        mock_table_client.list_entities.side_effect = ResourceNotFoundError(
            "Table not found"
        )

        client = TableStorageClient("testaccount", "testtable")
        entities = client.get_all_entities()

        assert len(entities) == 0

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_get_all_entities_general_error(
        self,
        mock_table_service_class,
        mock_default_credential,
        mock_table_service,
        mock_table_client,
    ):
        """Test retrieving entities with general error."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = mock_table_client

        mock_table_client.list_entities.side_effect = Exception("General error")

        client = TableStorageClient("testaccount", "testtable")
        entities = client.get_all_entities()

        assert len(entities) == 0

    @patch("entra_expiry_checker.clients.table_client.DefaultAzureCredential")
    @patch("entra_expiry_checker.clients.table_client.TableServiceClient")
    def test_get_all_entities_without_timestamp(
        self,
        mock_table_service_class,
        mock_default_credential,
        mock_table_service,
        mock_table_client,
    ):
        """Test retrieving entities without timestamp."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        mock_table_service_class.return_value = mock_table_service
        mock_table_service.get_table_client.return_value = mock_table_client

        entity = {
            "PartitionKey": "email@example.com",
            "RowKey": "object-id-1",
            # No Timestamp or etag
        }

        mock_table_client.list_entities.return_value = [entity]

        client = TableStorageClient("testaccount", "testtable")
        entities = client.get_all_entities()

        assert len(entities) == 1
        assert entities[0].timestamp is None
        assert entities[0].etag is None
