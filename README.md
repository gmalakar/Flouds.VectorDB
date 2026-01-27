# FloudsVector

**FloudsVector** is an enterprise-grade multi-tenant vector database service built on FastAPI and Milvus, providing production-grade APIs for semantic search, hybrid retrieval, and vector store management with comprehensive monitoring and security.

> **Note:** This is an active project looking for collaborators! If you're interested in vector databases, FastAPI, or scalable backend systems, contributions are welcome.

## Key Features

### 🔍 Vector Search
- **Dense Vector Search** – COSINE, L2, and IP distance metrics with configurable indices
- **Sparse Vector Search (BM25)** – Built-in BM25 keyword matching via `pymilvus[model]`
- **Hybrid Search with RRF** – Reciprocal Rank Fusion combining dense + sparse results
- **Advanced Filtering** – Stop word handling, minimum word matching, metadata filtering
- **Semantic Similarity** – High-performance similarity search at scale
- **Multi-collection Support** – Model-specific collections with automatic schema generation
- **NLTK Integration** – Automatic punkt_tab download for text tokenization

### 🏢 Multi-Tenancy
- **Complete Data Isolation** – Tenant-scoped collections and metadata
- **User & Role Management** – Authentication and authorization per tenant
- **Tenant-Aware Caching** – In-memory cache with automatic invalidation
- **Dynamic Configuration** – Runtime config changes without restart
- **CORS & Trusted Hosts** – Tenant-specific security policies with pattern matching (wildcards & regex)

### 🚀 Enterprise Features
- **High-Performance Backend** – Milvus 2.3+ for scalable similarity search
- **Multi-Tenant Architecture** – Horizontal scaling with tenant isolation
- **Production Middleware** – CORS, rate limiting, error handling, metrics collection
- **RESTful API** – OpenAPI documentation with versioning (`/api/v1/`)
- **Thread-Safe Design** – Concurrent request handling and state management
- **Docker Ready** – Multi-stage builds with health checks and orchestration
- **Comprehensive Monitoring** – Performance metrics, connection pooling, detailed logging

## Overview

Professional multi-tenant vector database service built on FastAPI and Milvus for production deployment of semantic search, vector embeddings, and hybrid retrieval with enterprise-grade monitoring and security.

## Quick Start

### Local Development

1. **Setup environment:**
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Unix/Linux

pip install -r app/requirements.txt
```

2. **Start Milvus (Docker):**
```bash
docker-compose up -d milvus
```

3. **Start the server:**
```bash
python -m app.main
```

Server runs on `http://localhost:19680` with API docs at `/api/v1/docs`

### Docker Deployment

**Build and run (with no-cache by default):**
```bash
.\build-flouds-vector.ps1
docker-compose up -d
```

**Or build manually:**
```bash
docker build --no-cache -t flouds-vector:latest .
docker run -p 19680:19680 \
  -e VECTORDB_CONTAINER_NAME=milvus-server \
  -e VECTORDB_PORT=19530 \
  flouds-vector:latest
```

**Docker Image Details:**
- Base: Python 3.12-slim (Debian)
- Runtime: FastAPI + Uvicorn
- BM25/Sparse: pymilvus[model] with BM25EmbeddingFunction
- Health checks enabled
- Multi-stage build for optimized size

### PowerShell Deployment

**Start with automatic dependencies:**
```powershell
.\start-flouds-vectordb.ps1 -Port 19680 -MilvusEndpoint localhost -MilvusPort 19530
```

## Installation

### Requirements
- **Python**: 3.10+ (3.12 recommended for Docker builds)
- **Milvus**: 2.3+ with sparse vector support
- **System**: 4GB+ RAM, Docker (optional)

### Setup Steps

1. **Check Python version:**
```bash
python --version  # Should be 3.10 or higher
```

2. **Install runtime dependencies:**
```bash
pip install -r app/requirements.txt
```

