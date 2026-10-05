"""Jalankan baseline atau perbandingan threading; hasil disimpan terpisah."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from dataset import load_batch
from image_processing import TRANSFORM_CONFIG, process_image
from sequential import run_sequential


def save_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Eksperimen performa CIFAR-10")
    parser.add_argument("--images", type=int, default=10000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--experiment", choices=("sequential", "threading", "comparison"), default="sequential")
    args = parser.parse_args()
    if not 1 <= args.images <= 10000 or args.repetitions < 2 or args.warmup < 0:
        parser.error("images: 1..10000; repetitions: >=2; warmup: >=0")
    if args.experiment == "comparison":
        from comparison_experiment import run_experiment
        run_experiment(args)
        return
    if args.experiment == "threading":
        from threading_experiment import run_experiment
        run_experiment(args)
        return
    images, _ = load_batch("data_batch_1.bin")
    images = images[:args.images]
    now = datetime.now(timezone(timedelta(hours=7)))
    run_id = now.strftime("%Y%m%d_%H%M%S_%f")
    output_dir = PROJECT_ROOT / "results" / "sequential" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "figures").mkdir()
    snapshot = output_dir / "source_snapshot"
    snapshot.mkdir()
    sources = [Path(__file__), *[PROJECT_ROOT / "src" / name for name in
               ("dataset.py", "image_processing.py", "sequential.py", "reporting.py")]]
    hashes = {}
    for source in sources:
        shutil.copy2(source, snapshot / source.name)
        hashes[str(source.relative_to(PROJECT_ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    cpu_name = platform.processor()
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    environment = {
        "timestamp": now.isoformat(), "run_id": run_id, "os": platform.platform(),
        "python": platform.python_version(), "python_executable": sys.executable,
        "cpu": cpu_name, "physical_cores": psutil.cpu_count(logical=False),
        "logical_cpus": psutil.cpu_count(), "total_ram_gib": psutil.virtual_memory().total / 1024**3,
        "execution": "local/on-premise", "benchmark_pid": psutil.Process().pid,
        "libraries": {name: importlib.metadata.version(name) for name in
                      ("numpy", "pillow", "psutil", "pandas", "matplotlib")},
    }
    batch_path = PROJECT_ROOT / "data" / "cifar-10-batches-bin" / "data_batch_1.bin"
    config = {"images": args.images, "repetitions": args.repetitions, "warmup_images_per_workload": min(args.warmup, len(images)),
              "batch": "data_batch_1.bin", "batch_sha256": hashlib.sha256(batch_path.read_bytes()).hexdigest(),
              "method": "sequential", "workers": 1, "rss_sample_every_images": 100,
              "transforms": TRANSFORM_CONFIG, "order": "light/heavy then heavy/light, alternating",
              "timer_includes": ["array-to-image", "transforms", "output hashing", "loop", "RSS sampling"],
              "timer_excludes": ["download", "load dataset", "warmup", "CSV", "figures", "process startup"],
              "source_sha256": hashes}
    for name, payload in (("environment.json", environment), ("config.json", config)):
        (output_dir / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for workload in ("light", "heavy"):
        for pixels in images[:args.warmup]:
            process_image(pixels, workload)
    raw, memory = [], []
    signatures = {}
    for repetition in range(1, args.repetitions + 1):
        order = ("light", "heavy") if repetition % 2 else ("heavy", "light")
        for workload in order:
            print(f"Run {repetition}/{args.repetitions}: {workload.upper()}, {len(images)} gambar...", flush=True)
            row = run_sequential(images, workload)
            samples = row.pop("memory_samples")
            row.update(run=repetition, run_id=run_id, sequence_index=len(raw) + 1)
            if workload in signatures and row["output_sha256"] != signatures[workload]:
                raise RuntimeError("Output antar-run tidak konsisten")
            signatures[workload] = row["output_sha256"]
            raw.append(row)
            memory.extend({"workload": workload, "run": repetition, **sample} for sample in samples)
            save_csv(output_dir / "raw_results.csv", raw)
            save_csv(output_dir / "memory_samples.csv", memory)
            print(f"  {row['time_s']:.3f} s | {row['throughput_images_s']:.1f} gambar/s | "
                  f"CPU proses {row['cpu_process_percent']:.1f}%", flush=True)
    from reporting import make_report
    make_report(output_dir)
    (output_dir / "status.json").write_text(json.dumps({"complete": True, "output_hashes_match": True,
         "measured_runs": len(raw)}, indent=2), encoding="utf-8")
    print(f"RESULT_DIR={output_dir}", flush=True)


if __name__ == "__main__":
    main()
