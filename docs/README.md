# Flouds Vector API Documentation

This directory contains comprehensive API documentation for the Flouds Vector Database service.

## Documentation Files

### 💡 [API Examples](api-examples.md)
Practical examples and usage scenarios:
- Complete workflow examples
- cURL commands for all endpoints
- Python SDK example
- Error handling examples
- Real-world use cases

### 🧪 [Postman Collection](postman-collection.json)
Ready-to-use Postman collection for API testing

### 🔧 [Test Script](test-endpoints.sh)
Bash script to test all API endpoints

## Quick Start

1. **View Interactive Documentation (Swagger UI)**
   ```
   http://localhost:19680/api/v1/docs
   ```

2. **Access ReDoc Documentation**
   ```
   http://localhost:19680/api/v1/redoc
   ```

3. **Download OpenAPI Spec**
   ```
   http://localhost:19680/api/v1/openapi.json
   ```

## API Overview

### Base URL
- **Development**: `http://localhost:19680`
- **Production**: `https://api.flouds.com`

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer user:password
```
Vector store and user management endpoints also require a database credential header:
```
Flouds-VectorDB-Token: db_user|db_password
```

### API Versioning
All endpoints are versioned under `/api/v1/` for backward compatibility.

## Endpoint Categories

### 🏥 Health & Monitoring
- `GET /health` - Comprehensive health check
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/connections` - Connection pool statistics
- `GET /api/v1/metrics` - System performance metrics

### 🗄️ Vector Store Management
- `POST /api/v1/vector_store/set_vector_store` - Set up tenant database and user
- `POST /api/v1/vector_store/generate_schema` - Generate model-specific collections
- `POST /api/v1/vector_store/insert` - Insert vectors with metadata
- `POST /api/v1/vector_store/search` - Search vectors (dense/hybrid)

### 👥 User Management
- `POST /api/v1/vector_store_users/set_user` - Create/manage tenant users
- `POST /api/v1/vector_store_users/reset_password` - Reset user passwords

## Key Features

### 🔒 Security
- Bearer token authentication
- Multi-tenant data isolation
- Rate limiting (100 req/min per IP)
- Input validation and sanitization
- XSS and injection protection

### 🚀 Performance
- Connection pooling for Milvus
- Optimized RRF algorithm
- Configurable search parameters
- Efficient vector indexing

### 🔍 Search Capabilities
- **Dense Vector Search**: Semantic similarity using COSINE/L2/IP metrics
- **Sparse Vector Search**: BM25 keyword-based matching
- **Hybrid Search**: Combines dense and sparse with RRF scoring
- **Text Filtering**: Advanced text matching with stop word handling

### 🏗️ Architecture
- Model-specific collections (`vector_store_schema_for_{tenant}_{model}`)
- Thread-safe operations
- Comprehensive error handling
- Detailed logging and monitoring

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

## Rate Limiting

- **Global**: 100 requests per minute per IP address
- **Per-Tenant**: Configurable limits based on tenant tier
- **Headers**: Rate limit information in response headers

## Validation Rules

### Tenant Code
- Pattern: `^[a-zA-Z0-9_-]+$`
- Length: 1-256 characters
- Required for all operations

### Vector Dimensions
- Range: 1-4096
- Must be consistent within a model
- Validated on insert and search

### Model Names
- Length: 1-256 characters
- Alphanumeric with hyphens/underscores
- Used for collection naming

## Error Codes

| Code | Error Type | Description |
|------|------------|-------------|
| 400 | ValidationError | Invalid input parameters |
| 401 | AuthenticationError | Invalid/missing authentication |
| 403 | AuthorizationError | Insufficient permissions |
| 429 | RateLimitError | Rate limit exceeded |
| 500 | InternalServerError | Unexpected server error |
| 503 | ServiceUnavailableError | Milvus connection issues |

## Development Tools

### Generate Client SDKs
Use the built-in OpenAPI specification to generate client SDKs:

```bash
# Download OpenAPI spec first
curl http://localhost:19680/api/v1/openapi.json > openapi.json

# Python
openapi-generator generate -i openapi.json -g python -o clients/python

# JavaScript
openapi-generator generate -i openapi.json -g javascript -o clients/javascript

# Java
openapi-generator generate -i openapi.json -g java -o clients/java
```

### Test API Endpoints
```bash
# Using Newman (Postman CLI)
newman run docs/postman-collection.json

# Using curl with examples
bash docs/test-endpoints.sh
```

## Support

For questions, issues, or contributions:
- **GitHub Issues**: [Report bugs or request features](https://github.com/your-org/FloudsVector.Py/issues)
- **Documentation**: [Project README](../README.md)
- **Security**: [Security Policy](../SECURITY.md)
- **Contributing**: [Contribution Guidelines](../CONTRIBUTING.md)

## License

Copyright (c) 2024 Goutam Malakar. All rights reserved.

---

*Last updated: 2024-01-01*
