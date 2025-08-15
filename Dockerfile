# Build stage
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY app/requirements.txt /tmp/
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLOUDS_API_ENV=Production \
    APP_DEBUG_MODE=0 \
    FLOUDS_LOG_PATH=/flouds-vector/logs \
    FLOUDS_APP_SECRETS=/flouds-vector/secrets \
    PATH=/root/.local/bin:$PATH

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

WORKDIR /flouds-vector

# Copy application code
COPY app ./app

# Create required directories and cleanup
RUN mkdir -p $FLOUDS_APP_SECRETS $FLOUDS_LOG_PATH && \
    chmod 755 $FLOUDS_APP_SECRETS && \
    chmod 777 $FLOUDS_LOG_PATH && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

EXPOSE 19680

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:19680/health || exit 1

CMD ["python", "-m", "app.main"]