3. **Install development tools (optional):**
```bash
pip install -r requirements-dev.txt
```

### Key Dependencies
- **fastapi** (≥0.116.1) – Modern web framework
- **pymilvus[model]** (≥2.4.4) – Milvus client with BM25 support
- **uvicorn[standard]** (≥0.32.0) – ASGI server
- **pydantic** (≥2.10.0) – Data validation
- **nltk** (≥3.9) – Natural language processing
- **cryptography** (≥42.0.0) – Encryption
- **requests** (≥2.31.0) – HTTP client

## Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `FloudsVectors` | Application name |
| `SERVER_HOST` | `0.0.0.0` | Server host binding |
| `SERVER_PORT` | `19680` | Server port |
| `VECTORDB_CONTAINER_NAME` | `localhost` | Milvus server endpoint |
| `VECTORDB_PORT` | `19530` | Milvus server port |
| `VECTORDB_USERNAME` | `root` | Milvus username |
| `VECTORDB_PASSWORD` | (required) | Milvus password |
| `DEFAULT_DIMENSION` | `384` | Default vector dimension |
| `METRIC_TYPE` | `COSINE` | Distance metric (COSINE, L2, IP) |
| `INDEX_TYPE` | `IVF_FLAT` | Milvus index type |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SECURITY_ENABLED` | `true` | Enable authentication |
| `CORS_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `TRUSTED_HOSTS` | `*` | Trusted hosts (comma-separated, supports wildcards) |

### appsettings.json

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
        "password": "your-password",
        "default_dimension": 384,
        "primary_key": "flouds_vector_id",
        "vector_field_name": "flouds_vector",
        "index_params": {
            "nlist": 256,
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT"
        }
    },
    "security": {
        "enabled": true,
        "cors_origins": ["*"],
        "trusted_hosts": ["*"]
    }
}
```

## API Endpoints

### Base URL
- **Development**: `http://localhost:19680`
- **Production**: `https://api.flouds.com`

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer user:password
```

Vector store and user management endpoints also require database credentials:
```
Flouds-VectorDB-Token: db_user|db_password
```

### Health & Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Comprehensive health status |
| `GET` | `/api/v1/health/ready` | Kubernetes readiness probe (Milvus connection check) |
| `GET` | `/api/v1/health/live` | Kubernetes liveness probe |
| `GET` | `/api/v1/health/connections` | Connection pool statistics |
| `GET` | `/api/v1/metrics` | Prometheus-compatible performance metrics |

### Vector Store Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vector/set_vector_store` | Set up tenant database and collections |
| `POST` | `/api/v1/vector/generate_schema` | Generate model-specific collection schema |
| `POST` | `/api/v1/vector/insert` | Insert vectors with metadata |
| `POST` | `/api/v1/vector/search` | Search vectors (dense/sparse/hybrid with RRF) |
| `POST` | `/api/v1/vector/flush` | Flush data to disk for persistence |

### User Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/user/set_user` | Create or update tenant user |
| `POST` | `/api/v1/user/reset_password` | Reset user password |

### Configuration Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/config/add` | Add new configuration entry |
| `GET` | `/api/v1/config/get` | Retrieve configuration value |
| `PUT` | `/api/v1/config/update` | Update configuration entry |
| `DELETE` | `/api/v1/config/delete` | Delete configuration entry |

### Administration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/fingerprints` | Get client fingerprints for audit |

### Interactive Documentation
- **Swagger UI**: `http://localhost:19680/api/v1/docs`
- **ReDoc**: `http://localhost:19680/api/v1/redoc`
- **OpenAPI Spec**: `http://localhost:19680/api/v1/openapi.json`

## Project Structure

