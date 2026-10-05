"""Satu loop pemrosesan dengan pengukuran waktu, CPU proses, dan sampel RSS."""

import gc
import hashlib
from time import perf_counter

import numpy as np
import psutil

from image_processing import process_image


def run_sequential(images: np.ndarray, workload: str, sample_every: int = 100) -> dict:
    if len(images) < 1 or sample_every < 1:
        raise ValueError("Jumlah gambar dan interval sampel harus positif")
    gc.collect()
    process = psutil.Process()
    rss_before = process.memory_info().rss / 1024**2
    samples = [{"processed_images": 0, "elapsed_s": 0.0, "rss_mib": rss_before}]
    digest = hashlib.sha256()
    cpu_before = process.cpu_times()
    start = perf_counter()
    for index, pixels in enumerate(images, start=1):
        result = process_image(pixels, workload)
        # Hash membuktikan hasil tiap pengulangan sama tanpa menyimpan 10.000 gambar.
        digest.update(result.tobytes())
        if index % sample_every == 0 or index == len(images):
            samples.append({
                "processed_images": index,
                "elapsed_s": perf_counter() - start,
                "rss_mib": process.memory_info().rss / 1024**2,
            })
    elapsed = perf_counter() - start
    cpu_after = process.cpu_times()
    cpu_seconds = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)
    cpu_percent = 100 * cpu_seconds / elapsed
    logical_cpus = psutil.cpu_count(logical=True) or 1
    return {
        "method": "sequential", "workers": 1, "workload": workload,
        "images": len(images), "time_s": elapsed,
        "throughput_images_s": len(images) / elapsed,
        "cpu_seconds": cpu_seconds,
        "cpu_process_percent": cpu_percent,
        "cpu_machine_capacity_percent": cpu_percent / logical_cpus,
        "rss_before_mib": rss_before,
        "rss_peak_sampled_mib": max(sample["rss_mib"] for sample in samples),
        "rss_after_mib": samples[-1]["rss_mib"],
        "output_sha256": digest.hexdigest(),
        "speedup": 1.0,
        "memory_samples": samples,
    }
