#!/usr/bin/env python3
"""
COLMAP Sparse Reconstruction to PLY Converter

This script reads COLMAP sparse reconstruction data (cameras.bin/txt, images.bin/txt, points3D.bin/txt)
and generates a PLY file containing:
1. The sparse 3D point cloud with colors
2. Camera positions and orientations visualized as RGB coordinate frames
   - Red points: X-axis direction
   - Green points: Y-axis direction  
   - Blue points: Z-axis direction

Usage:
    python sparse_to_ply.py <sparse_folder> <output.ply> [options]

Example:
    python sparse_to_ply.py /path/to/sparse/reconstruction reconstruction.ply --camera-scale 0.1
"""

import argparse
import struct
import numpy as np
import os
from pathlib import Path


def read_cameras_text(path):
    """Read COLMAP cameras.txt file."""
    cameras = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            camera_id = int(parts[0])
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = [float(x) for x in parts[4:]]
            
            # Map model names to model IDs
            model_name_to_id = {
                "SIMPLE_PINHOLE": 0, "PINHOLE": 1, "SIMPLE_RADIAL": 2,
                "RADIAL": 3, "OPENCV": 4
            }
            model_id = model_name_to_id.get(model, -1)
            
            cameras[camera_id] = {
                'model_id': model_id,
                'width': width,
                'height': height,
                'params': params
            }
    return cameras


def read_images_text(path):
    """Read COLMAP images.txt file."""
    images = {}
    with open(path, "r") as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        
        # First line: image info
        parts = line.split()
        image_id = int(parts[0])
        qvec = [float(x) for x in parts[1:5]]  # qw, qx, qy, qz
        tvec = [float(x) for x in parts[5:8]]  # tx, ty, tz
        camera_id = int(parts[8])
        name = parts[9] if len(parts) > 9 else f"image_{image_id}"
        
        images[image_id] = {
            'qvec': np.array(qvec),
            'tvec': np.array(tvec),
            'camera_id': camera_id,
            'name': name
        }
        
        # Skip second line (2D points)
        i += 2
    
    return images


def read_points3D_text(path):
    """Read COLMAP points3D.txt file."""
    points3D = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            point3D_id = int(parts[0])
            xyz = [float(x) for x in parts[1:4]]
            rgb = [int(x) for x in parts[4:7]]
            # Skip error and track info for PLY generation
            
            points3D[point3D_id] = {
                'xyz': np.array(xyz),
                'rgb': np.array(rgb)
            }
    return points3D


def read_cameras_binary(path):
    """Read COLMAP cameras.bin file."""
    cameras = {}
    with open(path, "rb") as f:
        num_cameras = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_cameras):
            camera_id = struct.unpack("<I", f.read(4))[0]
            model_id = struct.unpack("<i", f.read(4))[0]
            width = struct.unpack("<Q", f.read(8))[0]
            height = struct.unpack("<Q", f.read(8))[0]
            
            # Read parameters based on camera model
            if model_id in [0, 1]:  # SIMPLE_PINHOLE, PINHOLE
                params = struct.unpack("<4d", f.read(32))
            elif model_id in [2, 3]:  # SIMPLE_RADIAL, RADIAL
                params = struct.unpack("<3d", f.read(24))
            elif model_id == 4:  # OPENCV
                params = struct.unpack("<8d", f.read(64))
            else:
                raise NotImplementedError(f"Camera model {model_id} not supported")
            
            cameras[camera_id] = {
                'model_id': model_id,
                'width': width,
                'height': height,
                'params': params
            }
    return cameras


