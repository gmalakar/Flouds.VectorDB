# =============================================================================
# File: custom_exceptions.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

"""
Custom exception classes for FloudsVector application.
Provides specific exception types for better error handling and debugging.
"""


class FloudsVectorError(Exception):
    """
    Base exception class for all FloudsVector-related errors.

    This is the root exception for the application. All custom exceptions should inherit from this.
    """


# --- KeyManager/DB/Decryption exceptions (must come after FloudsVectorError) ---
class DatabaseConnectionError(FloudsVectorError):
    """
    Raised when database connection fails.
    """

    pass


class DatabaseCorruptionError(FloudsVectorError):
    """
    Raised when database file is corrupted.
    """

    pass


class DecryptionError(FloudsVectorError):
    """
    Raised when decryption of data fails.
    """

    pass


class ConfigurationError(FloudsVectorError):
    """
    Raised when there are configuration-related issues.
    """

    pass


class MilvusConnectionError(FloudsVectorError):
    """
    Raised when Milvus connection fails.
    """

    pass


class MilvusOperationError(FloudsVectorError):
    """
    Raised when Milvus operations fail.
    """

    pass


class VectorStoreError(FloudsVectorError):
    """
    Raised when vector store operations fail.
    """

    pass


class AuthenticationError(FloudsVectorError):
    """
    Raised when authentication fails.
    """

    pass


class ValidationError(FloudsVectorError):
    """
    Raised when input validation fails.
    """

    pass


class TenantError(FloudsVectorError):
    """
    Raised when tenant-related operations fail.
    """

    pass


class UserManagementError(FloudsVectorError):
    """
    Raised when user management operations fail.
    """

    pass


class SearchError(FloudsVectorError):
    """
    Raised when search operations fail.
    """

    pass


class IndexError(FloudsVectorError):
    """
    Raised when index operations fail.
    """

    pass


class CollectionError(FloudsVectorError):
    """
    Raised when collection operations fail.
    """

    pass


class PasswordPolicyError(FloudsVectorError):
    """
    Raised when password policy validation fails.
    """

    pass


class BM25Error(FloudsVectorError):
    """
    Raised when BM25 operations fail.
    """

    pass
