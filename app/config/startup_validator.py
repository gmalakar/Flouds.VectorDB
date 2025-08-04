# =============================================================================
# File: startup_validator.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import sys

from app.config.validation import validate_config
from app.logger import get_logger

logger = get_logger("startup_validator")


def validate_startup_config():
    """
    Validates configuration at startup and exits if invalid.
    """
    try:
        validate_config()
        logger.info("Startup configuration validation successful")
    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}")
        logger.critical("Application startup aborted due to invalid configuration")
        sys.exit(1)
    except (TypeError, AttributeError, KeyError) as e:
        logger.critical(f"Configuration structure error: {e}")
        sys.exit(1)
    except (ImportError, ModuleNotFoundError) as e:
        logger.critical(f"Module import error during validation: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error during configuration validation: {e}")
        sys.exit(1)
