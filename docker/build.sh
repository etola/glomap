#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"

# Parse arguments
DISABLE_CUDA=false
for arg in "$@"; do
    case $arg in
        --disable-cuda)
            DISABLE_CUDA=true
            shift
            ;;
    esac
done

echo "Building from: $DIR"

if [ "$DISABLE_CUDA" = true ]; then
    echo "Building without CUDA support..."
    docker build -t="glomap:local-nocuda" ${DIR} -f ${DIR}/docker/Dockerfile.nocuda
else
    echo "Building with CUDA support..."
    docker build -t="glomap:local" --build-arg CUDA_ARCHITECTURES=75 ${DIR} -f ${DIR}/docker/Dockerfile
    # In some cases, you may have to explicitly specify the compute architecture:
    #   docker build -t="glomap:latest" --build-arg CUDA_ARCHITECTURES=native .
fi
