# Operating System Assignment

Tugas Operating System: analisis performa pemrosesan gambar menggunakan tiga pendekatan:

- sequential
- multithreading
- multiprocessing

## Status

Setup dasar dan seluruh metode sudah disiapkan. Mulai dari `04_final_analysis.ipynb` untuk rangkaian akhir dengan tujuh pengulangan per-kondisi (70 pengukuran) dan laporan lengkap di `reports/`. Notebook 01 sampai 03 merupakan dokumentasi tahap awal.

## Panduan untuk pembaca

- [Notebook analisis akhir](04_final_analysis.ipynb): penjelasan, kode, output, tabel, dan grafik.
- [Laporan akhir](reports/20261005_135845_282190/Laporan_Akhir.md): metode, hasil, pembahasan, dan keterbatasan.
- [Hasil mentah akhir](results/comparison/20261005_135845_282190/raw_results.csv) dan [ringkasan akhir](results/comparison/20261005_135845_282190/summary.csv).
- [Dataset lengkap dan sumbernya](data/README.md): seluruh 60.000 gambar dalam enam batch binary, bukan hanya contoh gambar.

Eksperimen akhir memakai 10.000 gambar dari batch pertama, dua workload (LIGHT/HEAVY), sequential serta threading/multiprocessing dengan 2 dan 4 worker. Setiap kondisi diulang tujuh kali. Pada komputer pengujian, LIGHT tercepat dengan sequential (rata-rata 0,585 detik), sedangkan HEAVY tercepat dengan multiprocessing 4 worker (1,954 detik, speedup 2,39 kali terhadap sequential). Hasil ini khusus untuk konfigurasi dan kondisi pengujian yang dicatat, bukan jaminan untuk semua komputer atau workload.

Output notebook sudah tersimpan dan dapat dibaca tanpa menjalankan ulang benchmark. Folder `results/` mempertahankan tahap awal dan pengukuran akhir secara terpisah; angka antar-tahap tidak digabung karena metode monitoring telah diperbaiki.

## Struktur

