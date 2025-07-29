#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"

echo $DIR

docker build -t="glomap:local" --build-arg CUDA_ARCHITECTURES=75 ${DIR} -f ${DIR}/docker/Dockerfile
# In some cases, you may have to explicitly specify the compute architecture:
#   docker build -t="glomap:latest" --build-arg CUDA_ARCHITECTURES=native .
