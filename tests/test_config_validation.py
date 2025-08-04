# =============================================================================
# File: test_config_validation.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from unittest.mock import Mock, patch

import pytest

from app.config.validation import (
    _validate_security_config,
    _validate_server_config,
    _validate_vectordb_config,
    validate_config,
)


class TestConfigValidation:

    @patch("app.config.validation.APP_SETTINGS")
    def test_validate_server_config_valid(self, mock_settings):
        mock_settings.server.host = "localhost"
        mock_settings.server.port = 8080
        mock_settings.app.is_production = False

        errors = _validate_server_config()
        assert errors == []

    @patch("app.config.validation.APP_SETTINGS")
    def test_validate_server_config_invalid_port(self, mock_settings):
        mock_settings.server.host = "localhost"
        mock_settings.server.port = 70000  # Invalid port
        mock_settings.app.is_production = False

        errors = _validate_server_config()
        assert len(errors) == 1
        assert "port must be between" in errors[0]

    @patch("app.config.validation.APP_SETTINGS")
    @patch("app.config.validation.os.getenv")
    def test_validate_vectordb_config_valid(self, mock_getenv, mock_settings):
        mock_settings.vectordb.endpoint = "localhost"
        mock_settings.vectordb.port = 19530
        mock_settings.vectordb.username = "root"
        mock_settings.vectordb.password = "password"
        mock_settings.vectordb.password_file = None
        mock_settings.vectordb.default_dimension = 384
        mock_getenv.return_value = None

        errors = _validate_vectordb_config()
        assert errors == []

    @patch("app.config.validation.APP_SETTINGS")
    @patch("app.config.validation.os.getenv")
    def test_validate_vectordb_config_missing_credentials(
        self, mock_getenv, mock_settings
    ):
        mock_settings.vectordb.endpoint = "localhost"
        mock_settings.vectordb.port = 19530
        mock_settings.vectordb.username = ""  # Missing username
        mock_settings.vectordb.password = ""
        mock_settings.vectordb.password_file = None
        mock_settings.vectordb.default_dimension = 384
        mock_getenv.return_value = None

        errors = _validate_vectordb_config()
        assert len(errors) >= 2  # Missing username and password

    @patch("app.config.validation.APP_SETTINGS")
    @patch("app.config.validation.os.getenv")
    def test_validate_security_config_production(self, mock_getenv, mock_settings):
        mock_settings.app.is_production = True
        mock_settings.app.debug = True  # Debug in production
        mock_settings.vectordb.password = "weak"  # Weak password
        mock_settings.vectordb.password_file = None  # No password file
        mock_getenv.side_effect = lambda key: (
            "weak" if key == "VECTORDB_PASSWORD" else None
        )

        errors = _validate_security_config()
        assert len(errors) >= 2  # Debug mode and weak password

    @patch("app.config.validation.APP_SETTINGS")
    @patch("app.config.validation.os.getenv")
    def test_validate_security_config_password_file(self, mock_getenv, mock_settings):
        mock_settings.app.is_production = True
        mock_settings.app.debug = False
        mock_settings.vectordb.password = "weak"  # Weak password but should be ignored
        mock_settings.vectordb.password_file = "/path/to/password"
        mock_getenv.side_effect = lambda key: (
            "/path/to/password" if key == "VECTORDB_PASSWORD_FILE" else None
        )

        errors = _validate_security_config()
        assert len(errors) == 0  # No password validation when using file

    @patch("app.config.validation._validate_server_config")
    @patch("app.config.validation._validate_vectordb_config")
    @patch("app.config.validation._validate_security_config")
    def test_validate_config_success(self, mock_security, mock_vectordb, mock_server):
        mock_server.return_value = []
        mock_vectordb.return_value = []
        mock_security.return_value = []

        # Should not raise exception
        validate_config()

    @patch("app.config.validation._validate_server_config")
    @patch("app.config.validation._validate_vectordb_config")
    @patch("app.config.validation._validate_security_config")
    def test_validate_config_failure(self, mock_security, mock_vectordb, mock_server):
        mock_server.return_value = ["Server error"]
        mock_vectordb.return_value = ["VectorDB error"]
        mock_security.return_value = []

        with pytest.raises(ValueError) as exc_info:
            validate_config()

        assert "Configuration validation failed" in str(exc_info.value)
