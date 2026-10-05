"""Download, verify, and inspect CIFAR-10; no benchmark is run."""

import hashlib
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

from PIL import Image

from dataset import DATASET_DIR, PROJECT_ROOT, load_batch, load_label_names

URL = "https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz"
EXPECTED_MD5 = "c32a1d4ab5d03f1284b67883e8d87530"
BATCHES = [f"data_batch_{i}.bin" for i in range(1, 6)] + ["test_batch.bin"]


def checksum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(archive: Path) -> None:
    if archive.exists():
        if checksum(archive) == EXPECTED_MD5:
            print("Verified cached archive.", flush=True)
            return
        raise ValueError(f"Existing archive failed checksum: {archive}. Keep it for inspection or rename it before retrying.")
    partial = archive.with_suffix(archive.suffix + ".part")
    print(f"Downloading official dataset: {URL}", flush=True)
    request = urllib.request.Request(URL, headers={"User-Agent": "OS-Assignment-Dataset-Setup/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
        received = 0
        last_report = 0
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            received += len(chunk)
            if received - last_report >= 10 * 1024 * 1024:
                print(f"Downloaded {received / 1024 / 1024:.0f} MiB", flush=True)
                last_report = received
    if checksum(partial) != EXPECTED_MD5:
        raise ValueError(f"Download checksum mismatch. Partial file retained at {partial}")
    partial.rename(archive)
    print("Archive checksum OK.", flush=True)


def extract(archive: Path) -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    # Copy only exact expected regular files; never extract arbitrary archive paths.
    with tarfile.open(archive, "r:gz") as bundle:
        for name in BATCHES + ["batches.meta.txt"]:
            member = bundle.getmember(f"cifar-10-batches-bin/{name}")
            if not member.isfile():
                raise ValueError(f"Unexpected archive entry: {name}")
            if name in BATCHES and member.size != 10000 * 3073:
                raise ValueError(f"Unexpected batch size: {name}")
            if name == "batches.meta.txt" and member.size > 4096:
                raise ValueError("Unexpected metadata size")
            destination = DATASET_DIR / name
            if destination.exists():
                with bundle.extractfile(member) as source, destination.open("rb") as existing:
                    if hashlib.sha256(source.read()).digest() != hashlib.sha256(existing.read()).digest():
                        raise ValueError(f"Existing dataset file differs: {destination}")
                continue
            with bundle.extractfile(member) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)


def main() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    archive = data_dir / "cifar-10-binary.tar.gz"
    download(archive)
    extract(archive)
    names = load_label_names()
    counts = {}
    for batch in BATCHES:
        images, labels = load_batch(batch)
        assert images.shape == (10000, 32, 32, 3)
        counts[batch] = len(images)
        print(f"Verified {batch}: {len(images)} RGB images, {images.dtype}", flush=True)
    images, labels = load_batch()
    sample = Image.fromarray(images[0])
    sample_path = data_dir / "sample_image.png"
    preview_path = data_dir / "sample_image_preview.png"
    sample.save(sample_path)
    sample.resize((320, 320), Image.Resampling.NEAREST).save(preview_path)
    with Image.open(sample_path) as reopened:
        assert reopened.size == (32, 32) and reopened.mode == "RGB"
    report = {
        "source_url": URL,
        "archive_md5": checksum(archive),
        "training_images": 50000,
        "test_images": 10000,
        "total_images": sum(counts.values()),
        "batch_counts": counts,
        "initial_experiment_batch": "data_batch_1.bin",
        "initial_experiment_images": len(images),
        "image_shape": list(images.shape[1:]),
        "dtype": str(images.dtype),
        "classes": names,
        "sample_label": names[int(labels[0])],
        "sample_path": str(sample_path),
    }
    (data_dir / "dataset_info.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
