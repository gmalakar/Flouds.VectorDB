# FloudsVector Service Patterns Documentation

## Service Method Decorator Pattern

The `@service_method` decorator in `app/services/vector_store_service.py` provides unified error handling, timing, and logging for service layer operations.

### Pattern Overview

```python
from app.services.vector_store_service import service_method
from app.models.base_response import BaseResponse

@service_method(lambda request, **_: BaseResponse(...))
def my_service_method(request: MyRequest, token: str, **kwargs):
    # Returns (response, main_logic) tuple
    def main_logic(response: BaseResponse) -> BaseResponse:
        # Perform business logic here
        response.results = perform_operation(request, token, **kwargs)
        return response
    
    return (response_obj, main_logic)
```

### How It Works

1. **Automatic Exception Handling**: All exceptions are caught and logged
2. **Response Population**: Success/failure status and messages are set automatically
3. **Timing**: Execution time is captured in `response.time_taken`
4. **Consistency**: Same error handling applies across all service methods

### Exception Mapping

Exceptions are automatically mapped to user-friendly messages:

| Exception Type | Message | HTTP Code |
|---|---|---|
| `UserManagementError` | "User management error: {}" | 400 |
| `MilvusOperationError` | "Database operation error: {}" | 400 |
| `VectorStoreError` | "Vector store error: {}" | 400 |
| `SearchError` | "Search error: {}" | 400 |
| `ValidationError` | "Validation error: {}" | 400 |
| `AuthenticationError` | "Database token error: {}" | 400 |
| `ValueError` | "Invalid data: {}" | 400 |
| Any other exception | "Unexpected error: {}" | 500 |

### Example: Insert with Transaction

```python
from app.modules.transaction_manager import transactional_operation

@service_method(lambda requests, **_: BaseResponse(...))
def insert_with_flush(requests: InsertRequest, token: str, **kwargs):
    def main_logic(response: BaseResponse) -> BaseResponse:
        with transactional_operation("insert_and_flush") as txn:
            # Add insert operation with delete rollback
            txn.add_operation(
                MilvusHelper.insert_embedded_data,
                MilvusHelper.delete_vectors,
                request=requests,
                token=token
            )
            
            # Add flush operation with rollback
            txn.add_operation(
                MilvusHelper.flush_collection,
                lambda _: None,  # No rollback needed for flush
                tenant_code=requests.tenant_code,
                model_name=requests.model,
                token=token
            )
            
            results = txn.execute()
            response.results = {"inserted": results[0], "flushed": True}
        
        return response
    
    return (BaseResponse(...), main_logic)
```

---

## Transaction Manager Pattern

The `app/modules/transaction_manager.py` provides ACID-like semantics for multi-step operations with automatic rollback.

### Basic Usage

```python
from app.modules.transaction_manager import transactional_operation

with transactional_operation("my_operation") as txn:
    # Add operation with rollback function
    txn.add_operation(
        operation_func,
        rollback_func,
        arg1, arg2,
        kwarg1="value"
    )
    
    # Execute all operations
    results = txn.execute()  # Returns list of results
```

### Rollback Example

```python
from app.modules.transaction_manager import transactional_operation

def delete_collection(collection_name):
    # Implementation
    pass

def recreate_collection(collection_name):
    # Implementation
    pass

with transactional_operation("create_and_index") as txn:
    # If create_index fails, collection will be recreated
    txn.add_operation(
        create_collection,
        delete_collection,
        collection_name="users"
    )
    
    txn.add_operation(
        create_index,
        recreate_collection,
        collection_name="users"
    )
    
    txn.execute()  # Auto-rollback on error
```

### Error Handling

```python
from app.modules.transaction_manager import transactional_operation

try:
    with transactional_operation("risky_operation") as txn:
        txn.add_operation(step1, rollback1)
        txn.add_operation(step2, rollback2)
        txn.execute()
except Exception as e:
    # Rollback already executed automatically
    logger.error(f"Operation failed and rolled back: {e}")
```

---

## Exception Handling Pattern

### Raising Custom Exceptions

```python
from app.exceptions.custom_exceptions import ValidationError, MilvusOperationError

# In service methods
if not vector_data:
    raise ValidationError("Vector data cannot be empty")

if not collection_exists:
    raise MilvusOperationError(f"Collection '{name}' does not exist")

# Exceptions are caught by @service_method decorator
# and included in response with proper HTTP status codes
```

### Custom Exception Stack

```
FloudsVectorError (base)
├── DatabaseConnectionError
├── DatabaseCorruptionError
├── DecryptionError
├── ConfigurationError
├── MilvusConnectionError
├── MilvusOperationError
├── VectorStoreError
├── AuthenticationError
├── ValidationError
├── TenantError
├── UserManagementError
├── SearchError
├── IndexError
├── CollectionError
├── PasswordPolicyError
└── BM25Error
```

---

## Logging Pattern

### Basic Logging with Sanitization

```python
from app.utils.log_sanitizer import (
    sanitize_for_log,
    sanitize_dict_for_log,
    LogLevel,
)

# Simple value sanitization
logger.info(f"Processing tenant: {sanitize_for_log(tenant_code)}")

# Dictionary with auto-redaction
data = {
    "username": "john",
    "password": "secret123",
    "email": "john@example.com"
}
safe_data = sanitize_dict_for_log(data, log_level=LogLevel.INFO)
logger.debug(f"User data: {safe_data}")
# Result: {"username": "john", "password": "[REDACTED]", "email": "jo*...com"}
```

### Audit Logging

