"""Ringkasan, grafik, dan analisis yang dihitung dari hasil eksperimen aktual."""

import json
from pathlib import Path


def make_report(output_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    raw = pd.read_csv(output_dir / "raw_results.csv")
    summary = raw.groupby("workload", sort=False).agg(
        runs=("run", "count"), images=("images", "first"),
        mean_time_s=("time_s", "mean"), std_time_s=("time_s", "std"),
        min_time_s=("time_s", "min"), max_time_s=("time_s", "max"),
        mean_throughput_images_s=("throughput_images_s", "mean"),
        mean_cpu_process_percent=("cpu_process_percent", "mean"),
        mean_cpu_machine_capacity_percent=("cpu_machine_capacity_percent", "mean"),
        mean_rss_before_mib=("rss_before_mib", "mean"),
        max_rss_peak_sampled_mib=("rss_peak_sampled_mib", "max"),
    ).reset_index()
    summary["std_time_s"] = summary["std_time_s"].fillna(0)
    summary["time_cv_percent"] = 100 * summary.std_time_s / summary.mean_time_s
    summary.to_csv(output_dir / "summary.csv", index=False)
    light = summary.set_index("workload").loc["light"]
    heavy = summary.set_index("workload").loc["heavy"]
    ratio = heavy.mean_time_s / light.mean_time_s
    environment = json.loads((output_dir / "environment.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    colors = ["#3b82a0", "#dc8745"]
    axes[0].bar(summary.workload.str.upper(), summary.mean_time_s,
                yerr=summary.std_time_s, capsize=6, color=colors)
    axes[0].set(title="Waktu sequential: rata-rata dan SD", ylabel="Detik")
    axes[1].bar(summary.workload.str.upper(), summary.mean_throughput_images_s, color=colors)
    axes[1].set(title="Throughput sequential", ylabel="Gambar / detik")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    fig.savefig(output_dir / "figures" / "time_throughput.png", dpi=160)
    plt.close(fig)

    samples = pd.read_csv(output_dir / "memory_samples.csv")
    fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
    for (workload, run), frame in samples.groupby(["workload", "run"], sort=False):
        ax.plot(frame.elapsed_s, frame.rss_mib, label=f"{workload.upper()} run {run}")
    ax.set(title="Sampel RAM proses selama pemrosesan", xlabel="Detik sejak mulai run", ylabel="RSS (MiB)")
    ax.legend(ncol=3, fontsize=8)
    ax.grid(alpha=0.2)
    fig.savefig(output_dir / "figures" / "memory_samples.png", dpi=160)
    plt.close(fig)

    lines = [
        "# Analisis Sequential Baseline", "",
        "Pada tahap ini saya menguji pemrosesan gambar satu per satu sebagai baseline. "
        "Saya menggunakan batch pertama CIFAR-10 yang sama untuk LIGHT dan HEAVY, "
        "dengan parameter transformasi tetap. Hasil di bawah berasal dari run lokal yang tersimpan di folder ini.", "",
        "## Hasil pengukuran", "",
        "| Workload | Gambar/run | Run | Waktu rata-rata (s) | SD (s) | Throughput rata-rata (gambar/s) | CPU proses (%) | RSS maksimum tersampel (MiB) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples():
        lines.append(f"| {row.workload.upper()} | {row.images} | {row.runs} | {row.mean_time_s:.3f} | "
                     f"{row.std_time_s:.3f} | {row.mean_throughput_images_s:.1f} | "
                     f"{row.mean_cpu_process_percent:.1f} | {row.max_rss_peak_sampled_mib:.2f} |")
    lines.extend([
        "", "## Pembacaan hasil", "",
        f"Rata-rata waktu HEAVY adalah {ratio:.2f} kali waktu LIGHT. "
        "Rasio ini membandingkan dua workload, bukan speedup metode paralel. "
        "HEAVY melakukan lebih banyak tahap transformasi, sehingga hasil tersebut saya baca "
        "dalam konteks jumlah operasi yang berbeda. Saya tidak menganggap HEAVY menghasilkan gambar yang lebih baik; "
        "pipeline ini sengaja dipakai sebagai pekerjaan eksperimen.", "",
        f"Variasi waktu LIGHT (SD/rata-rata) adalah {light.time_cv_percent:.2f}%, "
        f"sedangkan HEAVY {heavy.time_cv_percent:.2f}%. "
        "Tiga pengulangan memberi gambaran variasi awal, tetapi belum cukup untuk memastikan "
        "penyebab perbedaan antar-run. Aktivitas aplikasi lain, scheduling, dan kondisi CPU "
        "merupakan kemungkinan, bukan penyebab yang sudah dibuktikan oleh pengukuran ini.", "",
        f"CPU proses rata-rata tercatat {light.mean_cpu_process_percent:.1f}% untuk LIGHT dan "
        f"{heavy.mean_cpu_process_percent:.1f}% untuk HEAVY. Skala yang saya gunakan menganggap "
        f"100% setara dengan satu logical CPU selama interval pengukuran. Komputer ini memiliki "
        f"{environment['logical_cpus']} logical CPU. Kolom kapasitas mesin pada CSV membagi "
        "CPU proses dengan jumlah logical CPU; nilai itu bukan pengukuran pemakaian CPU seluruh sistem. "
        "Saya juga tidak menyimpulkan proses selalu berjalan pada core fisik yang sama.", "",
        f"RSS maksimum tersampel adalah {light.max_rss_peak_sampled_mib:.2f} MiB untuk LIGHT dan "
        f"{heavy.max_rss_peak_sampled_mib:.2f} MiB untuk HEAVY. RSS mencakup interpreter, library, "
        "dataset yang sudah dimuat, dan memori kerja. Nilai tersebut bukan hanya ukuran output gambar. "
        "Saya tidak menumpuk semua gambar hasil di RAM; setiap gambar hasil digunakan untuk hash "
        "kemudian diganti oleh hasil gambar berikutnya. Alokasi yang dipertahankan oleh library "
        "dan urutan run dapat memengaruhi RSS. Pengambilan sampel setiap 100 gambar juga dapat "
        "melewatkan puncak singkat, jadi angka ini bukan peak RAM mutlak.", "",
        "## Validasi dan batas pengukuran", "",
        "Hash SHA-256 output konsisten antar-pengulangan untuk workload yang sama. "
        "Ini memeriksa reproduksibilitas byte output, bukan penilaian kualitas visual. "
        "Waktu mencakup konversi array ke gambar, transformasi, perhitungan hash output, loop, "
        "dan pemeriksaan RSS. Download, pemuatan dataset, warm-up, penulisan CSV, dan pembuatan grafik "
        "berada di luar timer. Overhead monitoring tetap ada; belum diukur terpisah.", "",
        "LIGHT dan HEAVY dijalankan bergantian antar-pengulangan untuk mengurangi ketergantungan "
        "pada urutan, tetapi ini tidak menghilangkan pengaruh background task atau temperatur. "
        "Resize mengubah ukuran kerja menjadi 64 x 64; gambar input tetap berasal dari CIFAR-10 32 x 32. "
        "Efek memperbesar gambar ini harus dijaga sama ketika metode lain dibandingkan.", "",
        "## Kesimpulan sementara", "",
        "Saya sudah memperoleh baseline untuk dua tingkat pekerjaan. Speedup sequential ditetapkan "
        "1,00 sebagai acuan. Saya belum bisa menyimpulkan threading atau multiprocessing lebih cepat "
        "karena keduanya belum diuji. Langkah berikutnya adalah menjalankan transformasi, jumlah "
        "gambar, dan kebijakan output yang sama dengan 2 dan 4 worker, lalu membandingkan waktu serta resource-nya.", "",
        "## Sumber", "",
        "- CIFAR-10: https://www.cs.toronto.edu/~kriz/cifar.html",
        "- Pillow ImageFilter: https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html",
        "- psutil: https://psutil.readthedocs.io/",
        "- Python perf_counter: https://docs.python.org/3/library/time.html#time.perf_counter", "",
    ])
    (output_dir / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
