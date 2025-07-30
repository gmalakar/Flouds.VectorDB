# =============================================================================
# File: validation.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from app.app_init import APP_SETTINGS


def validate_config():
    """Validate critical configuration settings."""
    if not APP_SETTINGS.vectordb.endpoint:
        raise ValueError("Milvus endpoint is required")
    if APP_SETTINGS.vectordb.default_dimension <= 0:
        raise ValueError("Vector dimension must be positive")
    if not APP_SETTINGS.vectordb.username:
        raise ValueError("Milvus username is required")
    if not APP_SETTINGS.vectordb.password:
        raise ValueError("Milvus password is required")
