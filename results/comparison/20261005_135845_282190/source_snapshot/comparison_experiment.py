"""Lima konfigurasi, dua workload, dan proses pengukuran segar tiap run."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil

from dataset import load_batch
from image_processing import TRANSFORM_CONFIG, process_image
from parallel_processing import run_method

PROJECT = Path(__file__).resolve().parents[1]
METHODS = [("sequential", 1), ("threading", 2), ("threading", 4),
           ("multiprocessing", 2), ("multiprocessing", 4)]


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def measure_one(args):
    images, _ = load_batch()
    images = images[:args.images]
    for pixels in images[:args.warmup]:
        process_image(pixels, args.workload)
    return run_method(images, args.workload, args.method, args.workers)


def run_experiment(args):
    now = datetime.now(timezone(timedelta(hours=7)))
    run_id = now.strftime("%Y%m%d_%H%M%S_%f")
    output = PROJECT / "results" / "comparison" / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "figures").mkdir()
    (output / "source_snapshot").mkdir()
    hashes = {}
    for source in [PROJECT / "main.py", *[PROJECT / "src" / name for name in
                   ("dataset.py", "image_processing.py", "resource_monitor.py", "parallel_processing.py",
                    "comparison_experiment.py", "comparison_reporting.py")]]:
        shutil.copy2(source, output / "source_snapshot" / source.name)
        hashes[str(source.relative_to(PROJECT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    cpu_name = platform.processor()
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    environment = {"timestamp": now.isoformat(), "run_id": run_id, "os": platform.platform(),
                   "python": platform.python_version(), "python_executable": sys.executable,
                   "cpu": cpu_name, "physical_cores": psutil.cpu_count(logical=False),
                   "logical_cpus": psutil.cpu_count(), "total_ram_gib": psutil.virtual_memory().total / 1024**3,
                   "execution": "local/on-premise; fresh process per measurement",
                   "libraries": {n: importlib.metadata.version(n) for n in
                                 ("numpy", "pillow", "psutil", "pandas", "matplotlib")}}
    batch = PROJECT / "data" / "cifar-10-batches-bin" / "data_batch_1.bin"
    config = {"images": args.images, "repetitions": args.repetitions,
              "warmup_images_in_parent": min(args.warmup, args.images), "worker_warmup": False,
              "batch": batch.name, "batch_sha256": hashlib.sha256(batch.read_bytes()).hexdigest(),
              "methods": METHODS, "transforms": TRANSFORM_CONFIG, "process_start_method": "spawn",
              "chunk_size_images": 100, "max_unconsumed_tasks": "2 * workers",
              "resource_sample_interval_s": 0.05, "resource_scope": "parent + live descendant processes",
              "ram_metric": "maximum simultaneous sum of RSS samples; shared pages may be double-counted",
              "cpu_metric": "parent CPU delta + last observed cumulative CPU of each child; approximate",
              "order": "rotate ten conditions by three positions per repetition",
              "timer_includes": ["conversion/transforms", "ordered output SHA256", "task scheduling",
                                 "pool startup/shutdown", "IPC and serialization for process",
                                 "resource monitoring overhead"],
              "timer_excludes": ["measurement interpreter startup", "dataset load", "parent warmup", "reports"],
              "source_sha256": hashes}
    for name, payload in (("environment.json", environment), ("config.json", config)):
        (output / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    conditions = [(w, method, workers) for w in ("light", "heavy") for method, workers in METHODS]
    raw, memory, signatures = [], [], {}
    for repetition in range(1, args.repetitions + 1):
        offset = (3 * (repetition - 1)) % len(conditions)
        for workload, method, workers in conditions[offset:] + conditions[:offset]:
            print(f"Run {repetition}/{args.repetitions}: {workload.upper()} {method} {workers}", flush=True)
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--single", "--images", str(args.images),
                 "--warmup", str(args.warmup), "--workload", workload, "--method", method, "--workers", str(workers)],
                cwd=PROJECT, capture_output=True, text=True, check=True, timeout=180,
            )
            row = json.loads(completed.stdout)
            samples = row.pop("memory_samples")
            if workload in signatures and row["output_sha256"] != signatures[workload]:
                raise RuntimeError("Hash output berbeda antar-metode/run")
            signatures[workload] = row["output_sha256"]
            row.update(run=repetition, run_id=run_id, sequence_index=len(raw) + 1)
            raw.append(row)
            memory.extend({"method": method, "workers": workers, "workload": workload,
                           "run": repetition, **sample} for sample in samples)
            save_csv(output / "raw_results.csv", raw)
            save_csv(output / "resource_samples.csv", memory)
            print(f"  {row['time_s']:.3f} s | {row['throughput_images_s']:.1f} gambar/s | "
                  f"RSS tree {row['rss_tree_peak_sampled_mib']:.1f} MiB", flush=True)
    from comparison_reporting import make_report
    make_report(output)
    (output / "status.json").write_text(json.dumps({"complete": True, "output_hashes_match": True,
                                       "measured_runs": len(raw)}, indent=2), encoding="utf-8")
    print(f"RESULT_DIR={output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--images", type=int, default=10000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--workload", choices=("light", "heavy"), default="light")
    parser.add_argument("--method", choices=("sequential", "threading", "multiprocessing"), default="sequential")
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=1)
    args = parser.parse_args()
    if not 1 <= args.images <= 10000 or args.repetitions < 2 or args.warmup < 0:
        parser.error("images 1..10000, repetitions >=2, warmup >=0")
    if args.single:
        print(json.dumps(measure_one(args)))
    else:
        run_experiment(args)
