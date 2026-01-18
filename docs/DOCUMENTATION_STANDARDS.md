# Documentation Standards

## Overview
This document defines the documentation standards for the FloudsVector project to ensure consistency, clarity, and maintainability across all code files.

## File Header Standards

### Standard Header Format
All Python files must include a standardized header with the following format:

```python
# =============================================================================
# File: filename.py
# Description: Brief description of file purpose and functionality
# Author: Goutam Malakar
# Date: YYYY-MM-DD (last significant update)
# Version: X.Y.Z
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
```

### Header Fields
- **File**: Exact filename including extension
- **Description**: One-line summary of file purpose and main functionality
- **Author**: Primary author/maintainer name
- **Date**: Date of last significant update (YYYY-MM-DD format)
- **Version**: Semantic version number (Major.Minor.Patch)
- **Copyright**: Copyright notice with year and owner

### Examples by File Type

#### Service Files
```python
# =============================================================================
# File: vector_store_service.py
# Description: Service layer for vector store operations including CRUD and search
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
```

#### Model Files
```python
# =============================================================================
# File: search_request.py
# Description: Pydantic models for vector search requests with validation
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
```

#### Utility Files
```python
# =============================================================================
# File: input_validator.py
# Description: Input validation utilities with sanitization and security checks
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
```

## Function Documentation Standards

### Docstring Format
Use Google-style docstrings for all functions, methods, and classes:

```python
def function_name(param1: str, param2: int = 10) -> bool:
    """
    Brief description of what the function does.

    Longer description if needed, explaining the purpose, behavior,
    and any important implementation details.

    Args:
        param1 (str): Description of first parameter
        param2 (int, optional): Description of second parameter. Defaults to 10.

    Returns:
        bool: Description of return value

    Raises:
        ValueError: When parameter validation fails
        ConnectionError: When database connection fails

    Example:
        >>> result = function_name("test", 5)
        >>> print(result)
        True
    """
```

### Required Sections
- **Brief Description**: One-line summary (required)
- **Detailed Description**: Extended explanation if needed (optional)
- **Args**: All parameters with types and descriptions (required if parameters exist)
- **Returns**: Return value type and description (required if function returns value)
- **Raises**: Exceptions that may be raised (required if function raises exceptions)
- **Example**: Usage example (optional but recommended for complex functions)

### Parameter Documentation
- Include type hints in function signature
- Document all parameters in Args section
- Specify optional parameters with default values
- Include parameter constraints (ranges, valid values, etc.)

```python
def search_vectors(
    query: List[float],
    limit: int = 10,
    threshold: float = 0.0,
    metric: str = "COSINE"
) -> List[Dict[str, Any]]:
    """
    Search for similar vectors using specified parameters.

    Args:
        query (List[float]): Query vector for similarity search
        limit (int, optional): Maximum results to return. Range: 1-100. Defaults to 10.
        threshold (float, optional): Minimum similarity score. Range: 0.0-1.0. Defaults to 0.0.
        metric (str, optional): Distance metric. Options: 'L2', 'IP', 'COSINE'. Defaults to 'COSINE'.

    Returns:
        List[Dict[str, Any]]: List of search results with scores and metadata

    Raises:
        ValueError: If query vector is empty or invalid
        VectorStoreError: If search operation fails
    """
```

## Class Documentation Standards

### Class Docstrings
```python
class VectorStoreService:
    """
    Service class for vector store operations.

    Provides high-level business logic for vector store management including
    user management, tenant setup, data insertion, and similarity search.
    All methods are class methods for stateless operation.

    Attributes:
        None (all methods are class methods)

    Example:
        >>> response = VectorStoreService.search_in_vector_store(request, token)
        >>> print(response.success)
        True
    """
```

### Method Documentation
- Document all public methods
- Include parameter validation details
- Specify thread-safety characteristics
- Document side effects and state changes

## Field Description Standards

### Pydantic Model Fields
Use clear, concise descriptions with constraints and defaults:

```python
class SearchRequest(BaseModel):
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of search results to return. Range: 1-100, default: 10."
    )

    score_threshold: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold for results. Range: 0.0-1.0, default: 0.0."
    )

    metric_type: str = Field(
        "COSINE",
        description="Distance metric for similarity calculation. Options: 'L2', 'IP', 'COSINE'. Default: 'COSINE'."
    )
```

### Field Description Format
- Start with action or purpose
- Include valid ranges or options
- Specify default values
- Use consistent terminology

