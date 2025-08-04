#!/usr/bin/env python3
"""
Example workflow showing model-specific collections:
1. set_vector_store - Creates tenant infrastructure
2. generate_schema - Creates collection for specific model
3. insert - Inserts vectors for that model
4. search - Searches in model-specific collection
"""

import json

import requests

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

    print("🔧 Step 1: Setting up tenant infrastructure...")
    response = requests.post(
        SET_VECTOR_STORE_ENDPOINT, headers=headers, json=payload, timeout=30
    )

    if response.status_code == 200 and response.json().get("success"):
        print("✅ Tenant setup successful!")
        return True
    else:
        print(f"❌ Tenant setup failed: {response.text}")
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

    print(f"🏗️ Step 2: Generating schema for model '{model_name}'...")
    response = requests.post(
        GENERATE_SCHEMA_ENDPOINT, headers=headers, json=payload, timeout=30
    )

    if response.status_code == 200 and response.json().get("success"):
        result = response.json()
        collection_name = result.get("results", {}).get("collection_name")
        print(f"✅ Schema generated! Collection: {collection_name}")
        return True
    else:
        print(f"❌ Schema generation failed: {response.text}")
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
                "vector": [0.1] * 768,  # Sample 768-dimensional vector
            },
            {
                "key": "doc_002",
                "chunk": "Another document discussing artificial intelligence.",
                "model": model_name,
                "metadata": {"source": "example", "category": "ai"},
                "vector": [0.2] * 768,  # Sample 768-dimensional vector
            },
        ],
    }

    print(f"📝 Step 3: Inserting vectors for model '{model_name}'...")
    response = requests.post(INSERT_ENDPOINT, headers=headers, json=payload, timeout=30)

    if response.status_code == 200 and response.json().get("success"):
        print("✅ Vectors inserted successfully!")
        return True
    else:
        print(f"❌ Vector insertion failed: {response.text}")
        return False


def search_vectors_for_model(model_name):
    """Step 4: Search vectors in model-specific collection"""
    payload = {
        "tenant_code": "example_tenant",
        "model": model_name,
        "vector": [0.15] * 768,  # Sample query vector
        "limit": 5,
        "metric_type": "COSINE",
        "score_threshold": 0.0,
    }

    print(f"🔍 Step 4: Searching vectors for model '{model_name}'...")
    response = requests.post(SEARCH_ENDPOINT, headers=headers, json=payload, timeout=30)

    if response.status_code == 200 and response.json().get("success"):
        result = response.json()
        data = result.get("data", [])
        print(f"✅ Search successful! Found {len(data)} results:")
        for i, item in enumerate(data[:2]):  # Show first 2 results
            print(f"   Result {i+1}: {item.get('content', '')[:50]}...")
        return True
    else:
        print(f"❌ Search failed: {response.text}")
        return False


def demonstrate_multiple_models():
    """Demonstrate multiple models for the same tenant"""
    models = ["sentence-transformers-all-MiniLM-L6-v2", "openai-text-embedding-ada-002"]

    print("🚀 Starting multi-model workflow...\n")

    # Step 1: Setup tenant (once)
    if not setup_tenant():
        return

    # Steps 2-4: For each model
    for model in models:
        print(f"\n📋 Working with model: {model}")

        if generate_schema_for_model(model):
            if insert_vectors_for_model(model):
                search_vectors_for_model(model)
            else:
                print(f"❌ Skipping search for {model} due to insertion failure")
        else:
            print(f"❌ Skipping {model} due to schema generation failure")

    print("\n🎉 Multi-model workflow completed!")
    print("Each model now has its own collection with isolated data.")


if __name__ == "__main__":
    demonstrate_multiple_models()
