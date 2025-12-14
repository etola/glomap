#!/bin/bash
set -e

# default is to run GLOMAP

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            echo "Usage: $0 [--colmap] [--undistort] [--dense] [--max-resolution <value>]"
            echo "Options:"
            echo "  --help    Show this help message"
            echo "  --colmap   Run COLMAP feature extraction and matching"
            echo "  --undistort   Run COLMAP undistorted reconstruction"
            echo "  --dense   Run COLMAP dense reconstruction after SFM computation"
            echo "  --max-resolution <value>   Maximum image resolution for undistorted reconstruction"
            echo "             If no options are provided, runs GLOMAP processing."
            echo "  --mesh    Run Poisson meshing after dense reconstruction (implies --dense)"
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
        --max-resolution)
            if [[ -n "$2" ]] && [[ "$2" != --* ]]; then
                MAX_RESOLUTION=$2
                shift 2
            else
                echo "ERROR: --max-resolution requires a value." >&2
                exit 1
            fi
            ;;
        *)
            echo "ERROR: Unknown option '$1'." >&2
            echo "Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

WFOLDER='/working/'

CONFIG_FILE='/working/config.yaml'
if [ "${COLMAP}" ]; then
    echo 'runner: colmap'
    echo 'runner: colmap' > ${CONFIG_FILE}
else
    echo 'runner: glomap' > ${CONFIG_FILE}
fi
if [ -n "$DENSE" ]; then
    echo 'densification: enabled' >> ${CONFIG_FILE}
fi
if [ -n "$MAX_RESOLUTION" ]; then
    echo "max_resolution: ${MAX_RESOLUTION}" >> ${CONFIG_FILE}
fi
if [ -n "$MESHING" ]; then
    echo 'meshing: enabled' >> ${CONFIG_FILE}
fi

ASSETS_FOLDER='/working/assets'
mkdir -p ${ASSETS_FOLDER}

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

echo "/scripts/export_calibration.py '/working' -o ${ASSETS_FOLDER}/calibration.json"
/scripts/export_calibration.py '/working' -o ${ASSETS_FOLDER}/calibration.json

cp -r ${WFOLDER}/sparse/0 ${ASSETS_FOLDER}/sparse/
python3 /scripts/sparse_to_ply.py ${ASSETS_FOLDER}/sparse calib.ply
python3 /scripts/binary_to_text_converter.py ${ASSETS_FOLDER}/sparse

if [ -n "$DENSE" ] || [ -n "$UNDISTORT" ]; then
    mkdir -p ${WFOLDER}/dense
    echo "Running COLMAP undistorted reconstruction..."

    if [ -n "$MAX_RESOLUTION" ]; then
        colmap image_undistorter \
            --image_path /working/images \
            --input_path ${WFOLDER}/sparse/0 \
            --output_path ${WFOLDER}/dense \
            --output_type COLMAP \
            --max_image_size $MAX_RESOLUTION
    else
        colmap image_undistorter \
            --image_path /working/images \
            --input_path ${WFOLDER}/sparse/0 \
            --output_path ${WFOLDER}/dense \
            --output_type COLMAP
    fi

    if [ -d "${WFOLDER}/dense/sparse" ]; then
        python3 /scripts/sparse_to_ply.py ${WFOLDER}/dense/sparse calib.ply
        python3 /scripts/binary_to_text_converter.py ${WFOLDER}/dense/sparse
    fi

fi

# if [ -d "${WFOLDER}/sparse/0" ]; then
#     python3 /scripts/sparse_to_ply.py ${WFOLDER}/sparse/0/ calib.ply
#     python3 /scripts/binary_to_text_converter.py ${WFOLDER}/sparse/0
# fi

if [ -n "$DENSE" ]; then
    mkdir -p ${WFOLDER}/dense

    echo "Running COLMAP dense reconstruction..."

    PM_RESOLUTION=512
    if [ "$MAX_RESOLUTION" -le 512 ]; then
        PM_RESOLUTION=256
    fi

    echo "pm_resolution: ${PM_RESOLUTION}" >> ${CONFIG_FILE}

    echo "Running RESOLUTION for PatchMatchStereo: ${PM_RESOLUTION}"

    colmap patch_match_stereo \
        --workspace_path ${WFOLDER}/dense \
        --PatchMatchStereo.geom_consistency 0 \
        --PatchMatchStereo.window_radius 7 \
        --PatchMatchStereo.num_samples 7 \
        --PatchMatchStereo.num_iterations 2 \
        --PatchMatchStereo.max_image_size ${PM_RESOLUTION}

    colmap stereo_fusion \
        --workspace_path ${WFOLDER}/dense \
        --output_path ${WFOLDER}/dense/fused.ply \
        --input_type photometric

    # if [ -n "$MESHING" ]; then
    #     echo "Running COLMAP Poisson meshing..."
    #     mkdir -p ${WFOLDER}/dense/poisson
    #     colmap poisson_mesher \
    #         --input_path ${WFOLDER}/dense/fused.ply \
    #         --output_path ${WFOLDER}/dense/poisson/meshed-poisson.ply \
    #         --PoissonMeshing.depth 8
    # fi

    cp ${WFOLDER}/dense/fused.ply ${ASSETS_FOLDER}/point_cloud.ply

fi

