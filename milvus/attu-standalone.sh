#!/bin/bash

# Set constants
NETWORK_NAME="milvus_network"
MILVUS_NAME="milvus-standalone"
ATTU_NAME="attu-instance"

# Ensure network exists
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    echo "Creating network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
else
    echo "Network $NETWORK_NAME already exists."
fi

# Check if Milvus container is running
if ! docker inspect -f "{{.State.Running}}" "$MILVUS_NAME" &>/dev/null || \
   ! docker inspect -f "{{.State.Running}}" "$MILVUS_NAME" | grep -q "true"; then
    echo "ERROR: Milvus container \"$MILVUS_NAME\" is not running."
    echo "Please start Milvus before launching ATTU."
    exit 1
fi

# Check if ATTU container exists
if docker ps -a --format "{{.Names}}" | grep -q "$ATTU_NAME"; then
    echo "Stopping and removing existing ATTU container: $ATTU_NAME"
    docker stop "$ATTU_NAME" >/dev/null
    docker rm "$ATTU_NAME" >/dev/null
fi

# Run ATTU container
echo "Starting ATTU container..."
docker run -d \
    --network "$NETWORK_NAME" \
    --name "$ATTU_NAME" \
    -p 8000:3000 \
    -e MILVUS_URL="$MILVUS_NAME" \
    zilliz/attu:latest >/dev/null

# Wait for ATTU container to be running
echo "Waiting for ATTU container to be live..."
retries=10
while [ $retries -gt 0 ]; do
    if docker inspect -f "{{.State.Running}}" "$ATTU_NAME" 2>/dev/null | grep -q "true"; then
        echo "ATTU container is running."
        echo "Done."
        exit 0
    fi
    retries=$((retries-1))
    sleep 2
done

echo "ERROR: ATTU container failed to start."
exit 1
