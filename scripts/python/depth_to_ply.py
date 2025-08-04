#!/usr/bin/env python

import argparse
import os
import numpy as np
from read_write_dense import read_array
from PIL import Image

from read_sparse_calibration import get_intrinsics_for_image

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("main_folder", type=str, help="Main folder containing depth_maps, normal_maps, and images subfolders")
    parser.add_argument("image_name", type=str, help="Image file name (e.g. IMG_0001.jpg)")
    parser.add_argument("-o", "--output", required=True, help="Output PLY file")
    return parser.parse_args()

def write_ply(filename, points, colors=None, normals=None):
    with open(filename, "w") as f:
        n = points.shape[0]
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
        if normals is not None:
            header += [
                "property float nx",
                "property float ny",
                "property float nz"
            ]
        header += ["end_header"]
        f.write("\n".join(header) + "\n")
        for i in range(n):
            line = [f"{points[i,0]} {points[i,1]} {points[i,2]}"]
            if colors is not None:
                line += [f"{int(colors[i,0])} {int(colors[i,1])} {int(colors[i,2])}"]
            if normals is not None:
                line += [f"{normals[i,0]} {normals[i,1]} {normals[i,2]}"]
            f.write(" ".join(line) + "\n")

def main():

    args = parse_args()
    depth_map_path = os.path.join(args.main_folder, "stereo/depth_maps", args.image_name + ".geometric.bin")
    normal_map_path = os.path.join(args.main_folder, "stereo/normal_maps", args.image_name + ".geometric.bin")
    image_path = os.path.join(args.main_folder, "images", args.image_name)

    if not os.path.exists(depth_map_path):
        raise FileNotFoundError(f"Depth map not found: {depth_map_path}")
    if not os.path.exists(normal_map_path):
        normal = None
    else:
        normal = read_array(normal_map_path)
        if normal.shape[2] > 3:
            normal = normal[:, :, :3]

    depth = read_array(depth_map_path)
    if len(depth.shape) == 3:
        depth = depth[:, :, 0]
    h, w = depth.shape

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    img = np.array(Image.open(image_path).convert("RGB"))

    fx, fy, cx, cy = get_intrinsics_for_image( os.path.join(args.main_folder, 'sparse'), args.image_name )

    points = []
    colors = []
    normals = []

    for v in range(h):
        for u in range(w):
            z = depth[v, u]
            if z <= 0 or np.isnan(z):
                continue
            x = (u - cx) * z / fx
            y = (v - cy) * z / fy
            points.append([x, y, z])
            # Always use image for color
            colors.append(img[v, u])
            if normal is not None:
                normals.append(normal[v, u])

    points = np.array(points)
    colors = np.array(colors) if colors else None
    normals = np.array(normals) if normals else None

    write_ply(args.output, points, colors, normals)
    print(f"Saved {points.shape[0]} points to {args.output}")

if __name__ == "__main__":
    main()
    