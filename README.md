# Flouds.VectorDB

Flouds.VectorDB is a FastAPI-based service for managing multi-tenant vector stores using Milvus as the backend. It provides APIs for creating tenants, managing users, and storing and searching vector embeddings with metadata.

**This is a new project and we are looking for collaborators!**  
If you are interested in vector databases, FastAPI, or scalable backend systems, your contributions are welcome.

---

## Features

- **Multi-tenant vector store management** with complete data isolation
- **User and role management** for each tenant with authentication
- **Hybrid search capabilities** combining dense and sparse vectors
- **Dense vector search** for semantic similarity using COSINE/L2/IP metrics
- **Sparse vector search** using BM25 for keyword-based matching
- **Reciprocal Rank Fusion (RRF)** for intelligent result combination
- **Advanced text filtering** with stop word handling and minimum word matching
- **Insert and search vector embeddings** with metadata support
- **RESTful API endpoints** with OpenAPI documentation
- **Milvus vector database backend** for high-performance similarity search
- **Production-ready middleware** (CORS, rate limiting, error handling, metrics)
- **API versioning** (`/api/v1/`) for backward compatibility
- **Docker containerization** with health checks
- **Configurable via JSON** and environment variables
- **Thread-safe and scalable** architecture

- **Tenant-scoped config caching:** Runtime caching for tenant-scoped configuration values (for example `cors_origins` and `trusted_hosts`) with automatic invalidation on write/delete operations to ensure changes take effect immediately.
- **Tenant header enforcement:** Non-public endpoints require the `X-Tenant-Code` header; handlers may omit `tenant_code` in request bodies because the service will resolve tenant context from the header or request state.
- **Optional tenant_code in requests:** `tenant_code` on base request models is optional and resolved from `X-Tenant-Code` when omitted.


---

## Project Structure

```
app/
  config/           # Configuration and settings
  milvus/           # Milvus integration and vector store logic
  models/           # Pydantic models for requests and responses
  modules/          # Utility modules (e.g., thread-safe dict)
  routers/          # FastAPI routers for API endpoints
  middleware/       # ASGI/Starlette middlewares (CORS, auth, rate limiting, etc.)
  services/         # Service layer for business logic
  utils/            # Utility functions
  main.py           # FastAPI app entry point
  logger.py         # Logging setup
  app_init.py       # App settings loader
  requirements.txt  # Python dependencies
tests/              # Pytest-based unit tests
```

---

Notable services and files:

- `app/services/config_service.py` — stores tenant-scoped configuration values (persisted in the `config_kv` table) and implements an in-memory, thread-safe cache with write-time invalidation.
- `app/middleware/` — tenant-aware and operational middlewares such as CORS, trusted-host enforcement, authentication/authorization, rate limiting, metrics, and request logging.
- `app/modules/key_manager.py` — manages client records and encryption of client secrets. KeyManager supports tenant-scoped clients and enforces tenant matching when a tenant is supplied to authentication calls.

Developer snippet: resolving tenant in handlers

```py
# Example: in a FastAPI route handler using a Pydantic `BaseRequest` subclass
def set_vector_store(request: Request, body: SetVectorStoreRequest):
  # resolve tenant from body or X-Tenant-Code header
  tenant = body.resolve_tenant(request)
  # proceed with tenant-scoped operation
```


## Configuration

### appsettings.json

All main configuration is handled via `app/config/appsettings.json`.  
You can set server type, host, port, logging, and Milvus options.

**Example:**
```json
{
    "app": {
        "name": "FloudsVectors",
        "default_executor_workers": 16
    },
    "server": {
        "host": "0.0.0.0",
        "port": 19680
    },
    "vectordb": {
        "endpoint": "localhost",
        "port": 19530,
        "username": "root",
        "password": "<your_milvus_password>",
        "password_file": "<path to password file>",
        "default_dimension": 384,
        "admin_role_name": "flouds_admin_role",
        "primary_key": "flouds_vector_id",
        "primary_key_data_type": "VARCHAR",
        "vector_field_name": "flouds_vector",
        "auto_flush_min_batch": 100,
        "index_params": {
            "nlist": 256,
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT"
        }
    },
    "logging": {
        "folder": "logs",
        "app_log_file": "flouds.log"
    },
    "security": {
        "enabled": true,
        "clients_db_path": "data/clients.db",
        "cors_origins": [
            "*"
        ],
        "trusted_hosts": [
            "*"
        ]
    }
}
```

