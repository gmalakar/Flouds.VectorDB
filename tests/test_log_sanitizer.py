from app.utils.log_sanitizer import (
    LogLevel,
    sanitize_for_log,
    sanitize_dict_for_log,
    sanitize_for_audit,
    is_audit_event,
)


def test_sanitize_for_log_removes_control_chars_and_limits_length():
    s = sanitize_for_log("hello\nworld\t\x00")
    assert "\n" not in s and "\t" not in s
    assert "_" in s  # replaced control chars


def test_sanitize_dict_for_log_redacts_sensitive_fields():
    original_email = "user@example.com"
    d = sanitize_dict_for_log({"password": "p@ss", "email": original_email}, log_level=LogLevel.INFO)
    assert d["password"] == "[REDACTED]"
    # Non-sensitive fields are sanitized for control chars but preserved otherwise
    assert d["email"] == sanitize_for_log(original_email, LogLevel.INFO)


def test_sanitize_for_audit_preserves_fields_but_sanitizes_strings():
    entry = sanitize_for_audit(
        event="USER_CREATED",
        data={"token": "abc", "nested": {"password": "xyz"}},
        user="admin\n",
        tenant="tenantA\t",
        details="multi\nline",
    )
    assert entry["event"] == "USER_CREATED"
    assert isinstance(entry["timestamp"], float)
    # audit uses sanitize_dict_for_log with redact_sensitive=False
    assert entry["data"]["token"] == "abc"
    assert entry["user"] == "admin_"
    assert entry["tenant"] == "tenantA_"


def test_is_audit_event_detection():
    assert is_audit_event("USER_CREATED") is True
    assert is_audit_event("SOMETHING_ELSE") is False