### Common Field Patterns
```python
# Identifiers
tenant_code: str = Field(
    ...,
    description="Unique tenant identifier for multi-tenant isolation."
)

# Limits and counts
limit: int = Field(
    10,
    ge=1,
    le=100,
    description="Maximum number of items to return. Range: 1-100, default: 10."
)

# Thresholds and scores
threshold: float = Field(
    0.0,
    ge=0.0,
    le=1.0,
    description="Minimum score threshold for filtering. Range: 0.0-1.0, default: 0.0."
)

# Boolean flags
enabled: bool = Field(
    False,
    description="Whether feature is enabled. Default: False."
)

# Optional text fields
description: Optional[str] = Field(
    None,
    max_length=500,
    description="Optional description text. Maximum 500 characters."
)
```

## Error Message Standards

### Exception Documentation
Document all custom exceptions with clear descriptions:

```python
class VectorStoreError(FloudsVectorError):
    """
    Raised when vector store operations fail.

    This exception indicates issues with vector database operations
    such as insertion, search, or collection management failures.
    """
    pass
```

### Error Message Format
- Use clear, actionable error messages
- Include context information
- Avoid exposing sensitive data
- Provide guidance for resolution

```python
# Good error messages
"Vector dimension mismatch: expected 384, got 512"
"Tenant 'example_tenant' not found or access denied"
"Search operation failed: collection not ready"

# Avoid
"Error occurred"
"Invalid input"
"Database error"
```

## Comment Standards

### Inline Comments
- Use sparingly for complex logic
- Explain "why" not "what"
- Keep comments up-to-date with code changes

```python
# Calculate RRF score combining dense and sparse results
rrf_score = 1.0 / (rank + k)  # k=60 is standard RRF constant

# Sanitize input to prevent log injection attacks
safe_input = sanitize_for_log(user_input)
```

### TODO Comments
Use consistent format for TODO items:

```python
# TODO(author): Description of what needs to be done
# FIXME(author): Description of issue that needs fixing
# NOTE(author): Important information for future developers
```

## API Documentation Standards

### Endpoint Documentation
Document all API endpoints with OpenAPI/Swagger compatible docstrings:

```python
@router.post("/search", response_model=SearchResponse)
async def search_vectors(
    request: SearchRequest,
    token: str = Depends(get_token)
) -> SearchResponse:
    """
    Search for similar vectors in the vector store.

    Performs similarity search using dense vectors with optional hybrid search
    combining keyword filtering for improved relevance.

    - **tenant_code**: Tenant identifier for multi-tenant isolation
    - **vector**: Query vector for similarity search
    - **limit**: Maximum number of results (1-100)
    - **metric_type**: Distance metric (L2, IP, COSINE)
    - **hybrid_search**: Enable keyword-based filtering

    Returns search results with similarity scores and metadata.
    """
```

## Version Control Standards

### Commit Message Format
Use conventional commit format:

```
type(scope): description

feat(search): add hybrid search with keyword filtering
fix(auth): resolve token validation issue
docs(api): update search endpoint documentation
refactor(milvus): extract connection pooling logic
```

### Documentation Updates
- Update file headers when making significant changes
- Increment version numbers following semantic versioning
- Update docstrings when function signatures change
- Keep README and API documentation synchronized

## Validation and Enforcement

### Pre-commit Checks
- Verify all files have proper headers
- Check docstring completeness for public functions
- Validate field descriptions in Pydantic models
- Ensure consistent formatting

### Documentation Review
- Include documentation review in pull request process
- Verify examples work as documented
- Check for consistency with existing patterns
- Validate technical accuracy

### Tools and Automation
- Use automated tools to check documentation coverage
- Implement linting rules for docstring format
- Generate API documentation from code comments
- Maintain documentation changelog

## Best Practices

### Writing Guidelines
1. **Clarity**: Use clear, concise language
2. **Consistency**: Follow established patterns
3. **Completeness**: Document all public interfaces
4. **Accuracy**: Keep documentation synchronized with code
5. **Examples**: Provide practical usage examples

### Maintenance
1. **Regular Reviews**: Periodically review and update documentation
2. **User Feedback**: Incorporate feedback from API users
3. **Continuous Improvement**: Refine standards based on experience
4. **Knowledge Sharing**: Document lessons learned and best practices

## Conclusion
Consistent documentation standards improve code maintainability, reduce onboarding time for new developers, and enhance the overall quality of the FloudsVector project. All contributors should follow these standards to ensure a professional and maintainable codebase.