def read_images_binary(path):
    """Read COLMAP images.bin file."""
    images = {}
    with open(path, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack("<I", f.read(4))[0]
            # Quaternion (w, x, y, z)
            qvec = struct.unpack("<4d", f.read(32))
            # Translation vector (x, y, z)
            tvec = struct.unpack("<3d", f.read(24))
            camera_id = struct.unpack("<I", f.read(4))[0]
            
            # Read image name
            name = b""
            while True:
                c = f.read(1)
                if c == b"\x00":
                    break
                name += c
            name = name.decode("utf-8")
            
            # Skip 2D points
            num_points2D = struct.unpack("<Q", f.read(8))[0]
            f.read(num_points2D * 24)  # Each point2D: 16 bytes (x,y) + 8 bytes (point3D_id)
            
            images[image_id] = {
                'qvec': np.array(qvec),
                'tvec': np.array(tvec),
                'camera_id': camera_id,
                'name': name
            }
    return images


def read_points3D_binary(path):
    """Read COLMAP points3D.bin file."""
    points3D = {}
    with open(path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            point3D_id = struct.unpack("<Q", f.read(8))[0]
            # 3D coordinates (x, y, z)
            xyz = struct.unpack("<3d", f.read(24))
            # RGB color
            rgb = struct.unpack("<3B", f.read(3))
            # Error (reprojection error)
            error = struct.unpack("<d", f.read(8))[0]
            
            # Read track (skip for PLY generation)
            track_length = struct.unpack("<Q", f.read(8))[0]
            f.read(track_length * 8)  # Each track element: 4 bytes (image_id) + 4 bytes (point2D_idx)
            
            points3D[point3D_id] = {
                'xyz': np.array(xyz),
                'rgb': np.array(rgb)
            }
    return points3D


def read_colmap_data(sparse_folder):
    """Read COLMAP data, preferring binary format over text format."""
    sparse_folder = Path(sparse_folder)
    
    # Try binary format first
    cameras_bin = sparse_folder / "cameras.bin"
    images_bin = sparse_folder / "images.bin"
    points3D_bin = sparse_folder / "points3D.bin"
    
    if all(f.exists() for f in [cameras_bin, images_bin, points3D_bin]):
        print("Reading binary format...")
        cameras = read_cameras_binary(cameras_bin)
        images = read_images_binary(images_bin)
        points3D = read_points3D_binary(points3D_bin)
        return cameras, images, points3D
    
    # Fall back to text format
    cameras_txt = sparse_folder / "cameras.txt"
    images_txt = sparse_folder / "images.txt"
    points3D_txt = sparse_folder / "points3D.txt"
    
    if all(f.exists() for f in [cameras_txt, images_txt, points3D_txt]):
        print("Reading text format...")
        cameras = read_cameras_text(cameras_txt)
        images = read_images_text(images_txt)
        points3D = read_points3D_text(points3D_txt)
        return cameras, images, points3D
    
    # Check what's missing
    missing_files = []
    for name, path in [("cameras", cameras_bin), ("images", images_bin), ("points3D", points3D_bin)]:
        if not path.exists() and not (sparse_folder / f"{name}.txt").exists():
            missing_files.append(f"{name}.bin or {name}.txt")
    
    raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")


def quaternion_to_rotation_matrix(qvec):
    """Convert quaternion to rotation matrix.
    
    Args:
        qvec: Quaternion as [w, x, y, z]
    
    Returns:
        3x3 rotation matrix
    """
    w, x, y, z = qvec
    return np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*w*z, 2*x*z + 2*w*y],
        [2*x*y + 2*w*z, 1 - 2*x*x - 2*z*z, 2*y*z - 2*w*x],
        [2*x*z - 2*w*y, 2*y*z + 2*w*x, 1 - 2*x*x - 2*y*y]
    ])


def generate_camera_coordinate_frame(position, rotation_matrix, scale=0.1, num_points_per_axis=10):
    """Generate points for camera coordinate frame visualization.
    
    Args:
        position: Camera center position (3,)
        rotation_matrix: Camera rotation matrix (3, 3)
        scale: Scale factor for coordinate frame axes
        num_points_per_axis: Number of points per axis
        
    Returns:
        points: Array of coordinate frame points (N, 3)
        colors: Array of RGB colors for each point (N, 3)
    """
    # Camera coordinate system axes (X: right, Y: down, Z: forward)
    axes = np.array([
        [1, 0, 0],  # X-axis (Red)
        [0, 1, 0],  # Y-axis (Green)  
        [0, 0, 1]   # Z-axis (Blue)
    ]) * scale
    
    # Transform axes to world coordinates
    world_axes = rotation_matrix.T @ axes.T  # Transpose to go from camera to world
    
    points = []
    colors = []
    
    # Generate points along each axis
    for i, (axis, color) in enumerate(zip(world_axes.T, [[255, 0, 0], [0, 255, 0], [0, 0, 255]])):
        for t in np.linspace(0, 1, num_points_per_axis):
            point = position + t * axis
            points.append(point)
            colors.append(color)
    
    return np.array(points), np.array(colors)


