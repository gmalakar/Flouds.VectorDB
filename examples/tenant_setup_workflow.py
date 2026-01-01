#!/usr/bin/env python3
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
                logging.info(f"📊 Setup Details:")
                logging.info(f"   Tenant Code: {results.get('tenant_code')}")
                logging.info(f"   Database Created: {results.get('db_created')}")
                logging.info(f"   Role Created: {results.get('role_created')}")
                logging.info(f"   Role Assigned: {results.get('role_assigned')}")
                logging.info(f"   Client ID: {results.get('client_id')}")
                logging.info(f"   New Client: {results.get('new_client_id')}")
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
    logging.info(f"URL: {GENERATE_SCHEMA_ENDPOINT}")
    logging.info(f"Payload: {json.dumps(payload, indent=2)}")

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
                logging.info(f"📊 Schema Details:")
                logging.info(f"   Collection Name: {results.get('collection_name')}")
                logging.info(f"   Database Name: {results.get('db_name')}")
                logging.info(f"   Schema Created: {results.get('schema_created')}")
                logging.info(f"   Index Created: {results.get('index_created')}")
                logging.info(f"   Dimension: {results.get('dimension')}")
                logging.info(f"   Metric Type: {results.get('metric_type')}")
                logging.info(f"   Index Type: {results.get('index_type')}")
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
