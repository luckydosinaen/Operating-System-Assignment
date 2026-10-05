"""Thread pool dengan chunk kecil dan antrean terbatas, bukan 10.000 future sekaligus."""

import gc
import hashlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import numpy as np
import psutil

from image_processing import process_image


def process_chunk(images: np.ndarray, workload: str) -> list[bytes]:
    """Worker hanya membaca input dan mengembalikan byte output sesuai urutan."""
    return [process_image(pixels, workload).tobytes() for pixels in images]


def run_threading(images: np.ndarray, workload: str, workers: int,
                  chunk_size: int = 100, sample_every: int = 100) -> dict:
    if workers not in (2, 4) or len(images) < 1 or min(chunk_size, sample_every) < 1:
        raise ValueError("Worker harus 2/4; jumlah gambar dan interval harus positif")
    gc.collect()
    process = psutil.Process()
    rss_before = process.memory_info().rss / 1024**2
    samples = [{"processed_images": 0, "elapsed_s": 0.0, "rss_mib": rss_before}]
    digest = hashlib.sha256()
    cpu_before = process.cpu_times()
    start = perf_counter()
    # Timer juga mencakup startup dan shutdown pool, serta penjadwalan task.
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="image-worker") as pool:
        pending = deque()
        next_start = 0

        def submit_next() -> None:
            nonlocal next_start
            chunk = images[next_start:next_start + chunk_size]
            pending.append(pool.submit(process_chunk, chunk, workload))
            next_start += len(chunk)

        # Maksimum 2 x workers chunk di antrean, termasuk yang sedang dikerjakan.
        while next_start < len(images) and len(pending) < 2 * workers:
            submit_next()
        processed = 0
        while pending:
            outputs = pending.popleft().result()
            for output in outputs:
                digest.update(output)
                processed += 1
                if processed % sample_every == 0 or processed == len(images):
                    samples.append({"processed_images": processed,
                                    "elapsed_s": perf_counter() - start,
                                    "rss_mib": process.memory_info().rss / 1024**2})
            del outputs
            if next_start < len(images):
                submit_next()
    elapsed = perf_counter() - start
    cpu_after = process.cpu_times()
    rss_after = process.memory_info().rss / 1024**2
    cpu_seconds = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)
    cpu_percent = 100 * cpu_seconds / elapsed
    return {
        "method": "threading", "workers": workers, "workload": workload,
        "images": len(images), "time_s": elapsed, "throughput_images_s": len(images) / elapsed,
        "cpu_seconds": cpu_seconds, "cpu_process_percent": cpu_percent,
        "cpu_machine_capacity_percent": cpu_percent / (psutil.cpu_count() or 1),
        "rss_before_mib": rss_before, "rss_peak_sampled_mib": max(rss_after, *(s["rss_mib"] for s in samples)),
        "rss_after_mib": rss_after, "output_sha256": digest.hexdigest(),
        "speedup": None, "memory_samples": samples,
    }