```
FloudsVector.Py/
├── app/
│   ├── config/
│   │   ├── appsettings.json              # Application configuration
│   │   └── config_loader.py              # Configuration loader
│   ├── middleware/
│   │   ├── cors.py                       # Tenant-aware CORS
│   │   ├── auth.py                       # Authentication/authorization
│   │   ├── rate_limit.py                 # Rate limiting
│   │   └── tenant_security.py            # Tenant header enforcement
│   ├── milvus/
│   │   ├── vector_store.py              # Milvus integration
│   │   └── connection_pool.py           # Connection pooling
│   ├── models/                          # Pydantic request/response models
│   ├── routers/
│   │   ├── vector.py                    # Vector store endpoints
│   │   ├── user.py                      # User management
│   │   ├── config.py                    # Configuration CRUD
│   │   ├── health.py                    # Health checks
│   │   ├── metrics.py                   # Prometheus metrics
│   │   └── admin.py                     # Administration
│   ├── services/
│   │   ├── vector_service.py            # Vector search logic
│   │   ├── config_service.py            # Configuration management
│   │   └── auth_service.py              # Authentication service
│   ├── modules/
│   │   ├── transaction_manager.py       # Multi-step transactions with rollback
│   │   ├── key_manager.py               # Client key management
│   │   └── thread_safe_dict.py          # Thread-safe data structures
│   ├── utils/
│   │   ├── log_sanitizer.py             # Log injection prevention
│   │   ├── error_handler.py             # Error handling utilities
│   │   └── cache_manager.py             # Cache operations
│   ├── main.py                          # FastAPI application entry
│   ├── app_init.py                      # App initialization
│   ├── logger.py                        # Logging setup
│   └── requirements.txt                 # Python dependencies
├── docs/
│   ├── api-examples.md                  # API examples and cURL commands
│   ├── USAGE_EXAMPLES.md                # Copy-paste examples for common tasks
│   └── postman-collection.json          # Postman API collection
├── tests/                               # Pytest test suite
├── Dockerfile                           # Container image
├── docker-compose.yml                   # Multi-service orchestration
├── pyproject.toml                       # Project metadata
├── pytest.ini                           # Pytest configuration
└── README.md                            # This file
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[API Examples](docs/api-examples.md)** – Practical examples and cURL commands
- **[Usage Examples](docs/USAGE_EXAMPLES.md)** – Copy-paste examples for common tasks
- **[Postman Collection](docs/postman-collection.json)** – Ready-to-use API collection

## Key Concepts

### Multi-Tenancy

All data is isolated per tenant using the `X-Tenant-Code` header:

```bash
curl -X POST "http://localhost:19680/api/v1/vector/insert" \
  -H "X-Tenant-Code: tenant-123" \
  -H "Authorization: Bearer user:password" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Hybrid Search

Combine dense and sparse vectors with Reciprocal Rank Fusion:

```bash
curl -X POST "http://localhost:19680/api/v1/vector/search" \
  -H "X-Tenant-Code: tenant-123" \
  -H "Authorization: Bearer user:password" \
  -H "Content-Type: application/json" \
  -d '{
    "dense_vector": [...],
    "sparse_vector": {...},
    "metric_type": "COSINE",
    "top_k": 10
  }'
```

### Transaction Management

Multi-step operations with automatic rollback:

```python
from app.modules.transaction_manager import TransactionManager

with TransactionManager(tenant_code="tenant-123") as tm:
    tm.insert_vectors(...)
    tm.update_metadata(...)
    tm.search(...)  # All commit or all rollback on error
```

## Request/Response Format

### Standard Request
```json
{
  "tenant_code": "mytenant",
  "model_name": "sentence-transformers",
  "data": [...]
}
```

