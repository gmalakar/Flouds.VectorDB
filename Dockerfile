FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLOUDS_API_ENV=Production \
    FLOUDS_DEBUG_MODE=0

WORKDIR /flouds-vector

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .

# Install all requirements
RUN pip install --no-cache-dir -r requirements.txt

# Clean up build dependencies to reduce image size
RUN apt-get purge -y build-essential && apt-get autoremove -y

# Copy application code
COPY app ./app

# Create required directories
RUN mkdir -p /var/log/flouds /app/secrets

# Remove Python cache
RUN rm -rf /root/.cache/*

EXPOSE 19680

# Directly start the Python application (no entrypoint script)
CMD ["python", "-m", "app.main"]