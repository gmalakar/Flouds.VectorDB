#!/bin/bash

# Usage: milvus-standalone.sh [start|stop|restart|delete] [config-path] [data-path]

set -e

COMMAND="$1"
CONFIG_PATH="$2"
DATA_PATH="$3"

NETWORK_NAME="milvus_network"
MILVUS_NAME="milvus-standalone"

if [[ -z "$COMMAND" ]]; then
    echo "ERROR: Missing command."
    echo "Usage: $0 start|stop|restart|delete [config-path] [data-path]"
    exit 1
fi

if [[ "$COMMAND" == "start" || "$COMMAND" == "restart" ]]; then
    if [[ -z "$CONFIG_PATH" || -z "$DATA_PATH" ]]; then
        echo "ERROR: You must provide both config and data paths for '$COMMAND'."
        echo "Usage: $0 $COMMAND [config-path] [data-path]"
        exit 1
    fi
fi

# Normalize slashes and create directories if needed
if [[ -n "$CONFIG_PATH" ]]; then
    CONFIG_PATH="${CONFIG_PATH//\\//}"
    mkdir -p "$CONFIG_PATH"
fi
if [[ -n "$DATA_PATH" ]]; then
    DATA_PATH="${DATA_PATH//\\//}"
    mkdir -p "$DATA_PATH"
fi

ETCD_CONFIG="$CONFIG_PATH/embedEtcd.yaml"
USER_CONFIG="$CONFIG_PATH/user.yaml"
VOLUME_PATH="$DATA_PATH"

run_embed() {
    # Create config files only if they don't exist
    if [[ ! -e "$ETCD_CONFIG" ]]; then
        echo "Creating etcd config file: $ETCD_CONFIG"
        cat > "$ETCD_CONFIG" <<EOF
listen-client-urls: http://0.0.0.0:2379
advertise-client-urls: http://0.0.0.0:2379
quota-backend-bytes: 4294967296
auto-compaction-mode: revision
auto-compaction-retention: '1000'
EOF
        echo "✓ Created new etcd config file"
    else
        echo "Using existing etcd config file: $ETCD_CONFIG"
    fi

    if [[ ! -e "$USER_CONFIG" ]]; then
        echo "Creating user config file: $USER_CONFIG"
        echo "# Extra config to override default milvus.yaml" > "$USER_CONFIG"
        echo "✓ Created new user config file"
    else
        echo "Using existing user config file: $USER_CONFIG"
    fi

    # Ensure network exists
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        echo "Creating network: $NETWORK_NAME"
        docker network create "$NETWORK_NAME"
    else
        echo "Network $NETWORK_NAME already exists."
    fi

    # Run Milvus container
    echo "Starting Milvus container..."
    docker run -d \
        --network "$NETWORK_NAME" \
        --name "$MILVUS_NAME" \
        --security-opt seccomp:unconfined \
        -e ETCD_USE_EMBED=true \
        -e ETCD_DATA_DIR=/var/lib/milvus/etcd \
        -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml \
        -e COMMON_STORAGETYPE=local \
        -v "$VOLUME_PATH:/var/lib/milvus" \
        -v "$ETCD_CONFIG:/milvus/configs/embedEtcd.yaml" \
        -v "$USER_CONFIG:/milvus/configs/user.yaml" \
        -p 19530:19530 \
        -p 9091:9091 \
        -p 2379:2379 \
        --health-cmd="curl -f http://localhost:9091/healthz" \
        --health-interval=30s \
        --health-start-period=90s \
        --health-timeout=20s \
        --health-retries=3 \
        milvusdb/milvus:v2.5.5 \
        milvus run standalone >/dev/null

    if [[ $? -ne 0 ]]; then
        echo "Failed to start Milvus container."
        exit 1
    fi
}

wait_for_milvus_running() {
    echo "Waiting for Milvus to become healthy..."
    while true; do
        if docker ps | grep "$MILVUS_NAME" | grep -q "healthy"; then
            echo "✓ Milvus started successfully."
            echo "To change the default configuration, edit user.yaml and restart the service."
            break
        fi
        sleep 1
    done
}

start() {
    if docker ps | grep "$MILVUS_NAME" | grep -q "healthy"; then
        echo "Milvus is already running."
        exit 0
    fi

    if docker ps -a | grep -q "$MILVUS_NAME"; then
        echo "Starting existing container..."
        docker start "$MILVUS_NAME" >/dev/null
    else
        echo "Running new Milvus container..."
        run_embed
    fi

    wait_for_milvus_running
}

stop() {
    echo "Stopping Milvus container..."
    if ! docker stop "$MILVUS_NAME" >/dev/null 2>&1; then
        echo "WARNING: Failed to stop Milvus container. It might not be running."
        exit 0
    fi
    echo "✓ Stopped successfully."
}

delete_container() {
    if docker ps | grep -q "$MILVUS_NAME"; then
        echo "ERROR: Please stop Milvus before deleting."
        exit 1
    fi
    if ! docker rm "$MILVUS_NAME" >/dev/null 2>&1; then
        echo "WARNING: Failed to delete Milvus container. It might not exist."
        exit 0
    fi
    echo "✓ Milvus container deleted."
}

delete() {
    delete_container
    if [[ -n "$CONFIG_PATH" ]]; then
        echo "Cleaning up config files in $CONFIG_PATH..."
        rm -f "$ETCD_CONFIG"
        rm -f "$USER_CONFIG"
        echo "✓ Configuration files cleaned"
    fi
    if [[ -n "$DATA_PATH" ]]; then
        echo "Cleaning up data in $DATA_PATH..."
        rm -rf "$DATA_PATH/volumes"
        echo "✓ Data files cleaned"
    fi
    echo "✓ Deleted all Milvus data and configs."
}

case "$COMMAND" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    delete)
        delete
        ;;
    *)
        echo "Unknown command: $COMMAND"
        exit 1
        ;;
esac