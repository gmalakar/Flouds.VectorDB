# Build stage
FROM python:3.11-alpine AS builder

# Keep pip lean and avoid .pyc files to shrink copy size
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install build dependencies only in the builder (alpine packages are smaller)
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev libffi-dev openssl-dev python3-dev

# Create isolated venv for runtime reuse
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Upgrade pip to fix CVE vulnerabilities (pip <=25.2 affected) with minimal deps
RUN python -m pip install --no-deps --upgrade "pip>=25.3"

# Copy and install Python dependencies into the venv
COPY app/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-compile -r /tmp/requirements.txt && \
    # Strip unnecessary files to reduce size
    find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyo" -delete && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.exe" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python3.11/site-packages/pip/_vendor/distlib/*.exe && \
    # Remove build dependencies to reduce layer size
    apk del .build-deps && \
    # Clean up any remaining pip cache
    rm -rf /root/.cache /tmp/*

# Runtime stage
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/flouds-vector \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLOUDS_API_ENV=Production \
    APP_DEBUG_MODE=0 \
    FLOUDS_LOG_PATH=/flouds-vector/logs \
    FLOUDS_CLIENTS_DB=/flouds-vector/data/clients.db \
    FLOUDS_APP_SECRETS=/flouds-vector/data/secrets \
    PATH=/opt/venv/bin:$PATH

# Install runtime dependencies only (libffi for cryptography, libstdc++ for some C++ libs)
RUN apk add --no-cache libffi libstdc++ && \
    rm -rf /tmp/* /var/cache/apk/*

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
