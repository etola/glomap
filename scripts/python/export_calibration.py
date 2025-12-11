#!/usr/bin/env python3
import os
import sys
import json
import struct
import argparse
from typing import Dict, Tuple, Optional
from scipy.spatial.transform import Rotation as SciRot
import numpy as np

model_name_to_id = {
    'SIMPLE_PINHOLE': 0,
    'PINHOLE': 1,
    'SIMPLE_RADIAL': 2,
    'RADIAL': 3,
    'OPENCV': 4,
    'OPENCV_FISHEYE': 5,
    'FULL_OPENCV': 6,
    'FOV': 7,
    'SIMPLE_RADIAL_FISHEYE': 8,
    'RADIAL_FISHEYE': 9,
    'THIN_PRISM_FISHEYE': 10,
}

model_param_descriptions = {
    'SIMPLE_PINHOLE': ['f', 'cx', 'cy'],
    'PINHOLE': ['fx', 'fy', 'cx', 'cy'],
    'SIMPLE_RADIAL': ['f', 'cx', 'cy', 'k'],
    'RADIAL': ['f', 'cx', 'cy', 'k1', 'k2'],
    'OPENCV': ['fx', 'fy', 'cx', 'cy', 'k1', 'k2', 'p1', 'p2'],
    'OPENCV_FISHEYE': ['fx', 'fy', 'cx', 'cy', 'k1', 'k2', 'k3', 'k4'],
    'FULL_OPENCV': ['fx', 'fy', 'cx', 'cy', 'k1', 'k2', 'p1', 'p2', 'k3', 'k4', 'k5', 'k6'],
    'FOV': ['fx', 'fy', 'cx', 'cy', 'omega'],
    'SIMPLE_RADIAL_FISHEYE': ['f', 'cx', 'cy', 'k'],
    'RADIAL_FISHEYE': ['f', 'cx', 'cy', 'k1', 'k2'],
    'THIN_PRISM_FISHEYE': ['fx', 'fy', 'cx', 'cy', 'k1', 'k2', 'p1', 'p2', 'k3', 'k4', 'sx1', 'sy1'],
}

model_id_to_name = {v: k for k, v in model_name_to_id.items()}

def _read_cameras_binary(path: str) -> Dict[int, dict]:
    cameras = {}
    # COLMAP binary format:
    # uint64 num_cameras
    # For each:
    #  - uint32 camera_id
    #  - int32  model_id
    #  - uint64 width
    #  - uint64 height
    #  - double params[num_params] (num_params inferred from model_id)
    model_param_counts = {
        0: 3,  # SIMPLE_PINHOLE: f, cx, cy
        1: 4,  # PINHOLE: fx, fy, cx, cy
        2: 4,  # SIMPLE_RADIAL: f, cx, cy, k
        3: 5,  # RADIAL: f, cx, cy, k1, k2
        4: 8,  # OPENCV: fx, fy, cx, cy, k1, k2, p1, p2
        5: 8,  # OPENCV_FISHEYE: fx, fy, cx, cy, k1, k2, k3, k4
        6: 12,  # FULL_OPENCV: fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6
        7: 5,  # FOV: fx, fy, cx, cy, omega
        8: 4, # SIMPLE_RADIAL_FISHEYE: f, cx, cy, k
        9: 5, # RADIAL_FISHEYE: f, cx, cy, k1, k2
        10: 12, # THIN_PRISM_FISHEYE: fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, sx1, sy1
    }
    with open(path, 'rb') as f:
        num_cameras = struct.unpack('<Q', f.read(8))[0]
        for _ in range(num_cameras):
            camera_id = struct.unpack('<I', f.read(4))[0]
            model_id = struct.unpack('<i', f.read(4))[0]
            width = struct.unpack('<Q', f.read(8))[0]
            height = struct.unpack('<Q', f.read(8))[0]
            num_params = model_param_counts.get(model_id)
            if num_params is None:
                raise NotImplementedError(f"Unsupported camera model id: {model_id}")
            params = struct.unpack(f'<{num_params}d', f.read(8 * num_params))
            cameras[camera_id] = {
                'camera_id': camera_id,
                'model_id': model_id,
                'width': width,
                'height': height,
                'params': params,
                'model_name': model_id_to_name[model_id],
                'param_descriptions': model_param_descriptions[model_id_to_name[model_id]],
            }
    return cameras

