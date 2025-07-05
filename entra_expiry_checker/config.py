"""
Configuration settings for the App Registration Secret Expiry Checker.
"""

import re
from typing import Optional

from decouple import UndefinedValueError, config


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings but don't load environment variables yet."""
        self._sg_api_key: Optional[str] = None
        self._from_email: Optional[str] = None
        self._stg_acct_name: Optional[str] = None
        self._stg_acct_table_name: Optional[str] = None
        self._days_threshold: Optional[int] = None
        self._mode: Optional[str] = None
        self._default_notification_email: Optional[str] = None
        self._verify_ssl: Optional[bool] = None
        self._loaded = False

    def _load_config(self):
        """Load configuration from environment variables."""
        if self._loaded:
            return

        # Set defaults first
        self._days_threshold = 30
        self._mode = "tenant"
        self._verify_ssl = True  # Default to SSL verification enabled

        # SendGrid configuration (required)
        try:
            self._sg_api_key = config("SG_API_KEY")
        except UndefinedValueError:
            self._sg_api_key = None

        try:
            self._from_email = config("FROM_EMAIL")
        except UndefinedValueError:
            self._from_email = None

        # Azure Storage configuration (optional)
        try:
            self._stg_acct_name = config("STG_ACCT_NAME", default=None)
        except UndefinedValueError:
            self._stg_acct_name = None

        try:
            self._stg_acct_table_name = config(
                "STG_ACCT_TABLE_NAME", default=None)
        except UndefinedValueError:
            self._stg_acct_table_name = None

        # Application settings
        try:
            self._days_threshold = config(
                "DAYS_THRESHOLD", default=30, cast=int)
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
    def SG_API_KEY(self) -> str:
        """Get SendGrid API key."""
        self._load_config()
        return self._sg_api_key

    @property
    def FROM_EMAIL(self) -> str:
        """Get the SendGrid from email address."""
        self._load_config()
        return self._from_email

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
        return self._days_threshold

    @property
    def MODE(self) -> str:
        """Get operation mode."""
        self._load_config()
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

        # Required SendGrid settings
        if not self._sg_api_key:
            errors.append("SG_API_KEY is required")
        elif not self._sg_api_key.startswith("SG."):
            errors.append("SG_API_KEY should start with 'SG.'")

        if not self._from_email:
            errors.append("FROM_EMAIL is required")
        elif not self._is_valid_email(self._from_email):
            errors.append("FROM_EMAIL must be a valid email address")

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
                errors.append(
                    "STG_ACCT_TABLE_NAME is required when MODE=storage")
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

    def print_config(self):
        """Print current configuration (safe for missing variables)."""
        self._load_config()

        print("\n📋 Current Configuration:")
        print(f"   Mode: {self._mode or 'NOT SET'}")
        print(f"   Days Threshold: {self._days_threshold or 'NOT SET'}")
        print(
            f"   SendGrid API Key: {'✓ Set' if self._sg_api_key else '❌ NOT SET'}")
        print(f"   From Email: {self._from_email or 'NOT SET'}")
        print(f"   SSL Verification: {self._verify_ssl or 'NOT SET'}")

        if self._mode == "storage":
            print(f"   Storage Account: {self._stg_acct_name or 'NOT SET'}")
            print(
                f"   Storage Table: {self._stg_acct_table_name or 'NOT SET'}")
        elif self._mode == "tenant":
            print(
                f"   Default Notification Email: {self._default_notification_email or 'NOT SET'}"
            )

        print()


# Global settings instance - removed to avoid caching issues in tests
# settings = Settings()