You can override any setting using environment variables or the `.env` file.

---

### Config storage and caching

- Tenant-scoped configuration entries are persisted in the `config_kv` table and are managed by `app/services/config_service.py`.
- Certain configuration lists (notably `cors_origins` and `trusted_hosts`) are cached in-memory per-tenant for performance. The cache is invalidated automatically when configurations are added, updated, or deleted, so changes are applied immediately without polling.
- If you need immediate cross-process refresh in clustered deployments, consider using a distributed cache or publish/subscribe mechanism to notify other instances when config changes occur.

**Trusted Hosts & CORS Patterns**

- `trusted_hosts` and `cors_origins` accept simple patterns to provide flexible matching.
- Supported pattern formats:
  - Exact match: `example.com` or `https://app.example.com`
  - Wildcard: `*.example.com` — matches `example.com` and any subdomain like `api.example.com`.
  - Full wildcard: `*` — allow all hosts/origins.
  - Regex: prefix with `re:` and provide a full regular expression (for advanced cases). Example: `re:^(.+\.)?example\\.org$`.

- Notes:
  - Wildcard patterns support `*` as a glob-like wildcard. A pattern beginning with `*.` will match both the root domain and subdomains (e.g. `*.example.com` matches `example.com` and `api.example.com`).
  - Regex entries must be valid Python regular expressions and are evaluated with full-match semantics.
  - CORS origin checks consider both full origin strings (including scheme) and hostnames; configure entries accordingly.

Database schema note

- The `config_kv` table stores tenant-scoped entries. It is modeled as a composite primary key on `(key, tenant_code)` with columns similar to:

```sql
CREATE TABLE IF NOT EXISTS config_kv (
  key TEXT NOT NULL,
  tenant_code TEXT NOT NULL DEFAULT '',
  value TEXT,
  encrypted INTEGER DEFAULT 0,
  PRIMARY KEY (key, tenant_code)
);
```

Multi-instance considerations

- Cache is currently in-memory per process. For high-availability or horizontally scaled deployments use a shared cache (Redis, Memcached) or publish/subscribe notifications so other instances can invalidate their local cache on writes.


## Requirements

