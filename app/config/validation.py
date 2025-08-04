# =============================================================================
# File: validation.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import re
from typing import List

from app.app_init import APP_SETTINGS
from app.logger import get_logger

logger = get_logger("config_validation")


def validate_config() -> None:
    """Validates the application configuration."""
    errors: List[str] = []

    # Validate server configuration
    errors.extend(_validate_server_config())

    # Validate vector database configuration
    errors.extend(_validate_vectordb_config())

    # Note: Logging configuration validation removed as logging is handled by logger.py

    # Validate security settings
    errors.extend(_validate_security_config())

    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(
            f"- {error}" for error in errors
        )
        logger.error(error_message)
        raise ValueError(error_message)

    logger.info("Configuration validation passed")


def _validate_server_config() -> List[str]:
    """Validate server configuration."""
    errors = []

    if not APP_SETTINGS.server.host:
        errors.append("Server host is required")
    elif APP_SETTINGS.server.host == "0.0.0.0" and APP_SETTINGS.app.is_production:
        logger.warning("Server bound to 0.0.0.0 in production")

    if not isinstance(APP_SETTINGS.server.port, int) or APP_SETTINGS.server.port <= 0:
        errors.append("Server port must be a positive integer")
    elif APP_SETTINGS.server.port < 1024 or APP_SETTINGS.server.port > 65535:
        errors.append("Server port must be between 1024 and 65535")

    return errors


def _validate_vectordb_config() -> List[str]:
    """Validate vector database configuration."""
    errors = []

    if not APP_SETTINGS.vectordb:
        errors.append("Vector database configuration is required")
        return errors

    # Validate endpoint
    if not APP_SETTINGS.vectordb.endpoint:
        errors.append("Vector database endpoint is required")
    elif not re.match(r"^(https?://)?[\w\.-]+(:\d+)?$", APP_SETTINGS.vectordb.endpoint):
        errors.append("Vector database endpoint format is invalid")

    # Validate port
    if (
        not isinstance(APP_SETTINGS.vectordb.port, int)
        or APP_SETTINGS.vectordb.port <= 0
    ):
        errors.append("Vector database port must be a positive integer")
    elif APP_SETTINGS.vectordb.port < 1 or APP_SETTINGS.vectordb.port > 65535:
        errors.append("Vector database port must be between 1 and 65535")

    # Validate credentials
    if not APP_SETTINGS.vectordb.username:
        errors.append("Vector database username is required")

    # Check password or password file
    password = os.getenv("VECTORDB_PASSWORD") or APP_SETTINGS.vectordb.password
    password_file = (
        os.getenv("VECTORDB_PASSWORD_FILE") or APP_SETTINGS.vectordb.password_file
    )

    if not password and not password_file:
        errors.append("Vector database password or password file is required")

    if password_file and not os.path.exists(password_file):
        errors.append(f"Vector database password file does not exist: {password_file}")

    # Validate dimensions
    if not isinstance(APP_SETTINGS.vectordb.default_dimension, int):
        errors.append("Vector database default dimension must be an integer")
    elif (
        APP_SETTINGS.vectordb.default_dimension < 1
        or APP_SETTINGS.vectordb.default_dimension > 4096
    ):
        errors.append("Vector database default dimension must be between 1 and 4096")

    return errors


def _validate_security_config() -> List[str]:
    """Validate security-related configuration."""
    errors = []

    if APP_SETTINGS.app.is_production:
        if APP_SETTINGS.app.debug:
            errors.append("Debug mode should not be enabled in production")

        # Skip password validation if password is read from file
        password_file = (
            os.getenv("VECTORDB_PASSWORD_FILE") or APP_SETTINGS.vectordb.password_file
        )
        if not password_file:
            password = os.getenv("VECTORDB_PASSWORD") or APP_SETTINGS.vectordb.password
            if password and len(password) < 8:
                errors.append(
                    "Vector database password should be at least 8 characters"
                )

            weak_passwords = ["password", "admin", "root", "milvus", "123456"]
            if password and password.lower() in weak_passwords:
                errors.append("Vector database password appears to be weak")

    return errors
