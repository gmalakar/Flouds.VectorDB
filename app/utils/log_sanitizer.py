# =============================================================================
# File: log_sanitizer.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import re
from enum import Enum
from typing import Any, Set


class LogLevel(str, Enum):
    """Log level enumeration for different sensitivity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    AUDIT = "audit"


# Sensitive field patterns that should be redacted in logs
_SENSITIVE_PATTERNS = {
    "password", "passwd", "pwd", "secret", "token", "auth",
    "api_key", "apikey", "access_key", "private_key", "credentials",
    "bearer", "authorization", "x-api-key", "api-key", "key",
}

# Fields that can be partially logged (first N chars visible)
_PARTIAL_LOG_FIELDS = {
    "email", "phone", "ssn", "credit_card", "tenant_code", "user_id"
}

# Audit events that should always be logged regardless of log level
_AUDIT_EVENTS = {
    "USER_CREATED", "USER_DELETED", "USER_MODIFIED",
    "TENANT_CREATED", "TENANT_DELETED",
    "DATABASE_MODIFIED", "SECURITY_POLICY_CHANGED",
    "AUTHENTICATION_FAILED", "AUTHORIZATION_DENIED",
}


def sanitize_for_log(value: Any, log_level: LogLevel = LogLevel.INFO) -> str:
    """
    Sanitize input for safe logging by removing or encoding dangerous characters.

    Args:
        value (Any): Input value to sanitize for logging.
        log_level (LogLevel): Log level to determine sanitization strictness.

    Returns:
        str: Sanitized string safe for logging.
    """
    if value is None:
        return "None"

    str_value: str = str(value)
    # Remove newlines, carriage returns, and other control characters
    sanitized: str = re.sub(r"[\r\n\t\x00-\x1f\x7f-\x9f]", "_", str_value)

    # Limit length to prevent log flooding
    if len(sanitized) > 200:
        sanitized = sanitized[:197] + "..."

    return sanitized


def sanitize_dict_for_log(
    data: dict[str, Any],
    log_level: LogLevel = LogLevel.INFO,
    redact_sensitive: bool = True,
) -> dict[str, str]:
    """
    Sanitize all values in a dictionary for safe logging with sensitive field redaction.

    Args:
        data (dict[str, Any]): Dictionary to sanitize.
        log_level (LogLevel): Log level to determine redaction strictness.
        redact_sensitive (bool): Whether to redact sensitive fields.

    Returns:
        dict[str, str]: Dictionary with sanitized string values.
    """
    result = {}
    for k, v in data.items():
        key_lower = k.lower()

        # Always redact sensitive fields at WARNING and below
        if redact_sensitive and key_lower in _SENSITIVE_PATTERNS:
            result[k] = "[REDACTED]"
        # Partial logging for PII at DEBUG level only
        elif log_level == LogLevel.DEBUG and key_lower in _PARTIAL_LOG_FIELDS:
            str_v = str(v)
            if len(str_v) > 4:
                result[k] = str_v[:2] + "*" * (len(str_v) - 4) + str_v[-2:]
            else:
                result[k] = "*" * len(str_v)
        else:
            result[k] = sanitize_for_log(v, log_level)

    return result


def sanitize_for_audit(
    event: str,
    data: dict[str, Any],
    user: str,
    tenant: str,
    details: str = "",
) -> dict[str, Any]:
    """
    Create an audit log entry with comprehensive event tracking.

    Audit logs always capture full events with selective field redaction.

    Args:
        event: Event type (e.g., "USER_CREATED", "TENANT_DELETED").
        data: Event data dictionary.
        user: User performing the action.
        tenant: Tenant context.
        details: Additional details for the audit event.

    Returns:
        dict: Audit log entry with timestamp and context.
    """
    import time

    return {
        "timestamp": time.time(),
        "event": event,
        "user": sanitize_for_log(user),
        "tenant": sanitize_for_log(tenant),
        "data": sanitize_dict_for_log(data, log_level=LogLevel.AUDIT, redact_sensitive=False),
        "details": sanitize_for_log(details),
    }


def is_audit_event(event_name: str) -> bool:
    """
    Check if an event should be logged as an audit event.

    Args:
        event_name: Name of the event.

    Returns:
        bool: True if event should be audited.
    """
    return event_name.upper() in _AUDIT_EVENTS


def redact_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively redact sensitive fields in a nested dictionary structure.

    Args:
        data: Dictionary possibly containing nested dictionaries.

    Returns:
        dict: Dictionary with sensitive fields redacted.
    """
    result = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_PATTERNS:
            result[k] = "[REDACTED]"
        elif isinstance(v, dict):
            result[k] = redact_sensitive_fields(v)
        elif isinstance(v, list):
            result[k] = [
                redact_sensitive_fields(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            result[k] = v
    return result

