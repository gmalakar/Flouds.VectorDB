# =============================================================================
# File: logger.py
# Description: Centralized logging configuration with file and console handlers
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler


def get_logger(name: str) -> logging.Logger:
    """
    Get logger with explicit name. Auto-detection removed for performance.

    Args:
        name (str): Logger name identifier (will be prefixed with 'flouds.')

    Returns:
        logging.Logger: Configured logger instance with file and console handlers
    """
    return _get_or_create_logger(f"flouds.{name}")


# Track configured loggers
_configured_loggers = set()


def _get_or_create_logger(logger_name: str) -> logging.Logger:
    """
    Get or create logger with specific name and configuration.

    Args:
        logger_name (str): Full logger name

    Returns:
        logging.Logger: Configured logger with appropriate handlers and formatters
    """
    logger = logging.getLogger(logger_name)

    # Only configure if not already configured
    if logger_name in _configured_loggers:
        return logger

    _configured_loggers.add(logger_name)
    is_production = os.getenv("FLOUDS_API_ENV", "Production").lower() == "production"
    level = logging.INFO  # Default log level
    if is_production:
        log_dir = os.getenv("FLOUDS_LOG_PATH", "/flouds-vectordb/logs")
        level = (
            logging.DEBUG if os.getenv("APP_DEBUG_MODE", "0") == "1" else logging.INFO
        )
    else:
        # Get parent directory of app folder and create logs folder there
        current_dir = os.path.dirname(os.path.abspath(__file__))  # app folder
        parent_dir = os.path.dirname(current_dir)  # parent of app
        log_dir = os.path.join(parent_dir, "logs")
        level = logging.DEBUG  # Override for development

    # Add date to log file name

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"flouds-vectordb-{date_str}.log"
    max_bytes = int(os.getenv("FLOUDS_LOG_MAX_FILE_SIZE", "10485760"))
    backup_count = int(os.getenv("FLOUDS_LOG_BACKUP_COUNT", "5"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, log_file)

    logger.setLevel(level)

    log_format = os.getenv(
        "FLOUDS_LOG_FORMAT", "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Rotating file handler
    try:
        fh = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except (OSError, PermissionError, FileNotFoundError) as e:
        # If logger setup fails we cannot rely on logger; fall back to stderr prints
        print(f"Warning: Failed to create log file handler: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except (ValueError, TypeError, AttributeError) as e:
        print(
            f"Warning: Configuration error creating log file handler: {e}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(
            f"Warning: Unexpected error creating log file handler: {e}", file=sys.stderr
        )
        traceback.print_exc(file=sys.stderr)

    return logger
