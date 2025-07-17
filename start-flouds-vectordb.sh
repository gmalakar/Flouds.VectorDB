#!/bin/bash
# =============================================================================
# File: start-flouds-vectordb.sh
# Date: 2024-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
#
# This script sets up and runs the Flouds Vector container with proper volume mapping
# and environment variable handling based on a .env file.
#
# Usage:
#   ./start-flouds-vectordb.sh [--env-file <path>] [--instance <name>] [--image <name>] [--port <port>] [--force] [--build-image] [--pull-always]
#
# Parameters:
#   --env-file     : Path to .env file (default: ".env")
#   --instance     : Name of the Docker container (default: "floudsvector-instance")
#   --image        : Docker image to use (default: "gmalakar/flouds-vector:latest")
#   --port         : Port to expose for the API (default: 19680)
#   --force        : Force restart container if it exists
#   --build-image  : Build Docker image locally before starting container
#   --pull-always  : Always pull image from registry before running
# =============================================================================

set -e

# Parse command line arguments
ENV_FILE=".env"
INSTANCE_NAME="floudsvector-instance"
IMAGE_NAME="gmalakar/flouds-vector:latest"
PORT=19680
PULL_ALWAYS=""
FORCE=false
BUILD_IMAGE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --instance)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --pull-always)
            PULL_ALWAYS="--pull always"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --build-image)
            BUILD_IMAGE=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default configuration
FLOUDS_VECTOR_NETWORK="flouds_vector_network"
CONTAINER_PASSWORD_FILE="/flouds-vector/secrets/password.txt"
CONTAINER_LOG_PATH="/flouds-vector/logs"

# Display header
echo "========================================================="
echo "                FLOUDS VECTOR STARTER SCRIPT             "
echo "========================================================="
echo "Instance Name : $INSTANCE_NAME"
echo "Image         : $IMAGE_NAME"
echo "Environment   : $ENV_FILE"
echo "Port          : $PORT"
echo "========================================================="

# Helper: ensure network exists
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

# Helper: attach network if not already connected
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
    echo "⚠️ $ENV_FILE not found. Using default values."
else
    echo "✅ Using environment file: $ENV_FILE"
    # Convert to Unix line endings
    awk '{ sub("\r$", ""); print }' "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
fi

# Set defaults for required variables
: "${VECTORDB_NETWORK:=milvus_network}"
: "${VECTORDB_ENDPOINT:=milvus-standalone}"

# Check and create log directory if needed
if [[ -n "$VECTORDB_LOG_PATH" ]]; then
    if [[ ! -d "$VECTORDB_LOG_PATH" ]]; then
        echo "⚠️ Log directory does not exist: $VECTORDB_LOG_PATH"
        echo "Creating directory..."
        mkdir -p "$VECTORDB_LOG_PATH"
        echo "✅ Log directory created: $VECTORDB_LOG_PATH"
    else
        echo "✅ Found log directory: $VECTORDB_LOG_PATH"
    fi
else
    echo "⚠️ VECTORDB_LOG_PATH not set. Container logs will not be persisted to host."
fi

# Ensure networks exist
ensure_network "$FLOUDS_VECTOR_NETWORK"
ensure_network "$VECTORDB_NETWORK"

# Stop and remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${INSTANCE_NAME}$"; then
    echo "🛑 Stopping and removing existing container: $INSTANCE_NAME"
    docker stop "$INSTANCE_NAME"
    docker rm "$INSTANCE_NAME"
    echo "✅ Container removed"
fi

# Build image if requested
if [[ "$BUILD_IMAGE" == true ]]; then
    echo "Building Docker image: $IMAGE_NAME"
    docker build -t "$IMAGE_NAME" .
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to build Docker image."
        exit 1
    fi
    echo "✅ Docker image built successfully"
fi

# Check if Milvus is running
milvusContainerName="$VECTORDB_ENDPOINT"
if ! docker ps --format '{{.Names}}' | grep -q "^${milvusContainerName}$"; then
    echo "⚠️ Milvus container '$milvusContainerName' is not running. Vector service may fail to connect."
    if [[ "$FORCE" != true ]]; then
        read -p "Continue anyway? (y/n) " confirmation
        if [[ "$confirmation" != "y" ]]; then
            echo "Aborted by user."
            exit 0
        fi
    else
        echo "Force flag set, continuing anyway."
    fi
else
    echo "✅ Milvus container '$milvusContainerName' is running"
fi

# Build Docker run command
DOCKER_ARGS=(run -d $PULL_ALWAYS --name "$INSTANCE_NAME" --network "$FLOUDS_VECTOR_NETWORK" -p ${PORT}:${PORT} -e FLOUDS_API_ENV=Production -e FLOUDS_DEBUG_MODE=0)

# Add environment variables
for key in VECTORDB_ENDPOINT VECTORDB_PORT VECTORDB_USERNAME VECTORDB_NETWORK; do
    val="${!key}"
    if [[ -n "$val" ]]; then
        echo "Setting $key: $val"
        DOCKER_ARGS+=(-e "$key=$val")
    fi
done

# Add password file if specified
if [[ -n "$VECTORDB_PASSWORD_FILE" ]]; then
    echo "Mounting password file: $VECTORDB_PASSWORD_FILE → $CONTAINER_PASSWORD_FILE"
    DOCKER_ARGS+=(-v "$VECTORDB_PASSWORD_FILE:$CONTAINER_PASSWORD_FILE:rw")
    DOCKER_ARGS+=(-e "VECTORDB_PASSWORD_FILE=$CONTAINER_PASSWORD_FILE")
fi

# Add log directory if specified
if [[ -n "$VECTORDB_LOG_PATH" ]]; then
    echo "Mounting logs: $VECTORDB_LOG_PATH → $CONTAINER_LOG_PATH"
    DOCKER_ARGS+=(-v "$VECTORDB_LOG_PATH:$CONTAINER_LOG_PATH:rw")
    DOCKER_ARGS+=(-e "FLOUDS_LOG_PATH=$CONTAINER_LOG_PATH")
fi

DOCKER_ARGS+=("$IMAGE_NAME")

echo "========================================================="
echo "Starting Flouds Vector container..."
echo "Command: docker ${DOCKER_ARGS[*]}"

# Start container
if docker "${DOCKER_ARGS[@]}"; then
    echo "✅ Flouds Vector container started successfully"
    echo "Waiting for container to initialize..."
    sleep 5

    echo "Connecting container to Milvus network..."
    attach_network_if_not_connected "$INSTANCE_NAME" "$VECTORDB_NETWORK"

    if docker ps --format '{{.Names}}' | grep -q "^${milvusContainerName}$"; then
        echo "Connecting Milvus to Flouds Vector network..."
        attach_network_if_not_connected "$milvusContainerName" "$FLOUDS_VECTOR_NETWORK"
    fi

    echo "========================================================="
    echo "Container Status:"
    docker ps --filter "name=$INSTANCE_NAME" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
    echo "========================================================="
    echo "API available at: http://localhost:${PORT}/docs"
else
    echo "❌ Failed to start Flouds Vector container."
    exit 1
fi

echo "========================================================="
echo "Container Management:"
echo "  * View logs: docker logs -f $INSTANCE_NAME"
echo "  * Stop container: docker stop $INSTANCE_NAME"
echo "  * Remove container: docker rm $INSTANCE_NAME"
echo

read -p "Would you like to view container logs now? (y/n) " showLogs
if [[ "$showLogs" == "y" || "$showLogs" == "Y" ]]; then
    docker logs -f "$INSTANCE_NAME"
fi
echo "========================================================="
