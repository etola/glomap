#!/bin/bash
set -e

# default is to run GLOMAP

for i in "$@"; do
    case $i in
        --help)
            echo "Usage: $0 <host_directory> [--colmap]"
            echo "Example: $0 ../dataset/"
            echo "Options:"
            echo "  --help    Show this help message"
            echo "  --colmap   Run COLMAP feature extraction and matching"
            echo "  --dense   Run COLMAP dense reconstruction after SFM computation"
            echo "             If no options are provided, runs GLOMAP processing."
            exit 0
            ;;
        --colmap)
            COLMAP=true
            shift
            ;;
        --dense)
            DENSE=true
            shift
            ;;
        *)
        echo "ERROR: Unknown option '$i'." >&2
            echo "Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

WFOLDER='/working/'

if [ -z "$COLMAP" ]; then
    echo "Running GLOMAP processing..."

    WFOLDER='/working/glomap'

    colmap feature_extractor \
        --image_path    ${WFOLDER}/images \
        --database_path ${WFOLDER}/database.db
    colmap exhaustive_matcher --database_path ${WFOLDER}/database.db 

    glomap mapper \
        --database_path ${WFOLDER}/database.db \
        --image_path    ${WFOLDER}/images \
        --output_path   ${WFOLDER}/sparse

else
    echo "Running COLMAP feature extraction and matching..."

    WFOLDER='/working/colmap'

    colmap feature_extractor \
        --image_path    ${WFOLDER}/images \
        --database_path ${WFOLDER}/database.db
    colmap exhaustive_matcher --database_path ${WFOLDER}/database.db 

    colmap mapper \
        --database_path ${WFOLDER}/database.db \
        --image_path    ${WFOLDER}/images \
        --output_path   ${WFOLDER}/sparse
fi

if [ -n "$DENSE" ]; then
    echo "Running COLMAP dense reconstruction..."

    colmap patch_match_stereo \
        --workspace_path ${WFOLDER}/dense \
        --PatchMatchStereo.geom_consistency true

    colmap stereo_fusion \
        --workspace_path ${WFOLDER}/dense \
        --output_path ${WFOLDER}/dense/fused.ply
fi
