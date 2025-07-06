"""
Email notification service using SendGrid.
"""

import os
import ssl
import sys
from typing import Any, Dict

try:
    import requests
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError as e:
    print(f"Missing required dependency: {e}")
    sys.exit(1)

from ..models import ExpiryCheckResult


class EmailService:
    """Service for sending email notifications using SendGrid."""

    def __init__(self, api_key: str, from_email: str, verify_ssl: bool = True):
        """
        Initialize the email service.

        Args:
            api_key: SendGrid API key
            from_email: Email address to send from
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.from_email = from_email

        # Configure SSL verification
        if not verify_ssl:
            # Set environment variable to disable SSL verification
            os.environ["PYTHONHTTPSVERIFY"] = "0"

            # Create a custom SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Monkey patch the default SSL context
            ssl._create_default_https_context = lambda: ssl_context

            # Also patch requests to use our SSL context
            import requests.adapters

            class CustomHTTPAdapter(requests.adapters.HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    kwargs["ssl_context"] = ssl_context
                    return super().init_poolmanager(*args, **kwargs)

            # Create a session with custom adapter and patch it globally
            session = requests.Session()
            session.mount("https://", CustomHTTPAdapter())
            session.verify = False

            # Store the session for potential future use
            self._session = session
            print("⚠️  SSL certificate verification disabled")
        else:
            self._session = None

        # Initialize SendGrid client
        self.sg = SendGridAPIClient(api_key=api_key)

    def send_expiry_notification(
        self, to_email: str, result: ExpiryCheckResult
    ) -> bool:
        """
        Send email notification about expiring secrets and certificates.

        Args:
            to_email: Email address to send notification to
            result: ExpiryCheckResult containing app info and expiring credentials

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            total_expiring = len(result.expiring_secrets) + len(
                result.expiring_certificates
            )

            subject = f"Entra ID App Registration Credential Expiry Alert - {result.app_registration.display_name}"

            # Build email content for expiring credentials
            body = self._build_expiry_email_body(result)

            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=body,
            )

            response = self.sg.send(message)

            if response.status_code in [200, 201, 202]:
                message_id = response.headers.get("X-Message-Id", "Unknown")
                print(
                    f"✅ Email notification sent to {to_email} (Message ID: {message_id})"
                )
                return True
            else:
                print(
                    f"❌ Failed to send email. Status code: {response.status_code}")
                print(f"❌ Response body: {response.body}")
                return False

        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False

    def _build_expiry_email_body(self, result: ExpiryCheckResult) -> str:
        """Build HTML email body for expiring credentials."""
        total_expiring = len(result.expiring_secrets) + len(
            result.expiring_certificates
        )

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .credential-item {{ background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; }}
                .expired {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
                .expiring {{ background-color: #fff3cd; border: 1px solid #ffeaa7; }}
                .status {{ font-weight: bold; }}
                .expired-status {{ color: #721c24; }}
                .expiring-status {{ color: #856404; }}
                .section {{ margin: 20px 0; }}
                .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Entra ID App Registration Credential Expiry Alert</h2>
                <p><strong>App Name:</strong> {result.app_registration.display_name}</p>
                <p><strong>App ID:</strong> {result.app_registration.app_id}</p>
                <p><strong>Object ID:</strong> {result.app_registration.object_id}</p>
                <p><strong>Expiring Secrets:</strong> {len(result.expiring_secrets)}</p>
                <p><strong>Expiring Certificates:</strong> {len(result.expiring_certificates)}</p>
                <p><strong>Days Threshold:</strong> {result.days_threshold}</p>
            </div>

            <div class="alert">
                <h3>⚠️ Found {total_expiring} credential(s) expiring within {result.days_threshold} days:</h3>
            </div>
        """

        # Add expiring secrets section
        if result.expiring_secrets:
            html += f"""
            <div class="section">
                <div class="section-title">🔑 Expiring Secrets ({len(result.expiring_secrets)})</div>
            """

            for i, secret in enumerate(result.expiring_secrets, 1):
                status_class = (
                    "expired-status" if secret.is_expired else "expiring-status"
                )
                status_text = "EXPIRED" if secret.is_expired else "EXPIRING SOON"
                item_class = (
                    "credential-item expired"
                    if secret.is_expired
                    else "credential-item expiring"
                )

                html += f"""
                <div class="{item_class}">
                    <h4>{i}. {secret.display_name} ({secret.key_id})</h4>
                    <p><span class="status {status_class}">Status: {status_text}</span></p>
                    <p><strong>End Date:</strong> {secret.end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Days Until Expiry:</strong> {secret.days_until_expiry}</p>
                </div>
                """

            html += "</div>"

        # Add expiring certificates section
        if result.expiring_certificates:
            html += f"""
            <div class="section">
                <div class="section-title">📜 Expiring Certificates ({len(result.expiring_certificates)})</div>
            """

            for i, certificate in enumerate(result.expiring_certificates, 1):
                status_class = (
                    "expired-status" if certificate.is_expired else "expiring-status"
                )
                status_text = "EXPIRED" if certificate.is_expired else "EXPIRING SOON"
                item_class = (
                    "credential-item expired"
                    if certificate.is_expired
                    else "credential-item expiring"
                )

                html += f"""
                <div class="{item_class}">
                    <h4>{i}. {certificate.display_name} ({certificate.key_id})</h4>
                    <p><span class="status {status_class}">Status: {status_text}</span></p>
                    <p><strong>End Date:</strong> {certificate.end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Days Until Expiry:</strong> {certificate.days_until_expiry}</p>
                    {f'<p><strong>Thumbprint:</strong> {certificate.thumbprint}</p>' if certificate.thumbprint else ''}
                </div>
                """

            html += "</div>"

        html += """
        <p><em>Please take action to rotate these credentials before they expire to avoid service disruption.</em></p>
        </body>
        </html>
        """

        return html
