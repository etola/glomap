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
            echo "  --undistort   Run COLMAP undistortion"
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
        --undistort)
            UNDISTORT=true
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
    mkdir -p ${WFOLDER}/sparse

    colmap feature_extractor \
        --image_path    /working/images \
        --database_path ${WFOLDER}/database.db

    colmap exhaustive_matcher --database_path ${WFOLDER}/database.db

    glomap mapper \
        --image_path    /working/images \
        --database_path ${WFOLDER}/database.db \
        --output_path   ${WFOLDER}/sparse

else
    echo "Running COLMAP feature extraction and matching..."

    WFOLDER='/working/colmap'
    mkdir -p ${WFOLDER}/sparse

    colmap feature_extractor \
        --image_path    /working/images \
        --database_path ${WFOLDER}/database.db

    colmap exhaustive_matcher --database_path ${WFOLDER}/database.db

    colmap mapper \
        --image_path    /working/images \
        --database_path ${WFOLDER}/database.db \
        --output_path   ${WFOLDER}/sparse
fi

if [ -d "${WFOLDER}/sparse/0" ]; then
    python3 /scripts/sparse_to_ply.py ${WFOLDER}/sparse/0/ calib.ply
    python3 /scripts/binary_to_text_converter.py ${WFOLDER}/sparse/0
fi


if [ -n "$DENSE" ] || [ -n "$UNDISTORT" ]; then
    mkdir -p ${WFOLDER}/dense
    echo "Running COLMAP undistorted reconstruction..."

    colmap image_undistorter \
        --image_path /working/images \
        --input_path ${WFOLDER}/sparse/0 \
        --output_path ${WFOLDER}/dense \
        --output_type COLMAP

    if [ -d "${WFOLDER}/dense/sparse" ]; then
        python3 /scripts/sparse_to_ply.py ${WFOLDER}/dense/sparse calib.ply
        python3 /scripts/binary_to_text_converter.py ${WFOLDER}/dense/sparse
    fi
fi


if [ -n "$DENSE" ]; then
    mkdir -p ${WFOLDER}/dense

    echo "Running COLMAP dense reconstruction..."

    colmap patch_match_stereo \
        --workspace_path ${WFOLDER}/dense \
        --PatchMatchStereo.geom_consistency true

    colmap stereo_fusion \
        --workspace_path ${WFOLDER}/dense \
        --output_path ${WFOLDER}/dense/fused.ply
else
    echo "No dense reconstruction requested"
    rm -rf ${WFOLDER}/dense/stereo
    rm ${WFOLDER}/dense/run-colmap-geometric.sh
    rm ${WFOLDER}/dense/run-colmap-photometric.sh
fi
