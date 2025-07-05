"""
Tests for the config module.
"""

from unittest.mock import patch

from entra_expiry_checker.config import Settings


class TestSettings:
    """Test the Settings class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings()
            assert settings.DAYS_THRESHOLD == 30
            assert settings.MODE == "tenant"
            assert settings.VERIFY_SSL is True

    def test_environment_variable_loading(self):
        """Test that environment variables are loaded correctly."""
        test_env = {
            "SG_API_KEY": "SG.test_key",
            "FROM_EMAIL": "test@example.com",
            "DAYS_THRESHOLD": "14",
            "MODE": "storage",
            "VERIFY_SSL": "false",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.SG_API_KEY == "SG.test_key"
            assert settings.FROM_EMAIL == "test@example.com"
            assert settings.DAYS_THRESHOLD == 14
            assert settings.MODE == "storage"
            assert settings.VERIFY_SSL is False

    def test_validation_with_valid_config(self):
        """Test validation with valid configuration."""
        test_env = {
            "SG_API_KEY": "SG.test_key",
            "FROM_EMAIL": "test@example.com",
            "MODE": "tenant",
            "DAYS_THRESHOLD": "30",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.validate() is True

    def test_validation_with_missing_required_vars(self):
        """Test validation with missing required variables."""
        # Mock the config function to simulate missing environment variables
        with patch("entra_expiry_checker.config.config") as mock_config:

            def mock_config_func(key, default=None, cast=None):
                # Simulate missing required variables
                if key in ["SG_API_KEY", "FROM_EMAIL"]:
                    from decouple import UndefinedValueError

                    raise UndefinedValueError(f"{key} not found")
                # Return defaults for optional variables
                return default

            mock_config.side_effect = mock_config_func

            settings = Settings()
            # Debug: Print the actual values
            print(f"DEBUG: SG_API_KEY = {settings.SG_API_KEY}")
            print(f"DEBUG: FROM_EMAIL = {settings.FROM_EMAIL}")
            print(f"DEBUG: MODE = {settings.MODE}")
            print(f"DEBUG: validate() = {settings.validate()}")
            assert settings.validate() is False

    def test_email_validation(self):
        """Test email validation."""
        settings = Settings()

        # Valid emails
        assert settings._is_valid_email("test@example.com") is True
        assert settings._is_valid_email("user.name@domain.co.uk") is True

        # Invalid emails
        assert settings._is_valid_email("invalid-email") is False
        assert settings._is_valid_email("@example.com") is False
        assert settings._is_valid_email("test@") is False

    def test_storage_account_name_validation(self):
        """Test storage account name validation."""
        settings = Settings()

        # Valid names
        assert settings._is_valid_storage_account_name("storage123") is True
        assert settings._is_valid_storage_account_name("myaccount") is True

        # Invalid names
        assert (
            settings._is_valid_storage_account_name("Storage123") is False
        )  # uppercase
        assert settings._is_valid_storage_account_name(
            "st") is False  # too short
        assert (
            settings._is_valid_storage_account_name("storage-account") is False
        )  # hyphens