### Standard Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": {...}
}
```

### Error Response
```json
{
  "error": "ValidationError",
  "message": "Invalid input parameters",
  "details": {"field": "tenant_code", "issue": "required field missing"},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Validation Rules

### Tenant Code
- Pattern: `^[a-zA-Z0-9_-]+$`
- Length: 1-256 characters
- Required for all operations

### Vector Dimensions
- Range: 1-4096 dimensions
- Must be consistent within a model
- Default: 384 dimensions

### Model Names
- Length: 1-256 characters
- Alphanumeric with hyphens/underscores
- Used for collection naming

## Error Codes

| Code | Error Type | Description |
|------|------------|-------------|
| 400 | ValidationError | Invalid input parameters |
| 401 | AuthenticationError | Invalid or missing authentication token |
| 403 | AuthorizationError | Insufficient permissions for operation |
| 429 | RateLimitError | Rate limit exceeded (100 req/min per IP) |
| 500 | InternalServerError | Unexpected server error |
| 503 | ServiceUnavailableError | Milvus connection unavailable |

## Security

### Authentication & Authorization
- **Token-based security** with client key management
- **Tenant isolation** – Strict data separation per tenant
- **Role-based access control** – Admin and user roles
- **Encrypted credentials** – Secure client secret storage

### Configuration Security
- **Tenant-scoped configs** – Separate settings per tenant
- **Pattern matching** – CORS and trusted hosts with wildcard/regex support
- **Log sanitization** – Prevent log injection attacks
- **Request validation** – Size limits and timeout handling

## Performance & Scalability

### Optimization Strategies
- **Connection pooling** – Efficient Milvus connection management
- **In-memory caching** – Tenant-scoped configuration caching
- **Batch operations** – Efficient bulk insert/search
- **Index tuning** – Configurable index types and parameters
- **Rate limiting** – Request throttling and backpressure

### Scaling Options
- **Horizontal scaling** – Multiple instances behind load balancer
- **Milvus clustering** – Distributed vector database backend
- **Distributed caching** – Redis/Memcached for cross-instance cache
- **Connection pooling** – Automatic connection reuse and limits

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused: Milvus` | Verify Milvus is running and accessible at configured endpoint:port |
| `Authentication failed` | Check tenant code in `X-Tenant-Code` header and verify credentials |
| `Collection not found` | Create collection with `/api/v1/vector/set_vector_store` first |
| `Vector dimension mismatch` | Ensure vector dimension matches collection schema (default: 384) |
| `Rate limit exceeded` | Reduce request rate or configure higher limits in appsettings.json |
| `Out of memory` | Reduce batch size, enable pagination, or scale Milvus cluster |
| `Search timeout` | Increase search timeout in config or optimize index parameters |

## Development

### Run Tests
```bash
pytest tests/ -v
pytest tests/ -v --cov=app  # with coverage
```

### Code Quality
```bash
black app/                    # Format code
isort app/                    # Sort imports
pylint app/                   # Linting
mypy app/                     # Type checking
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## Logging

Logs are saved to `logs/` directory with configurable levels:

- **DEBUG** – Detailed diagnostic information
- **INFO** – General operational messages
- **WARNING** – Warning messages
- **ERROR** – Error messages with context

Configure via `LOG_LEVEL` environment variable or `appsettings.json`.

## Requirements

- **Python**: 3.9 or later
- **Milvus**: 2.3 or later (standalone or cluster)
- **Dependencies**: See `app/requirements.txt`
- **System**: ≥4 GB RAM (8+ GB recommended for production)

## Deployment

### Production Checklist
- [ ] Set `SECURITY_ENABLED=true`
- [ ] Configure strong Milvus password
- [ ] Set appropriate `CORS_ORIGINS` and `TRUSTED_HOSTS`
- [ ] Enable HTTPS via reverse proxy
- [ ] Configure log rotation
- [ ] Setup resource limits (memory, CPU)
- [ ] Monitor `/api/v1/metrics` endpoint
- [ ] Setup alerting for health check failures
- [ ] Test graceful shutdown

### High Availability
- Deploy multiple instances behind load balancer
- Use Milvus cluster for distributed backend
- Implement distributed cache for config sharing
- Setup monitoring and alerting

## License

See LICENSE file.

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.