```python
from app.utils.log_sanitizer import sanitize_for_audit, is_audit_event

event = "USER_CREATED"
if is_audit_event(event):
    audit_log = sanitize_for_audit(
        event=event,
        data={"username": "newuser", "role": "admin"},
        user="admin@system",
        tenant="acme-corp",
        details="Created via admin API"
    )
    logger.info(f"AUDIT: {audit_log}")
```

---

## Rate Limiting Pattern

### Per-Tenant Rate Limiting

```python
from app.middleware.tenant_rate_limit import tenant_limiter

# Check if tenant is within limits
allowed, info = tenant_limiter.check_tenant_limit(
    tenant_code="acme-corp",
    tier="premium"  # "default" or "premium"
)

if not allowed:
    logger.warning(f"Rate limit exceeded: {info['retry_after']}s")
    raise HTTPException(
        status_code=429,
        detail=f"Rate limit exceeded. Retry after {info['retry_after']}s"
    )

# Cleanup inactive tenants (called automatically in background)
removed = tenant_limiter.cleanup_inactive_tenants(max_inactive_seconds=3600)
logger.info(f"Cleaned up {removed} inactive tenants")
```

### Rate Limiting Tiers

| Tier | Calls/Min | Use Case |
|---|---|---|
| default | 200 | Standard API users |
| premium | 1000 | High-volume integrations |

---

## Configuration Validation Pattern

### During Startup

```python
# In main.py lifespan
from app.config.startup_validator import validate_startup_config

validate_startup_config()  # Exits with code 1 if invalid

# Validates:
# - Server port is in valid range (1-65535)
# - Vector dimension is between 1-4096
# - Primary key != vector field name
# - All required fields are set
# - All enum values are valid
```

### Adding Custom Validators

```python
from pydantic import field_validator
from app.config.appsettings import ServerConfig

class ServerConfig(BaseModel):
    port: int = Field(default=5001)
    
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v
```

---

## Connection Pool Pattern

### Automatic Cleanup

```python
from app.milvus.connection_pool import milvus_pool

# Connections are automatically reused from pool
client = milvus_pool.get_connection(
    uri="localhost:19530",
    user="root",
    password="password",
    database="default"
)

# Cleanup is done automatically in background task
# cleanup_connections() runs every 60 seconds
# AND when application shuts down: milvus_pool.close()
```

### Monitoring Pool Health

```python
# Get pool statistics
stats = milvus_pool.get_stats()
print(f"Active connections: {stats['active_connections']}/{stats['max_connections']}")
for conn in stats['connections']:
    print(f"  {conn['key']}: idle {conn['idle_seconds']}s")
```

---

## CORS and Security Pattern

### Using SecurityPatternMatcher

```python
from app.middleware.tenant_security import SecurityPatternMatcher

# Pattern matching examples
matcher = SecurityPatternMatcher()

# Wildcard matching
matcher.match_pattern("api.example.com", "*.example.com")  # True

# Regex matching
matcher.match_pattern("api-v2.example.com", "re:^api-v\\d+\\..*")  # True

# Check if origin is in allowed list
matcher.is_allowed(
    "https://app.example.com",
    ["https://app.example.com", "https://dev.example.com"]
)  # True
```

### Configuring CORS Origins

```python
# Via environment variables
export FLOUDS_CORS_ORIGINS="https://app.example.com,https://*.example.com,re:^.*localhost.*"

# Via database (after startup)
from app.services.config_service import config_service
config_service.set_cors_origins([
    "https://app.example.com",
    "*.example.com",
    "re:^.*localhost.*"
])
```

---

## Middleware Stack Order

The middleware stack is applied in this order (bottom to top = most to least restrictive):

```
App
├── RequestLoggingMiddleware        # Log all requests
├── ValidationMiddleware            # Validate request format
├── MetricsMiddleware              # Collect metrics
├── RateLimitMiddleware            # Check global rate limits
├── ErrorHandlerMiddleware         # Handle exceptions → JSON responses
├── AuthMiddleware                 # Validate authentication
├── TenantTrustedHostMiddleware    # Validate Host header
├── TenantCorsMiddleware           # Handle CORS
Router (endpoint logic)
```

### Request Flow Example

1. Browser sends `OPTIONS /api/data` request to check CORS
2. TenantCorsMiddleware checks if origin is allowed
3. If yes, returns 204 with CORS headers
4. Browser sends actual request
5. TenantTrustedHostMiddleware validates Host header
6. AuthMiddleware extracts and validates bearer token
7. Request reaches endpoint handler
8. @service_method catches any exceptions
9. RequestLoggingMiddleware logs response and timing

---

## Best Practices

### ✅ Do
- Use `@service_method` for all service layer methods
- Use `transactional_operation` for multi-step operations
- Log with `sanitize_for_log()` to prevent sensitive data leaks
- Call `validate_startup_config()` in application lifespan
- Use specific exception types instead of generic `Exception`

### ❌ Don't
- Catch exceptions without logging them
- Log raw user input without sanitization
- Use bare `dict` return types when `BaseResponse` exists
- Skip startup validation to speed up development
- Mix transaction logic with service method logic

---

## Troubleshooting

### Issue: "Rate limit exceeded" on all requests
**Solution**: Check that `cleanup_inactive_tenants()` is running in background cleanup task

### Issue: Connections never freed, eventual "pool full" error
**Solution**: Ensure connection pool close() is called in application shutdown

### Issue: Sensitive data in logs
**Solution**: Use `sanitize_dict_for_log()` with `redact_sensitive=True` (default)

### Issue: Configuration validation fails at startup
**Solution**: Run with debug output:
```bash
export FLOUDS_API_ENV="Development"
python -m app.main
```
Check configuration values for port (1-65535), dimension (1-4096), etc.