def write_ply(filename, points, colors=None):
    """Write points to PLY file.
    
    Args:
        filename: Output PLY filename
        points: Array of 3D points (N, 3)
        colors: Array of RGB colors (N, 3), optional
    """
    with open(filename, "w") as f:
        n = points.shape[0]
        
        # Write header
        header = [
            "ply",
            "format ascii 1.0",
            f"element vertex {n}",
            "property float x",
            "property float y", 
            "property float z"
        ]
        
        if colors is not None:
            header += [
                "property uchar red",
                "property uchar green",
                "property uchar blue"
            ]
        
        header += ["end_header"]
        f.write("\n".join(header) + "\n")
        
        # Write point data
        for i in range(n):
            line = f"{points[i,0]} {points[i,1]} {points[i,2]}"
            if colors is not None:
                line += f" {int(colors[i,0])} {int(colors[i,1])} {int(colors[i,2])}"
            f.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert COLMAP sparse reconstruction to PLY with camera coordinate frames",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python sparse_to_ply.py /path/to/sparse reconstruction.ply
  
  # With custom camera scale
  python sparse_to_ply.py /path/to/sparse reconstruction.ply --camera-scale 0.2
  
  # Only point cloud (no cameras)
  python sparse_to_ply.py /path/to/sparse points_only.ply --no-cameras
        """
    )
    
    parser.add_argument("sparse_folder", type=str,
                       help="Path to COLMAP sparse reconstruction folder (containing cameras.bin/txt, images.bin/txt, points3D.bin/txt)")
    parser.add_argument("output_ply", type=str,
                       help="Output PLY filename (will be saved in sparse_folder)")
    parser.add_argument("--camera-scale", type=float, default=0.1,
                       help="Scale factor for camera coordinate frame axes (default: 0.1)")
    parser.add_argument("--no-cameras", action="store_true",
                       help="Don't include camera coordinate frames in output")
    parser.add_argument("--camera-points-per-axis", type=int, default=10,
                       help="Number of points per coordinate axis for camera visualization (default: 10)")
    
    args = parser.parse_args()
    
    # Check input folder
    sparse_folder = Path(args.sparse_folder)
    if not sparse_folder.exists():
        print(f"Error: Sparse folder '{sparse_folder}' does not exist")
        return 1
    
    # Generate full output path
    output_path = sparse_folder / args.output_ply
    
    print(f"Reading COLMAP sparse reconstruction from: {sparse_folder}")
    
    # Read COLMAP data
    try:
        cameras, images, points3D = read_colmap_data(sparse_folder)
        print(f"Loaded {len(cameras)} cameras, {len(images)} images, {len(points3D)} 3D points")
        
    except Exception as e:
        print(f"Error reading COLMAP files: {e}")
        return 1
    
    # Collect all points and colors
    all_points = []
    all_colors = []
    
    # Add 3D points from sparse reconstruction
    if points3D:
        sparse_points = np.array([p['xyz'] for p in points3D.values()])
        sparse_colors = np.array([p['rgb'] for p in points3D.values()])
        all_points.append(sparse_points)
        all_colors.append(sparse_colors)
        print(f"Added {len(sparse_points)} sparse reconstruction points")
    
    # Add camera coordinate frames
    if not args.no_cameras and images:
        camera_points = []
        camera_colors = []
        
        for image_id, image_data in images.items():
            # Convert quaternion to rotation matrix
            R = quaternion_to_rotation_matrix(image_data['qvec'])
            
            # Camera center in world coordinates
            # The camera center is: -R^T * t
            camera_center = -R.T @ image_data['tvec']
            
            # Generate coordinate frame points
            frame_points, frame_colors = generate_camera_coordinate_frame(
                camera_center, R, args.camera_scale, args.camera_points_per_axis
            )
            
            camera_points.append(frame_points)
            camera_colors.append(frame_colors)
        
        if camera_points:
            camera_points = np.vstack(camera_points)
            camera_colors = np.vstack(camera_colors)
            all_points.append(camera_points)
            all_colors.append(camera_colors)
            print(f"Added {len(camera_points)} camera coordinate frame points for {len(images)} cameras")
    
    # Combine all points
    if not all_points:
        print("Error: No points to write (empty reconstruction)")
        return 1
    
    final_points = np.vstack(all_points)
    final_colors = np.vstack(all_colors)
    
    # Write PLY file
    try:
        write_ply(output_path, final_points, final_colors)
        print(f"Successfully wrote {len(final_points)} points to: {output_path}")
        
        # Print summary
        print("\nSummary:")
        if points3D:
            print(f"  - Sparse reconstruction points: {len(sparse_points)}")
        if not args.no_cameras and images:
            print(f"  - Camera coordinate frame points: {len(camera_points)}")
            print(f"  - Camera frame scale: {args.camera_scale}")
        print(f"  - Total points in PLY: {len(final_points)}")
        
    except Exception as e:
        print(f"Error writing PLY file: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 