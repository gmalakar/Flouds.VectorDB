# Enhanced Error Responses

## Overview
This document outlines the enhanced error response system that provides detailed information for rate limiting and ensures sensitive information is not exposed in error messages.

## Problem Statement
The original error responses had several issues:
- **Rate limit responses lacked detail** - No information about limits, retry timing, or current usage
- **Sensitive information exposure** - Error messages could leak passwords, tokens, IP addresses, and other sensitive data
- **Inconsistent error formats** - Different error types used different response structures
- **Poor client experience** - Clients couldn't determine how to handle errors effectively

## Solution Implementation

### 1. Enhanced Rate Limit Responses

#### Before (Basic Response):
```json
{
  "detail": "Rate limit exceeded: 100 requests per 60 seconds"
}
```

#### After (Detailed Response):
```json
{
  "error": "Rate Limit Exceeded",
  "message": "Too many requests. Limit: 100 requests per 60 seconds",
  "type": "rate_limit_error",
  "limit_info": {
    "limit": 100,
    "period": 60,
    "retry_after": 45,
    "limit_type": "ip"
  }
}
```

#### Tenant Rate Limit Response:
```json
{
  "error": "Rate Limit Exceeded",
  "message": "Too many requests. Limit: 1000 requests per 60 seconds",
  "type": "rate_limit_error",
  "limit_info": {
    "limit": 1000,
    "period": 60,
    "retry_after": 30,
    "limit_type": "tenant",
    "tier": "premium"
  },
  "suggestion": "Consider upgrading your tier for higher limits"
}
```

### 2. Sensitive Information Sanitization

#### Patterns Detected and Sanitized:
- **Passwords**: `password=secret123` → `password=[REDACTED]`
- **Tokens**: `token: abc123xyz` → `token: [REDACTED]`
- **API Keys**: `key=sk-1234567890` → `key=[REDACTED]`
- **Secrets**: `secret: mysecret` → `secret: [REDACTED]`
- **IP Addresses**: `192.168.1.100` → `[REDACTED]`
- **Email Addresses**: `user@example.com` → `[REDACTED]`
- **Database URLs**: `mongodb://user:pass@host` → `[REDACTED]`

#### Example Sanitization:
```python
# Before
"Connection failed to mongodb://admin:password123@192.168.1.100:27017/db"

# After
"Connection failed to [REDACTED]"
```

### 3. Consistent Error Response Structure

All error responses now follow a consistent structure:

```json
{
  "error": "Error Type",
  "message": "Human-readable description",
  "type": "error_type_identifier",
  "details": "Sanitized technical details",
  "retry_after": 30  // Optional: seconds to wait before retry
}
```

## Error Response Types

### 1. Application Errors (400)
```json
{
  "error": "Application Error",
  "message": "A business logic error occurred",
  "type": "application_error",
  "details": "Sanitized error details"
}
```

### 2. Validation Errors (400)
```json
{
  "error": "Validation Error",
  "message": "Invalid input data provided",
  "type": "validation_error",
  "details": "Field 'email' is required"
}
```

### 3. Connection Errors (503)
```json
{
  "error": "Service Unavailable",
  "message": "Unable to connect to required services",
  "type": "connection_error",
  "details": "Connection timeout or failure",
  "retry_after": 30
}
```

### 4. System Errors (500)
```json
{
  "error": "System Error",
  "message": "A system-level error occurred",
  "type": "system_error",
  "details": "Insufficient permissions or system resource issue"
}
```

### 5. Configuration Errors (500)
```json
{
  "error": "Configuration Error",
  "message": "Service configuration issue detected",
  "type": "configuration_error",
  "details": "Service is temporarily misconfigured"
}
```

