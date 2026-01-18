# =============================================================================
# File: generate_schema_example.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

"""
Example usage of the GenerateSchema API endpoint.

This example demonstrates how to call the new /api/v1/vector_store/generate_schema endpoint
to create a custom schema with specific parameters.
"""

import json
import logging

import requests

# Configure basic logging for examples
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

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
        logging.info("Calling GenerateSchema API...")
        logging.info(f"URL: {API_ENDPOINT}")
        logging.info(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=30)

        logging.info(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logging.info("✅ Schema generation successful!")
            logging.debug(f"Response: {json.dumps(result, indent=2)}")

            # Extract key information
            if result.get("success"):
                results = result.get("results", {})
                logging.info("\n📊 Schema Details:")
                logging.info(f"   Tenant Code: {results.get('tenant_code')}")
                logging.info(f"   Model Name: {results.get('model_name')}")
                logging.info(f"   Collection Name: {results.get('collection_name')}")
                logging.info(f"   Database Name: {results.get('db_name')}")
                logging.info(f"   Dimension: {results.get('dimension')}")
                logging.info(f"   Metric Type: {results.get('metric_type')}")
                logging.info(f"   Index Type: {results.get('index_type')}")
                logging.info(f"   NList: {results.get('nlist')}")
                logging.info(f"   Metadata Length: {results.get('metadata_length')}")
                logging.info(f"   Schema Created: {results.get('schema_created')}")
                logging.info(f"   Index Created: {results.get('index_created')}")
            else:
                logging.error(f"❌ Schema generation failed: {result.get('message')}")
        else:
            logging.error(f"❌ HTTP Error: {response.status_code}")
            try:
                error_detail = response.json()
                logging.error(f"Error Details: {json.dumps(error_detail, indent=2)}")
            except Exception:
                logging.error(f"Error Text: {response.text}", exc_info=True)

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Request failed: {e}")
    except Exception:
        logging.exception("❌ Unexpected error while generating schema")


if __name__ == "__main__":
    generate_schema()
