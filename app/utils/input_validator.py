# =============================================================================
# File: input_validator.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import re
from typing import Optional

from werkzeug.utils import secure_filename


def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    Validate and sanitize file paths to prevent path traversal attacks.
    Uses a safe join approach to prevent directory traversal.

    Args:
        file_path (str): The file path to validate.
        base_dir (Optional[str]): Optional base directory to restrict access to.

    Returns:
        str: Sanitized absolute path.

    Raises:
        ValueError: If path is invalid or contains traversal attempts.
    """
    if not file_path or not isinstance(file_path, str):
        raise ValueError("File path must be a non-empty string")

    # Remove null bytes and normalize
    clean_path = file_path.replace("\x00", "").strip()

    if not clean_path:
        raise ValueError("File path cannot be empty after sanitization")

    # Extract directory and filename components
    dir_path, filename = os.path.split(clean_path)

    # Secure the filename component
    if filename:
        secure_name = secure_filename(filename)
        if not secure_name:
            raise ValueError("Invalid filename after security validation")
        clean_path = os.path.join(dir_path, secure_name) if dir_path else secure_name

    # If base directory is specified, use safe join approach
    if base_dir:
        base_abs = os.path.abspath(base_dir)
        # Resolve the joined path
        joined_path = os.path.join(base_abs, clean_path)
        resolved_path = os.path.abspath(joined_path)

        # Ensure the resolved path is still within the base directory
        if (
            not resolved_path.startswith(base_abs + os.sep)
            and resolved_path != base_abs
        ):
            raise ValueError(
                f"Path traversal attempt detected: path must be within {base_dir}"
            )

        return resolved_path
    else:
        # Without base directory, just return absolute path
        return os.path.abspath(clean_path)


def validate_tenant_code(tenant_code: str) -> str:
    """
    Validate tenant code format.

    Args:
        tenant_code (str): The tenant code to validate.

    Returns:
        str: Validated tenant code.

    Raises:
        ValueError: If tenant code is invalid.
    """
    if not tenant_code or not isinstance(tenant_code, str):
        raise ValueError("Tenant code must be a non-empty string")

    # Remove whitespace and convert to lowercase
    clean_code = tenant_code.strip().lower()

    # Check format: alphanumeric and underscores only, 3-50 chars
    if not re.match(r"^[a-z0-9_]{3,50}$", clean_code):
        raise ValueError(
            "Tenant code must be 3-50 characters, alphanumeric and underscores only"
        )

    return clean_code


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format.

    Args:
        user_id (str): The user ID to validate.

    Returns:
        str: Validated user ID.

    Raises:
        ValueError: If user ID is invalid.
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID must be a non-empty string")

    clean_id = user_id.strip()

    # Check format: alphanumeric, underscores, hyphens, 3-100 chars
    if not re.match(r"^[a-zA-Z0-9_-]{3,100}$", clean_id):
        raise ValueError(
            "User ID must be 3-100 characters, alphanumeric, underscores, and hyphens only"
        )

    return clean_id


def validate_model_name(model_name: str) -> str:
    """
    Validate model name format.

    Args:
        model_name (str): The model name to validate.

    Returns:
        str: Validated model name.

    Raises:
        ValueError: If model name is invalid.
    """
    if not model_name or not isinstance(model_name, str):
        raise ValueError("Model name must be a non-empty string")

    clean_name = model_name.strip().lower()

    # Check format: alphanumeric, underscores, hyphens, dots, 1-100 chars
    if not re.match(r"^[a-z0-9_.-]{1,100}$", clean_name):
        raise ValueError(
            "Model name must be 1-100 characters, alphanumeric, underscores, hyphens, and dots only"
        )

    return clean_name


def validate_vector_dimension(dimension: int) -> int:
    """
    Validate vector dimension.

    Args:
        dimension (int): The vector dimension to validate.

    Returns:
        int: Validated vector dimension.

    Raises:
        ValueError: If dimension is not in the valid range.
    """
    if not isinstance(dimension, int) or dimension < 1 or dimension > 4096:
        raise ValueError("Vector dimension must be between 1 and 4096")
    return dimension


def validate_limit(limit: int) -> int:
    """
    Validate search/query limit.

    Args:
        limit (int): The limit value to validate.

    Returns:
        int: Validated limit.

    Raises:
        ValueError: If limit is not in the valid range.
    """
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000")
    return limit


def validate_offset(offset: int) -> int:
    """
    Validate search/query offset.

    Args:
        offset (int): The offset value to validate.

    Returns:
        int: Validated offset.

    Raises:
        ValueError: If offset is not in the valid range.
    """
    if not isinstance(offset, int) or offset < 0 or offset > 10000:
        raise ValueError("Offset must be between 0 and 10000")
    return offset


def validate_score_threshold(threshold: float) -> float:
    """
    Validate score threshold.

    Args:
        threshold (float): The score threshold to validate.

    Returns:
        float: Validated score threshold.

    Raises:
        ValueError: If threshold is not in the valid range.
    """
    if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
        raise ValueError("Score threshold must be between 0.0 and 1.0")
    return float(threshold)


def validate_vector(vector: list[float]) -> list[float]:
    """
    Validate vector data.

    Args:
        vector (list[float]): The vector to validate.

    Returns:
        list[float]: Validated vector.

    Raises:
        ValueError: If vector is not a valid list of numbers.
    """
    if not isinstance(vector, list) or len(vector) == 0 or len(vector) > 4096:
        raise ValueError("Vector must be a non-empty list with max 4096 dimensions")

    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            raise ValueError(f"Vector element at index {i} must be numeric")
        if abs(val) > 1e6:
            raise ValueError(f"Vector element at index {i} is too large")

    return vector


def sanitize_text_input(input_text: str, max_length: int = 1000) -> str:
    """
    Sanitize text input by removing dangerous characters and limiting length.

    Args:
        input_text (str): The text to sanitize.
        max_length (int, optional): Maximum allowed length. Defaults to 1000.

    Returns:
        str: Sanitized text.

    Raises:
        ValueError: If text is too long.
    """
    if not isinstance(input_text, str):
        return str(input_text) if input_text is not None else ""

    # Remove null bytes and control characters except newlines and tabs
    sanitized_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", input_text)

    # Limit length
    if len(sanitized_text) > max_length:
        raise ValueError(f"Text input too long (max {max_length} characters)")

    return sanitized_text.strip()
