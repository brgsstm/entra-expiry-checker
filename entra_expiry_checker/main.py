"""
Microsoft Graph Entra ID App Registration Credential Expiry Checker

This script connects to Microsoft Graph API and checks for expiring secrets and certificates
on app registrations, sending email notifications. Can operate in two modes:
- Storage mode: Read applications from Azure Table Storage
- Tenant mode: Check all applications in the tenant
"""

import sys
from typing import Optional

from .clients.graph_client import MicrosoftGraphClient
from .clients.table_client import TableStorageClient
from .config import Settings
from .orchestrator import SecretExpiryOrchestrator
from .services.email_service import EmailService


def main():
    """Main function - automatically process all app registrations and send emails."""
    print("🚀 Starting app registration credential expiry check process...")

    # Create settings instance
    settings = Settings()

    # Validate configuration first
    if not settings.validate():
        sys.exit(1)

    # Print configuration for debugging (after validation)
    settings.print_config()

    # Initialize Graph client (always needed)
    graph_client = MicrosoftGraphClient()

    # Initialize Table client (only for storage mode)
    table_client: Optional[TableStorageClient] = None
    if settings.MODE == "storage":
        table_client = TableStorageClient(
            settings.STG_ACCT_NAME, settings.STG_ACCT_TABLE_NAME
        )

    # Initialize email service
    email_service = EmailService(
        settings.SG_API_KEY, settings.FROM_EMAIL, settings.VERIFY_SSL
    )

    # Initialize orchestrator
    orchestrator = SecretExpiryOrchestrator(
        graph_client, email_service, table_client, settings
    )

    # Process all app registrations
    results = orchestrator.process_all_app_registrations(
        settings.DAYS_THRESHOLD)

    # Print summary
    orchestrator.print_summary(results)

    # Exit with error if there were processing errors
    if results.errors:
        print(f"\n❌ Processing completed with {len(results.errors)} errors.")
        sys.exit(1)
    else:
        print(f"\n✅ Processing completed successfully!")


if __name__ == "__main__":
    main()
