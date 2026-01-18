# Usage Examples

This guide shows how to use core features added or enhanced in this release:

- Tenant security helpers (CORS, trusted hosts)
- Transaction manager for multi-step operations
- Tenant rate limiter cleanup
- Log sanitization and audit logging
- Milvus connection pool lifecycle
- Configuration validation with Pydantic v2

## Tenant Security

### CORS Helpers

```python
from app.middleware.tenant_security import _cors_preflight, _apply_cors_headers
from starlette.responses import Response

def options_handler(origin: str) -> Response:
    # Preflight: returns 204 with CORS headers
    return _cors_preflight(origin)

def add_cors(response: Response, origin: str) -> None:
    # Append CORS headers to an existing response
    _apply_cors_headers(response, origin)
```

### Trusted Host Middleware

```python
from fastapi import FastAPI
from app.middleware.tenant_security import TenantTrustedHostMiddleware

app = FastAPI()
app.add_middleware(TenantTrustedHostMiddleware)
```

## Transaction Manager

Use the transactional context to coordinate multi-step operations with rollback.

```python
from app.modules.transaction_manager import transactional_operation

def insert_vectors(vectors):
    # insert into DB and return ids
    return [1, 2, 3]

def remove_vectors(ids):
    # rollback: remove inserted ids
    pass

def create_index(collection):
    # create index and return index name
    return "hnsw_1"

def drop_index(index_name):
    # rollback: drop index
    pass

with transactional_operation("create_and_index") as txn:
    txn.add_operation(insert_vectors, remove_vectors, vectors=[...])
    txn.add_operation(create_index, drop_index, collection="my_collection")
    results = txn.execute()
```

## Tenant Rate Limiter Cleanup

```python
from app.middleware.tenant_rate_limit import tenant_limiter

# Periodic cleanup (e.g., in a background task)
removed = tenant_limiter.cleanup_inactive_tenants(max_inactive_seconds=3600)
```

## Log Sanitization and Audit

```python
from app.utils.log_sanitizer import (
    LogLevel, sanitize_for_log, sanitize_dict_for_log, sanitize_for_audit, is_audit_event
)

safe_msg = sanitize_for_log("hello\nworld")
safe_dict = sanitize_dict_for_log({"password": "p@ss", "email": "a@b.com"})

audit_entry = sanitize_for_audit(
    event="USER_CREATED",
    data={"user_id": "123", "token": "abc"},
    user="admin",
    tenant="tenantA",
    details="provisioned via UI",
)

if is_audit_event("USER_CREATED"):
    # send audit_entry to audit log sink
    pass
```

## Connection Pool Lifecycle

```python
from app.milvus.connection_pool import milvus_pool

# Acquire connection
client = milvus_pool.get_connection(
    uri="http://127.0.0.1:19530", user="root", password="****", database="default"
)

# On shutdown (FastAPI lifespan or shutdown event)
milvus_pool.close()
```

## Configuration Validation

```python
from app.config.appsettings import AppSettings

settings = AppSettings()

# Cross-field validation
AppSettings.validate_all(settings)

# Pydantic field validators run at construction; invalid values raise ValueError
# Example invalid: default_dimension <= 0 or port not in 1..65535
```
