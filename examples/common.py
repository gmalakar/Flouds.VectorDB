import json
import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def api_post(url, payload, headers, timeout=30):
    """
    Send a POST request and return (status_code, response_json or None, error_text or None).
    """
    try:
        logging.info(f"POST {url}")
        logging.info(f"Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        try:
            result = response.json()
        except Exception:
            result = None
        return response.status_code, result, response.text if result is None else None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None, None, str(e)


def print_schema_details(results):
    """
    Print key schema details from a result dict.
    """
    logging.info("\n📊 Schema Details:")
    for key in [
        "tenant_code",
        "model_name",
        "collection_name",
        "db_name",
        "dimension",
        "metric_type",
        "index_type",
        "nlist",
        "metadata_length",
        "schema_created",
        "index_created",
    ]:
        if key in results:
            logging.info(f"   {key.replace('_', ' ').title()}: {results[key]}")
