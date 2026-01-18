# =============================================================================
# File: healthcheck.py
# Date: 2025-12-23
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
#
# Docker container healthcheck script with configurable endpoints.
# Uses environment variables for flexible configuration without hardcoding.
#
# Environment Variables:
#   HEALTHCHECK_URL      : Complete URL override (e.g., http://localhost:19680/health)
#   HEALTHCHECK_HOST     : Host for healthcheck (default: SERVER_HOST or "localhost")
#   HEALTHCHECK_PORT     : Port for healthcheck (default: SERVER_PORT or "19680")
#   HEALTHCHECK_PATH     : Path for healthcheck (default: "/health")
#   HEALTHCHECK_TIMEOUT  : Request timeout in seconds (default: "8")
# =============================================================================

import os
import sys
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException


def build_healthcheck_url() -> str:
    """
    Build the healthcheck URL from environment variables.

    Priority:
    1. HEALTHCHECK_URL (complete override)
    2. Compose from HEALTHCHECK_HOST/PORT/PATH
    3. Fall back to SERVER_HOST/PORT defaults

    Returns:
        str: Complete healthcheck URL
    """
    # Explicit URL overrides everything if provided
    explicit = os.getenv("HEALTHCHECK_URL")
    if explicit:
        return explicit

    # Compose from host/port/path envs to avoid hardcoding
    host = os.getenv("HEALTHCHECK_HOST", os.getenv("SERVER_HOST", "localhost"))
    port = os.getenv("HEALTHCHECK_PORT", os.getenv("SERVER_PORT", "19680"))
    path = os.getenv("HEALTHCHECK_PATH", "/api/v1/health")

    # Normalize path
    if not path.startswith("/"):
        path = f"/{path}"

    return f"http://{host}:{port}{path}"


def main() -> int:
    """
    Execute healthcheck request.

    Returns:
        int: 0 if healthy (2xx/3xx response), 1 otherwise
    """
    url = build_healthcheck_url()
    timeout_s = float(os.getenv("HEALTHCHECK_TIMEOUT", "8"))

    # Basic safety: only allow http(s) schemes and restrict hosts to localhost by default
    parsed = urlparse(url)
    allowed_schemes = {"http", "https"}
    server_host = os.getenv("SERVER_HOST", "localhost")
    allowed_hosts = {"localhost", "127.0.0.1", "::1", server_host}

    if parsed.scheme not in allowed_schemes:
        return 1

    hostname = parsed.hostname or ""
    if hostname not in allowed_hosts:
        # refuse to call out to arbitrary hosts by default
        return 1

    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout_s)
        status = getattr(resp, "status_code", 200)
        if 200 <= status < 400:
            return 0
        return 1
    except RequestException:
        return 1


if __name__ == "__main__":
    sys.exit(main())
