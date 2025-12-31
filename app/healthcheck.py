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
import urllib.request
import urllib.error


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
    path = os.getenv("HEALTHCHECK_PATH", "/health")

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

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            # Consider any 2xx/3xx as healthy
            if 200 <= status < 400:
                return 0
            else:
                return 1
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception):
        return 1


if __name__ == "__main__":
    sys.exit(main())
