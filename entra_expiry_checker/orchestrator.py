"""
Orchestrator for coordinating the credential expiry checking process.
"""

from typing import List, Optional

from .clients.graph_client import MicrosoftGraphClient
from .clients.table_client import TableStorageClient
from .config import Settings
from .models import ProcessingResult
from .services.app_discovery import AppDiscoveryService
from .services.email_service import EmailService
from .services.secret_checker import CredentialCheckerService


class SecretExpiryOrchestrator:
    """Orchestrates checking multiple app registrations and sending notifications."""

    def __init__(
        self,
        graph_client: MicrosoftGraphClient,
        email_service: EmailService,
        table_client: Optional[TableStorageClient] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            graph_client: Microsoft Graph client for API calls
            email_service: Email service for sending alerts
            table_client: Table Storage client (optional, only needed for storage mode)
            settings: Settings instance (optional, will create new one if not provided)
        """
        self.graph_client = graph_client
        self.table_client = table_client
        self.email_service = email_service
        self.settings = settings or Settings()
        self.credential_checker = CredentialCheckerService(graph_client)
        self.app_discovery = AppDiscoveryService(
            graph_client, table_client, self.settings
        )

    def process_all_app_registrations(
        self, days_threshold: int = 30
    ) -> ProcessingResult:
        """
        Process all app registrations and send notifications.

        Args:
            days_threshold: Number of days to consider as "expiring soon"

        Returns:
            ProcessingResult with summary of processing results
        """
        print(
            f"🚀 Starting app registration credential expiry check process (Mode: {self.settings.MODE})..."
        )

        # Discover applications based on mode
        try:
            applications = self.app_discovery.discover_applications()
        except Exception as e:
            print(f"❌ Error discovering applications: {e}")
            return ProcessingResult(
                total_entities=0,
                processed=0,
                successful_checks=0,
                emails_sent=0,
                not_found=0,
                errors=[f"Application discovery failed: {e}"],
            )

        if not applications:
            print("❌ No applications found to process.")
            return ProcessingResult(
                total_entities=0,
                processed=0,
                successful_checks=0,
                emails_sent=0,
                not_found=0,
                errors=[],
            )

        # Group applications by object_id to get unique apps and their notification emails
        app_groups = {}
        for app in applications:
            object_id = app["object_id"]
            if object_id not in app_groups:
                app_groups[object_id] = {
                    "display_name": app.get("display_name", "Unknown"),
                    "source": app.get("source", "unknown"),
                    "notification_emails": [],
                }
            app_groups[object_id]["notification_emails"].append(app["email"])

        unique_apps = len(app_groups)
        print(f"📋 Processing {unique_apps} app registrations...")

        results = ProcessingResult(
            total_entities=unique_apps,
            processed=0,
            successful_checks=0,
            emails_sent=0,
            not_found=0,
            errors=[],
        )

        # Process each unique application
        for i, (object_id, app_info) in enumerate(app_groups.items(), 1):
            display_name = app_info["display_name"]
            notification_emails = app_info["notification_emails"]
            source = app_info["source"]

            print(f"📧 Processing {i}/{unique_apps}: {display_name}")

            try:
                # Check expiring credentials for this app registration
                result = self.credential_checker.check_expiring_credentials(
                    object_id, days_threshold
                )

                if result is None:
                    # App registration not found
                    error_msg = f"App registration {object_id} not found (may have been deleted)"
                    print(f"⚠️  {error_msg}")
                    results.not_found += 1
                    results.processed += 1
                    continue

                results.successful_checks += 1

                # Send email notification only if there are expiring credentials
                total_expiring = len(result.expiring_secrets) + len(
                    result.expiring_certificates
                )
                if total_expiring > 0:
                    print(
                        f"⚠️  Found {total_expiring} expiring credentials - sending notifications"
                    )

                    # Send to all notification recipients for this app
                    for email in notification_emails:
                        success = self.email_service.send_expiry_notification(
                            email, result
                        )
                        if success:
                            results.emails_sent += 1
                        else:
                            error_msg = f"Failed to send email to {email}"
                            print(f"   ❌ {error_msg}")
                            results.errors.append(error_msg)
                else:
                    print(f"✅ No expiring credentials found")

                results.processed += 1

            except Exception as e:
                error_msg = f"Error processing {display_name} ({object_id}): {e}"
                print(f"❌ {error_msg}")
                results.errors.append(error_msg)
                results.processed += 1

        return results

    def print_summary(self, results: ProcessingResult):
        """Print a summary of the processing results."""
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Mode: {self.settings.MODE}")
        print(f"Total Applications: {results.total_entities}")
        print(f"Processed: {results.processed}")
        print(f"Successful Checks: {results.successful_checks}")
        print(f"Emails Sent: {results.emails_sent}")
        print(f"Not Found: {results.not_found}")
        print(f"Errors: {len(results.errors)}")

        if results.not_found > 0:
            print(
                f"\n⚠️  {results.not_found} app registration(s) not found (may have been deleted)"
            )

        if results.errors:
            print("\n❌ Errors encountered:")
            for error in results.errors:
                print(f"  - {error}")

        print("=" * 60)
