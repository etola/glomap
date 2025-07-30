import struct
import numpy as np

def read_cameras_binary(path):
    cameras = {}
    with open(path, "rb") as f:
        num_cameras = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_cameras):
            camera_id = struct.unpack("<I", f.read(4))[0]
            model_id = struct.unpack("<i", f.read(4))[0]
            width = struct.unpack("<Q", f.read(8))[0]
            height = struct.unpack("<Q", f.read(8))[0]
            if model_id in [0, 1]:  # SIMPLE_PINHOLE, PINHOLE
                params = struct.unpack("<4d", f.read(32))
            elif model_id in [2, 3]:  # SIMPLE_RADIAL, RADIAL
                params = struct.unpack("<3d", f.read(24))
            elif model_id == 4:  # OPENCV
                params = struct.unpack("<8d", f.read(64))
            else:
                raise NotImplementedError("Camera model not supported")
            cameras[camera_id] = (model_id, width, height, params)
    return cameras

def read_images_binary(path):
    images = {}
    with open(path, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack("<I", f.read(4))[0]
            qvec = struct.unpack("<4d", f.read(32))
            tvec = struct.unpack("<3d", f.read(24))
            camera_id = struct.unpack("<I", f.read(4))[0]
            name = b""
            while True:
                c = f.read(1)
                if c == b"\x00":
                    break
                name += c
            name = name.decode("utf-8")
            num_points2D = struct.unpack("<Q", f.read(8))[0]
            f.read(num_points2D * 24)  # skip 2D points
            images[name] = camera_id
    return images

def get_intrinsics_for_image(model_dir, image_name):
    cameras = read_cameras_binary(f"{model_dir}/cameras.bin")
    images = read_images_binary(f"{model_dir}/images.bin")
    if image_name not in images:
        raise ValueError(f"Image {image_name} not found in model")
    camera_id = images[image_name]
    model_id, width, height, params = cameras[camera_id]
    # For PINHOLE model: fx, fy, cx, cy
    if model_id == 1:
        fx, fy, cx, cy = params[:4]
    elif model_id == 0:  # SIMPLE_PINHOLE
        fx = fy = params[0]
        cx, cy = params[1:3]
    elif model_id == 2:  # SIMPLE_RADIAL
        fx = fy = params[0]
        cx, cy = params[1:3]
    elif model_id == 3:  # RADIAL
        fx = fy = params[0]
        cx, cy = params[1:3]
    elif model_id == 4:  # OPENCV
        fx, fy, cx, cy = params[:4]
    else:
        raise NotImplementedError("Camera model not supported")
    return fx, fy, cx, cy


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Get intrinsics for a given image from COLMAP sparse model.")
    parser.add_argument("model_dir", type=str, help="Path to sparse model directory (containing cameras.bin, images.bin)")
    parser.add_argument("image_name", type=str, help="Image name to query (e.g. IMG_0001.jpg)")
    args = parser.parse_args()
    fx, fy, cx, cy = get_intrinsics_for_image(args.model_dir, args.image_name)
    print(f"fx={fx}, fy={fy}, cx={cx}, cy={cy}")
    