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


def main() -> None:
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
        stg_name = settings.STG_ACCT_NAME
        stg_table = settings.STG_ACCT_TABLE_NAME
        if stg_name is None or stg_table is None:
            print(
                "❌ Error: STG_ACCT_NAME and STG_ACCT_TABLE_NAME required for storage mode"
            )
            sys.exit(1)
        table_client = TableStorageClient(stg_name, stg_table)

    # Initialize email service based on provider
    if settings.EMAIL_PROVIDER == "smtp":
        smtp_host = settings.SMTP_HOST
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        from_email = settings.FROM_EMAIL
        if (
            smtp_host is None
            or smtp_user is None
            or smtp_password is None
            or from_email is None
        ):
            print("❌ Error: SMTP configuration incomplete")
            sys.exit(1)
        email_service = EmailService.create_smtp(
            host=smtp_host,
            port=settings.SMTP_PORT,
            user=smtp_user,
            password=smtp_password,
            from_email=from_email,
            use_tls=settings.SMTP_USE_TLS,
            use_ssl=settings.SMTP_USE_SSL,
            verify_ssl=settings.VERIFY_SSL,
        )
    else:  # default to sendgrid
        sg_api_key = settings.SG_API_KEY
        from_email = settings.FROM_EMAIL
        if sg_api_key is None or from_email is None:
            print("❌ Error: SendGrid configuration incomplete")
            sys.exit(1)
        email_service = EmailService.create_sendgrid(
            sg_api_key, from_email, settings.VERIFY_SSL
        )

    # Initialize orchestrator
    orchestrator = SecretExpiryOrchestrator(
        graph_client, email_service, table_client, settings
    )

    # Process all app registrations
    results = orchestrator.process_all_app_registrations(settings.DAYS_THRESHOLD)

    # Print summary
    orchestrator.print_summary(results)

    # Exit with error if there were processing errors
    if results.errors:
        print(f"\n❌ Processing completed with {len(results.errors)} errors.")
        sys.exit(1)
    else:
        print("\n✅ Processing completed successfully!")


if __name__ == "__main__":
    main()
