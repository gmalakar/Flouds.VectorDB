# Build stage
FROM python:3.12-slim AS builder

# Keep pip lean and avoid .pyc files to shrink copy size
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install build dependencies only in the builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create isolated venv for runtime reuse
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Upgrade pip to fix CVE vulnerabilities (pip <=25.2 affected) with minimal deps
RUN python -m pip install --no-deps --upgrade "pip>=25.3"

# Copy and install Python dependencies into the venv
COPY app/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-compile -r /tmp/requirements.txt

# Debug: capture installed packages and sizes before cleanup
RUN echo "=== Installed Packages ===" && \
    python -m pip list && \
    echo "" && \
    echo "=== Venv Size Before Cleanup ===" && \
    du -sh /opt/venv && \
    echo "" && \
    echo "=== Top 15 Largest Packages ===" && \
    du -sh /opt/venv/lib/python*/site-packages/* 2>/dev/null | sort -rh | head -n 15

# Strip unnecessary files to reduce size
RUN find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyo" -delete && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.exe" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.a" -delete && \
    rm -rf /opt/venv/lib/python3.12/site-packages/pip/_vendor/distlib/*.exe && \
    apt-get remove -y build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /root/.cache /tmp/* && \
    echo "" && \
    echo "=== Venv Size After Cleanup ===" && \
    du -sh /opt/venv

# Runtime stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/flouds-vector \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLOUDS_API_ENV=Production \
    APP_DEBUG_MODE=0 \
    FLOUDS_OPENAPI_URL= \
    FLOUDS_LOG_PATH=/flouds-vector/logs \
    FLOUDS_CLIENTS_DB=/flouds-vector/data/clients.db \
    FLOUDS_APP_SECRETS=/flouds-vector/data/secrets \
    # CSP env overrides (can be JSON array or comma-separated string)
        # CSP is configured in app/config/appsettings.json; keep Dockerfile minimal
    # Docs assets configuration
    FLOUDS_DOCS_ASSET_BASE= \
    FLOUDS_DOCS_USE_PROXY=0 \
    PATH=/opt/venv/bin:$PATH

# Install runtime dependencies only (ca-certificates for HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy prebuilt venv from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR ${PYTHONPATH}

# Copy application code
COPY app ./app

# Create required directories (secrets under data path, logs and clients DB parent)
RUN mkdir -p "$FLOUDS_APP_SECRETS" "$FLOUDS_LOG_PATH" "$(dirname "$FLOUDS_CLIENTS_DB")" && \
    # Make secrets writable (apps may run as non-root and need to write secrets)
    chmod 777 "$FLOUDS_APP_SECRETS" && \
    chmod 777 "$FLOUDS_LOG_PATH" && \
    chmod 777 "$(dirname "$FLOUDS_CLIENTS_DB")"

EXPOSE 19680

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python /flouds-vector/app/healthcheck.py || exit 1

CMD ["python", "-m", "app.main"]
