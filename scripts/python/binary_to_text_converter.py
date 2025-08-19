#!/usr/bin/env python3
"""
COLMAP Binary to Text Converter

This script converts COLMAP binary format files to text format:
- cameras.bin -> cameras.txt
- images.bin -> images.txt
- points3D.bin -> points3D.txt

Usage:
    python binary_to_text_converter.py <input_folder> [output_folder] [--cameras-only]

Example:
    python binary_to_text_converter.py /path/to/sparse/binary /path/to/sparse/text
    python binary_to_text_converter.py /path/to/sparse  # outputs to same folder
    python binary_to_text_converter.py /path/to/sparse --cameras-only  # only cameras
"""

import argparse
import struct
import numpy as np
import os
from pathlib import Path


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
            if model_id == 0:  # SIMPLE_PINHOLE: f, cx, cy
                params = struct.unpack("<3d", f.read(24))
                # Pad with zero for consistency with PINHOLE
                params = params + (0.0,)
            elif model_id == 1:  # PINHOLE: fx, fy, cx, cy
                params = struct.unpack("<4d", f.read(32))
            elif model_id == 2:  # SIMPLE_RADIAL: f, cx, cy, k
                params = struct.unpack("<4d", f.read(32))
            elif model_id == 3:  # RADIAL: f, cx, cy, k1, k2
                params = struct.unpack("<5d", f.read(40))
            elif model_id == 4:  # OPENCV: fx, fy, cx, cy, k1, k2, p1, p2
                params = struct.unpack("<8d", f.read(64))
            elif model_id == 5:  # OPENCV_FISHEYE: fx, fy, cx, cy, k1, k2, k3, k4
                params = struct.unpack("<8d", f.read(64))
            elif model_id == 6:  # FULL_OPENCV: fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6
                params = struct.unpack("<12d", f.read(96))
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
            
            # Read 2D points
            num_points2D = struct.unpack("<Q", f.read(8))[0]
            points2D = []
            for _ in range(num_points2D):
                x, y = struct.unpack("<2d", f.read(16))
                point3D_id = struct.unpack("<Q", f.read(8))[0]
                points2D.append((x, y, point3D_id))
            
            images[image_id] = {
                'qvec': np.array(qvec),
                'tvec': np.array(tvec),
                'camera_id': camera_id,
                'name': name,
                'points2D': points2D
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
            
            # Read track
            track_length = struct.unpack("<Q", f.read(8))[0]
            track = []
            for _ in range(track_length):
                image_id = struct.unpack("<I", f.read(4))[0]
                point2D_idx = struct.unpack("<I", f.read(4))[0]
                track.append((image_id, point2D_idx))
            
            points3D[point3D_id] = {
                'xyz': np.array(xyz),
                'rgb': np.array(rgb),
                'error': error,
                'track': track
            }
    return points3D


def write_cameras_text(cameras, path):
    """Write COLMAP cameras.txt file."""
    # Model ID to name mapping
    model_id_to_name = {
        0: "SIMPLE_PINHOLE",
        1: "PINHOLE", 
        2: "SIMPLE_RADIAL",
        3: "RADIAL",
        4: "OPENCV",
        5: "OPENCV_FISHEYE",
        6: "FULL_OPENCV"
    }
    
    with open(path, "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write("# Number of cameras: {}\n".format(len(cameras)))
        
        for camera_id in sorted(cameras.keys()):
            camera = cameras[camera_id]
            model_name = model_id_to_name[camera['model_id']]
            width = camera['width']
            height = camera['height']
            params = camera['params']
            
            # Format parameters
            params_str = " ".join(f"{p:.10g}" for p in params)
            
            f.write(f"{camera_id} {model_name} {width} {height} {params_str}\n")


def write_images_text(images, path):
    """Write COLMAP images.txt file."""
    with open(path, "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        f.write("# Number of images: {}, mean observations per image: {:.2f}\n".format(
            len(images), 
            np.mean([len(img['points2D']) for img in images.values()]) if images else 0
        ))
        
        for image_id in sorted(images.keys()):
            image = images[image_id]
            qvec = image['qvec']
            tvec = image['tvec']
            camera_id = image['camera_id']
            name = image['name']
            points2D = image['points2D']
            
            # Write first line: image info
            f.write(f"{image_id} {qvec[0]:.10g} {qvec[1]:.10g} {qvec[2]:.10g} {qvec[3]:.10g} "
                   f"{tvec[0]:.10g} {tvec[1]:.10g} {tvec[2]:.10g} {camera_id} {name}\n")
            
            # Write second line: 2D points
            if points2D:
                points_str = " ".join(f"{x:.10g} {y:.10g} {point3D_id}" 
                                    for x, y, point3D_id in points2D)
                f.write(f"{points_str}\n")
            else:
                f.write("\n")


def write_points3D_text(points3D, path):
    """Write COLMAP points3D.txt file."""
    with open(path, "w") as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        f.write("# Number of points: {}, mean track length: {:.2f}\n".format(
            len(points3D),
            np.mean([len(pt['track']) for pt in points3D.values()]) if points3D else 0
        ))
        
        for point3D_id in sorted(points3D.keys()):
            point = points3D[point3D_id]
            xyz = point['xyz']
            rgb = point['rgb']
            error = point['error']
            track = point['track']
            
            # Format track
            track_str = " ".join(f"{image_id} {point2D_idx}" for image_id, point2D_idx in track)
            
            f.write(f"{point3D_id} {xyz[0]:.10g} {xyz[1]:.10g} {xyz[2]:.10g} "
                   f"{rgb[0]} {rgb[1]} {rgb[2]} {error:.10g} {track_str}\n")


def convert_binary_to_text(input_folder, output_folder=None, cameras_only=False):
    """Convert all binary files in input_folder to text format."""
    input_path = Path(input_folder)
    output_path = Path(output_folder) if output_folder else input_path
    
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert cameras.bin
    cameras_bin = input_path / "cameras.bin"
    if cameras_bin.exists():
        print(f"Converting {cameras_bin} -> {output_path / 'cameras.txt'}")
        cameras = read_cameras_binary(cameras_bin)
        write_cameras_text(cameras, output_path / "cameras.txt")
        print(f"  Converted {len(cameras)} cameras")
    else:
        print(f"Warning: {cameras_bin} not found")
    
    if cameras_only:
        print("Cameras-only mode: Skipping images.bin and points3D.bin conversion")
        return
    
    # Convert images.bin
    images_bin = input_path / "images.bin"
    if images_bin.exists():
        print(f"Converting {images_bin} -> {output_path / 'images.txt'}")
        images = read_images_binary(images_bin)
        write_images_text(images, output_path / "images.txt")
        print(f"  Converted {len(images)} images")
    else:
        print(f"Warning: {images_bin} not found")
    
    # Convert points3D.bin
    points3D_bin = input_path / "points3D.bin"
    if points3D_bin.exists():
        print(f"Converting {points3D_bin} -> {output_path / 'points3D.txt'}")
        points3D = read_points3D_binary(points3D_bin)
        write_points3D_text(points3D, output_path / "points3D.txt")
        print(f"  Converted {len(points3D)} 3D points")
    else:
        print(f"Warning: {points3D_bin} not found")


def main():
    parser = argparse.ArgumentParser(
        description="Convert COLMAP binary format files to text format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python binary_to_text_converter.py /path/to/sparse
  python binary_to_text_converter.py /path/to/sparse/binary /path/to/sparse/text
  python binary_to_text_converter.py /path/to/sparse --cameras-only
        """
    )
    parser.add_argument("input_folder", help="Input folder containing binary files")
    parser.add_argument("output_folder", nargs="?", 
                       help="Output folder for text files (default: same as input)")
    parser.add_argument("--cameras-only", action="store_true",
                       help="Only convert cameras.bin, skip images.bin and points3D.bin")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_folder):
        print(f"Error: Input folder '{args.input_folder}' does not exist")
        return 1
    
    try:
        convert_binary_to_text(args.input_folder, args.output_folder, args.cameras_only)
        print("Conversion completed successfully!")
        return 0
    except Exception as e:
        print(f"Error during conversion: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 