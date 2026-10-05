"""Bandingkan sequential dan thread 2/4 dengan proses segar setiap pengukuran."""

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
from sequential import run_sequential
from threading_processing import run_threading

PROJECT = Path(__file__).resolve().parents[1]


def save_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def measure_one(args: argparse.Namespace) -> dict:
    images, _ = load_batch("data_batch_1.bin")
    images = images[:args.images]
    images.flags.writeable = False
    for pixels in images[:args.warmup]:
        process_image(pixels, args.workload)
    if args.method == "sequential":
        row = run_sequential(images, args.workload)
    else:
        row = run_threading(images, args.workload, args.workers)
    row["benchmark_pid"] = psutil.Process().pid
    return row


def run_experiment(args: argparse.Namespace) -> None:
    now = datetime.now(timezone(timedelta(hours=7)))
    run_id = now.strftime("%Y%m%d_%H%M%S_%f")
    output = PROJECT / "results" / "threading" / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "figures").mkdir()
    (output / "source_snapshot").mkdir()
    hashes = {}
    for source in [PROJECT / "main.py", *[PROJECT / "src" / name for name in
                   ("dataset.py", "image_processing.py", "sequential.py", "threading_processing.py",
                    "threading_experiment.py", "threading_reporting.py")]]:
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
                   "execution": "local/on-premise; fresh benchmark process per run",
                   "libraries": {name: importlib.metadata.version(name) for name in
                                 ("numpy", "pillow", "psutil", "pandas", "matplotlib")}}
    batch = PROJECT / "data" / "cifar-10-batches-bin" / "data_batch_1.bin"
    config = {"images": args.images, "repetitions": args.repetitions,
              "warmup_images_per_run": min(args.warmup, args.images), "batch": batch.name,
              "batch_sha256": hashlib.sha256(batch.read_bytes()).hexdigest(),
              "configurations": [["sequential", 1], ["threading", 2], ["threading", 4]],
              "workloads": ["light", "heavy"], "transforms": TRANSFORM_CONFIG,
              "chunk_size_images": 100, "max_queued_chunks": "2 * workers",
              "rss_sample_every_consumed_images": 100, "input_read_only": True,
              "order": "rotate six conditions by two positions each repetition",
              "timer_includes": ["image conversion", "transforms", "to bytes", "ordered SHA256",
                                 "RSS sampling", "thread pool startup/shutdown", "task scheduling/waiting"],
              "timer_excludes": ["interpreter startup", "dataset loading", "warmup", "CSV/plots"],
              "speedup_reference": "mean sequential time for the same workload in this suite",
              "source_sha256": hashes}
    for name, payload in (("environment.json", environment), ("config.json", config)):
        (output / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    conditions = [(workload, method, workers) for workload in ("light", "heavy")
                  for method, workers in (("sequential", 1), ("threading", 2), ("threading", 4))]
    rows, memory, signatures = [], [], {}
    for repetition in range(1, args.repetitions + 1):
        offset = (2 * (repetition - 1)) % len(conditions)
        for workload, method, workers in conditions[offset:] + conditions[:offset]:
            print(f"Run {repetition}/{args.repetitions}: {workload.upper()} {method} {workers}", flush=True)
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--single", "--images", str(args.images),
                 "--warmup", str(args.warmup), "--workload", workload, "--method", method, "--workers", str(workers)],
                cwd=PROJECT, capture_output=True, text=True, check=True,
            )
            row = json.loads(completed.stdout)
            samples = row.pop("memory_samples")
            if workload in signatures and row["output_sha256"] != signatures[workload]:
                raise RuntimeError(f"Hash output berbeda pada {workload}/{method}/{workers}")
            signatures[workload] = row["output_sha256"]
            row.update(run=repetition, run_id=run_id, sequence_index=len(rows) + 1)
            rows.append(row)
            memory.extend({"method": method, "workers": workers, "workload": workload,
                           "run": repetition, **sample} for sample in samples)
            save_csv(output / "raw_results.csv", rows)
            save_csv(output / "memory_samples.csv", memory)
            print(f"  {row['time_s']:.3f} s | {row['throughput_images_s']:.1f} gambar/s | "
                  f"CPU proses {row['cpu_process_percent']:.1f}%", flush=True)
    reference = {workload: sum(r["time_s"] for r in rows if r["method"] == "sequential" and r["workload"] == workload)
                 / args.repetitions for workload in ("light", "heavy")}
    for row in rows:
        row["speedup"] = reference[row["workload"]] / row["time_s"]
    save_csv(output / "raw_results.csv", rows)
    from threading_reporting import make_threading_report
    make_threading_report(output)
    (output / "status.json").write_text(json.dumps({"complete": True, "output_hashes_match": True,
                                       "measured_runs": len(rows)}, indent=2), encoding="utf-8")
    print(f"RESULT_DIR={output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--images", type=int, default=10000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--workload", choices=("light", "heavy"), default="light")
    parser.add_argument("--method", choices=("sequential", "threading"), default="sequential")
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=1)
    args = parser.parse_args()
    if not 1 <= args.images <= 10000 or args.repetitions < 2 or args.warmup < 0:
        parser.error("images: 1..10000; repetitions: >=2; warmup: >=0")
    if args.single:
        if (args.method == "sequential" and args.workers != 1) or (args.method == "threading" and args.workers == 1):
            parser.error("sequential memakai 1 worker; threading memakai 2/4")
        print(json.dumps(measure_one(args)))
    else:
        run_experiment(args)
