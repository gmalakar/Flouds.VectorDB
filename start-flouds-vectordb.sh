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

# Valid parameter list
VALID_PARAMS=("--force" "--env-file" "--instance-name" "--image-name" "--port" "--build-image" "--pull-always")
SWITCH_PARAMS=("--force" "--build-image" "--pull-always")

while [[ $# -gt 0 ]]; do
    param="$1"
    
    # Check if parameter is valid
    if [[ ! " ${VALID_PARAMS[@]} " =~ " ${param} " ]]; then
        echo "❌ Error: Invalid parameter '$param'"
        echo "Valid parameters: ${VALID_PARAMS[*]}"
        exit 1
    fi
    
    # Handle parameter based on type
    if [[ " ${SWITCH_PARAMS[@]} " =~ " ${param} " ]]; then
        # Switch parameters
        case "$param" in
            --force) FORCE=true ;;
            --build-image) BUILD_IMAGE=true ;;
            --pull-always) PULL_ALWAYS="--pull always" ;;
        esac
        shift
    else
        # Parameters with values
        if [[ $# -lt 2 ]]; then
            echo "❌ Error: Parameter '$param' requires a value"
            exit 1
        fi
        case "$param" in
            --env-file) ENV_FILE="$2" ;;
            --instance-name) INSTANCE_NAME="$2" ;;
            --image-name) IMAGE_NAME="$2" ;;
            --port) PORT="$2" ;;
        esac
        shift 2
    fi
done

# Default configuration
FLOUDS_VECTOR_NETWORK="flouds_vector_network"
CONTAINER_DATA_PATH="/flouds-vector/data"
CONTAINER_SECRET_PATH="$CONTAINER_DATA_PATH/secrets"
CONTAINER_PASSWORD_FILE="$CONTAINER_SECRET_PATH/password.txt"
CONTAINER_LOG_PATH="/flouds-vector/logs"

# Helper functions
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

test_directory_writable() {
    local path="$1"
    local test_file="${path}/test_write_$$_$(date +%s).tmp"
    if echo "test" > "$test_file" 2>/dev/null && rm -f "$test_file" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

set_directory_permissions() {
    local path="$1"
    local description="$2"
    
    if [[ ! -d "$path" ]]; then
        echo "⚠️ $description directory does not exist: $path"
        echo "Creating directory..."
        if ! mkdir -p "$path"; then
            echo "❌ Failed to create $description directory: $path"
            exit 1
        fi
        echo "✅ $description directory created: $path"
    else
        echo "✅ Found $description directory: $path"
    fi
    
    # Test if directory is writable
    if test_directory_writable "$path"; then
        echo "✅ $description directory is writable: $path"
    else
        echo "⚠️ $description directory is not writable: $path"
        echo "Setting permissions on $description directory..."
        if chmod 755 "$path" 2>/dev/null; then
            echo "✅ Permissions set successfully"
        else
            echo "⚠️ Failed to set permissions on $description directory"
            echo "⚠️ $description may not be writable. Please check directory permissions manually."
            if [[ "$FORCE" != true ]]; then
                read -p "Continue anyway? (y/n) " continue
                if [[ "$continue" != "y" ]]; then
                    echo "Aborted by user."
                    exit 0
                fi
            else
                echo "Force flag set, continuing anyway."
            fi
        fi
    fi
}

# Display header
echo "========================================================="
echo "                FLOUDS VECTOR STARTER SCRIPT             "
echo "========================================================="
echo "Instance Name : $INSTANCE_NAME"
echo "Image         : $IMAGE_NAME"
echo "Environment   : $ENV_FILE"
echo "Port          : $PORT"
echo "========================================================="

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

# Require FLOUDS_DATA_PATH_AT_HOST and FLOUDS_SECRET_PATH_AT_HOST to be set for host mapping
if [[ -z "$FLOUDS_DATA_PATH_AT_HOST" ]]; then
    echo "❌ Error: FLOUDS_DATA_PATH_AT_HOST must be set in the .env file or environment."
    exit 1
fi

if [[ -z "$FLOUDS_SECRET_PATH_AT_HOST" ]]; then
    echo "❌ Error: FLOUDS_SECRET_PATH_AT_HOST must be set in the .env file or environment."
    exit 1
fi

# Set defaults for required variables
: "${VECTORDB_NETWORK:=milvus_network}"
: "${VECTORDB_CONTAINER_NAME:=milvus-standalone}"

# Check and create log directory if needed
if [[ -n "$VECTORDB_LOG_PATH" ]]; then
    set_directory_permissions "$VECTORDB_LOG_PATH" "Log"
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
milvusContainerName="$VECTORDB_CONTAINER_NAME"
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
DOCKER_ARGS=(run -d $PULL_ALWAYS --name "$INSTANCE_NAME" --network "$FLOUDS_VECTOR_NETWORK" -p ${PORT}:${PORT} -e FLOUDS_API_ENV=Production -e APP_DEBUG_MODE=0)

# Add all environment variables from .env file
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Remove quotes from value
    value=$(echo "$value" | sed 's/^["'\'']*//;s/["'\'']*$//')
    
    echo "Setting $key: $value"
    DOCKER_ARGS+=(-e "$key=$value")
done < <(grep -v '^[[:space:]]*$' "$ENV_FILE" 2>/dev/null || true)

# Data directory mapping (SQLite database) — require host data mapping and set clients DB env
if [[ -n "$FLOUDS_DATA_PATH_AT_HOST" ]]; then
    host_data_path="$FLOUDS_DATA_PATH_AT_HOST"
    echo "Mapping Data directory: $host_data_path -> $CONTAINER_DATA_PATH"
    DOCKER_ARGS+=(-v "$host_data_path:$CONTAINER_DATA_PATH:rw")

    # Determine clients DB filename (allow override via env)
    CLIENTS_FILENAME="${FLOUDS_CLIENTS_DB_FILENAME:-clients.db}"
    echo "Using FLOUDS_CLIENTS_DB_FILENAME: $CLIENTS_FILENAME"
    DOCKER_ARGS+=(-e "FLOUDS_CLIENTS_DB=$CONTAINER_DATA_PATH/$CLIENTS_FILENAME")
fi

# Secrets handling: mount FLOUDS_SECRET_PATH_AT_HOST read-only and export VECTORDB_PASSWORD_FILE
if [[ -n "$FLOUDS_SECRET_PATH_AT_HOST" ]]; then
    host_secret_dir="$FLOUDS_SECRET_PATH_AT_HOST"
    set_directory_permissions "$host_secret_dir" "Secrets"

    echo "Mapping Secrets directory: $host_secret_dir -> $CONTAINER_SECRET_PATH"
    DOCKER_ARGS+=(-v "$host_secret_dir:$CONTAINER_SECRET_PATH:ro")

    # Determine password filename (allow override via env)
    PASSWORD_FILENAME="${VECTORDB_PASSWORD_FILENAME:-password.txt}"
    echo "Using VECTORDB_PASSWORD_FILENAME: $PASSWORD_FILENAME"

    # Export container-side env pointing into mounted secrets dir
    DOCKER_ARGS+=(-e "VECTORDB_PASSWORD_FILE=$CONTAINER_SECRET_PATH/$PASSWORD_FILENAME")
else
    echo "❌ Error: FLOUDS_SECRET_PATH_AT_HOST must be set to mount secrets directory."
    exit 1
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
