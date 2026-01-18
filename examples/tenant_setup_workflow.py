# =============================================================================
# File: tenant_setup_workflow.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

"""
Example workflow showing the new two-step process:
1. set_vector_store - Creates database, user, and permissions
2. generate_schema - Creates collections and indexes with custom parameters
"""

import json
import logging

import requests

# Configure basic logging for examples
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Configuration
BASE_URL = "http://localhost:19680"
SET_VECTOR_STORE_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/set_vector_store"
GENERATE_SCHEMA_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/generate_schema"

# Authentication
USERNAME = "admin"
PASSWORD = "admin_password"
AUTH_TOKEN = f"{USERNAME}:{PASSWORD}"

# Headers
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}"}


def step1_setup_tenant():
    """
    Step 1: Set up tenant infrastructure (database, user, permissions)
    """
    payload = {
        "tenant_code": "example_tenant",
        "vector_dimension": 768,  # This is kept for compatibility but not used for collection creation
    }

    logging.info("🔧 Step 1: Setting up tenant infrastructure...")
    logging.info(f"URL: {SET_VECTOR_STORE_ENDPOINT}")
    logging.info(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            SET_VECTOR_STORE_ENDPOINT, headers=headers, json=payload, timeout=30
        )

        logging.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logging.info("✅ Tenant setup successful!")

            if result.get("success"):
                results = result.get("results", {})
                logging.info("📊 Setup Details:")
                logging.info("   Tenant Code: %s", results.get("tenant_code"))
                logging.info("   Database Created: %s", results.get("db_created"))
                logging.info("   Role Created: %s", results.get("role_created"))
                logging.info("   Role Assigned: %s", results.get("role_assigned"))
                logging.info("   Client ID: %s", results.get("client_id"))
                logging.info("   New Client: %s", results.get("new_client_id"))
                return True
            else:
                logging.error(f"❌ Tenant setup failed: {result.get('message')}")
                return False
        else:
            logging.error(f"❌ HTTP Error: {response.status_code}")
            return False

    except Exception:
        logging.exception("❌ Error while setting up tenant")
        return False


def step2_generate_schema():
    """
    Step 2: Generate custom schema with collections and indexes
    """
    payload = {
        "tenant_code": "example_tenant",
        "dimension": 768,
        "nlist": 2048,
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "model_name": "sentence-transformers-all-MiniLM-L6-v2",
        "metadata_length": 8192,
    }

    logging.info("\n🏗️ Step 2: Generating custom schema...")
    logging.info("URL: %s", GENERATE_SCHEMA_ENDPOINT)
    logging.info("Payload: %s", json.dumps(payload, indent=2))

    try:
        response = requests.post(
            GENERATE_SCHEMA_ENDPOINT, headers=headers, json=payload, timeout=30
        )

        logging.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logging.info("✅ Schema generation successful!")

            if result.get("success"):
                results = result.get("results", {})
                logging.info("📊 Schema Details:")
                logging.info("   Collection Name: %s", results.get("collection_name"))
                logging.info("   Database Name: %s", results.get("db_name"))
                logging.info("   Schema Created: %s", results.get("schema_created"))
                logging.info("   Index Created: %s", results.get("index_created"))
                logging.info("   Dimension: %s", results.get("dimension"))
                logging.info("   Metric Type: %s", results.get("metric_type"))
                logging.info("   Index Type: %s", results.get("index_type"))
                return True
            else:
                logging.error(f"❌ Schema generation failed: {result.get('message')}")
                return False
        else:
            logging.error(f"❌ HTTP Error: {response.status_code}")
            return False

    except Exception:
        logging.exception("❌ Error while generating schema")
        return False


def main():
    """
    Complete workflow: Setup tenant then generate schema
    """
    logging.info("🚀 Starting tenant setup workflow...\n")

    # Step 1: Setup tenant infrastructure
    if step1_setup_tenant():
        # Step 2: Generate custom schema
        if step2_generate_schema():
            logging.info("\n🎉 Complete workflow successful!")
            logging.info("Your tenant is now ready with custom schema!")
        else:
            logging.error(
                "\n❌ Schema generation failed. Tenant infrastructure is set up but no collections created."
            )
    else:
        logging.error("\n❌ Tenant setup failed. Cannot proceed to schema generation.")


if __name__ == "__main__":
    main()
