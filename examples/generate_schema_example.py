#!/usr/bin/env python3
"""
Example usage of the GenerateSchema API endpoint.

This example demonstrates how to call the new /api/v1/vector_store/generate_schema endpoint
to create a custom schema with specific parameters.
"""

import json

import requests

# Configuration
BASE_URL = "http://localhost:19680"
API_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/generate_schema"

# Authentication (replace with your actual credentials)
USERNAME = "admin"
PASSWORD = "admin_password"
AUTH_TOKEN = f"{USERNAME}:{PASSWORD}"

# Request payload
payload = {
    "tenant_code": "example_tenant",
    "dimension": 768,  # Vector dimension
    "nlist": 2048,  # Number of cluster units for IVF index
    "metric_type": "COSINE",  # Similarity metric
    "index_type": "IVF_FLAT",  # Index type
    "model_name": "sentence-transformers-all-MiniLM-L6-v2",  # Model name
    "metadata_length": 8192,  # Maximum metadata length
}

# Headers
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}"}


def generate_schema():
    """
    Call the GenerateSchema API endpoint.
    """
    try:
        print("Calling GenerateSchema API...")
        print(f"URL: {API_ENDPOINT}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            API_ENDPOINT, headers=headers, json=payload, timeout=30
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Schema generation successful!")
            print(f"Response: {json.dumps(result, indent=2)}")

            # Extract key information
            if result.get("success"):
                results = result.get("results", {})
                print(f"\n📊 Schema Details:")
                print(f"   Tenant Code: {results.get('tenant_code')}")
                print(f"   Model Name: {results.get('model_name')}")
                print(f"   Collection Name: {results.get('collection_name')}")
                print(f"   Database Name: {results.get('db_name')}")
                print(f"   Dimension: {results.get('dimension')}")
                print(f"   Metric Type: {results.get('metric_type')}")
                print(f"   Index Type: {results.get('index_type')}")
                print(f"   NList: {results.get('nlist')}")
                print(f"   Metadata Length: {results.get('metadata_length')}")
                print(f"   Schema Created: {results.get('schema_created')}")
                print(f"   Index Created: {results.get('index_created')}")
            else:
                print(f"❌ Schema generation failed: {result.get('message')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error Details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error Text: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    generate_schema()
