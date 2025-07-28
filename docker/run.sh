#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"

docker run --gpus all -w /working -v $1:/working -it glomap:latest
