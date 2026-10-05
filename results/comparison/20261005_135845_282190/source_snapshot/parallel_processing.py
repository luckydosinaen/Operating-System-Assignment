"""Pipeline dan kebijakan timer seragam untuk sequential, thread, dan process."""

import gc
import hashlib
import multiprocessing
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from time import perf_counter

import numpy as np
import psutil

from image_processing import process_image
from resource_monitor import ResourceMonitor


def process_chunk(images: np.ndarray, workload: str) -> list[bytes]:
    # Pada process input merupakan salinan chunk; pada thread berupa view shared.
    images.flags.writeable = False
    return [process_image(pixels, workload).tobytes() for pixels in images]


def run_method(images, workload, method, workers, chunk_size=100):
    if method not in ("sequential", "threading", "multiprocessing"):
        raise ValueError("Metode tidak dikenal")
    if (method == "sequential" and workers != 1) or (method != "sequential" and workers not in (2, 4)):
        raise ValueError("Sequential: 1 worker; pool: 2/4 worker")
    if len(images) < 1 or chunk_size < 1:
        raise ValueError("Input dan chunk harus positif")
    gc.collect()
    images.flags.writeable = False
    parent = psutil.Process()
    monitor = ResourceMonitor(interval=0.05)
    digest = hashlib.sha256()
    processed = 0
    monitor.start()
    cpu_before = parent.cpu_times()
    start = perf_counter()
    monitor.origin = start
    try:
        if method == "sequential":
            for pixels in images:
                digest.update(process_image(pixels, workload).tobytes())
                processed += 1
        else:
            if method == "threading":
                pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="image-worker")
            else:
                pool = ProcessPoolExecutor(max_workers=workers,
                                           mp_context=multiprocessing.get_context("spawn"))
            with pool:
                pending = deque()
                next_start = 0

                def submit_next():
                    nonlocal next_start
                    chunk = images[next_start:next_start + chunk_size]
                    pending.append(pool.submit(process_chunk, chunk, workload))
                    next_start += len(chunk)

                while next_start < len(images) and len(pending) < 2 * workers:
                    submit_next()
                while pending:
                    outputs = pending.popleft().result()
                    for output in outputs:
                        digest.update(output)
                        processed += 1
                    del outputs
                    if next_start < len(images):
                        submit_next()
                # Snapshot terakhir saat semua worker masih hidup, sebelum shutdown.
                monitor.sample()
        monitor.sample()
        elapsed = perf_counter() - start
        cpu_after = parent.cpu_times()
    finally:
        monitor.stop()
    if processed != len(images):
        raise RuntimeError("Tidak semua gambar diproses")
    parent_cpu = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)
    child_cpu = sum(monitor.child_cpu.values())
    tree_cpu = parent_cpu + child_cpu
    return {
        "method": method, "workers": workers, "workload": workload, "images": processed,
        "time_s": elapsed, "throughput_images_s": processed / elapsed,
        "parent_cpu_seconds": parent_cpu, "child_cpu_seconds_sampled": child_cpu,
        "tree_cpu_seconds_sampled": tree_cpu, "cpu_tree_sampled_percent": 100 * tree_cpu / elapsed,
        "cpu_machine_capacity_sampled_percent": 100 * tree_cpu / elapsed / (psutil.cpu_count() or 1),
        "rss_tree_before_mib": monitor.samples[0]["tree_rss_sum_mib"],
        "rss_tree_peak_sampled_mib": max(s["tree_rss_sum_mib"] for s in monitor.samples),
        "rss_parent_peak_sampled_mib": max(s["parent_rss_mib"] for s in monitor.samples),
        "child_processes_max_sampled": max(s["child_processes"] for s in monitor.samples),
        "output_sha256": digest.hexdigest(), "benchmark_pid": parent.pid,
        "memory_samples": monitor.samples,
    }
