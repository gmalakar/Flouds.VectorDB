# =============================================================================
# File: enhance-openapi.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
"""
Script to enhance FastAPI's built-in OpenAPI documentation with additional metadata.
This script modifies the OpenAPI spec at runtime to add more detailed descriptions,
examples, and documentation that might not be easily added through decorators.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def enhance_openapi_schema(app: FastAPI) -> dict:
    """
    Enhance the OpenAPI schema with additional metadata and examples.

    Args:
        app: FastAPI application instance

    Returns:
        Enhanced OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Get the base OpenAPI schema
    openapi_schema = get_openapi(
        title="Flouds Vector API",
        version="1.0.0",
        description="""
        ## Multi-tenant Vector Database API

        Flouds Vector API provides a comprehensive solution for managing multi-tenant vector stores
        using Milvus as the backend. It offers advanced features for vector similarity search,
        hybrid search capabilities, and complete tenant isolation.

        ### Key Features
        - **Multi-tenant Architecture**: Complete data isolation between tenants
        - **Model-specific Collections**: Organize vectors by model for better performance
        - **Hybrid Search**: Combine dense and sparse vectors with RRF scoring
        - **Advanced Security**: Bearer token authentication with rate limiting
        - **Production Ready**: Connection pooling, monitoring, and health checks

        ### Authentication
        All endpoints require Bearer token authentication:
        ```
        Authorization: Bearer username:password
        ```

        ### Rate Limiting
        - Global: 100 requests/minute per IP
        - Per-tenant: Configurable based on tenant tier

        ### Workflow
        1. **Setup**: Create tenant database and user with `set_vector_store`
        2. **Schema**: Generate model-specific collections with `generate_schema`
        3. **Insert**: Add vectors with metadata using `insert`
        4. **Search**: Find similar vectors with `search` (dense or hybrid)

        ### Support
        - **Documentation**: [GitHub Repository](https://github.com/your-org/FloudsVector.Py)
        - **Issues**: [Report Issues](https://github.com/your-org/FloudsVector.Py/issues)
        """,
        routes=app.routes,
    )

    # Add additional metadata
    openapi_schema["info"]["contact"] = {
        "name": "Flouds Vector API Support",
        "url": "https://github.com/your-org/FloudsVector.Py",
        "email": "support@flouds.com",
    }

    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://github.com/your-org/FloudsVector.Py/blob/main/LICENSE",
    }

    # Add servers
    openapi_schema["servers"] = [
        {"url": "http://localhost:19680", "description": "Development server"},
        {"url": "https://api.flouds.com", "description": "Production server"},
    ]

    # Enhance specific endpoints with better examples
    paths = openapi_schema.get("paths", {})

    # Enhance vector store endpoints
    if "/api/v1/vector_store/insert" in paths:
        insert_path = paths["/api/v1/vector_store/insert"]["post"]
        insert_path["summary"] = "Insert vectors with metadata"
        insert_path[
            "description"
        ] = """
        Insert embedded vectors into the model-specific collection for the given tenant.

        **Important Notes:**
        - All vectors must use the same model name
        - Vector dimensions must be consistent within a model
        - Automatically generates BM25 sparse vectors for hybrid search
        - Maximum 1000 vectors per request
        - Chunk text limited to 60,000 characters
        """

        # Add example
        if "requestBody" in insert_path and "content" in insert_path["requestBody"]:
            content = insert_path["requestBody"]["content"]
            if "application/json" in content:
                content["application/json"]["example"] = {
                    "tenant_code": "demo_tenant",
                    "model_name": "sentence-transformers",
                    "data": [
                        {
                            "key": "doc_001",
                            "chunk": "Machine learning is transforming how we process information.",
                            "model": "sentence-transformers",
                            "metadata": {
                                "source": "research_paper",
                                "category": "AI",
                                "author": "Dr. Smith",
                            },
                            "vector": [0.1, 0.2, 0.3, 0.4],  # 384-dimensional vector
                        }
                    ],
                }

    # Enhance search endpoint
    if "/api/v1/vector_store/search" in paths:
        search_path = paths["/api/v1/vector_store/search"]["post"]
        search_path["summary"] = "Search vectors (dense or hybrid)"
        search_path[
            "description"
        ] = """
        Search for similar vectors in the model-specific collection.

        **Search Types:**
        - **Dense Search**: Semantic similarity using vector embeddings
        - **Hybrid Search**: Combines dense vectors with BM25 sparse vectors using RRF

        **Supported Metrics:**
        - COSINE: Cosine similarity (recommended for normalized vectors)
        - L2: Euclidean distance
        - IP: Inner product

        **Hybrid Search Features:**
        - Text filtering with stop word handling
        - Minimum word matching requirements
        - Reciprocal Rank Fusion (RRF) for result combination
        """

    # Add custom tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check and system monitoring endpoints",
        },
        {
            "name": "Monitoring",
            "description": "Performance metrics and system statistics",
        },
        {
            "name": "Vector Store",
            "description": "Vector database operations including setup, insert, and search",
        },
        {
            "name": "User Management",
            "description": "Tenant user creation and password management",
        },
    ]

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "username:password",
            "description": "Bearer token authentication in the format: Bearer username:password",
        }
    }

    # Set global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_enhanced_openapi(app: FastAPI) -> None:
    """
    Setup enhanced OpenAPI documentation for the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    def custom_openapi() -> dict:
        return enhance_openapi_schema(app)

    app.openapi = custom_openapi


if __name__ == "__main__":
    # Example usage
    from fastapi import FastAPI

    app = FastAPI()
    setup_enhanced_openapi(app)

    # Print the enhanced schema
    import json

    schema = app.openapi()
    print(json.dumps(schema, indent=2))
