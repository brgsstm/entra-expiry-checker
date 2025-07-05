"""
Azure Table Storage client for retrieving app registration entities.
"""

import sys
from typing import List

try:
    from azure.core.exceptions import ResourceNotFoundError
    from azure.data.tables import TableServiceClient
    from azure.identity import DefaultAzureCredential
except ImportError as e:
    print(f"Missing required dependency: {e}")
    sys.exit(1)

from ..models import TableEntity


class TableStorageClient:
    """Client for interacting with Azure Table Storage."""

    def __init__(self, account_name: str, table_name: str):
        """
        Initialize the Table Storage client.

        Args:
            account_name: Azure Storage account name
            table_name: Table name containing app registration entities
        """
        self.account_name = account_name
        self.table_name = table_name
        self.table_service = TableServiceClient(
            endpoint=f"https://{account_name}.table.core.windows.net/",
            credential=DefaultAzureCredential(),
        )
        self.table_client = self.table_service.get_table_client(table_name)

    def get_all_entities(self) -> List[TableEntity]:
        """
        Retrieve all entities from the table.

        Returns:
            List of TableEntity objects
        """
        try:
            print(
                f"🔍 Connecting to table '{self.table_name}' in storage account '{self.account_name}'"
            )

            entities = []
            query = self.table_client.list_entities()

            for entity in query:
                table_entity = TableEntity(
                    email=entity.get("PartitionKey"),
                    object_id=entity.get("RowKey"),
                    timestamp=entity.get("Timestamp"),
                    etag=entity.get("etag"),
                )
                entities.append(table_entity)

            print(f"✅ Retrieved {len(entities)} entities from table")
            return entities

        except ResourceNotFoundError:
            print(
                f"❌ Table '{self.table_name}' not found in storage account '{self.account_name}'"
            )
            return []
        except Exception as e:
            print(f"❌ Error retrieving entities from table: {e}")
            return []
