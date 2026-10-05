# Analisis Perbandingan Sequential, Multithreading, dan Multiprocessing

Saya menguji 10,000 gambar dari batch pertama CIFAR-10 secara lokal di Windows. Ada lima konfigurasi pada LIGHT dan HEAVY, masing-masing 7 pengulangan. Seluruh angka perbandingan berasal dari rangkaian ini, dengan fungsi transformasi dan pemantauan resource yang sama. Hasil notebook 01 dan 02 tetap menjadi catatan tahap awal.

## Hasil pengukuran

| Workload | Metode | Worker | Waktu rata-rata (s) | SD (s) | Gambar/s | Speedup | Estimasi CPU tree (%) | RSS tree peak rata-rata (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| HEAVY | sequential | 1 | 4.672 | 0.106 | 2141.5 | 1.00 | 97.2 | 66.75 |
| HEAVY | threading | 2 | 3.357 | 0.065 | 2979.7 | 1.39 | 156.4 | 69.40 |
| HEAVY | threading | 4 | 3.275 | 0.126 | 3057.2 | 1.43 | 190.6 | 72.37 |
| HEAVY | multiprocessing | 2 | 2.639 | 0.033 | 3790.1 | 1.77 | 211.4 | 146.76 |
| HEAVY | multiprocessing | 4 | 1.954 | 0.052 | 5121.1 | 2.39 | 368.5 | 226.26 |
| LIGHT | sequential | 1 | 0.585 | 0.021 | 17101.8 | 1.00 | 98.4 | 66.60 |
| LIGHT | threading | 2 | 0.947 | 0.078 | 10613.9 | 0.62 | 130.1 | 68.28 |
| LIGHT | threading | 4 | 0.938 | 0.043 | 10680.2 | 0.62 | 134.2 | 70.34 |
| LIGHT | multiprocessing | 2 | 0.737 | 0.022 | 13580.5 | 0.79 | 194.4 | 145.52 |
| LIGHT | multiprocessing | 4 | 0.682 | 0.005 | 14668.4 | 0.86 | 347.3 | 222.00 |

## Analisis per-workload

### LIGHT

Rata-rata tercepat adalah sequential, dengan waktu 0.585 detik dan speedup 1.00. Process 2 membutuhkan 0.737 detik (speedup 0.79), sedangkan process 4 0.682 detik (speedup 0.86). Nilai speedup di bawah 1 menunjukkan lebih lambat dari sequential.

Dari process 2 ke process 4, perubahan waktu rata-rata adalah -7.5%. Angka positif berarti bertambah lambat, angka negatif berarti lebih cepat. Saya tidak menganggap jumlah worker berbanding lurus dengan peningkatan kecepatan.

RSS tree peak tersampel rata-rata meningkat dari 66.60 MiB pada sequential menjadi 145.52 MiB untuk process 2 dan 222.00 MiB untuk process 4. Nilai ini adalah jumlah RSS proses pada snapshot bersamaan, bukan ukuran memori unik.

Konfigurasi dengan waktu terendah pada setiap putaran adalah sequential_1: 7 dari 7 putaran. Setiap putaran berisi seluruh konfigurasi yang dijalankan berurutan, bukan pada saat bersamaan. Hitungan ini menunjukkan konsistensi deskriptif, bukan uji signifikansi.

| Konfigurasi | Median (s) | Minimum (s) | Maksimum (s) | CV waktu (%) |
|---|---:|---:|---:|---:|
| sequential_1 | 0.588 | 0.554 | 0.613 | 3.52 |
| threading_2 | 0.933 | 0.864 | 1.079 | 8.24 |
| threading_4 | 0.925 | 0.903 | 1.025 | 4.60 |
| multiprocessing_2 | 0.731 | 0.703 | 0.768 | 3.04 |
| multiprocessing_4 | 0.682 | 0.672 | 0.687 | 0.76 |

Median saya gunakan sebagai pembanding terhadap rata-rata ketika terdapat run yang jauh lebih lambat. Semua run tetap disertakan dalam CSV dan rata-rata.

### HEAVY

Rata-rata tercepat adalah multiprocessing 4 worker, dengan waktu 1.954 detik dan speedup 2.39. Process 2 membutuhkan 2.639 detik (speedup 1.77), sedangkan process 4 1.954 detik (speedup 2.39). Nilai speedup di bawah 1 menunjukkan lebih lambat dari sequential.

Dari process 2 ke process 4, perubahan waktu rata-rata adalah -26.0%. Angka positif berarti bertambah lambat, angka negatif berarti lebih cepat. Saya tidak menganggap jumlah worker berbanding lurus dengan peningkatan kecepatan.

RSS tree peak tersampel rata-rata meningkat dari 66.75 MiB pada sequential menjadi 146.76 MiB untuk process 2 dan 226.26 MiB untuk process 4. Nilai ini adalah jumlah RSS proses pada snapshot bersamaan, bukan ukuran memori unik.

Konfigurasi dengan waktu terendah pada setiap putaran adalah multiprocessing_4: 7 dari 7 putaran. Setiap putaran berisi seluruh konfigurasi yang dijalankan berurutan, bukan pada saat bersamaan. Hitungan ini menunjukkan konsistensi deskriptif, bukan uji signifikansi.

| Konfigurasi | Median (s) | Minimum (s) | Maksimum (s) | CV waktu (%) |
|---|---:|---:|---:|---:|
| sequential_1 | 4.626 | 4.545 | 4.830 | 2.26 |
| threading_2 | 3.379 | 3.265 | 3.438 | 1.93 |
| threading_4 | 3.244 | 3.156 | 3.528 | 3.86 |
| multiprocessing_2 | 2.644 | 2.572 | 2.674 | 1.24 |
| multiprocessing_4 | 1.952 | 1.896 | 2.058 | 2.67 |

Median saya gunakan sebagai pembanding terhadap rata-rata ketika terdapat run yang jauh lebih lambat. Semua run tetap disertakan dalam CSV dan rata-rata.

## Hubungan hasil dengan Operating System

Thread membaca array input dalam satu proses. Process memiliki interpreter serta ruang alamat sendiri. Implementasi ini mengirim chunk array melalui mekanisme serialization/IPC dan menerima byte output kembali; tidak memakai shared memory. Akibatnya, multiprocessing mengubah biaya koordinasi dan memori, selain jumlah worker.

Worker Windows dibuat dengan spawn. Startup worker, import library di worker, pengiriman data, pemrosesan, pengumpulan output, dan shutdown pool berada di dalam timer. Warm-up 50 gambar hanya dilakukan pada proses utama sebelum timer; worker baru tidak mendapat warm-up sebelumnya. Ini merupakan skenario pool baru per-run, bukan skenario pool persistent. Overhead tersebut merupakan kemungkinan penjelasan hasil, tetapi saya belum mengukurnya sebagai komponen terpisah.

Setiap worker process mempunyai GIL sendiri. Namun menghindari GIL antar-worker tidak menjamin program lebih cepat karena IPC, serialization, serta bagian serial seperti hashing tetap ada. Pada threading, library native dapat melepas GIL. Saya tidak menganggap perbedaan waktu membuktikan GIL sebagai satu-satunya penyebab.

Task pool berisi 100 gambar, dengan maksimum 2 x worker task belum dikonsumsi. Task diambil sesuai urutan pengiriman agar hash sama. Menunggu output awal dapat menghambat pengumpulan output lain. Sequential memproses satu gambar per-iterasi tanpa task pool. Kesimpulan berlaku untuk kebijakan pembagian pekerjaan ini.

## Cara membaca CPU dan RAM

CPU tree mencakup proses benchmark dan turunannya, dengan 100% setara satu logical CPU. Komputer ini memiliki 22 logical CPU. Persentase dapat melebihi 100%, tetapi bukan total penggunaan seluruh CPU komputer.

CPU proses utama dihitung dari perubahan CPU time selama timer. CPU worker dihitung dari nilai kumulatif terakhir yang sempat diamati; snapshot diambil sebelum shutdown agar worker yang masih hidup tercatat. Sebagian CPU teardown setelah snapshot terakhir dapat tidak tercatat. Karena itu kolom CPU tree adalah estimasi tersampel, bukan pengukuran CPU total yang sepenuhnya presisi.

RAM diambil tiap sekitar 50 ms dengan monitor thread yang sama untuk semua metode, serta snapshot di awal, sebelum shutdown pool, dan di akhir. Yang dilaporkan adalah maksimum jumlah RSS pada snapshot, bukan penjumlahan peak tiap proses pada waktu berbeda. Halaman memori shared bisa dihitung lebih dari sekali; puncak singkat dan perubahan proses saat snapshot bisa terlewat. Angka ini bukan unique memory/PSS atau seluruh RAM komputer. Overhead monitor ikut memengaruhi semua kondisi.

## Validasi dan keterbatasan

Semua konfigurasi pada workload yang sama menghasilkan hash SHA-256 yang sama. Jumlah output dan rumus throughput juga diperiksa. Hash membuktikan konsistensi byte output pada input ini, bukan penilaian kualitas visual.

7 pengulangan memberi gambaran variasi yang lebih lengkap, tetapi bukan uji signifikansi. Input ringan yang selesai di bawah satu detik sensitif terhadap gangguan kecil. Urutan konfigurasi diputar, tetapi temperatur, background task, serta pemilihan core tidak dikendalikan atau dicatat. Saya belum membandingkan input lebih besar, chunk lain, shared memory, pool persistent, atau pipeline penyimpanan file.

Metode monitoring pada tahap ini berbeda dari notebook 01/02. Karena itu, perbandingan akhir hanya memakai CSV rangkaian ini; angka CPU/RAM lama tidak dicampur dengan kolom process tree baru. Error bar adalah sample SD, bukan confidence interval.

## Kesimpulan

Berdasarkan rata-rata yang terukur, konfigurasi tercepat adalah LIGHT: sequential; HEAVY: multiprocessing 4 worker. Saya membaca pilihan tersebut bersama biaya CPU/RAM dan variasi run. Hasil ini menunjukkan pilihan metode perlu disesuaikan dengan workload serta biaya koordinasi, bukan sekadar memilih jumlah worker terbanyak. Kesimpulan terbatas pada kondisi lokal ini.

## Referensi

- https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor
- https://docs.python.org/3.11/library/multiprocessing.html#contexts-and-start-methods
- https://psutil.readthedocs.io/
- https://www.cs.toronto.edu/~kriz/cifar.html