def _read_cameras_text(path: str) -> Dict[int, dict]:
    cameras: Dict[int, dict] = {}
    if not os.path.exists(path):
        return cameras

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            # CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS...
            if len(parts) < 5:
                continue
            camera_id = int(parts[0])
            model_name = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = list(map(float, parts[4:]))
            model_id = model_name_to_id.get(model_name)
            if model_id is None:
                raise NotImplementedError(f"Unsupported camera model: {model_name}")
            cameras[camera_id] = {
                'camera_id': camera_id,
                'model_id': model_id,
                'width': width,
                'height': height,
                'params': params,
                'model_name': model_name,
                'param_descriptions': model_param_descriptions[model_name],
            }
    return cameras

# Minimal COLMAP readers (binary + text) focused on images
def _read_images_binary(path: str) -> Dict[int, dict]:
    images = {}
    with open(path, 'rb') as f:
        num_images = struct.unpack('<Q', f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack('<I', f.read(4))[0]
            qvec = struct.unpack('<4d', f.read(32))  # qw, qx, qy, qz
            tvec = struct.unpack('<3d', f.read(24))
            camera_id = struct.unpack('<I', f.read(4))[0]

            # name: null-terminated UTF-8 string
            name_bytes = bytearray()
            while True:
                c = f.read(1)
                if c == b'\x00' or c == b'':
                    break
                name_bytes.extend(c)
            name = name_bytes.decode('utf-8')

            num_points2D = struct.unpack('<Q', f.read(8))[0]
            # Skip point2D entries (x, y, point3D_id) = 2*float64 + int64 = 24 bytes
            f.read(num_points2D * 24)

            images[image_id] = {
                'image_id': image_id,
                'name': name,
                'qvec': qvec,
                'tvec': tvec,
                'camera_id': camera_id,
            }
    return images


def _read_images_text(path: str) -> Dict[int, dict]:
    images: Dict[int, dict] = {}
    if not os.path.exists(path):
        return images
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Images.txt uses two lines per image; first line has pose + name
            parts = line.split()
            if len(parts) < 10:
                # Likely the 2D points line; skip
                continue
            # Format: IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
            image_id = int(parts[0])
            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            camera_id = int(parts[8])
            name = ' '.join(parts[9:])  # image names typically have no spaces, but be safe
            images[image_id] = {
                'image_id': image_id,
                'name': name,
                'qvec': (qw, qx, qy, qz),
                'tvec': (tx, ty, tz),
                'camera_id': camera_id,
            }
    return images

def _rotation_matrix_from_quaternion(q: Tuple[float, float, float, float]):
    # Prefer SciPy; fallback to transforms3d. Both are well-tested libraries.
    # COLMAP stores quaternion as (qw, qx, qy, qz). SciPy expects (qx, qy, qz, qw),
    # transforms3d expects (w, x, y, z).
    qw, qx, qy, qz = q
    R = SciRot.from_quat([qx, qy, qz, qw]).as_matrix()
    return [[float(R[0,0]), float(R[0,1]), float(R[0,2])],
            [float(R[1,0]), float(R[1,1]), float(R[1,2])],
            [float(R[2,0]), float(R[2,1]), float(R[2,2])]]

def _detect_model_dir(base_dir: str) -> Optional[str]:
    # Expected: base_dir contains a 'sparse' folder.
    candidates = [
        os.path.join(base_dir, 'sparse'),
        os.path.join(base_dir, 'sparse', '0'),
        os.path.join(base_dir, 'sparse', '1'),
        base_dir,  # in case user points directly to the sparse dir
    ]
    for cand in candidates:
        if (os.path.exists(os.path.join(cand, 'images.bin')) and
                os.path.exists(os.path.join(cand, 'cameras.bin'))):
            return cand
        if (os.path.exists(os.path.join(cand, 'images.txt')) and
                os.path.exists(os.path.join(cand, 'cameras.txt'))):
            return cand
    return None


def _detect_images_dir(base_dir: str) -> Optional[str]:
    # Prefer undistorted images if present (typical COLMAP undistorter output)
    candidates = [
        os.path.join(base_dir, 'images'),
        os.path.join(os.path.dirname(base_dir), 'images'),
    ]
    for cand in candidates:
        if os.path.isdir(cand):
            return cand
    return None


def build_calibration(base_dir: str) -> Dict[int, dict]:
    model_dir = _detect_model_dir(base_dir)
    if model_dir is None:
        raise FileNotFoundError(
            f"Could not find COLMAP sparse model in '{base_dir}'. "
            "Expected 'sparse/{cameras,images}.bin' or '.txt'."
        )

    images_path_bin = os.path.join(model_dir, 'images.bin')
    images_path_txt = os.path.join(model_dir, 'images.txt')

    if os.path.exists(images_path_bin):
        images = _read_images_binary(images_path_bin)
    elif os.path.exists(images_path_txt):
        images = _read_images_text(images_path_txt)
    else:
        raise FileNotFoundError(f"Neither images.bin nor images.txt found in '{model_dir}'.")

    images_dir = _detect_images_dir(base_dir)

    calib: Dict[str, dict] = {}
    calib["images"] = {}
    for img_id, rec in sorted(images.items()):
        name = rec['name']
        qvec = rec['qvec']
        tvec = rec['tvec']
        R = _rotation_matrix_from_quaternion(qvec)

        if images_dir is not None:
            img_path = os.path.join(images_dir, name)
        else:
            img_path = name  # fallback to filename only

        cam_from_world = np.eye(4)
        cam_from_world[0:3, 0:3] = np.array(R)
        cam_from_world[0:3, 3] = np.array(tvec)

        calib["images"][img_id] = {
            'name': name,
            'path': os.path.relpath(img_path, base_dir),
            'cam_from_world': cam_from_world.flatten().tolist(),  # row-major
            'camera_id': rec['camera_id'],
        }

    cameras_path_bin = os.path.join(model_dir, 'cameras.bin')
    cameras_path_txt = os.path.join(model_dir, 'cameras.txt')
    if os.path.exists(cameras_path_bin):
        cameras = _read_cameras_binary(cameras_path_bin)
    elif os.path.exists(cameras_path_txt):
        cameras = _read_cameras_text(cameras_path_txt)
    else:
        raise FileNotFoundError(f"Neither cameras.bin nor cameras.txt found in '{model_dir}'.")

    calib['cameras'] = {}
    for cam_id, cam in cameras.items():
        calib['cameras'][cam_id] = cam


    return calib


def main():
    parser = argparse.ArgumentParser(
        description='Process COLMAP sparse model to calibration.json (poses per image).'
    )
    parser.add_argument('base_dir', type=str,
                        help="Directory that contains the 'sparse' folder (e.g., COLMAP undistorted 'dense' dir).")
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output JSON path (default: <base_dir>/calibration.json)')
    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    out_path = args.output or os.path.join(base_dir, 'calibration.json')

    calib = build_calibration(base_dir)

    # Convert to plain dict with string keys if preferred; the requirement asked for key=image_id
    # Using int keys is fine in JSON, but some tools prefer strings. We'll keep ints.
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(calib, f, indent=2)

    print(f"Wrote calibration with {len(calib)} entries to: {out_path}")

if __name__ == '__main__':
    main()