- **Python 3.9+**
- **Milvus 2.3+** (standalone or cluster)
- **Docker** (optional, for containerized deployment)
- See [app/requirements.txt](app/requirements.txt) for Python dependencies
- [Uvicorn](https://www.uvicorn.org/) ASGI server (included)

---

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-org/FloudsVector.Py.git
   cd FloudsVector.Py
   ```

2. **Install dependencies:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r app/requirements.txt
   ```

  On Windows PowerShell, we ship an updated `Activate.ps1` that also sets the
  `FLOUDS_API_ENV` to `Development` for convenience. To ensure the environment
  variable is applied to your current session, dot-source the script instead of
  invoking it with `&`:

  ```powershell
  # Dot-source so session variables are applied
  . .\.venv\Scripts\Activate.ps1
  ```
  If you prefer the call operator, run `& .\.venv\Scripts\Activate.ps1` but
  note some shells may not propagate the `FLOUDS_API_ENV` process variable to
  the interactive session.

3. **Configure settings:**
   - Edit [app/config/appsettings.json](app/config/appsettings.json) for your Milvus and server settings.
   - Optionally, create environment-specific overrides such as [app/config/appsettings.development.json](app/config/appsettings.development.json).
   - You can override any setting using environment variables or the `.env` file.

4. **Run the server:**
   ```sh
   python -m app.main
   ```
   Or with Uvicorn:
   ```sh
   uvicorn app.main:app --host 0.0.0.0 --port 19680 --reload
   ```

---

## Environment Variables and .env File

The `.env` file is used to configure environment variables for the container, including Milvus connection details, logging paths, and other settings.

**Environment Setup:**
```bash
# Copy template and customize
cp .env.template .env

# Or use example for development
cp .env.example .env
```

**Example `.env` for development:**
```
FLOUDS_API_ENV=Development
APP_DEBUG_MODE=1
VECTORDB_USERNAME=root
VECTORDB_PASSWORD=<your_milvus_password>
VECTORDB_CONTAINER_NAME=localhost
VECTORDB_PORT=19530
VECTORDB_NETWORK=milvus_network
VECTORDB_PASSWORD_FILENAME=<password file name>
FLOUDS_LOG_PATH=./logs
FLOUDS_SECURITY_ENABLED=true
FLOUDS_CLIENTS_DB_FILENAME=clients.db
```

- The `.env` file allows you to configure the container without modifying code or the Dockerfile.
- It is used to set environment variables for Milvus connection, logging, debug mode, and other runtime options.
- You can keep different `.env` files for development, testing, and production.
- The container will read this file at startup and apply the settings automatically.

Note about activation: the PowerShell activation script (`.venv\Scripts\Activate.ps1`)
now sets `FLOUDS_API_ENV=Development` when activated (dot-sourced). If you use
VS Code, ensure the setting `python.terminal.activateEnvironment` is enabled so
the editor's integrated terminal applies the venv activation correctly.

---

## API Endpoints

All endpoints are versioned under `/api/v1/` and require authentication via `Authorization: Bearer user:password` header. Vector store and user management endpoints also require a database credential header: `Flouds-VectorDB-Token: db_user|db_password` (or `db_user:db_password`).

### Vector Store Operations

- `POST /api/v1/vector_store/set_vector_store` - Create or retrieve a vector store for a tenant
- `POST /api/v1/vector_store/generate_schema` - Generate custom schema for tenant with specific parameters
- `POST /api/v1/vector_store/insert` - Insert embedded vectors with metadata
- `POST /api/v1/vector_store/search` - Search for similar vectors using cosine/L2 similarity

### User Management

- `POST /api/v1/vector_store_users/set_user` - Create or manage tenant users
- `POST /api/v1/vector_store_users/reset_password` - Reset user passwords

### Monitoring

- `GET /health` - Health check endpoint
- `GET /api/v1/metrics` - System metrics and performance data
- `GET /docs` - Interactive API documentation (Swagger UI)

### Config Management API

- **Prefix:** `/api/v1/config`
- **Purpose:** manage tenant-scoped configuration entries (admin-only). These configuration entries are persisted in the `config_kv` table and are used by runtime middleware for CORS and Trusted Host enforcement.
- **Endpoints:**
  - `POST /api/v1/config/add` — create a new config entry. Body fields: `key`, `value`, `tenant_code` (optional; header overrides), `encrypted` (bool).
  - `GET /api/v1/config/get?key=...&tenant_code=...` — retrieve config meta. Encrypted values return `"value": "<encrypted>"` (the service never returns ciphertext in the API).
  - `PUT /api/v1/config/update` — update an existing entry. Body must include `key`, `tenant_code`, and `value` (optional `encrypted`).
  - `DELETE /api/v1/config/delete` — delete an entry by composite PK.

**Notes:**
- Admin access is required (use `Authorization: Bearer <admin_token>`). Include `X-Tenant-Code` header when appropriate.
- Example: create a CORS origins entry for tenant `mytenant`:

```sh
curl -X POST http://localhost:19680/api/v1/config/add \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -H "X-Tenant-Code: mytenant" \
  -d '{"key":"cors_origins","value":"[\"https://app.example.com\"]","encrypted":false}'
```

---

## How to Call the API

You can use `curl`, `httpie`, or any HTTP client to call the endpoints.  
All API endpoints are versioned under `/api/v1/`. Below are some example requests:

### 1. Health Check

```sh
curl http://localhost:19680/health
```

### 2. Create or Get a Vector Store

```sh
curl -X POST http://localhost:19680/api/v1/vector_store/set_vector_store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -H "Flouds-VectorDB-Token: root|<your_milvus_password>" \
  -H "X-Tenant-Code: mytenant" \
  -d '{
    "tenant_code": "mytenant"  # optional when X-Tenant-Code header is provided
  }'
```

### 3. Generate Custom Schema

```sh
curl -X POST http://localhost:19680/api/v1/vector_store/generate_schema \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -H "Flouds-VectorDB-Token: root|<your_milvus_password>" \
  -d '{
    "tenant_code": "mytenant",
    "model_name": "sentence-transformers",
    "dimension": 384,
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "nlist": 1024,
    "metadata_length": 4096,
    "drop_ratio_build": 0.1
  }'
```

### 4. Insert Embedded Vectors

```sh
curl -X POST http://localhost:19680/api/v1/vector_store/insert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -H "Flouds-VectorDB-Token: user|user_password" \
  -H "X-Tenant-Code: mytenant" \
  -d '{
    "tenant_code": "mytenant",  # optional when X-Tenant-Code header is provided
    "data": [
      {
        "key": "doc_001",
        "chunk": "This is a test.",
        "model": "sentence-transformers",
        "metadata": {"source": "test"},
        "vector": [0.1, 0.2, 0.3, ...]
      }
    ]
  }'
```

### 5. Search Embedded Vectors (Dense Search)

```sh
curl -X POST http://localhost:19680/api/v1/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -H "Flouds-VectorDB-Token: user|user_password" \
  -H "X-Tenant-Code: mytenant" \
  -d '{
    "tenant_code": "mytenant",  # optional when X-Tenant-Code header is provided
    "model": "sentence-transformers",
    "limit": 10,
    "score_threshold": 0.0,
    "metric_type": "COSINE",
    "hybrid_search": false,
    "vector": [0.1, 0.2, 0.3, ...]
  }'
```

### 6. Hybrid Search (Dense + Sparse)

```sh
curl -X POST http://localhost:19680/api/v1/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -H "Flouds-VectorDB-Token: user|user_password" \
  -H "X-Tenant-Code: mytenant" \
  -d '{
    "tenant_code": "mytenant",  # optional when X-Tenant-Code header is provided
    "model": "sentence-transformers",
    "limit": 10,
    "score_threshold": 0.0,
    "metric_type": "COSINE",
    "hybrid_search": true,
    "text_filter": "invoice billed to customer",
    "minimum_words_match": 2,
    "include_stop_words": false,
    "vector": [0.1, 0.2, 0.3, ...]
  }'
```

### 7. Create or Set a User

```sh
curl -X POST http://localhost:19680/api/v1/vector_store_users/set_user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -H "Flouds-VectorDB-Token: root|<your_milvus_password>" \
  -H "X-Tenant-Code: mytenant" \
  -d '{
    "tenant_code": "mytenant"  # optional when X-Tenant-Code header is provided
  }'
```

---

## Docker Usage

Flouds.VectorDB is available as a pre-built image on [Docker Hub](https://hub.docker.com/r/gmalakar/flouds-vector).

### Option 1: Production Deployment (Recommended)

Use this when you have an existing Milvus instance or want manual control.

#### 1. Pull the Docker image
```sh
docker pull gmalakar/flouds-vector:latest
```

#### 2. Build locally (optional)
```sh
# Using PowerShell script
./build-flouds-vector.ps1

# Or manually
docker build -t floudsvectors-py .
```

#### 3. Start with helper scripts
```sh
# Windows
./start-flouds-vectordb.ps1

# Linux/macOS
./start-flouds-vectordb.sh
```

**Prerequisites:** Milvus must be running separately (see `/milvus` folder for scripts).

### Option 2: Complete Development Stack

Use this for local development or when you need everything in one command.

```sh
# Start complete stack (Milvus + FloudsVector)
docker-compose up -d

# Stop everything
docker-compose down
```

This includes:
- Milvus vector database
- etcd (Milvus dependency)
- MinIO (Milvus storage)
- FloudsVector API

### Configuration

- **Port**: 19680 (API), 19530 (Milvus)
- **Environment**: Use `.env` file or environment variables
- **Logs**: Mounted to host for persistence
- **Health Check**: Built-in Docker health monitoring

---

**When to use which:**
- **PowerShell scripts**: Production deployment to existing Milvus infrastructure
- **Docker Compose**: Local development, testing, or complete stack deployment
- **Manual Docker**: Custom deployments or Kubernetes

### Environment Variables

Key configuration options:
```bash
# Milvus Connection
VECTORDB_CONTAINER_NAME=localhost
VECTORDB_PORT=19530
VECTORDB_USERNAME=root
VECTORDB_PASSWORD=<your_milvus_password>
VECTORDB_NETWORK=milvus_network

# Security (alternative to password)
VECTORDB_PASSWORD_FILE=/app/secrets/password.txt

# API Configuration
FLOUDS_API_ENV=Production
APP_DEBUG_MODE=0

# Logging
FLOUDS_LOG_PATH=/var/log/flouds
```

---

## Logging

Logs are written to the `/var/log/flouds` directory inside the container and can be mapped to your host for persistence.  
Configure log file and level in [app/config/appsettings.json](app/config/appsettings.json) or via environment variables.

---

## Development

### Testing
```sh
# Install development dependencies
pip install -r app/requirements-dev.txt

# Run tests with coverage
pytest tests/ --cov=app

# Code formatting
black app/
isort app/
```

Testing notes

- If you run integration tests locally with `TestClient`, the client uses host `testserver` which may be rejected by TrustedHost middleware unless `trusted_hosts` for the tenant includes `testserver`. If you see "Invalid Host header" in tests, seed `trusted_hosts` for the test tenant or set `FLOUDS_TRUSTED_HOSTS="testserver"` when running tests.
- Some TestClient versions treat `DELETE` requests differently; prefer `client.request("DELETE", "/path", json={...})` in tests when passing a JSON body.

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and [SECURITY.md](SECURITY.md) for security policies.

---

## Production Features

### Security & Authentication
- **Bearer token authentication** (`Authorization: Bearer user:password`)
- **Multi-tenant isolation** with role-based access control
- **Rate limiting** (100 requests/minute per IP)
- **CORS support** for web frontend integration
- **Enhanced exception handling** with custom exception classes
- **Input sanitization** for XSS prevention
- **Optimized performance** with improved algorithms

### Monitoring & Observability
- **Health checks** with Milvus connectivity status
- **Performance metrics** with request timing
- **Comprehensive logging** with configurable levels
- **Docker health checks** for container orchestration

### Development & Deployment
- **API versioning** for backward compatibility
- **Environment-based configuration** (Development/Production)
- **Docker containerization** with multi-stage builds
- **Thread-safe architecture** for concurrent operations

### Security & Code Quality Improvements

#### ✅ **Recently Implemented**
- **Custom Exception Handling**: 13 specific exception classes for better error categorization
- **XSS Prevention**: Input sanitization in password policy error messages
- **Performance Optimization**: Optimized RRF (Reciprocal Rank Fusion) algorithm
- **Import Optimization**: Specific imports instead of broad imports for better performance
- **Thread-Safe Architecture**: Improved concurrent operation handling

#### ⚠️ **Security Issues Requiring Attention**
- **Log Injection**: Multiple files need `sanitize_for_log()` for user inputs in logs
- **Path Traversal**: Config loader needs path validation using `safe_join()`
- **Remaining XSS**: One instance in `base_milvus.py` needs sanitization

### Recent Updates (v1.1.0)

#### ✅ **Schema Generation Improvements**
- **Custom Schema Generation**: New `/generate_schema` endpoint for creating collections with specific parameters
- **Flexible Vector Dimensions**: Support for custom vector dimensions per model/tenant
- **Index Optimization**: Removed model field indexing for better performance and compatibility
- **Permission Management**: Enhanced tenant role privileges including Upsert permissions

#### ✅ **API Simplification**
- **Streamlined Vector Store Setup**: Removed unused `vector_dimension` parameter from `set_vector_store`
- **Model-Agnostic Operations**: Insert and search operations no longer depend on model field filtering
- **Improved Error Handling**: Better error messages for schema generation and permission issues

#### ✅ **Code Quality & Testing**
- **Python 3.9 Compatibility**: Fixed syntax issues for better compatibility
- **Enhanced Test Coverage**: All 48 tests passing with improved fixtures
- **Dependency Management**: Added missing dependencies (werkzeug, psutil)
- **Code Cleanup**: Removed unused methods, parameters, and imports
- **Import Optimization**: Removed all unused imports identified by flake8
- **Rate Limiting Fix**: Fixed broken dependency injection in tenant rate limiting
- **Configuration Validation**: Enhanced null value handling in config validation

### Key Notes
- **Super user required** for tenant and vector store creation
- **Custom schema generation** allows per-tenant/model configuration
- **Hybrid search** combines semantic (dense) and keyword (sparse) matching
- **BM25 sparse vectors** automatically generated during data insertion
- **RRF scoring** intelligently combines dense and sparse search results
- **Collection-specific permissions** automatically granted to tenant users
- **Environment variables** override JSON configuration
- **Uvicorn ASGI server** for high performance

---

## License

Copyright (c) 2024 Goutam Malakar.  
All rights reserved.

---

*For more details, see the code and comments in each module.*

**Interested in collaborating? Please open an issue or pull request!**