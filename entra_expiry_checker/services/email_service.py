"""
Email notification service supporting SendGrid and SMTP.
"""

import html
import os
import ssl
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import requests  # noqa: F401
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from ..models import ExpiryCheckResult


def _build_expiry_email_body(result: ExpiryCheckResult) -> str:
    """Build HTML email body for expiring credentials (shared by all providers)."""
    total_expiring = len(result.expiring_secrets) + len(result.expiring_certificates)

    app_name = html.escape(result.app_registration.display_name)
    app_id = html.escape(result.app_registration.app_id)
    object_id = html.escape(result.app_registration.object_id)

    body = f"""
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
            <h2>Entra ID App Registration Credential Expiry Alert</h2>
            <p><strong>App Name:</strong> {app_name}</p>
            <p><strong>App ID:</strong> {app_id}</p>
            <p><strong>Object ID:</strong> {object_id}</p>
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
        body += f"""
        <div class="section">
            <div class="section-title">🔑 Expiring Secrets ({len(result.expiring_secrets)})</div>
        """

        for i, secret in enumerate(result.expiring_secrets, 1):
            status_class = "expired-status" if secret.is_expired else "expiring-status"
            status_text = "EXPIRED" if secret.is_expired else "EXPIRING SOON"
            item_class = (
                "credential-item expired"
                if secret.is_expired
                else "credential-item expiring"
            )
            secret_name = html.escape(secret.display_name)
            secret_key_id = html.escape(secret.key_id)

            body += f"""
            <div class="{item_class}">
                <h4>{i}. {secret_name} ({secret_key_id})</h4>
                <p><span class="status {status_class}">Status: {status_text}</span></p>
                <p><strong>End Date:</strong> {secret.end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Days Until Expiry:</strong> {secret.days_until_expiry}</p>
            </div>
            """

        body += "</div>"

    # Add expiring certificates section
    if result.expiring_certificates:
        body += f"""
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
            cert_name = html.escape(certificate.display_name)
            cert_key_id = html.escape(certificate.key_id)
            thumbprint_html = (
                f"<p><strong>Thumbprint:</strong> {html.escape(certificate.thumbprint)}</p>"
                if certificate.thumbprint
                else ""
            )

            body += f"""
            <div class="{item_class}">
                <h4>{i}. {cert_name} ({cert_key_id})</h4>
                <p><span class="status {status_class}">Status: {status_text}</span></p>
                <p><strong>End Date:</strong> {certificate.end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Days Until Expiry:</strong> {certificate.days_until_expiry}</p>
                {thumbprint_html}
            </div>
            """

        body += "</div>"

    body += """
    <p><em>Please take action to rotate these credentials before they expire to avoid service disruption.</em></p>
    </body>
    </html>
    """

    return body


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def send_expiry_notification(
        self, to_email: str, result: ExpiryCheckResult
    ) -> bool:
        """Send email notification about expiring credentials."""
        pass


class SendGridProvider(EmailProvider):
    """SendGrid email provider implementation."""

    def __init__(self, api_key: str, from_email: str, verify_ssl: bool = True):
        """
        Initialize SendGrid provider.

        Args:
            api_key: SendGrid API key
            from_email: Email address to send from
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        if not SENDGRID_AVAILABLE:
            raise ImportError(
                "sendgrid package is required for SendGrid provider. "
                "Install it with: pip install sendgrid"
            )

        self.from_email = from_email
        self._configure_ssl(verify_ssl)
        self.sg = SendGridAPIClient(api_key=api_key)

    def _configure_ssl(self, verify_ssl: bool) -> None:
        """Configure SSL verification for SendGrid requests."""
        if not verify_ssl:
            # PYTHONHTTPSVERIFY=0 is the standard Python mechanism for disabling
            # SSL verification. Note: this affects all HTTPS connections in the
            # process, not just SendGrid. Only set VERIFY_SSL=false in controlled
            # environments where you accept that risk.
            os.environ["PYTHONHTTPSVERIFY"] = "0"
            print(
                "⚠️  SSL certificate verification disabled for all HTTPS connections in this process"
            )

    def send_expiry_notification(
        self, to_email: str, result: ExpiryCheckResult
    ) -> bool:
        """
        Send email notification via SendGrid.

        Args:
            to_email: Email address to send notification to
            result: ExpiryCheckResult containing app info and expiring credentials

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"Entra ID App Registration Credential Expiry Alert - {result.app_registration.display_name}"
            body = _build_expiry_email_body(result)

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
                print(f"❌ Failed to send email. Status code: {response.status_code}")
                print(f"❌ Response body: {response.body}")
                return False

        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False


class SMTPProvider(EmailProvider):
    """SMTP email provider implementation."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        verify_ssl: bool = True,
    ):
        """
        Initialize SMTP provider.

        Args:
            host: SMTP server hostname
            port: SMTP server port
            user: SMTP username
            password: SMTP password
            from_email: Email address to send from
            use_tls: Use STARTTLS (default: True)
            use_ssl: Use SSL/TLS from the start (default: False)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl

    def send_expiry_notification(
        self, to_email: str, result: ExpiryCheckResult
    ) -> bool:
        """
        Send email notification via SMTP.

        Args:
            to_email: Email address to send notification to
            result: ExpiryCheckResult containing app info and expiring credentials

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"Entra ID App Registration Credential Expiry Alert - {result.app_registration.display_name}"
            body = _build_expiry_email_body(result)

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Add HTML content
            html_part = MIMEText(body, "html")
            msg.attach(html_part)

            # Create SSL context if needed
            ssl_context = None
            if self.verify_ssl:
                ssl_context = ssl.create_default_context()
            else:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # Connect and send
            if self.use_ssl:
                server: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
                    self.host, self.port, context=ssl_context
                )
            else:
                server = smtplib.SMTP(self.host, self.port)

            if self.use_tls and not self.use_ssl:
                server.starttls(context=ssl_context)

            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Email notification sent to {to_email}")
            return True

        except Exception as e:
            print(f"❌ Error sending email via SMTP: {e}")
            return False


class EmailService:
    """Service for sending email notifications via multiple providers."""

    def __init__(self, provider: EmailProvider):
        """
        Initialize the email service with a provider.

        Args:
            provider: Email provider instance (SendGridProvider or SMTPProvider)
        """
        self.provider = provider

    @classmethod
    def create_sendgrid(
        cls, api_key: str, from_email: str, verify_ssl: bool = True
    ) -> "EmailService":
        """
        Create EmailService with SendGrid provider.

        Args:
            api_key: SendGrid API key
            from_email: Email address to send from
            verify_ssl: Whether to verify SSL certificates (default: True)

        Returns:
            EmailService instance with SendGrid provider
        """
        provider = SendGridProvider(api_key, from_email, verify_ssl)
        return cls(provider)

    @classmethod
    def create_smtp(
        cls,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        verify_ssl: bool = True,
    ) -> "EmailService":
        """
        Create EmailService with SMTP provider.

        Args:
            host: SMTP server hostname
            port: SMTP server port
            user: SMTP username
            password: SMTP password
            from_email: Email address to send from
            use_tls: Use STARTTLS (default: True)
            use_ssl: Use SSL/TLS from the start (default: False)
            verify_ssl: Whether to verify SSL certificates (default: True)

        Returns:
            EmailService instance with SMTP provider
        """
        provider = SMTPProvider(
            host, port, user, password, from_email, use_tls, use_ssl, verify_ssl
        )
        return cls(provider)

    def send_expiry_notification(
        self, to_email: str, result: ExpiryCheckResult
    ) -> bool:
        """
        Send email notification (delegates to provider).

        Args:
            to_email: Email address to send notification to
            result: ExpiryCheckResult containing app info and expiring credentials

        Returns:
            True if email sent successfully, False otherwise
        """
        return self.provider.send_expiry_notification(to_email, result)
