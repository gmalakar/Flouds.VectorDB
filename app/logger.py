# =============================================================================
# File: logger.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


def get_logger(name: str = "flouds", log_path: Optional[str] = None) -> logging.Logger:
    """
    Returns a configured logger instance.
    - Uses rotating file handler and console handler.
    - Log file location and level are environment-aware.
    - Avoids duplicate handlers for the same logger.
    """
    is_production = os.getenv("FLOUDS_API_ENV", "Production").lower() == "production"

    if log_path is None:
        if is_production:
            log_dir = os.getenv("FLOUDS_LOG_PATH", "/flouds-vector/logs")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            log_dir = os.path.join(parent_dir, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"flouds-ai-{date_str}.log"
        log_path = os.path.join(log_dir, log_file)
    else:
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    max_bytes = 10 * 1024 * 1024  # 10 MB
    backup_count = 5

    logger = logging.getLogger(name)
    level = logging.DEBUG if os.getenv("APP_DEBUG_MODE", "0") == "1" else logging.INFO
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Prevent duplicate handlers
    handler_paths = [
        h.baseFilename for h in logger.handlers if hasattr(h, "baseFilename")
    ]
    stream_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler)
    ]

    # Console handler
    if not stream_handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Rotating file handler
    if log_path not in handler_paths:
        fh = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Avoid log message duplication in child loggers
    logger.propagate = False

    return logger
