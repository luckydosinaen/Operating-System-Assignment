"""Laporan terpadu dari satu rangkaian pengukuran dengan metodologi seragam."""

import json
from pathlib import Path


def make_report(output: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    raw = pd.read_csv(output / "raw_results.csv")
    raw["configuration"] = raw.method + "_" + raw.workers.astype(str)
    order = ["sequential_1", "threading_2", "threading_4", "multiprocessing_2", "multiprocessing_4"]
    labels = ["Seq", "Thread 2", "Thread 4", "Process 2", "Process 4"]
    summary = raw.groupby(["workload", "configuration", "method", "workers"]).agg(
        runs=("run", "count"), images=("images", "first"),
        mean_time_s=("time_s", "mean"), std_time_s=("time_s", "std"),
        mean_throughput_images_s=("throughput_images_s", "mean"),
        mean_cpu_tree_sampled_percent=("cpu_tree_sampled_percent", "mean"),
        mean_rss_tree_peak_sampled_mib=("rss_tree_peak_sampled_mib", "mean"),
        max_rss_tree_peak_sampled_mib=("rss_tree_peak_sampled_mib", "max"),
        mean_rss_parent_peak_sampled_mib=("rss_parent_peak_sampled_mib", "mean"),
    ).reset_index()
    summary["order"] = summary.configuration.map({name: index for index, name in enumerate(order)})
    summary = summary.sort_values(["workload", "order"]).drop(columns="order")
    summary["std_time_s"] = summary.std_time_s.fillna(0)
    summary["time_cv_percent"] = 100 * summary.std_time_s / summary.mean_time_s
    baseline = summary[summary.method == "sequential"].set_index("workload").mean_time_s
    summary["speedup"] = summary.workload.map(baseline) / summary.mean_time_s
    summary["efficiency_percent"] = 100 * summary.speedup / summary.workers
    summary.to_csv(output / "summary.csv", index=False)
    raw["speedup"] = raw.workload.map(baseline) / raw.time_s
    raw.to_csv(output / "raw_results.csv", index=False)
    colors = ["#728295", "#3b82a0", "#61b4c4", "#c28448", "#e5ad6f"]
    for filename, column, title, ylabel, with_error in [
        ("time_comparison.png", "mean_time_s", "Waktu rata-rata dan SD", "Detik", True),
        ("speedup.png", "speedup", "Speedup terhadap sequential", "Rasio", False),
        ("memory_comparison.png", "mean_rss_tree_peak_sampled_mib", "RSS process tree: rata-rata peak tersampel", "MiB", False),
        ("cpu_comparison.png", "mean_cpu_tree_sampled_percent", "Estimasi CPU process tree", "Persen (100% = satu logical CPU)", False),
    ]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
        for ax, workload in zip(axes, ("light", "heavy")):
            frame = summary[summary.workload == workload]
            ax.bar(labels, frame[column], color=colors,
                   yerr=frame.std_time_s if with_error else None, capsize=4)
            ax.set(title=f"{workload.upper()}\n{title}", ylabel=ylabel)
            ax.tick_params(axis="x", rotation=15)
            ax.set_ylim(bottom=0)
            if column == "speedup":
                ax.axhline(1, linestyle="--", color="black", linewidth=1)
            ax.grid(axis="y", alpha=0.2)
            ax.set_axisbelow(True)
        fig.savefig(output / "figures" / filename, dpi=160)
        plt.close(fig)

    environment = json.loads((output / "environment.json").read_text(encoding="utf-8"))
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    lines = ["# Analisis Perbandingan Sequential, Multithreading, dan Multiprocessing", "",
             f"Saya menguji {config['images']:,} gambar dari batch pertama CIFAR-10 secara lokal di Windows. "
             f"Ada lima konfigurasi pada LIGHT dan HEAVY, masing-masing {config['repetitions']} pengulangan. "
             "Seluruh angka perbandingan berasal dari rangkaian ini, dengan fungsi transformasi dan "
             "pemantauan resource yang sama. Hasil notebook 01 dan 02 tetap menjadi catatan tahap awal.", "",
             "## Hasil pengukuran", "",
             "| Workload | Metode | Worker | Waktu rata-rata (s) | SD (s) | Gambar/s | Speedup | Estimasi CPU tree (%) | RSS tree peak rata-rata (MiB) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary.itertuples():
        lines.append(f"| {r.workload.upper()} | {r.method} | {r.workers} | {r.mean_time_s:.3f} | "
                     f"{r.std_time_s:.3f} | {r.mean_throughput_images_s:.1f} | {r.speedup:.2f} | "
                     f"{r.mean_cpu_tree_sampled_percent:.1f} | {r.mean_rss_tree_peak_sampled_mib:.2f} |")
    lines += ["", "## Analisis per-workload", ""]
    winners = []
    for workload in ("light", "heavy"):
        frame = summary[summary.workload == workload].set_index("configuration")
        seq, p2, p4 = frame.loc["sequential_1"], frame.loc["multiprocessing_2"], frame.loc["multiprocessing_4"]
        best = frame.loc[frame.mean_time_s.idxmin()]
        winner = "sequential" if best.method == "sequential" else f"{best.method} {int(best.workers)} worker"
        winners.append(f"{workload.upper()}: {winner}")
        lines += [f"### {workload.upper()}", "",
                  f"Rata-rata tercepat adalah {winner}, dengan waktu {best.mean_time_s:.3f} detik "
                  f"dan speedup {best.speedup:.2f}. Process 2 membutuhkan {p2.mean_time_s:.3f} detik "
                  f"(speedup {p2.speedup:.2f}), sedangkan process 4 {p4.mean_time_s:.3f} detik "
                  f"(speedup {p4.speedup:.2f}). Nilai speedup di bawah 1 menunjukkan lebih lambat dari sequential.", "",
                  f"Dari process 2 ke process 4, perubahan waktu rata-rata adalah "
                  f"{100 * (p4.mean_time_s / p2.mean_time_s - 1):+.1f}%. Angka positif berarti "
                  "bertambah lambat, angka negatif berarti lebih cepat. Saya tidak menganggap "
                  "jumlah worker berbanding lurus dengan peningkatan kecepatan.", "",
                  f"RSS tree peak tersampel rata-rata meningkat dari {seq.mean_rss_tree_peak_sampled_mib:.2f} MiB "
                  f"pada sequential menjadi {p2.mean_rss_tree_peak_sampled_mib:.2f} MiB untuk process 2 "
                  f"dan {p4.mean_rss_tree_peak_sampled_mib:.2f} MiB untuk process 4. "
                  "Nilai ini adalah jumlah RSS proses pada snapshot bersamaan, bukan ukuran memori unik.", ""]
        high_cv = frame[frame.time_cv_percent >= 10]
        if not high_cv.empty:
            lines += ["Variasi relatif waktu cukup besar pada " + ", ".join(
                f"{index} (CV {row.time_cv_percent:.1f}%)" for index, row in high_cv.iterrows()) +
                ". Saya mempertahankan semua run dan tidak membuang hasil lambat hanya agar "
                "rata-rata terlihat baik. Kondisi ini memerlukan pengulangan tambahan sebelum generalisasi.", ""]
        sorted_frame = frame.sort_values("mean_time_s")
        first, second = sorted_frame.iloc[0], sorted_frame.iloc[1]
        gap = second.mean_time_s - first.mean_time_s
        if gap < max(first.std_time_s, second.std_time_s):
            lines += ["Selisih dua rata-rata tercepat dekat dengan variasi waktu yang tercatat. "
                      "Urutan tercepat di tabel bersifat deskriptif, belum membuktikan keunggulan "
                      "statistik salah satu konfigurasi.", ""]
    lines += ["## Hubungan hasil dengan Operating System", "",
              "Thread membaca array input dalam satu proses. Process memiliki interpreter serta "
              "ruang alamat sendiri. Implementasi ini mengirim chunk array melalui mekanisme "
              "serialization/IPC dan menerima byte output kembali; tidak memakai shared memory. "
              "Akibatnya, multiprocessing mengubah biaya koordinasi dan memori, selain jumlah worker.", "",
              "Worker Windows dibuat dengan spawn. Startup worker, import library di worker, "
              "pengiriman data, pemrosesan, pengumpulan output, dan shutdown pool berada di dalam "
              "timer. Warm-up 50 gambar hanya dilakukan pada proses utama sebelum timer; worker "
              "baru tidak mendapat warm-up sebelumnya. Ini merupakan skenario pool baru per-run, "
              "bukan skenario pool persistent. Overhead tersebut merupakan kemungkinan penjelasan "
              "hasil, tetapi saya belum mengukurnya sebagai komponen terpisah.", "",
              "Setiap worker process mempunyai GIL sendiri. Namun menghindari GIL antar-worker "
              "tidak menjamin program lebih cepat karena IPC, serialization, serta bagian serial "
              "seperti hashing tetap ada. Pada threading, library native dapat melepas GIL. "
              "Saya tidak menganggap perbedaan waktu membuktikan GIL sebagai satu-satunya penyebab.", "",
              "Task pool berisi 100 gambar, dengan maksimum 2 x worker task belum dikonsumsi. "
              "Task diambil sesuai urutan pengiriman agar hash sama. Menunggu output awal dapat "
              "menghambat pengumpulan output lain. Sequential memproses satu gambar per-iterasi "
              "tanpa task pool. Kesimpulan berlaku untuk kebijakan pembagian pekerjaan ini.", "",
              "## Cara membaca CPU dan RAM", "",
              f"CPU tree mencakup proses benchmark dan turunannya, dengan 100% setara satu logical "
              f"CPU. Komputer ini memiliki {environment['logical_cpus']} logical CPU. "
              "Persentase dapat melebihi 100%, tetapi bukan total penggunaan seluruh CPU komputer.", "",
              "CPU proses utama dihitung dari perubahan CPU time selama timer. CPU worker "
              "dihitung dari nilai kumulatif terakhir yang sempat diamati; snapshot diambil "
              "sebelum shutdown agar worker yang masih hidup tercatat. Sebagian CPU teardown "
              "setelah snapshot terakhir dapat tidak tercatat. Karena itu kolom CPU tree adalah "
              "estimasi tersampel, bukan pengukuran CPU total yang sepenuhnya presisi.", "",
              "RAM diambil tiap sekitar 50 ms dengan monitor thread yang sama untuk semua metode, "
              "serta snapshot di awal, sebelum shutdown pool, dan di akhir. Yang dilaporkan adalah "
              "maksimum jumlah RSS pada snapshot, bukan penjumlahan peak tiap proses pada waktu "
              "berbeda. Halaman memori shared bisa dihitung lebih dari sekali; puncak singkat "
              "dan perubahan proses saat snapshot bisa terlewat. Angka ini bukan unique memory/PSS "
              "atau seluruh RAM komputer. Overhead monitor ikut memengaruhi semua kondisi.", "",
              "## Validasi dan keterbatasan", "",
              "Semua konfigurasi pada workload yang sama menghasilkan hash SHA-256 yang sama. "
              "Jumlah output dan rumus throughput juga diperiksa. Hash membuktikan konsistensi "
              "byte output pada input ini, bukan penilaian kualitas visual.", "",
              "Tiga pengulangan adalah gambaran awal, bukan uji signifikansi. Input ringan yang "
              "selesai di bawah satu detik sensitif terhadap gangguan kecil. Urutan konfigurasi "
              "diputar, tetapi temperatur, background task, serta pemilihan core tidak dikendalikan "
              "atau dicatat. Saya belum membandingkan input lebih besar, chunk lain, shared memory, "
              "pool persistent, atau pipeline penyimpanan file.", "",
              "Metode monitoring pada tahap ini berbeda dari notebook 01/02. Karena itu, "
              "perbandingan akhir hanya memakai CSV rangkaian ini; angka CPU/RAM lama tidak "
              "dicampur dengan kolom process tree baru. Error bar adalah sample SD, bukan confidence interval.", "",
              "## Kesimpulan", "",
              "Berdasarkan rata-rata yang terukur, konfigurasi tercepat adalah " + "; ".join(winners) + ". "
              "Saya membaca pilihan tersebut bersama biaya CPU/RAM dan variasi run. Hasil ini "
              "menunjukkan pilihan metode perlu disesuaikan dengan workload serta biaya koordinasi, "
              "bukan sekadar memilih jumlah worker terbanyak. Kesimpulan terbatas pada kondisi lokal ini.", "",
              "## Referensi", "",
              "- https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor",
              "- https://docs.python.org/3.11/library/multiprocessing.html#contexts-and-start-methods",
              "- https://psutil.readthedocs.io/",
              "- https://www.cs.toronto.edu/~kriz/cifar.html", ""]
    (output / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