```text
Operating-System-Assignment/
|-- .venv/
|-- data/
|-- results/
|-- src/
|-- reports/
|-- 01_sequential_baseline.ipynb
|-- 02_multithreading.ipynb
|-- 03_multiprocessing_comparison.ipynb
|-- 04_final_analysis.ipynb
|-- main.py
|-- requirements.txt
`-- README.md
```

## Menjalankan project

Python yang digunakan untuk pengukuran: **3.11.9**. Setelah clone/download repository, buka PowerShell di folder project dan siapkan environment sendiri:

```powershell
git clone https://github.com/luckydosinaen/Operating-System-Assignment.git
cd Operating-System-Assignment
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --sys-prefix --name os-assignment --display-name "Python (OS Assignment .venv)"
```

Jika hanya ada perintah `python`, gunakan `python -m venv .venv` dan periksa versinya. Pilih interpreter `.venv/Scripts/python.exe` atau kernel project di editor notebook. Paket yang dipakai tercatat dalam `environment.json` setiap pengukuran; instalasi baru dari `requirements.txt` dapat mengambil versi berbeda.

Environment `.venv/` tidak disertakan di GitHub karena merupakan instalasi lokal, bukan kode project. Dataset yang sudah diekstrak, notebook dengan output, seluruh hasil eksperimen, dan laporan disertakan. Arsip unduhan `data/cifar-10-binary.tar.gz` tidak diunggah karena mengulang isi enam batch yang sudah tersedia dan melewati batas ukuran file GitHub. Arsip asli tetap tersedia dari sumber resmi dan dapat diunduh kembali melalui script setup.

Aktivasi environment bersifat opsional:

```powershell
.\.venv\Scripts\Activate.ps1
```

Lalu jalankan:

```powershell
python main.py
```

Dataset dan hasil eksperimen disimpan di `data/` dan `results/`. Menjalankan `python main.py` menggunakan eksperimen sequential; untuk perbandingan akhir gunakan perintah di bagian terakhir.

## Dataset CIFAR-10

Sumber resmi: https://www.cs.toronto.edu/~kriz/cifar.html

Project memakai format binary resmi, dibaca langsung dengan NumPy tanpa library machine learning tambahan. Dataset lengkap berisi 50.000 gambar training dan 10.000 gambar test, semuanya RGB 32 x 32 piksel. Untuk eksperimen awal gunakan `data_batch_1.bin` (10.000 gambar), sehingga input dapat dipakai konsisten pada semua pendekatan.

Untuk mengunduh dan memverifikasi ulang dataset, jalankan dari folder project:

```powershell
.\.venv\Scripts\python.exe src\setup_dataset.py
```

Script memakai kembali arsip yang sudah terunduh jika checksum MD5 cocok dengan checksum resmi `c32a1d4ab5d03f1284b67883e8d87530`. Script memeriksa keenam batch, membuat contoh gambar, dan menyimpan ringkasan dataset:

- `data/cifar-10-binary.tar.gz`: cache arsip asli terverifikasi pada komputer lokal, tidak di GitHub.
- `data/cifar-10-batches-bin/`: lima batch training, satu batch test, dan nama kelas.
- `data/sample_image.png`: satu gambar asli 32 x 32 piksel.
- `data/sample_image_preview.png`: tampilan gambar yang diperbesar untuk inspeksi.
- `data/dataset_info.json`: hasil verifikasi dan informasi dataset.
- `src/dataset.py`: pembaca batch; `load_batch()` mengembalikan images dengan bentuk `(10000, 32, 32, 3)` dan labels dengan bentuk `(10000,)`, bertipe `uint8`.

Contoh gambar yang diperbesar hanya untuk melihat isi dataset; eksperimen tetap menggunakan gambar asli. Menjalankan setup dataset tidak menjalankan benchmark.

Referensi dataset: Alex Krizhevsky (2009), *Learning Multiple Layers of Features from Tiny Images*, tersedia melalui halaman sumber resmi di atas.

## Sequential baseline dan notebook

Buka `01_sequential_baseline.ipynb` di VS Code. Pilih kernel **Python (OS Assignment .venv)** atau interpreter `.venv/Scripts/python.exe`, lalu jalankan cell dari atas ke bawah. Notebook sudah dilengkapi output dari eksperimen lokal, penjelasan dengan sudut pandang saya, contoh gambar, tabel, grafik, dan analisis hasil. Pelajari dan sesuaikan penjelasannya dengan pemahaman sendiri sebelum dipresentasikan.

Untuk menjalankan eksperimen langsung melalui terminal tanpa aktivasi environment:

```powershell
.\.venv\Scripts\python.exe main.py --images 10000 --repetitions 3 --warmup 50
```

LIGHT: resize 64 x 64 dan grayscale. HEAVY: resize 64 x 64, rotate 15 derajat, Gaussian blur radius 2, sharpen, color factor 1,2, dan edge detection. Semua parameter tetap dan tidak memakai random augmentation. Input memakai `data_batch_1.bin`.

Struktur tambahan:

```text
01_sequential_baseline.ipynb
src/
|-- image_processing.py
|-- sequential.py
`-- reporting.py
results/sequential/<waktu-eksekusi>/
|-- raw_results.csv
|-- summary.csv
|-- memory_samples.csv
|-- environment.json
|-- config.json
|-- status.json
|-- analysis.md
|-- source_snapshot/
`-- figures/
```

Setiap eksekusi membuat folder hasil baru. `source_snapshot` dan hash input menyimpan jejak kode serta dataset yang dipakai. `status.json` dengan `complete: true` menandai eksperimen selesai; folder tanpa penanda ini merupakan eksekusi yang belum selesai.

Waktu yang diukur mencakup loop transformasi, konversi array, hashing output, dan sampling RSS setiap 100 gambar. Pemuatan data, startup proses, warm-up, penyimpanan hasil, serta grafik berada di luar timer. CPU dihitung dari perubahan CPU time proses, dengan 100% setara satu logical CPU. RSS maksimum adalah maksimum tersampel, bukan peak mutlak. Output tidak ditumpuk di RAM. Detail metode dan batasan ada di notebook serta `analysis.md`.

Notebook memanggil eksperimen melalui proses Python terpisah agar resource kernel tidak tercampur dengan resource benchmark; pengolahan gambar tetap memakai satu worker sequential. Angka analisis otomatis mengikuti CSV run yang bersangkutan. Rata-rata dan sample standard deviation berasal dari tiga run per-workload; error bar bukan confidence interval. Speedup sequential adalah 1,00 sebagai baseline, sedangkan rasio waktu HEAVY/LIGHT bukan speedup antar-metode.

## Perbandingan multithreading

Buka `02_multithreading.ipynb` dengan kernel project yang sama. Notebook ini mengukur ulang sequential bersama threading 2 dan 4 worker pada LIGHT/HEAVY, masing-masing tiga kali. Baseline pembanding berasal dari rangkaian ini, bukan angka notebook 01. Seluruh hash output per-workload harus sama antar-metode.

```powershell
.\.venv\Scripts\python.exe main.py --experiment threading --images 10000 --repetitions 3 --warmup 50
```

Fungsi pengolahan berada di `src/threading_processing.py`, pengatur eksperimen di `src/threading_experiment.py`, dan laporan di `src/threading_reporting.py`. Hasil tersimpan terpisah di `results/threading/<waktu-eksekusi>/`, dengan CSV mentah dan ringkasan, sampel RAM, konfigurasi, environment, snapshot kode, grafik, analisis, serta penanda selesai.

Setiap kondisi memakai proses Python baru untuk pengukuran. Di dalam kondisi threading, gambar dikerjakan oleh thread dalam proses tersebut, bukan beberapa process pengolah. ThreadPoolExecutor dibatasi 2/4 worker, dengan 100 gambar per task dan maksimum 2 x worker task yang belum dikonsumsi. Future dikonsumsi sesuai urutan input dan hashing dilakukan oleh thread utama. Output sementara per-chunk ada di RAM, sehingga kebijakan ini ikut memengaruhi penggunaan memori.

Startup dan shutdown thread pool masuk timer. Startup interpreter, load dataset, warm-up transformasi 50 gambar, serta laporan berada di luar timer. Tidak ada pool persistent. Speedup ringkasan adalah rata-rata waktu sequential dibagi rata-rata waktu metode untuk workload yang sama; nilai di bawah 1 berarti lebih lambat. Speedup per-run dalam CSV memakai rata-rata sequential sebagai pembilang, sehingga nilai per-run sequential bisa berbeda dari 1, sedangkan speedup ringkasannya selalu 1. Efficiency adalah speedup / worker x 100%, bukan persentase CPU.

## Multiprocessing dan perbandingan terpadu

Buka `03_multiprocessing_comparison.ipynb` dengan kernel project. Notebook ini merupakan tahap awal dengan lima konfigurasi pada dua workload, tiga pengulangan per-kondisi (30 pengukuran). Rangkaian akhir dengan lebih banyak pengulangan ada pada notebook 04.

```powershell
.\.venv\Scripts\python.exe main.py --experiment comparison --images 10000 --repetitions 3 --warmup 50
```

Kode baru berada di `src/parallel_processing.py`, `src/resource_monitor.py`, `src/comparison_experiment.py`, dan `src/comparison_reporting.py`. Hasil di `results/comparison/<waktu-eksekusi>/` mencakup CSV mentah/ringkasan, `resource_samples.csv`, environment, config, snapshot kode, grafik, analisis, dan status selesai.

ProcessPoolExecutor memakai `spawn`, function worker di module yang dapat di-import, dan entry point dengan `if __name__ == '__main__'` untuk Windows. Pool baru dibuat pada setiap run. Worker memproses 100 gambar per-task dan antrean dibatasi 2 x worker. Chunk array dan byte output dikirim melalui serialization/IPC; shared memory tidak digunakan. Startup/shutdown pool dan IPC masuk timer; startup interpreter benchmark, load dataset, serta warm-up parent di luar timer. Worker tidak di-warm-up sebelum timer.

CPU/RAM mencakup parent dan descendant processes. Monitor thread mengambil snapshot sekitar setiap 50 ms dengan metode sama untuk seluruh konfigurasi. RAM adalah maksimum jumlah RSS bersamaan yang sempat tersampel; halaman shared bisa dihitung berulang dan puncak singkat bisa terlewat. CPU adalah parent CPU delta ditambah kumulatif CPU terakhir tiap child yang sempat diamati, sehingga CPU teardown setelah snapshot terakhir mungkin tidak tercatat. Kolom tersebut diberi nama sampled/estimate agar batasannya jelas.

Notebook 01 dan 02 dipertahankan sebagai tahap awal. Perubahan metode monitoring berarti angka CPU/RAM lama tidak dicampurkan dengan tabel perbandingan baru. Detail analisis dan penjelasan ditulis pada notebook 03 serta `analysis.md` setiap eksekusi.

## Laporan akhir dengan tujuh pengulangan

Buka `04_final_analysis.ipynb` dengan kernel **Python (OS Assignment .venv)**. Notebook memuat eksekusi tujuh pengulangan per-kondisi, seluruh 70 hasil mentah, rata-rata/median/SD/CV/rentang, grafik distribusi tiap run, dan analisis yang mengikuti hasil aktual. Urutan kondisi, dataset, transformasi, chunk size, serta metode monitoring tetap sama dengan notebook 03. Seluruh run dipertahankan; hasil lama tidak digabungkan ke rata-rata akhir.

```powershell
.\.venv\Scripts\python.exe main.py --experiment comparison --images 10000 --repetitions 7 --warmup 50
```

Cell terakhir notebook menghasilkan `reports/<waktu-eksekusi>/Laporan_Akhir.md` dengan latar belakang, tujuan, dataset, spesifikasi komputer, metode, metrik, grafik, hasil, analisis, kesimpulan, keterbatasan, referensi, dan link ke bukti pengukuran. Folder laporan mencakup salinan grafik sehingga gambar menggunakan path relatif yang sesuai. Pembuat laporan berada di `src/final_report.py`.

`fastest_per_round.csv` mencatat konfigurasi tercepat dalam setiap putaran. Hitungan ini bersifat deskriptif, bukan uji signifikansi. Penambahan pengulangan memperlihatkan variasi lebih lengkap, tetapi tidak menjamin variasi lebih kecil atau membuat pengujian bebas dari pengaruh kondisi komputer.
