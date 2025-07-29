#!/bin/bash
set -e

colmap feature_extractor \
    --image_path    /working/images \
    --database_path /working/database.db
colmap exhaustive_matcher --database_path /working/database.db 

glomap mapper \
    --database_path /working/database.db \
    --image_path    /working/images \
    --output_path   /working/sparse
