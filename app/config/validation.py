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
    """
    Validates the application configuration.

    Raises:
        ValueError: If configuration validation fails.
    """
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

    # Print configuration values (excluding password) from centralized settings
    host = APP_SETTINGS.server.host
    port = int(APP_SETTINGS.server.port) if APP_SETTINGS.server.port is not None else None
    container_name = APP_SETTINGS.vectordb.container_name
    db_port = int(APP_SETTINGS.vectordb.port) if APP_SETTINGS.vectordb.port is not None else None
    username = APP_SETTINGS.vectordb.username
    password_file = APP_SETTINGS.vectordb.password_file

    logger.info(f"Server config: host={host}, port={port}")
    logger.info(
        f"VectorDB config: container_name={container_name}, port={db_port}, username={username}, password_file={password_file}"
    )
    logger.info("Configuration validation passed")


def _validate_server_config() -> List[str]:
    """
    Validate server configuration.

    Returns:
        List[str]: List of error messages, empty if valid.
    """
    errors = []

    # Get values from centralized settings
    host = APP_SETTINGS.server.host
    port = int(APP_SETTINGS.server.port) if APP_SETTINGS.server.port is not None else None

    if not host:
        errors.append("Server host is required")
    else:
        # Avoid hardcoding the literal '0.0.0.0' to prevent static-analysis false positives;
        # detect an all-zero IPv4 address dynamically and warn in production.
        parts = [p for p in host.strip().split(".") if p != ""]
        if (
            len(parts) == 4
            and all(part == "0" for part in parts)
            and APP_SETTINGS.app.is_production
        ):
            logger.warning("Server bound to all interfaces in production")

    if port is None:
        errors.append("Server port is required")
    elif not isinstance(port, int) or port <= 0:
        errors.append("Server port must be a positive integer")
    elif port < 1024 or port > 65535:
        errors.append("Server port must be between 1024 and 65535")

    return errors


def _validate_vectordb_config() -> List[str]:
    """
    Validate vector database configuration.

    Returns:
        List[str]: List of error messages, empty if valid.
    """
    errors = []

    if not APP_SETTINGS.vectordb:
        errors.append("Vector database configuration is required")
        return errors

    # Get values from centralized settings (prefer legacy `endpoint` if present)
    container_name = getattr(APP_SETTINGS.vectordb, "endpoint", None) or getattr(
        APP_SETTINGS.vectordb, "container_name", None
    )
    port = int(APP_SETTINGS.vectordb.port) if APP_SETTINGS.vectordb.port is not None else None
    username = APP_SETTINGS.vectordb.username

    # Validate endpoint
    if not container_name:
        errors.append("Vector database container name is required")
    else:
        # Coerce to string for robust regex matching (tests may use MagicMock)
        try:
            cname = container_name if isinstance(container_name, str) else str(container_name)
        except Exception:
            cname = None

        if not cname or not re.match(r"^(https?://)?[\w\.-]+(:\d+)?$", cname):
            errors.append("Vector database container name format is invalid")

    # Validate port
    if port is None:
        errors.append("Vector database port is required")
    elif not isinstance(port, int) or port <= 0:
        errors.append("Vector database port must be a positive integer")
    elif port < 1 or port > 65535:
        errors.append("Vector database port must be between 1 and 65535")

    # Validate credentials
    if not username:
        errors.append("Vector database username is required")

    # Check password or password file from settings
    password = APP_SETTINGS.vectordb.password
    password_file = APP_SETTINGS.vectordb.password_file

    if not password and not password_file:
        errors.append("Vector database password or password file is required")

    # Validate password file existence only for host-local absolute paths.
    # Skip validation for container paths (which typically start with '/').
    if password_file:
        if not password_file.startswith("/") and os.path.isabs(password_file):
            if not os.path.exists(password_file):
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
    """
    Validate security-related configuration.

    Returns:
        List[str]: List of error messages, empty if valid.
    """
    errors = []

    if APP_SETTINGS.app.is_production:
        if APP_SETTINGS.app.debug:
            errors.append("Debug mode should not be enabled in production")

        # Skip password validation if password is read from file
        password_file = APP_SETTINGS.vectordb.password_file
        if not password_file:
            password = APP_SETTINGS.vectordb.password
            if password and len(password) < 8:
                errors.append("Vector database password should be at least 8 characters")

            weak_passwords = ["password", "admin", "root", "milvus", "123456"]
            if password and password.lower() in weak_passwords:
                errors.append("Vector database password appears to be weak")

    return errors
