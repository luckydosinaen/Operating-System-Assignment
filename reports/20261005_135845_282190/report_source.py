"""Susun laporan akhir dari satu rangkaian terverifikasi tanpa mengarang angka."""

import json
import hashlib
import shutil
from pathlib import Path


def make_final_report(result_dir: Path, project: Path) -> Path:
    import pandas as pd

    config = json.loads((result_dir / "config.json").read_text(encoding="utf-8"))
    environment = json.loads((result_dir / "environment.json").read_text(encoding="utf-8"))
    status = json.loads((result_dir / "status.json").read_text(encoding="utf-8"))
    if not status.get("complete") or not status.get("output_hashes_match"):
        raise ValueError("Rangkaian belum selesai atau validasi hash gagal")
    summary = pd.read_csv(result_dir / "summary.csv")
    destination = project / "reports" / result_dir.name
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(result_dir / "figures", destination / "figures")
    relative_result = f"../../results/comparison/{result_dir.name}"
    winners = []
    for workload in ("light", "heavy"):
        frame = summary[summary.workload == workload]
        best = frame.loc[frame.mean_time_s.idxmin()]
        name = "sequential" if best.method == "sequential" else f"{best.method} {int(best.workers)} worker"
        winners.append(f"{workload.upper()} memiliki rata-rata tercepat pada {name} "
                       f"({best.mean_time_s:.3f} detik, speedup {best.speedup:.2f})")
    opening = f"""# Analisis Performa Sequential Multithreading dan Multiprocessing pada Pemrosesan Gambar

## Ringkasan

Saya membandingkan lima konfigurasi pemrosesan gambar pada komputer Windows lokal: sequential, multithreading dengan 2 dan 4 worker, serta multiprocessing dengan 2 dan 4 worker. Saya menggunakan {config['images']:,} gambar dari CIFAR-10, dua workload, dan {config['repetitions']} pengulangan per-kondisi, sehingga ada {status['measured_runs']} pengukuran. {'; '.join(winners)}. Hasil tersebut saya baca bersama penggunaan resource dan variasi run, sehingga pilihan metode tidak hanya ditentukan oleh jumlah worker.

## Latar belakang dan tujuan

Dalam pemrosesan gambar, pekerjaan dapat dilakukan satu per satu atau dibagi ke beberapa worker. Pembagian pekerjaan berpotensi mempercepat program, tetapi juga menambah biaya koordinasi dan penggunaan resource. Saya melakukan eksperimen ini untuk melihat hubungan tersebut dengan pengelolaan thread, process, CPU, dan memori pada Operating System.

Pertanyaan yang saya gunakan adalah:

1. Konfigurasi mana yang memiliki rata-rata waktu terendah pada LIGHT dan HEAVY?
2. Apakah penambahan worker dari 2 menjadi 4 mempercepat pekerjaan?
3. Bagaimana penggunaan CPU dan RAM berubah ketika metode pemrosesan berubah?
4. Seberapa konsisten hasilnya antar-pengulangan?

## Dataset dan lingkungan pengujian

Saya memakai batch pertama CIFAR-10 yang berisi 10.000 gambar RGB 32 × 32 piksel. Label kelas tidak digunakan dalam transformasi. Dataset resmi sudah diverifikasi dengan checksum, dan hash batch yang dipakai dicatat pada konfigurasi setiap eksekusi. Resize menggunakan ukuran kerja 64 × 64; ukuran kerja ini memperbesar jumlah piksel yang diproses, bukan menambah detail asli gambar.

| Komponen | Lingkungan yang tercatat |
|---|---|
| Waktu pengujian | {environment['timestamp']} |
| OS dari platform Python | {environment['os']} |
| Python | {environment['python']} |
| CPU | {environment['cpu']} |
| Core fisik dan logical CPU | {environment['physical_cores']} dan {environment['logical_cpus']} |
| RAM terpasang | {environment['total_ram_gib']:.2f} GiB |
| Tempat eksekusi | Local/on-premise |

String OS di atas adalah keluaran fungsi platform Python, bukan identifikasi edisi Windows melalui pemeriksaan terpisah. Versi library tercatat pada file environment: NumPy {environment['libraries']['numpy']}, Pillow {environment['libraries']['pillow']}, psutil {environment['libraries']['psutil']}, pandas {environment['libraries']['pandas']}, dan Matplotlib {environment['libraries']['matplotlib']}.

## Metode eksperimen

| Workload | Transformasi dengan parameter tetap |
|---|---|
| LIGHT | Resize 64 × 64 BILINEAR lalu grayscale |
| HEAVY | Resize 64 × 64 BILINEAR, rotate 15°, Gaussian blur radius 2, sharpen, color factor 1,2, lalu edge detection |

Sequential memakai satu worker pengolah. Thread pool memakai 2 atau 4 thread dalam satu proses. Process pool memakai 2 atau 4 proses dengan start method spawn. Pada kedua jenis pool, satu task berisi 100 gambar, dan jumlah task yang belum dikonsumsi dibatasi 2 × worker. Output dikonsumsi sesuai urutan input dan dimasukkan ke SHA-256; saya tidak menyimpan seluruh gambar hasil sekaligus.

Setiap kondisi dijalankan di proses benchmark baru. Parent memproses 50 gambar sebagai warm-up sebelum timer. Worker process tetap baru dan belum di-warm-up. Timer mencakup transformasi, konversi byte, hashing, monitoring, startup/shutdown pool, penjadwalan task, dan komunikasi data. Startup interpreter benchmark, pemuatan dataset, warm-up parent, serta penulisan laporan berada di luar timer.

Urutan sepuluh kondisi diputar tiga posisi setiap pengulangan. Saya tidak menghapus outlier untuk memperbaiki hasil. Angka laporan akhir berasal dari rangkaian dengan {config['repetitions']} pengulangan ini; hasil tiga pengulangan sebelumnya dipertahankan sebagai tahap awal dan tidak digabungkan ke rata-rata akhir.

| Metrik | Definisi |
|---|---|
| Execution time | Wall time dalam detik dari perf_counter |
| Throughput | Jumlah gambar dibagi waktu setiap run; ringkasan memakai rata-rata nilai per-run |
| Speedup | Rata-rata waktu sequential dibagi rata-rata waktu metode pada workload yang sama |
| Efficiency | Speedup dibagi worker × 100%; bukan persentase CPU |
| Variasi waktu | Sample SD, CV = SD/rata-rata × 100%, median, minimum, dan maksimum |
| CPU sampled tree | CPU delta parent ditambah CPU kumulatif terakhir child yang sempat diamati, dibagi wall time × 100% |
| RSS sampled tree | Maksimum jumlah RSS parent dan descendant processes pada snapshot bersamaan |

Monitor mengambil snapshot sekitar setiap 50 ms. CPU tree merupakan estimasi karena CPU teardown child setelah snapshot terakhir dapat terlewat. RAM tree bisa menghitung halaman shared lebih dari sekali dan melewatkan puncak singkat. Overhead monitor juga masuk ke pengukuran. Batasan ini berlaku pada seluruh konfigurasi dalam rangkaian akhir.

## Grafik hasil

![Waktu rata-rata dan sample SD](figures/time_comparison.png)

![Waktu setiap run dan median](figures/run_distribution.png)

![Speedup terhadap sequential](figures/speedup.png)

![Estimasi CPU process tree](figures/cpu_comparison.png)

![RSS process tree maksimum tersampel](figures/memory_comparison.png)

Titik pada grafik distribusi menunjukkan seluruh pengulangan; garis hitam menunjukkan median. Error bar pada grafik rata-rata adalah sample SD. Grafik tidak menyatakan confidence interval atau hasil uji signifikansi.

"""
    analysis = (result_dir / "analysis.md").read_text(encoding="utf-8")
    analysis_sections = analysis[analysis.index("## Hasil pengukuran"):]
    for url, label in [
        ("https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor", "Python 3.11 ProcessPoolExecutor"),
        ("https://docs.python.org/3.11/library/multiprocessing.html#contexts-and-start-methods", "Python 3.11 multiprocessing dan start methods"),
        ("https://psutil.readthedocs.io/", "psutil Process and System Utilities"),
        ("https://www.cs.toronto.edu/~kriz/cifar.html", "CIFAR-10 dan laporan Alex Krizhevsky 2009"),
    ]:
        analysis_sections = analysis_sections.replace("- " + url, f"- [{label}]({url})")
    ending = f"""

## Bukti hasil dan cara mengulang

Data pendukung tersedia di [hasil mentah]({relative_result}/raw_results.csv), [ringkasan]({relative_result}/summary.csv), [sampel resource]({relative_result}/resource_samples.csv), [konfigurasi]({relative_result}/config.json), dan [environment]({relative_result}/environment.json). Snapshot source serta hash input disimpan bersama hasil untuk membantu memeriksa pekerjaan yang dijalankan.

Notebook `04_final_analysis.ipynb` memuat penjelasan dan output eksekusi yang sama. Untuk mengulang melalui terminal dari folder project:

```powershell
.\\.venv\\Scripts\\python.exe main.py --experiment comparison --images 10000 --repetitions {config['repetitions']} --warmup 50
```

Setiap eksekusi membuat folder hasil baru. Pengulangan tambahan, input lebih besar, atau skenario pool persistent dapat menjadi pengembangan berikutnya; hasilnya harus dilaporkan terpisah jika mengubah skenario.
"""
    path = destination / "Laporan_Akhir.md"
    path.write_text(opening + analysis_sections + ending, encoding="utf-8")
    shutil.copy2(Path(__file__), destination / "report_source.py")
    manifest = {
        "measurement_results": str(result_dir),
        "notebook": "04_final_analysis.ipynb",
        "measured_runs": status["measured_runs"],
        "repetitions": config["repetitions"],
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "raw_csv_sha256": hashlib.sha256((result_dir / "raw_results.csv").read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (destination / "report_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
