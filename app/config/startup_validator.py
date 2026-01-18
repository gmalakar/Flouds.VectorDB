# =============================================================================
# File: startup_validator.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import sys

from app.app_init import APP_SETTINGS
from app.config.appsettings import AppSettings
from app.config.validation import validate_config
from app.logger import get_logger

logger = get_logger("startup_validator")


def validate_startup_config() -> None:
    """
    Validates configuration at startup and exits if invalid.

    Performs comprehensive validation of all settings including:
    - Individual field validation (via Pydantic validators)
    - Cross-field dependency validation
    - Configuration consistency checks

    Returns:
        None

    Raises:
        SystemExit: If any validation fails (exits with code 1).
    """
    try:
        # Validate individual fields and basic constraints
        validate_config()
        logger.info("Basic configuration validation successful")

        # Perform comprehensive cross-field and dependency validation
        AppSettings.validate_all(APP_SETTINGS)
        logger.info("Comprehensive configuration validation successful")

    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}")
        logger.critical("Application startup aborted due to invalid configuration")
        sys.exit(1)
    except (TypeError, AttributeError, KeyError) as e:
        logger.critical(f"Configuration structure error: {e}")
        logger.critical("Check that all required configuration fields are properly set")
        sys.exit(1)
    except ImportError as e:
        logger.critical(f"Module import error during validation: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error during configuration validation: {e}")
        logger.exception("Full stack trace:")
        sys.exit(1)
