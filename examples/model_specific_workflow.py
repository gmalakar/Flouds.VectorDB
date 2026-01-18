# =============================================================================
# File: model_specific_workflow.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

"""
Example workflow showing model-specific collections:
1. set_vector_store - Creates tenant infrastructure
2. generate_schema - Creates collection for specific model
3. insert - Inserts vectors for that model
4. search - Searches in model-specific collection
"""


import logging

# Use shared utilities
from common import api_post, print_schema_details

# Configuration
BASE_URL = "http://localhost:19680"
SET_VECTOR_STORE_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/set_vector_store"
GENERATE_SCHEMA_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/generate_schema"
INSERT_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/insert"
SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/search"

# Authentication
USERNAME = "admin"
PASSWORD = "admin_password"
AUTH_TOKEN = f"{USERNAME}:{PASSWORD}"

# Headers
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}"}


def setup_tenant():
    """Step 1: Setup tenant infrastructure"""
    payload = {"tenant_code": "example_tenant", "vector_dimension": 768}
    logging.info("🔧 Step 1: Setting up tenant infrastructure...")
    status_code, result, error_text = api_post(SET_VECTOR_STORE_ENDPOINT, payload, headers)
    if status_code == 200 and result and result.get("success"):
        logging.info("✅ Tenant setup successful!")
        return True
    elif status_code is not None:
        logging.error(f"❌ Tenant setup failed: {error_text or result}")
        return False
    else:
        logging.error(f"❌ Request failed: {error_text}")
        return False


def generate_schema_for_model(model_name):
    """Step 2: Generate schema for specific model"""
    payload = {
        "tenant_code": "example_tenant",
        "dimension": 768,
        "nlist": 2048,
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "model_name": model_name,
        "metadata_length": 8192,
    }
    logging.info(f"🏗️ Step 2: Generating schema for model '{model_name}'...")
    status_code, result, error_text = api_post(GENERATE_SCHEMA_ENDPOINT, payload, headers)
    if status_code == 200 and result and result.get("success"):
        print_schema_details(result.get("results", {}))
        collection_name = result.get("results", {}).get("collection_name")
        logging.info(f"✅ Schema generated! Collection: {collection_name}")
        return True
    elif status_code is not None:
        logging.error(f"❌ Schema generation failed: {error_text or result}")
        return False
    else:
        logging.error(f"❌ Request failed: {error_text}")
        return False


def insert_vectors_for_model(model_name):
    """Step 3: Insert vectors for specific model"""
    payload = {
        "tenant_code": "example_tenant",
        "model_name": model_name,
        "data": [
            {
                "key": "doc_001",
                "chunk": "This is a sample document about machine learning.",
                "model": model_name,
                "metadata": {"source": "example", "category": "ml"},
                "vector": [0.1] * 768,
            },
            {
                "key": "doc_002",
                "chunk": "Another document discussing artificial intelligence.",
                "model": model_name,
                "metadata": {"source": "example", "category": "ai"},
                "vector": [0.2] * 768,
            },
        ],
    }
    logging.info(f"📝 Step 3: Inserting vectors for model '{model_name}'...")
    status_code, result, error_text = api_post(INSERT_ENDPOINT, payload, headers)
    if status_code == 200 and result and result.get("success"):
        logging.info("✅ Vectors inserted successfully!")
        return True
    elif status_code is not None:
        logging.error(f"❌ Vector insertion failed: {error_text or result}")
        return False
    else:
        logging.error(f"❌ Request failed: {error_text}")
        return False


def search_vectors_for_model(model_name):
    """Step 4: Search vectors in model-specific collection"""
    payload = {
        "tenant_code": "example_tenant",
        "model": model_name,
        "vector": [0.15] * 768,
        "limit": 5,
        "metric_type": "COSINE",
        "score_threshold": 0.0,
    }
    logging.info(f"🔍 Step 4: Searching vectors for model '{model_name}'...")
    status_code, result, error_text = api_post(SEARCH_ENDPOINT, payload, headers)
    if status_code == 200 and result and result.get("success"):
        data = result.get("data", [])
        logging.info(f"✅ Search successful! Found {len(data)} results:")
        for i, item in enumerate(data[:2]):
            logging.info(f"   Result {i+1}: {item.get('content', '')[:50]}...")
        return True
    elif status_code is not None:
        logging.error(f"❌ Search failed: {error_text or result}")
        return False
    else:
        logging.error(f"❌ Request failed: {error_text}")
        return False


def demonstrate_multiple_models():
    """Demonstrate multiple models for the same tenant"""
    models = ["sentence-transformers-all-MiniLM-L6-v2", "openai-text-embedding-ada-002"]

    logging.info("🚀 Starting multi-model workflow...\n")

    # Step 1: Setup tenant (once)
    if not setup_tenant():
        return

    # Steps 2-4: For each model
    for model in models:
        logging.info(f"\n📋 Working with model: {model}")

        if generate_schema_for_model(model):
            if insert_vectors_for_model(model):
                search_vectors_for_model(model)
            else:
                logging.warning(f"❌ Skipping search for {model} due to insertion failure")
        else:
            logging.warning(f"❌ Skipping {model} due to schema generation failure")

    logging.info("\n🎉 Multi-model workflow completed!")
    logging.info("Each model now has its own collection with isolated data.")


if __name__ == "__main__":
    demonstrate_multiple_models()
