#!/bin/bash

# Check if any argument is provided.
if [ $# -eq 0 ]; then
    echo "Usage: $0 <host_directory>"
    echo "Example: $0 ../dataset/"
    exit 1
fi

# Check if local glomap:local image exists (in case you ran build.sh), otherwise use official image
if docker image inspect glomap:local >/dev/null 2>&1; then
    echo "Using local GLOMAP Docker image..."
    GLOMAP_IMAGE="glomap:local"
else
    echo "Local GLOMAP image not found, pulling official image..."
    echo "run ./build.sh to build the local image first."
    exit 1
fi

# Get absolute path
HOST_DIR=$(realpath "$1")
if [ ! -d "$HOST_DIR" ]; then
    echo "Error: Directory '$HOST_DIR' does not exist."
    exit 1
fi
echo "Running GLOMAP container with directory: $HOST_DIR"

# --- Build Docker Arguments ---
# Start with the base arguments.
DOCKER_ARGS=(
    -it --rm
    -v "${HOST_DIR}:/working"
    -w /working
    -v /etc/passwd:/etc/passwd:ro
    -v /etc/group:/etc/group:ro
    --user $(id -u):$(id -g)
)

# --- GPU Detection and Configuration ---
echo "Testing for GPU acceleration..."
# A successful `nvidia-smi` call is the most reliable test.
if docker run --rm --runtime=nvidia "${GLOMAP_IMAGE}" nvidia-smi >/dev/null 2>&1; then
    echo "✅ GPU detected. Using --runtime=nvidia."
    DOCKER_ARGS+=( --runtime=nvidia )
else
    echo "⚠️  GPU not detected. Using CPU mode."
fi

# --- Execute the Container ---
# Always start an interactive bash shell.
echo "Starting interactive bash shell..."
docker run "${DOCKER_ARGS[@]}" "${GLOMAP_IMAGE}" process-dataset.sh
