#!/bin/bash

# Flouds Vector API Test Script
# This script tests all API endpoints with sample data

set -e

# Configuration
BASE_URL="http://localhost:19680"
ADMIN_TOKEN="admin:admin_password"
USER_TOKEN="demo_user:demo_password"
TENANT_CODE="demo_tenant"
MODEL_NAME="sentence-transformers"

echo "🚀 Starting Flouds Vector API Tests"
echo "Base URL: $BASE_URL"
echo "Tenant: $TENANT_CODE"
echo "Model: $MODEL_NAME"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to make HTTP requests and check status
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_token=$4
    local description=$5

    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${YELLOW}$method${NC} $endpoint"

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $auth_token" \
            -d "$data" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $auth_token" \
            "$BASE_URL$endpoint")
    fi

    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    response_body=$(echo "$response" | head -n -1)

    if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
        echo -e "${GREEN}✓ Success${NC} (HTTP $http_code)"
        echo "$response_body" | jq '.' 2>/dev/null || echo "$response_body"
    else
        echo -e "${RED}✗ Failed${NC} (HTTP $http_code)"
        echo "$response_body" | jq '.' 2>/dev/null || echo "$response_body"
    fi
    echo ""
}

# Test Health Endpoints
echo "=== Health & Monitoring Tests ==="

test_endpoint "GET" "/" "" "" "Root health check"

test_endpoint "GET" "/health" "" "" "Comprehensive health check"

test_endpoint "GET" "/health/ready" "" "" "Readiness probe"

test_endpoint "GET" "/health/live" "" "" "Liveness probe"

test_endpoint "GET" "/health/connections" "" "" "Connection pool statistics"

test_endpoint "GET" "/api/v1/metrics" "" "$ADMIN_TOKEN" "System metrics"

# Test Vector Store Management
echo "=== Vector Store Management Tests ==="

# 1. Set up vector store
set_vector_store_data='{
  "tenant_code": "'$TENANT_CODE'",
  "vector_dimension": 384
}'

test_endpoint "POST" "/api/v1/vector_store/set_vector_store" "$set_vector_store_data" "$ADMIN_TOKEN" "Set up vector store"

# 2. Generate schema
generate_schema_data='{
  "tenant_code": "'$TENANT_CODE'",
  "model_name": "'$MODEL_NAME'",
  "dimension": 384,
  "nlist": 1024,
  "metric_type": "COSINE",
  "index_type": "IVF_FLAT",
  "metadata_length": 4096
}'

test_endpoint "POST" "/api/v1/vector_store/generate_schema" "$generate_schema_data" "$ADMIN_TOKEN" "Generate schema"

# 3. Insert vectors
insert_data='{
  "tenant_code": "'$TENANT_CODE'",
  "model_name": "'$MODEL_NAME'",
  "data": [
    {
      "key": "doc_001",
      "chunk": "This is a sample document about machine learning and artificial intelligence.",
      "model": "'$MODEL_NAME'",
      "metadata": {
        "source": "research_paper",
        "category": "AI",
        "author": "John Doe",
        "date": "2024-01-01"
      },
      "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2]
    },
    {
      "key": "doc_002",
      "chunk": "Vector databases are essential for similarity search in modern applications.",
      "model": "'$MODEL_NAME'",
      "metadata": {
        "source": "blog_post",
        "category": "Database",
        "author": "Jane Smith",
        "date": "2024-01-02"
      },
      "vector": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3]
    }
  ]
}'

test_endpoint "POST" "/api/v1/vector_store/insert" "$insert_data" "$USER_TOKEN" "Insert vectors"

# 4. Dense vector search
dense_search_data='{
  "tenant_code": "'$TENANT_CODE'",
  "model": "'$MODEL_NAME'",
  "limit": 10,
  "score_threshold": 0.7,
  "metric_type": "COSINE",
  "hybrid_search": false,
  "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.15, 0.25, 0.35, 0.45]
}'

test_endpoint "POST" "/api/v1/vector_store/search" "$dense_search_data" "$USER_TOKEN" "Dense vector search"

# 5. Hybrid search
hybrid_search_data='{
  "tenant_code": "'$TENANT_CODE'",
  "model": "'$MODEL_NAME'",
  "limit": 10,
  "score_threshold": 0.5,
  "metric_type": "COSINE",
  "hybrid_search": true,
  "text_filter": "machine learning artificial intelligence",
  "minimum_words_match": 2,
  "include_stop_words": false,
  "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.15, 0.25, 0.35, 0.45]
}'

test_endpoint "POST" "/api/v1/vector_store/search" "$hybrid_search_data" "$USER_TOKEN" "Hybrid search"

# Test User Management
echo "=== User Management Tests ==="

# 1. Create user
set_user_data='{
  "tenant_code": "'$TENANT_CODE'"
}'

test_endpoint "POST" "/api/v1/vector_store_users/set_user" "$set_user_data" "$ADMIN_TOKEN" "Create user"

# 2. Reset password
reset_password_data='{
  "tenant_code": "'$TENANT_CODE'"
}'

test_endpoint "POST" "/api/v1/vector_store_users/reset_password" "$reset_password_data" "$ADMIN_TOKEN" "Reset password"

# Test Error Scenarios
echo "=== Error Scenario Tests ==="

# Invalid tenant code
invalid_tenant_data='{
  "tenant_code": "invalid@tenant!",
  "vector_dimension": 384
}'

test_endpoint "POST" "/api/v1/vector_store/set_vector_store" "$invalid_tenant_data" "$ADMIN_TOKEN" "Invalid tenant code (should fail)"

# Missing authentication
test_endpoint "GET" "/api/v1/metrics" "" "" "Missing authentication (should fail)"

# Invalid vector dimension
invalid_dimension_data='{
  "tenant_code": "'$TENANT_CODE'",
  "vector_dimension": 5000
}'

test_endpoint "POST" "/api/v1/vector_store/set_vector_store" "$invalid_dimension_data" "$ADMIN_TOKEN" "Invalid vector dimension (should fail)"

echo "🏁 API Tests Completed"
echo ""
echo "Summary:"
echo "- All endpoints have been tested"
echo "- Check the output above for any failures"
echo "- Green checkmarks indicate successful requests"
echo "- Red X marks indicate failed requests (some failures are expected for error scenarios)"
