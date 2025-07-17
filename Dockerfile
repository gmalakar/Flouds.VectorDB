FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLOUDS_API_ENV=Production \
    FLOUDS_DEBUG_MODE=0 \
    FLOUDS_LOG_PATH=/flouds-vector/logs \
    FLOUDS_APP_SECRETS=/flouds-vector/secrets \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /flouds-vector

# Copy requirements first for better layer caching
COPY app/requirements.txt .

# Install dependencies in a single layer with proper cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential netcat-openbsd curl \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/* requirements.txt \
    && find /usr/local -name "*.pyc" -delete \
    && find /usr/local -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Copy application code
COPY app ./app

# Create required directories with proper permissions
RUN mkdir -p $FLOUDS_APP_SECRETS $FLOUDS_LOG_PATH && \
    chmod 755 $FLOUDS_APP_SECRETS && \
    chmod 777 $FLOUDS_LOG_PATH

EXPOSE 19680

CMD ["python", "-m", "app.main"]
