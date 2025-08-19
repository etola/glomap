# COLMAP Binary to Text Converter

This Python script converts COLMAP binary calibration files to their text format equivalents.

## Supported Files

The script converts the following COLMAP binary files:
- `cameras.bin` → `cameras.txt`
- `images.bin` → `images.txt`  
- `points3D.bin` → `points3D.txt`

## Usage

### Basic Usage
```bash
# Convert all binary files in a folder to text format (outputs in same folder)
python binary_to_text_converter.py /path/to/sparse/reconstruction

# Convert binary files to a different output folder
python binary_to_text_converter.py /path/to/sparse/binary /path/to/sparse/text

# Convert only cameras.bin (skip images and points3D for faster processing)
python binary_to_text_converter.py /path/to/sparse/reconstruction --cameras-only
```

### Examples

```bash
# Convert COLMAP reconstruction binary files to text
python binary_to_text_converter.py ./dense/sparse

# Convert and save to separate text folder
python binary_to_text_converter.py ./reconstruction/binary ./reconstruction/text

# Convert only camera calibration data (useful for large datasets)
python binary_to_text_converter.py ./reconstruction/binary --cameras-only
```

## Camera Models Supported

The script supports all major COLMAP camera models:
- **SIMPLE_PINHOLE** (ID: 0): f, cx, cy
- **PINHOLE** (ID: 1): fx, fy, cx, cy
- **SIMPLE_RADIAL** (ID: 2): f, cx, cy, k
- **RADIAL** (ID: 3): f, cx, cy, k1, k2
- **OPENCV** (ID: 4): fx, fy, cx, cy, k1, k2, p1, p2
- **OPENCV_FISHEYE** (ID: 5): fx, fy, cx, cy, k1, k2, k3, k4
- **FULL_OPENCV** (ID: 6): fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6

## Output Format

### cameras.txt
```
# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
1 PINHOLE 1920 1080 1066.778 1067.487 960 540
```

### images.txt
```
# Image list with two lines of data per image:
#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
#   POINTS2D[] as (X, Y, POINT3D_ID)
1 0.851068 0.098017 0.467086 0.220767 -1.34989 4.29558 1.2677 1 IMG_0001.jpg
512.5 384.2 1234 768.1 291.4 5678 ...
```

### points3D.txt
```
# 3D point list with one line of data per point:
#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)
1234 2.567 -1.234 5.678 255 128 64 0.567 1 512 2 346 3 789
```

## Dependencies

- Python 3.6+
- NumPy
- Built-in modules: struct, pathlib, argparse, os

## Features

- **Comprehensive conversion**: Handles all three main COLMAP file types
- **Preserves all data**: Including 2D points, tracks, errors, and full precision
- **Multiple camera models**: Supports all major COLMAP camera models
- **Flexible output**: Can output to same or different directory
- **Cameras-only mode**: Option to convert only camera calibration data for faster processing
- **Error handling**: Graceful handling of missing files and unsupported formats
- **Progress reporting**: Shows conversion progress and statistics

## Notes

- The script will warn if any expected binary files are missing but continue with available files
- Text files will overwrite existing files in the output directory
- Binary format is more compact and faster to read/write, while text format is human-readable and easier to inspect
- All precision from binary format is preserved in the text output using appropriate formatting 