"""Transformasi tetap untuk kedua workload; dipakai bersama oleh semua metode."""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

OUTPUT_SIZE = (64, 64)
WORKLOADS = ("light", "heavy")
TRANSFORM_CONFIG = {
    "resize": [64, 64], "resampling": "BILINEAR",
    "light": ["resize", "grayscale"],
    "heavy": ["resize", "rotate", "gaussian_blur", "sharpen", "color", "find_edges"],
    "rotation_degrees": 15, "rotation_expand": False,
    "blur_radius": 2, "color_factor": 1.2,
}


def process_image(pixels: np.ndarray, workload: str) -> Image.Image:
    if workload not in WORKLOADS:
        raise ValueError(f"Workload tidak dikenal: {workload}")
    image = Image.fromarray(pixels).resize(OUTPUT_SIZE, Image.Resampling.BILINEAR)
    if workload == "light":
        return image.convert("L")
    image = image.rotate(15, resample=Image.Resampling.BILINEAR, expand=False)
    image = image.filter(ImageFilter.GaussianBlur(radius=2))
    image = image.filter(ImageFilter.SHARPEN)
    image = ImageEnhance.Color(image).enhance(1.2)
    return image.filter(ImageFilter.FIND_EDGES)
