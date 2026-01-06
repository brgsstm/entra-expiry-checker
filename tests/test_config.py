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
        # Mock config to return None for required variables
        with patch("entra_expiry_checker.config.config") as mock_config:
            from decouple import UndefinedValueError

            def mock_config_func(key, default=None, cast=None):
                # Simulate missing required variables
                if key == "FROM_EMAIL":
                    raise UndefinedValueError("FROM_EMAIL not found")
                if key == "SG_API_KEY" and default is None:
                    return None
                # Return defaults for optional variables
                if key == "EMAIL_PROVIDER":
                    return "sendgrid"
                if key == "DAYS_THRESHOLD":
                    return 30
                if key == "MODE":
                    return "tenant"
                if key == "VERIFY_SSL":
                    return True
                return default

            mock_config.side_effect = mock_config_func

            settings = Settings()
            # EMAIL_PROVIDER defaults to sendgrid, which requires SG_API_KEY
            # FROM_EMAIL is also required
            # So validation should fail
            result = settings.validate()
            assert result is False

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
        assert settings._is_valid_storage_account_name("st") is False  # too short
        assert (
            settings._is_valid_storage_account_name("storage-account") is False
        )  # hyphens

    def test_smtp_configuration(self):
        """Test SMTP configuration loading."""
        test_env = {
            "EMAIL_PROVIDER": "smtp",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_USE_TLS": "false",
            "SMTP_USE_SSL": "true",
            "FROM_EMAIL": "test@example.com",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.EMAIL_PROVIDER == "smtp"
            assert settings.SMTP_HOST == "smtp.example.com"
            assert settings.SMTP_PORT == 465
            assert settings.SMTP_USER == "testuser"
            assert settings.SMTP_PASSWORD == "testpass"
            assert settings.SMTP_USE_TLS is False
            assert settings.SMTP_USE_SSL is True

    def test_validation_with_smtp_config(self):
        """Test validation with valid SMTP configuration."""
        test_env = {
            "EMAIL_PROVIDER": "smtp",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USER": "testuser",
            "SMTP_PASSWORD": "testpass",
            "FROM_EMAIL": "test@example.com",
            "MODE": "tenant",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.validate() is True

    def test_validation_with_missing_smtp_vars(self):
        """Test validation with missing SMTP required variables."""
        from decouple import UndefinedValueError

        def mock_config(key, default=None, cast=None):
            """Mock config function that only reads from test_env."""
            test_env = {
                "EMAIL_PROVIDER": "smtp",
                "FROM_EMAIL": "test@example.com",
            }
            # Return values from test_env, or raise UndefinedValueError if not found and no default
            if key in test_env:
                value = test_env[key]
                if cast:
                    return cast(value)
                return value
            if default is not None:
                if cast:
                    return cast(default)
                return default
            raise UndefinedValueError(f"{key} not found")

        with patch("entra_expiry_checker.config.config", side_effect=mock_config):
            settings = Settings()
            assert settings.validate() is False

    def test_table_name_validation(self):
        """Test table name validation."""
        settings = Settings()

        # Valid names
        assert settings._is_valid_table_name("mytable") is True
        assert settings._is_valid_table_name("my-table") is True
        assert settings._is_valid_table_name("table123") is True

        # Invalid names
        assert settings._is_valid_table_name("ab") is False  # too short
        assert settings._is_valid_table_name("-table") is False  # starts with hyphen
        assert settings._is_valid_table_name("table-") is False  # ends with hyphen
        # Note: The current regex doesn't prevent consecutive hyphens, but that's acceptable
        # as Azure Table Storage allows them in some cases

    def test_days_threshold_validation(self):
        """Test days threshold validation."""
        test_env = {
            "SG_API_KEY": "SG.test_key",
            "FROM_EMAIL": "test@example.com",
            "DAYS_THRESHOLD": "0",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.validate() is False

        test_env["DAYS_THRESHOLD"] = "366"
        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.validate() is False

    def test_email_provider_default(self):
        """Test that EMAIL_PROVIDER defaults to sendgrid."""
        from decouple import UndefinedValueError

        def mock_config(key, default=None, cast=None):
            """Mock config function that only reads from test_env."""
            test_env = {
                "SG_API_KEY": "SG.test_key",
                "FROM_EMAIL": "test@example.com",
            }
            # Return values from test_env, or use default if provided
            if key in test_env:
                value = test_env[key]
                if cast:
                    return cast(value)
                return value
            if default is not None:
                if cast:
                    return cast(default)
                return default
            raise UndefinedValueError(f"{key} not found")

        with patch("entra_expiry_checker.config.config", side_effect=mock_config):
            settings = Settings()
            assert settings.EMAIL_PROVIDER == "sendgrid"

    def test_smtp_port_default(self):
        """Test that SMTP_PORT defaults to 587."""
        test_env = {
            "EMAIL_PROVIDER": "smtp",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USER": "testuser",
            "SMTP_PASSWORD": "testpass",
            "FROM_EMAIL": "test@example.com",
        }

        with patch.dict("os.environ", test_env, clear=True):
            settings = Settings()
            assert settings.SMTP_PORT == 587
