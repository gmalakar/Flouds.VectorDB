# API Examples

This document provides practical examples for using the Flouds Vector API endpoints.

## Authentication

All API endpoints require Bearer token authentication:

```bash
Authorization: Bearer user:password
```

## Base URL

- Development: `http://localhost:19680`
- Production: `https://api.flouds.com`

## Health Check Endpoints

### Basic Health Check

```bash
curl http://localhost:19680/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "milvus": {
    "connected": true,
    "version": "2.3.0",
    "response_time": 15.2
  },
  "system": {
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "disk_usage": 60.1
  },
  "configuration": {
    "valid": true,
    "errors": []
  }
}
```

### Connection Pool Statistics

```bash
curl http://localhost:19680/health/connections
```

**Response:**
```json
{
  "active_connections": 5,
  "idle_connections": 3,
  "total_connections": 8,
  "max_connections": 20
}
```

## Vector Store Management

### 1. Set Up Vector Store (Database and User)

```bash
curl -X POST http://localhost:19680/api/v1/vector_store/set_vector_store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant",
    "vector_dimension": 384
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Vector store setup completed successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": {
    "database_created": true,
    "user_created": true,
    "permissions_granted": true
  }
}
```

### 2. Generate Schema (Collections and Indexes)

```bash
curl -X POST http://localhost:19680/api/v1/vector_store/generate_schema \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant",
    "model_name": "sentence-transformers",
    "dimension": 384,
    "nlist": 1024,
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "metadata_length": 4096
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Schema generated successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": {
    "collection_name": "vector_store_schema_for_mytenant_sentence-transformers",
    "collection_created": true,
    "index_created": true,
    "permissions_granted": true
  }
}
```

### 3. Insert Vectors

