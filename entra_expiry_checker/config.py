"""
Configuration settings for the App Registration Secret Expiry Checker.
"""

import re
from typing import Optional

from decouple import UndefinedValueError, config


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize settings but don't load environment variables yet."""
        self._email_provider: Optional[str] = None
        self._sg_api_key: Optional[str] = None
        self._from_email: Optional[str] = None
        self._smtp_host: Optional[str] = None
        self._smtp_port: Optional[int] = None
        self._smtp_user: Optional[str] = None
        self._smtp_password: Optional[str] = None
        self._smtp_use_tls: Optional[bool] = None
        self._smtp_use_ssl: Optional[bool] = None
        self._stg_acct_name: Optional[str] = None
        self._stg_acct_table_name: Optional[str] = None
        self._days_threshold: Optional[int] = None
        self._mode: Optional[str] = None
        self._default_notification_email: Optional[str] = None
        self._verify_ssl: Optional[bool] = None
        self._loaded = False

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        if self._loaded:
            return

        # Set defaults first
        self._days_threshold = 30
        self._mode = "tenant"
        self._verify_ssl = True  # Default to SSL verification enabled

        # Email provider configuration
        try:
            self._email_provider = config("EMAIL_PROVIDER", default="sendgrid").lower()
        except UndefinedValueError:
            self._email_provider = "sendgrid"

        # FROM_EMAIL is always required
        try:
            self._from_email = config("FROM_EMAIL")
        except UndefinedValueError:
            self._from_email = None

        # SendGrid configuration (required if EMAIL_PROVIDER=sendgrid)
        try:
            self._sg_api_key = config("SG_API_KEY", default=None)
        except UndefinedValueError:
            self._sg_api_key = None

        # SMTP configuration (required if EMAIL_PROVIDER=smtp)
        try:
            self._smtp_host = config("SMTP_HOST", default=None)
        except UndefinedValueError:
            self._smtp_host = None

        try:
            self._smtp_port = config("SMTP_PORT", default=587, cast=int)
        except UndefinedValueError:
            self._smtp_port = 587

        try:
            self._smtp_user = config("SMTP_USER", default=None)
        except UndefinedValueError:
            self._smtp_user = None

        try:
            self._smtp_password = config("SMTP_PASSWORD", default=None)
        except UndefinedValueError:
            self._smtp_password = None

        try:
            self._smtp_use_tls = config("SMTP_USE_TLS", default=True, cast=bool)
        except UndefinedValueError:
            self._smtp_use_tls = True

        try:
            self._smtp_use_ssl = config("SMTP_USE_SSL", default=False, cast=bool)
        except UndefinedValueError:
            self._smtp_use_ssl = False

        # Azure Storage configuration (optional)
        try:
            self._stg_acct_name = config("STG_ACCT_NAME", default=None)
        except UndefinedValueError:
            self._stg_acct_name = None

        try:
            self._stg_acct_table_name = config("STG_ACCT_TABLE_NAME", default=None)
        except UndefinedValueError:
            self._stg_acct_table_name = None

        # Application settings
        try:
            self._days_threshold = config("DAYS_THRESHOLD", default=30, cast=int)
        except UndefinedValueError:
            self._days_threshold = 30

        # Operation mode
        try:
            self._mode = config(
                "MODE", default="tenant"
            ).lower()  # "storage" or "tenant"
        except UndefinedValueError:
            self._mode = "tenant"
        # Tenant-wide settings (when MODE=tenant)
        try:
            self._default_notification_email = config(
                "DEFAULT_NOTIFICATION_EMAIL", default=None
            )
        except UndefinedValueError:
            self._default_notification_email = None

        # SSL verification setting
        try:
            self._verify_ssl = config("VERIFY_SSL", default=True, cast=bool)

        except UndefinedValueError:
            self._verify_ssl = True

        self._loaded = True

    @property
    def EMAIL_PROVIDER(self) -> str:
        """Get email provider (sendgrid or smtp)."""
        self._load_config()
        return self._email_provider or "sendgrid"

    @property
    def SG_API_KEY(self) -> Optional[str]:
        """Get SendGrid API key."""
        self._load_config()
        return self._sg_api_key

    @property
    def FROM_EMAIL(self) -> str:
        """Get the from email address."""
        self._load_config()
        if self._from_email is None:
            raise ValueError("FROM_EMAIL is not set")
        return self._from_email

    @property
    def SMTP_HOST(self) -> Optional[str]:
        """Get SMTP host."""
        self._load_config()
        return self._smtp_host

    @property
    def SMTP_PORT(self) -> int:
        """Get SMTP port."""
        self._load_config()
        return self._smtp_port or 587

    @property
    def SMTP_USER(self) -> Optional[str]:
        """Get SMTP username."""
        self._load_config()
        return self._smtp_user

    @property
    def SMTP_PASSWORD(self) -> Optional[str]:
        """Get SMTP password."""
        self._load_config()
        return self._smtp_password

    @property
    def SMTP_USE_TLS(self) -> bool:
        """Get SMTP USE_TLS setting."""
        self._load_config()
        return self._smtp_use_tls if self._smtp_use_tls is not None else True

    @property
    def SMTP_USE_SSL(self) -> bool:
        """Get SMTP USE_SSL setting."""
        self._load_config()
        return self._smtp_use_ssl if self._smtp_use_ssl is not None else False

    @property
    def STG_ACCT_NAME(self) -> Optional[str]:
        """Get storage account name."""
        self._load_config()
        return self._stg_acct_name

    @property
    def STG_ACCT_TABLE_NAME(self) -> Optional[str]:
        """Get storage table name."""
        self._load_config()
        return self._stg_acct_table_name

    @property
    def DAYS_THRESHOLD(self) -> int:
        """Get days threshold."""
        self._load_config()
        if self._days_threshold is None:
            return 30  # Default value
        return self._days_threshold

    @property
    def MODE(self) -> str:
        """Get operation mode."""
        self._load_config()
        if self._mode is None:
            return "tenant"  # Default value
        return self._mode

    @property
    def DEFAULT_NOTIFICATION_EMAIL(self) -> Optional[str]:
        """Get default notification email."""
        self._load_config()
        return self._default_notification_email

    @property
    def VERIFY_SSL(self) -> bool:
        """Get SSL verification setting."""
        self._load_config()
        return self._verify_ssl if self._verify_ssl is not None else True

    def validate(self) -> bool:
        """Validate all configuration settings."""
        self._load_config()

        errors = []
        warnings = []

        # Validate email provider
        if self._email_provider not in ["sendgrid", "smtp"]:
            errors.append("EMAIL_PROVIDER must be either 'sendgrid' or 'smtp'")

        # FROM_EMAIL is always required
        if not self._from_email:
            errors.append("FROM_EMAIL is required")
        elif not self._is_valid_email(self._from_email):
            errors.append("FROM_EMAIL must be a valid email address")

        # Provider-specific validations
        if self._email_provider == "sendgrid":
            if not self._sg_api_key:
                errors.append("SG_API_KEY is required when EMAIL_PROVIDER=sendgrid")
            elif not self._sg_api_key.startswith("SG."):
                errors.append("SG_API_KEY should start with 'SG.'")

        elif self._email_provider == "smtp":
            if not self._smtp_host:
                errors.append("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
            if not self._smtp_user:
                errors.append("SMTP_USER is required when EMAIL_PROVIDER=smtp")
            if not self._smtp_password:
                errors.append("SMTP_PASSWORD is required when EMAIL_PROVIDER=smtp")
            if self._smtp_port and (self._smtp_port < 1 or self._smtp_port > 65535):
                errors.append("SMTP_PORT must be between 1 and 65535")

        # Validate mode
        if self._mode not in ["storage", "tenant"]:
            errors.append("MODE must be either 'storage' or 'tenant'")

        # Mode-specific validations
        if self._mode == "storage":
            if not self._stg_acct_name:
                errors.append("STG_ACCT_NAME is required when MODE=storage")
            elif not self._is_valid_storage_account_name(self._stg_acct_name):
                errors.append(
                    "STG_ACCT_NAME must be 3-24 characters, lowercase letters and numbers only"
                )

            if not self._stg_acct_table_name:
                errors.append("STG_ACCT_TABLE_NAME is required when MODE=storage")
            elif not self._is_valid_table_name(self._stg_acct_table_name):
                errors.append(
                    "STG_ACCT_TABLE_NAME must be 3-63 characters, alphanumeric and hyphens only"
                )

        elif self._mode == "tenant":
            if not self._default_notification_email:
                warnings.append(
                    "DEFAULT_NOTIFICATION_EMAIL is recommended when MODE=tenant for apps without owners"
                )
            elif not self._is_valid_email(self._default_notification_email):
                errors.append(
                    "DEFAULT_NOTIFICATION_EMAIL must be a valid email address"
                )

        # Validate days threshold
        if (
            self._days_threshold is None
            or self._days_threshold < 1
            or self._days_threshold > 365
        ):
            errors.append("DAYS_THRESHOLD must be between 1 and 365 days")

        # Print errors and warnings
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   • {error}")

        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   • {warning}")

        return len(errors) == 0

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def _validate_sendgrid_api_key(api_key: str) -> bool:
        """Validate SendGrid API key format."""
        return api_key.startswith("SG.")

    @staticmethod
    def _is_valid_storage_account_name(name: str) -> bool:
        """Validate Azure Storage account name format."""
        # 3-24 characters, lowercase letters and numbers only
        pattern = r"^[a-z0-9]{3,24}$"
        return bool(re.match(pattern, name))

    @staticmethod
    def _is_valid_table_name(name: str) -> bool:
        """Validate Azure Table name format."""
        # 3-63 characters, alphanumeric and hyphens only, no consecutive hyphens
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$"
        return bool(re.match(pattern, name)) and 3 <= len(name) <= 63

    def print_config(self) -> None:
        """Print current configuration (safe for missing variables)."""
        self._load_config()

        print("\n📋 Current Configuration:")
        print(f"   Mode: {self._mode or 'NOT SET'}")
        print(f"   Days Threshold: {self._days_threshold or 'NOT SET'}")
        print(f"   Email Provider: {self._email_provider or 'NOT SET'}")
        print(f"   From Email: {self._from_email or 'NOT SET'}")
        print(f"   SSL Verification: {self._verify_ssl or 'NOT SET'}")

        if self._email_provider == "sendgrid":
            print(
                f"   SendGrid API Key: {'✓ Set' if self._sg_api_key else '❌ NOT SET'}"
            )
        elif self._email_provider == "smtp":
            print(f"   SMTP Host: {self._smtp_host or 'NOT SET'}")
            print(f"   SMTP Port: {self._smtp_port or 'NOT SET'}")
            print(f"   SMTP User: {'✓ Set' if self._smtp_user else '❌ NOT SET'}")
            print(
                f"   SMTP Password: {'✓ Set' if self._smtp_password else '❌ NOT SET'}"
            )
            print(f"   SMTP Use TLS: {self._smtp_use_tls}")
            print(f"   SMTP Use SSL: {self._smtp_use_ssl}")

        if self._mode == "storage":
            print(f"   Storage Account: {self._stg_acct_name or 'NOT SET'}")
            print(f"   Storage Table: {self._stg_acct_table_name or 'NOT SET'}")
        elif self._mode == "tenant":
            print(
                f"   Default Notification Email: {self._default_notification_email or 'NOT SET'}"
            )

        print()


# Global settings instance - removed to avoid caching issues in tests
# settings = Settings()
