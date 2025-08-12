# COLMAP Sparse Reconstruction to PLY Converter

This script (`sparse_to_ply.py`) converts COLMAP sparse reconstruction data into a PLY point cloud file that contains both the sparse 3D points and camera coordinate frames for visualization.

## Features

- ✅ **Sparse Point Cloud**: Reads 3D points with colors from COLMAP reconstruction
- ✅ **Camera Visualization**: Shows camera positions and orientations as RGB coordinate frames
  - 🔴 **Red points**: X-axis direction (camera right)
  - 🟢 **Green points**: Y-axis direction (camera down)  
  - 🔵 **Blue points**: Z-axis direction (camera forward)
- ✅ **Dual Format Support**: Reads both binary (.bin) and text (.txt) COLMAP files
- ✅ **Customizable**: Adjustable camera frame scale and point density

## Usage

### Basic Usage
```bash
python sparse_to_ply.py /path/to/sparse/reconstruction output.ply
```

### Advanced Options
```bash
# Custom camera frame scale
python sparse_to_ply.py /path/to/sparse output.ply --camera-scale 0.2

# Only point cloud (no camera frames)
python sparse_to_ply.py /path/to/sparse output.ply --no-cameras

# More points per camera axis
python sparse_to_ply.py /path/to/sparse output.ply --camera-points-per-axis 20
```

### All Options
```bash
python sparse_to_ply.py --help
```

## Input Requirements

The script expects a COLMAP sparse reconstruction folder containing one of these sets:

### Binary Format (preferred)
- `cameras.bin` - Camera intrinsic parameters
- `images.bin` - Camera poses and image information  
- `points3D.bin` - 3D points with colors

### Text Format (fallback)
- `cameras.txt` - Camera intrinsic parameters
- `images.txt` - Camera poses and image information
- `points3D.txt` - 3D points with colors

## Output

The script generates a PLY file containing:
1. **Original 3D points** from the sparse reconstruction with their RGB colors
2. **Camera coordinate frames** as colored point sets:
   - Each camera gets 3 axes (X, Y, Z) represented as lines of colored points
   - Points are colored Red-Green-Blue corresponding to X-Y-Z axes
   - Frame scale is adjustable to fit your scene

## Examples

### Example 1: Basic conversion
```bash
# Convert COLMAP sparse reconstruction to PLY
python sparse_to_ply.py /dataset/sparse/0 reconstruction.ply
```

### Example 2: Large scene with smaller camera frames
```bash
# Use smaller camera frames for large scenes
python sparse_to_ply.py /dataset/sparse/0 output.ply --camera-scale 0.05
```

### Example 3: Dense camera visualization
```bash
# More detailed camera coordinate frames
python sparse_to_ply.py /dataset/sparse/0 output.ply --camera-points-per-axis 20
```

## Viewing the Results

The generated PLY files can be viewed in:
- **CloudCompare** (recommended) - Free, powerful point cloud viewer
- **MeshLab** - Good for point clouds and mesh processing
- **ParaView** - Scientific visualization software
- **Blender** - 3D modeling software (import as point cloud)

## Camera Coordinate System

The script follows COLMAP's camera coordinate convention:
- **X-axis** (Red): Points to the right in the image
- **Y-axis** (Green): Points downward in the image  
- **Z-axis** (Blue): Points forward (viewing direction)

## Technical Details

### Coordinate Transformations
- Camera centers are computed as: `-R^T * t` where R is rotation matrix and t is translation
- Coordinate frames are transformed from camera space to world space
- Quaternions are converted to rotation matrices using Hamilton convention

### File Format Support
- **Binary files**: Fast reading, smaller file size (preferred by COLMAP)
- **Text files**: Human-readable, easier for debugging and manual inspection
- The script automatically detects and uses the available format

### Performance
- Efficient binary reading for large reconstructions
- Memory-efficient point generation
- ASCII PLY output for maximum compatibility

## Integration with GLOMAP

This script complements the GLOMAP pipeline by providing visualization for:
- Quality assessment of sparse reconstructions
- Camera pose verification
- Debugging reconstruction issues
- Preparation for dense reconstruction or further processing

## Dependencies

- Python 3.6+
- NumPy
- No additional dependencies required 