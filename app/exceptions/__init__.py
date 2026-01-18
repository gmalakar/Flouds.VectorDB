# =============================================================================
# File: __init__.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

# Re-export custom exceptions for easier imports
from .custom_exceptions import (
    AuthenticationError,
    BM25Error,
    CollectionError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseCorruptionError,
    DecryptionError,
    FloudsVectorError,
    IndexError,
    MilvusConnectionError,
    MilvusOperationError,
    PasswordPolicyError,
    SearchError,
    TenantError,
    UserManagementError,
    ValidationError,
    VectorStoreError,
)

__all__ = [
    "FloudsVectorError",
    "DatabaseConnectionError",
    "DatabaseCorruptionError",
    "DecryptionError",
    "ConfigurationError",
    "MilvusConnectionError",
    "MilvusOperationError",
    "VectorStoreError",
    "AuthenticationError",
    "ValidationError",
    "TenantError",
    "UserManagementError",
    "SearchError",
    "IndexError",
    "CollectionError",
    "PasswordPolicyError",
    "BM25Error",
]
