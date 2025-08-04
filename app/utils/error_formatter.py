# =============================================================================
# File: error_formatter.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import re
from typing import Any, Dict, Optional

from app.utils.input_validator import sanitize_for_log


def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error message to prevent sensitive information exposure."""
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
    retry_after: Optional[int] = None,
    additional_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format consistent error response structure."""
    response = {
        "error": error_type,
        "message": message,
        "type": error_type.lower().replace(" ", "_"),
        "timestamp": None,  # Will be added by middleware if needed
    }

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
    """Format rate limit error response."""
    response = {
        "error": "Rate Limit Exceeded",
        "message": f"Too many requests. Limit: {limit} requests per {period} seconds",
        "type": "rate_limit_error",
        "limit_info": {
            "limit": limit,
            "period": period,
            "retry_after": retry_after,
            "limit_type": limit_type,
        },
    }

    if tier:
        response["limit_info"]["tier"] = tier
        response["suggestion"] = "Consider upgrading your tier for higher limits"

    return response
