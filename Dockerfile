FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    FLOUDS_API_ENV=Production \
    FLOUDS_DEBUG_MODE=0 \
    FLOUDS_LOG_PATH=/var/log/flouds

WORKDIR /flouds-vector

COPY app/requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential netcat-openbsd curl \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/* \
    && find /usr/local -name "*.pyc" -delete \
    && find /usr/local -name "__pycache__" -exec rm -rf {} +

COPY app ./app

RUN mkdir -p /app/secrets $FLOUDS_LOG_PATH && \
    chmod 755 /app/secrets && \
    chmod 777 $FLOUDS_LOG_PATH

EXPOSE 19680

CMD ["python", "-m", "app.main"]