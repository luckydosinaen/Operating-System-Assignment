"""Read the official CIFAR-10 binary dataset as RGB NumPy arrays."""

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "cifar-10-batches-bin"


def load_batch(batch_name: str = "data_batch_1.bin") -> tuple[np.ndarray, np.ndarray]:
    """Return images (10000, 32, 32, 3) and labels (10000,)."""
    if batch_name not in {f"data_batch_{i}.bin" for i in range(1, 6)} | {"test_batch.bin"}:
        raise ValueError("Unknown CIFAR-10 batch name")
    path = DATASET_DIR / batch_name
    if not path.is_file():
        raise FileNotFoundError("Dataset missing. Run: python src/setup_dataset.py")
    records = np.fromfile(path, dtype=np.uint8)
    if records.size != 10000 * 3073:
        raise ValueError(f"Invalid batch size: {path}")
    records = records.reshape(10000, 3073)
    labels = records[:, 0].copy()
    images = records[:, 1:].reshape(-1, 3, 32, 32).transpose(0, 2, 3, 1).copy()
    if np.any(labels > 9):
        raise ValueError("Invalid CIFAR-10 labels")
    return images, labels


def load_label_names() -> list[str]:
    names = [
        line.strip()
        for line in (DATASET_DIR / "batches.meta.txt").read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(names) != 10:
        raise ValueError("Expected 10 class names")
    return names