### 6. Internal Errors (500)
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "type": "internal_error",
  "details": "Please try again later or contact support"
}
```

## Implementation Details

### 1. Error Formatter Utility (`app/utils/error_formatter.py`)

#### Key Functions:
- **`sanitize_error_message()`** - Removes sensitive information from error messages
- **`format_error_response()`** - Creates consistent error response structure
- **`format_rate_limit_response()`** - Specialized formatting for rate limit errors

#### Sensitive Pattern Detection:
```python
sensitive_patterns = [
    r'password[=:\s]*[^\s\'"]+',
    r'token[=:\s]*[^\s\'"]+',
    r'key[=:\s]*[^\s\'"]+',
    r'secret[=:\s]*[^\s\'"]+',
    r'auth[=:\s]*[^\s\'"]+',
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
    r'mongodb://[^\s]+',  # Database URLs
    r'postgresql://[^\s]+',
    r'mysql://[^\s]+',
]
```

### 2. Enhanced Rate Limiting

#### IP-Based Rate Limiting:
- **Default Limit**: 100 requests per 60 seconds
- **Response Includes**: Current usage, remaining requests, retry timing
- **Limit Type**: Identified as "ip" in response

#### Tenant-Based Rate Limiting:
- **Default Tier**: 200 requests per 60 seconds
- **Premium Tier**: 1000 requests per 60 seconds
- **Response Includes**: Tier information, upgrade suggestions
- **Limit Type**: Identified as "tenant" in response

#### Rate Limit Information:
```python
{
    "limit": 100,           # Maximum requests allowed
    "period": 60,           # Time period in seconds
    "current": 95,          # Current request count
    "remaining": 5,         # Remaining requests
    "retry_after": 45,      # Seconds until limit resets
    "tier": "premium"       # Tenant tier (if applicable)
}
```

### 3. Middleware Integration

#### Rate Limit Middleware:
- Tracks requests per IP and tenant
- Provides detailed limit information
- Calculates accurate retry timing
- Differentiates between IP and tenant limits

#### Error Handler Middleware:
- Sanitizes all error messages before logging and response
- Applies consistent error formatting
- Prevents sensitive information leakage
- Maintains error context for debugging

## Security Benefits

### 1. Information Disclosure Prevention
- **Credential Protection** - Passwords, tokens, and keys are redacted
- **Infrastructure Hiding** - IP addresses and internal URLs are masked
- **PII Protection** - Email addresses and personal data are sanitized
- **Error Context Preservation** - Technical details maintained for debugging while hiding sensitive data

### 2. Attack Surface Reduction
- **Enumeration Prevention** - Generic error messages prevent system enumeration
- **Configuration Hiding** - Internal configuration details are not exposed
- **Service Discovery Prevention** - Internal service information is masked

### 3. Compliance Support
- **Data Privacy** - Supports GDPR and similar privacy regulations
- **Security Standards** - Aligns with OWASP security guidelines
- **Audit Trail** - Maintains detailed logs while protecting sensitive data

## Client Benefits

### 1. Better Error Handling
- **Structured Responses** - Consistent format enables programmatic handling
- **Error Classification** - Type field allows specific error handling logic
- **Retry Guidance** - Retry timing information prevents unnecessary requests

### 2. Rate Limit Management
- **Usage Awareness** - Clients can track their usage against limits
- **Proactive Throttling** - Clients can implement proactive rate limiting
- **Upgrade Guidance** - Clear information about tier limitations and upgrade options

### 3. Debugging Support
- **Error Context** - Sufficient information for client-side debugging
- **Request Correlation** - Error types help correlate with client actions
- **Support Information** - Clear guidance on when to contact support

## Monitoring and Observability

### 1. Error Metrics
- **Error Type Distribution** - Track frequency of different error types
- **Rate Limit Violations** - Monitor rate limiting effectiveness
- **Sensitive Data Exposure** - Alert on potential information leakage

### 2. Performance Impact
- **Response Time** - Monitor impact of error processing on response times
- **Memory Usage** - Track memory usage of error handling components
- **CPU Overhead** - Measure CPU impact of sanitization processes

### 3. Security Monitoring
- **Pattern Detection** - Monitor for new sensitive data patterns
- **Sanitization Effectiveness** - Verify sensitive data is properly redacted
- **Error Frequency** - Track error patterns for security analysis

## Testing Strategy

### 1. Unit Tests
```python
def test_sanitize_password_in_error():
    error = "Login failed with password=secret123"
    result = sanitize_error_message(error)
    assert "[REDACTED]" in result
    assert "secret123" not in result

def test_rate_limit_response_format():
    response = format_rate_limit_response(100, 60, 30, "ip")
    assert response["error"] == "Rate Limit Exceeded"
    assert response["limit_info"]["retry_after"] == 30
```

### 2. Integration Tests
```python
def test_rate_limit_middleware_response():
    # Test that rate limit responses include detailed information

def test_error_handler_sanitization():
    # Test that sensitive information is properly sanitized
```

### 3. Security Tests
```python
def test_no_sensitive_data_in_responses():
    # Verify no sensitive patterns appear in error responses

def test_sanitization_patterns():
    # Test all sensitive data patterns are properly detected
```

## Configuration

### 1. Rate Limit Configuration
```python
# Default rate limits
RATE_LIMITS = {
    "ip": {"calls": 100, "period": 60},
    "tenant_default": {"calls": 200, "period": 60},
    "tenant_premium": {"calls": 1000, "period": 60}
}
```

### 2. Sanitization Configuration
```python
# Additional sensitive patterns can be configured
ADDITIONAL_SENSITIVE_PATTERNS = [
    r'custom_secret[=:\s]*[^\s\'"]+',
    r'api_token[=:\s]*[^\s\'"]+',
]
```

## Future Enhancements

### 1. Dynamic Rate Limiting
- Implement adaptive rate limits based on system load
- Add burst capacity for short-term spikes
- Implement sliding window rate limiting

### 2. Advanced Sanitization
- Machine learning-based sensitive data detection
- Context-aware sanitization rules
- Custom sanitization patterns per tenant

### 3. Error Analytics
- Error pattern analysis and prediction
- Automated error categorization
- Performance impact analysis of error handling

## Conclusion
The enhanced error response system significantly improves both security and user experience by providing detailed, structured error information while protecting sensitive data. The consistent error format enables better client-side error handling, while the comprehensive sanitization prevents information disclosure vulnerabilities.
