FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLOUDS_API_ENV=Production \
    FLOUDS_DEBUG_MODE=0

WORKDIR /flouds-py

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .

# Install all requirements (no torch, no onnx)
RUN pip install --no-cache-dir -r requirements.txt

# Clean up build dependencies to reduce image size
RUN apt-get purge -y build-essential && apt-get autoremove -y

COPY app ./app

# Remove Python cache
RUN rm -rf /root/.cache/*

EXPOSE 19680

ENV FLOUDS_ONNX_ROOT=/flouds-py/onnx
RUN mkdir -p $FLOUDS_ONNX_ROOT

RUN find / -type f -size +10M -exec du -h {} + | sort -hr > /large_files.log || true

CMD ["python", "-m", "app.main"]