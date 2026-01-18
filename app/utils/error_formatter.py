# =============================================================================
# File: error_formatter.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.utils.log_sanitizer import sanitize_for_log


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize error message to prevent sensitive information exposure.

    Args:
        error_msg (str): The error message to sanitize.

    Returns:
        str: Sanitized error message with sensitive data redacted.
    """
    sensitive_patterns = [
        r'password[=:\s]*[^\s\'"]+',
        r'token[=:\s]*[^\s\'"]+',
        r'key[=:\s]*[^\s\'"]+',
        r'secret[=:\s]*[^\s\'"]+',
        r'auth[=:\s]*[^\s\'"]+',
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email addresses
        r"mongodb://[^\s]+",  # Database URLs
        r"postgresql://[^\s]+",
        r"mysql://[^\s]+",
    ]

    sanitized = error_msg
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    return sanitize_for_log(sanitized)


def format_error_response(
    error_type: str,
    message: str,
    details: Optional[str] = None,
    status_code: int = 500,
    request_id: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    retry_after: Optional[int] = None,
    additional_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format a consistent error response structure for API responses.

    Args:
        error_type (str): The type of error.
        message (str): The error message.
        details (Optional[str], optional): Additional error details. Defaults to None.
        status_code (int, optional): HTTP status code. Defaults to 500.
        retry_after (Optional[int], optional): Retry-After value for rate limits. Defaults to None.
        additional_info (Optional[Dict[str, Any]], optional): Additional info to include. Defaults to None.

    Returns:
        Dict[str, Any]: Formatted error response dictionary.
    """
    response = {
        "error": error_type,
        "message": message,
        "type": error_type.lower().replace(" ", "_"),
        "status_code": status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if path:
        response["path"] = path

    if method:
        response["method"] = method

    if request_id:
        response["request_id"] = request_id

    if details:
        response["details"] = sanitize_error_message(details)

    if retry_after:
        response["retry_after"] = retry_after

    if additional_info:
        response.update(additional_info)

    return response


def format_rate_limit_response(
    limit: int,
    period: int,
    retry_after: int,
    limit_type: str = "general",
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format a rate limit error response for API clients.

    Args:
        limit (int): The request limit.
        period (int): The period in seconds for the limit.
        retry_after (int): Time in seconds to wait before retrying.
        limit_type (str, optional): The type of rate limit. Defaults to "general".
        tier (Optional[str], optional): The user tier, if applicable. Defaults to None.

    Returns:
        Dict[str, Any]: Formatted rate limit error response.
    """
    limit_info: Dict[str, Any] = {
        "limit": limit,
        "period": period,
        "retry_after": retry_after,
        "limit_type": limit_type,
    }

    if tier:
        limit_info["tier"] = tier

    response = {
        "error": "Rate Limit Exceeded",
        "message": f"Too many requests. Limit: {limit} requests per {period} seconds",
        "type": "rate_limit_error",
        "limit_info": limit_info,
    }

    if tier:
        response["suggestion"] = "Consider upgrading your tier for higher limits"

    return response
