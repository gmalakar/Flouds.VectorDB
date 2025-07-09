#!/bin/bash

set -e

ENV_FILE=".env"
INSTANCE_NAME="floudsvector-instance"
IMAGE_NAME="gmalakar/flouds-vector:latest"
FLOUDS_VECTOR_NETWORK="flouds_vector_network"

echo "========================================================="
echo "Starting Flouds Vector Service"
echo "========================================================="

# Function to ensure network exists
ensure_network() {
    local name="$1"
    if ! docker network ls --format '{{.Name}}' | grep -q "^${name}$"; then
        echo "🔧 Creating network: $name"
        docker network create "$name"
        echo "✅ Network $name created successfully"
    else
        echo "✅ Network $name already exists"
    fi
}

# Function to attach a container to a network if not already connected
attach_network_if_not_connected() {
    local container="$1"
    local network="$2"
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "⚠️ Container $container is not running. Skipping network attachment."
        return
    fi
    if ! docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$container" | grep -qw "$network"; then
        echo "🔗 Attaching network $network to container $container"
        docker network connect "$network" "$container"
        echo "✅ Successfully connected $container to $network"
    else
        echo "✅ Container $container is already connected to $network"
    fi
}

# Read .env file
if [[ ! -f "$ENV_FILE" ]]; then
    echo "⚠️ $ENV_FILE not found. Make sure environment variables are properly set."
    exit 1
fi

echo "✅ Using environment file: $ENV_FILE"
set -o allexport
source "$ENV_FILE"
set +o allexport

# Set defaults if not defined
: "${VECTORDB_NETWORK:=milvus_network}"
: "${VECTORDB_ENDPOINT:=milvus-standalone}"

# Ensure networks exist
ensure_network "$FLOUDS_VECTOR_NETWORK"
ensure_network "$VECTORDB_NETWORK"

# Stop and remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${INSTANCE_NAME}$"; then
    echo "🛑 Stopping and removing existing container: $INSTANCE_NAME"
    docker stop "$INSTANCE_NAME"
    docker rm "$INSTANCE_NAME"
fi

# Check if Milvus container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${VECTORDB_ENDPOINT}$"; then
    echo "⚠️ Milvus container '$VECTORDB_ENDPOINT' is not running. Vector service may fail to connect."
    read -p "Continue anyway? (y/n) " confirmation
    if [[ "$confirmation" != "y" ]]; then
        echo "Aborted by user."
        exit 0
    fi
fi

# Build docker run command
DOCKER_ARGS=(run -d --name "$INSTANCE_NAME" --network "$FLOUDS_VECTOR_NETWORK" -p 19680:19680)
DOCKER_ARGS+=(-e FLOUDS_API_ENV=Production -e FLOUDS_DEBUG_MODE=0)
for key in VECTORDB_ENDPOINT VECTORDB_PORT VECTORDB_USERNAME VECTORDB_NETWORK; do
    val="${!key}"
    if [[ -n "$val" ]]; then
        DOCKER_ARGS+=(-e "$key=$val")
    fi
done
if [[ -n "$VECTORDB_LOG_PATH" ]]; then
    DOCKER_ARGS+=(-v "$VECTORDB_LOG_PATH:/var/log/flouds:rw")
fi
if [[ -n "$VECTORDB_PASSWORD_FILE" ]]; then
    DOCKER_ARGS+=(-v "$VECTORDB_PASSWORD_FILE:/app/secrets/password.txt:rw")
    DOCKER_ARGS+=(-e "VECTORDB_PASSWORD_FILE=/app/secrets/password.txt")
fi
DOCKER_ARGS+=("$IMAGE_NAME")

echo "🚀 Starting Flouds Vector container..."
echo "Command: docker ${DOCKER_ARGS[*]}"
if docker "${DOCKER_ARGS[@]}"; then
    echo "✅ Flouds Vector container started successfully."
    echo "Waiting for container to initialize..."
    sleep 5

    echo "Connecting to Milvus network..."
    attach_network_if_not_connected "$INSTANCE_NAME" "$VECTORDB_NETWORK"

    if docker ps --format '{{.Names}}' | grep -q "^${VECTORDB_ENDPOINT}$"; then
        echo "Connecting Milvus container to our network..."
        attach_network_if_not_connected "$VECTORDB_ENDPOINT" "$FLOUDS_VECTOR_NETWORK"
    fi

    echo "✅ API available at: http://localhost:19680/docs"
    echo "✅ Network connections established"
else
    echo "❌ Failed to start Flouds Vector container."
    exit 1
fi

# Show logs - optional
read -p "Show container logs? (y/n) " showLogs
if [[ "$showLogs" == "y" ]]; then
    docker logs -f "$INSTANCE_NAME"
fi