```bash
curl -X POST http://localhost:19680/api/v1/vector_store/insert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -d '{
    "tenant_code": "mytenant",
    "model_name": "sentence-transformers",
    "data": [
      {
        "key": "doc_001",
        "chunk": "This is a sample document about machine learning and artificial intelligence.",
        "model": "sentence-transformers",
        "metadata": {
          "source": "research_paper",
          "category": "AI",
          "author": "John Doe",
          "date": "2024-01-01"
        },
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
      },
      {
        "key": "doc_002",
        "chunk": "Vector databases are essential for similarity search in modern applications.",
        "model": "sentence-transformers",
        "metadata": {
          "source": "blog_post",
          "category": "Database",
          "author": "Jane Smith",
          "date": "2024-01-02"
        },
        "vector": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
      }
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "2 vectors inserted successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 4. Dense Vector Search

```bash
curl -X POST http://localhost:19680/api/v1/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -d '{
    "tenant_code": "mytenant",
    "model": "sentence-transformers",
    "limit": 10,
    "score_threshold": 0.7,
    "metric_type": "COSINE",
    "hybrid_search": false,
    "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Search completed successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": [
    {
      "id": "doc_001",
      "score": 0.95,
      "chunk": "This is a sample document about machine learning and artificial intelligence.",
      "meta": {
        "source": "research_paper",
        "category": "AI",
        "author": "John Doe",
        "date": "2024-01-01"
      }
    },
    {
      "id": "doc_002",
      "score": 0.87,
      "chunk": "Vector databases are essential for similarity search in modern applications.",
      "meta": {
        "source": "blog_post",
        "category": "Database",
        "author": "Jane Smith",
        "date": "2024-01-02"
      }
    }
  ],
  "total_count": 2,
  "search_time": 12.5
}
```

### 5. Hybrid Search (Dense + Sparse)

```bash
curl -X POST http://localhost:19680/api/v1/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -d '{
    "tenant_code": "mytenant",
    "model": "sentence-transformers",
    "limit": 10,
    "score_threshold": 0.5,
    "metric_type": "COSINE",
    "hybrid_search": true,
    "text_filter": "machine learning artificial intelligence",
    "minimum_words_match": 2,
    "include_stop_words": false,
    "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Hybrid search completed successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": [
    {
      "id": "doc_001",
      "score": 0.98,
      "chunk": "This is a sample document about machine learning and artificial intelligence.",
      "meta": {
        "source": "research_paper",
        "category": "AI",
        "author": "John Doe",
        "date": "2024-01-01"
      }
    }
  ],
  "total_count": 1,
  "search_time": 18.3
}
```

## User Management

### 1. Create User

```bash
curl -X POST http://localhost:19680/api/v1/vector_store_users/set_user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User created successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "results": {
    "username": "mytenant_user",
    "password": "generated_password_123",
    "role": "mytenant_role"
  }
}
```

### 2. Reset Password

```bash
curl -X POST http://localhost:19680/api/v1/vector_store_users/reset_password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset successfully",
  "tenant_code": "mytenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "new_password": "new_generated_password_456"
}
```

## Error Responses

### Validation Error

```json
{
  "error": "ValidationError",
  "message": "Invalid input parameters",
  "details": {
    "field": "vector_dimension",
    "issue": "must be between 1 and 4096"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Authentication Error

```json
{
  "error": "AuthenticationError",
  "message": "Invalid or missing authentication token",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Rate Limit Error

```json
{
  "error": "RateLimitError",
  "message": "Rate limit exceeded. Please try again later.",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Internal Server Error

```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Complete Workflow Example

Here's a complete workflow for setting up a tenant and performing vector operations:

```bash
# 1. Set up vector store (database and user)
curl -X POST http://localhost:19680/api/v1/vector_store/set_vector_store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{"tenant_code": "demo", "vector_dimension": 384}'

# 2. Generate schema for a specific model
curl -X POST http://localhost:19680/api/v1/vector_store/generate_schema \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "demo",
    "model_name": "all-MiniLM-L6-v2",
    "dimension": 384,
    "metric_type": "COSINE"
  }'

# 3. Create user for the tenant
curl -X POST http://localhost:19680/api/v1/vector_store_users/set_user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{"tenant_code": "demo"}'

# 4. Insert sample data (use the generated user credentials)
curl -X POST http://localhost:19680/api/v1/vector_store/insert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_user:generated_password" \
  -d '{
    "tenant_code": "demo",
    "model_name": "all-MiniLM-L6-v2",
    "data": [
      {
        "key": "sample_001",
        "chunk": "Sample text for vector search",
        "model": "all-MiniLM-L6-v2",
        "metadata": {"type": "sample"},
        "vector": [/* 384-dimensional vector */]
      }
    ]
  }'

# 5. Search for similar vectors
curl -X POST http://localhost:19680/api/v1/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_user:generated_password" \
  -d '{
    "tenant_code": "demo",
    "model": "all-MiniLM-L6-v2",
    "limit": 5,
    "vector": [/* query vector */]
  }'
```

## Python SDK Example

```python
import requests
import json

class FloudsVectorClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {username}:{password}'
        }
    
    def insert_vectors(self, tenant_code, model_name, data):
        url = f"{self.base_url}/api/v1/vector_store/insert"
        payload = {
            "tenant_code": tenant_code,
            "model_name": model_name,
            "data": data
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()
    
    def search_vectors(self, tenant_code, model, vector, limit=10):
        url = f"{self.base_url}/api/v1/vector_store/search"
        payload = {
            "tenant_code": tenant_code,
            "model": model,
            "vector": vector,
            "limit": limit
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

# Usage
client = FloudsVectorClient("http://localhost:19680", "user", "password")

# Insert vectors
result = client.insert_vectors("mytenant", "sentence-transformers", [
    {
        "key": "doc_1",
        "chunk": "Sample text",
        "model": "sentence-transformers",
        "vector": [0.1, 0.2, 0.3, 0.4]
    }
])

# Search vectors
results = client.search_vectors("mytenant", "sentence-transformers", [0.1, 0.2, 0.3, 0.4])
```