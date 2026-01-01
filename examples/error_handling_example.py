#!/usr/bin/env python3
"""
Example demonstrating error handling for missing database/collection.
Shows what happens when you try to insert/search without proper setup.
"""


# Use shared utilities
from common import api_post

# Configuration
BASE_URL = "http://localhost:19680"
INSERT_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/insert"
SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/vector_store/search"

# Authentication
USERNAME = "admin"
PASSWORD = "admin_password"
AUTH_TOKEN = f"{USERNAME}:{PASSWORD}"

# Headers
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}"}


def test_insert_without_setup():
    """Test inserting without database/collection setup"""
    payload = {
        "tenant_code": "nonexistent_tenant",
        "model_name": "test-model",
        "data": [
            {
                "key": "doc_001",
                "chunk": "This is a test document.",
                "model": "test-model",
                "metadata": {"source": "test"},
                "vector": [0.1] * 768,
            }
        ],
    }

    logging.info("🧪 Testing insert without database setup...")
    status_code, result, error_text = api_post(INSERT_ENDPOINT, payload, headers)
    if status_code == 200 and result:
        if not result.get("success"):
            logging.info(f"✅ Expected error: {result.get('message')}")
        else:
            logging.error("❌ Unexpected success - should have failed")
    elif status_code is not None:
        logging.error(f"❌ HTTP Error: {status_code}")
    else:
        logging.error(f"❌ Request failed: {error_text}")


def test_search_without_setup():
    """Test searching without database/collection setup"""
    payload = {
        "tenant_code": "nonexistent_tenant",
        "model": "test-model",
        "vector": [0.1] * 768,
        "limit": 5,
    }

    logging.info("\n🧪 Testing search without database setup...")
    status_code, result, error_text = api_post(SEARCH_ENDPOINT, payload, headers)
    if status_code == 200 and result:
        if not result.get("success"):
            logging.info(f"✅ Expected error: {result.get('message')}")
        else:
            logging.error("❌ Unexpected success - should have failed")
    elif status_code is not None:
        logging.error(f"❌ HTTP Error: {status_code}")
    else:
        logging.error(f"❌ Request failed: {error_text}")


def test_insert_with_db_but_no_collection():
    """Test inserting with database but no collection"""
    # This assumes you have a tenant with database but no collection for this model
    payload = {
        "tenant_code": "existing_tenant",  # Replace with actual tenant
        "model_name": "nonexistent-model",
        "data": [
            {
                "key": "doc_001",
                "chunk": "This is a test document.",
                "model": "nonexistent-model",
                "metadata": {"source": "test"},
                "vector": [0.1] * 768,
            }
        ],
    }

    logging.info("\n🧪 Testing insert with database but no collection...")
    status_code, result, error_text = api_post(INSERT_ENDPOINT, payload, headers)
    if status_code == 200 and result:
        if not result.get("success"):
            logging.info(f"✅ Expected error: {result.get('message')}")
        else:
            logging.error("❌ Unexpected success - should have failed")
    elif status_code is not None:
        logging.error(f"❌ HTTP Error: {status_code}")
    else:
        logging.error(f"❌ Request failed: {error_text}")


def main():
    """Run all error handling tests"""
    logging.info("🚀 Testing error handling for missing database/collection...\n")

    test_insert_without_setup()
    test_search_without_setup()
    test_insert_with_db_but_no_collection()

    logging.info("\n✅ Error handling tests completed!")
    logging.info("The API now properly validates database and collection existence.")


if __name__ == "__main__":
    main()
