# Analisis Perbandingan Sequential, Multithreading, dan Multiprocessing

Saya menguji 10,000 gambar dari batch pertama CIFAR-10 secara lokal di Windows. Ada lima konfigurasi pada LIGHT dan HEAVY, masing-masing 3 pengulangan. Seluruh angka perbandingan berasal dari rangkaian ini, dengan fungsi transformasi dan pemantauan resource yang sama. Hasil notebook 01 dan 02 tetap menjadi catatan tahap awal.

## Hasil pengukuran

| Workload | Metode | Worker | Waktu rata-rata (s) | SD (s) | Gambar/s | Speedup | Estimasi CPU tree (%) | RSS tree peak rata-rata (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| HEAVY | sequential | 1 | 6.795 | 1.245 | 1502.2 | 1.00 | 97.0 | 66.76 |
| HEAVY | threading | 2 | 4.868 | 0.732 | 2084.4 | 1.40 | 147.0 | 69.45 |
| HEAVY | threading | 4 | 5.859 | 0.444 | 1713.5 | 1.16 | 173.9 | 72.39 |
| HEAVY | multiprocessing | 2 | 3.552 | 0.111 | 2816.9 | 1.91 | 207.6 | 147.60 |
| HEAVY | multiprocessing | 4 | 2.504 | 0.128 | 4001.3 | 2.71 | 395.1 | 224.81 |
| LIGHT | sequential | 1 | 0.732 | 0.121 | 13904.2 | 1.00 | 98.1 | 66.58 |
| LIGHT | threading | 2 | 1.298 | 0.190 | 7808.3 | 0.56 | 121.2 | 68.02 |
| LIGHT | threading | 4 | 1.457 | 0.558 | 7463.3 | 0.50 | 127.0 | 70.67 |
| LIGHT | multiprocessing | 2 | 1.041 | 0.229 | 9894.0 | 0.70 | 189.6 | 145.53 |
| LIGHT | multiprocessing | 4 | 0.884 | 0.050 | 11337.8 | 0.83 | 334.0 | 222.41 |

## Analisis per-workload

### LIGHT

Rata-rata tercepat adalah sequential, dengan waktu 0.732 detik dan speedup 1.00. Process 2 membutuhkan 1.041 detik (speedup 0.70), sedangkan process 4 0.884 detik (speedup 0.83). Nilai speedup di bawah 1 menunjukkan lebih lambat dari sequential.

Dari process 2 ke process 4, perubahan waktu rata-rata adalah -15.1%. Angka positif berarti bertambah lambat, angka negatif berarti lebih cepat. Saya tidak menganggap jumlah worker berbanding lurus dengan peningkatan kecepatan.

RSS tree peak tersampel rata-rata meningkat dari 66.58 MiB pada sequential menjadi 145.53 MiB untuk process 2 dan 222.41 MiB untuk process 4. Nilai ini adalah jumlah RSS proses pada snapshot bersamaan, bukan ukuran memori unik.

Variasi relatif waktu cukup besar pada sequential_1 (CV 16.5%), threading_2 (CV 14.6%), threading_4 (CV 38.3%), multiprocessing_2 (CV 22.0%). Saya mempertahankan semua run dan tidak membuang hasil lambat hanya agar rata-rata terlihat baik. Kondisi ini memerlukan pengulangan tambahan sebelum generalisasi.

### HEAVY

Rata-rata tercepat adalah multiprocessing 4 worker, dengan waktu 2.504 detik dan speedup 2.71. Process 2 membutuhkan 3.552 detik (speedup 1.91), sedangkan process 4 2.504 detik (speedup 2.71). Nilai speedup di bawah 1 menunjukkan lebih lambat dari sequential.

Dari process 2 ke process 4, perubahan waktu rata-rata adalah -29.5%. Angka positif berarti bertambah lambat, angka negatif berarti lebih cepat. Saya tidak menganggap jumlah worker berbanding lurus dengan peningkatan kecepatan.

RSS tree peak tersampel rata-rata meningkat dari 66.76 MiB pada sequential menjadi 147.60 MiB untuk process 2 dan 224.81 MiB untuk process 4. Nilai ini adalah jumlah RSS proses pada snapshot bersamaan, bukan ukuran memori unik.

Variasi relatif waktu cukup besar pada sequential_1 (CV 18.3%), threading_2 (CV 15.0%). Saya mempertahankan semua run dan tidak membuang hasil lambat hanya agar rata-rata terlihat baik. Kondisi ini memerlukan pengulangan tambahan sebelum generalisasi.

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

Tiga pengulangan adalah gambaran awal, bukan uji signifikansi. Input ringan yang selesai di bawah satu detik sensitif terhadap gangguan kecil. Urutan konfigurasi diputar, tetapi temperatur, background task, serta pemilihan core tidak dikendalikan atau dicatat. Saya belum membandingkan input lebih besar, chunk lain, shared memory, pool persistent, atau pipeline penyimpanan file.

Metode monitoring pada tahap ini berbeda dari notebook 01/02. Karena itu, perbandingan akhir hanya memakai CSV rangkaian ini; angka CPU/RAM lama tidak dicampur dengan kolom process tree baru. Error bar adalah sample SD, bukan confidence interval.

## Kesimpulan

Berdasarkan rata-rata yang terukur, konfigurasi tercepat adalah LIGHT: sequential; HEAVY: multiprocessing 4 worker. Saya membaca pilihan tersebut bersama biaya CPU/RAM dan variasi run. Hasil ini menunjukkan pilihan metode perlu disesuaikan dengan workload serta biaya koordinasi, bukan sekadar memilih jumlah worker terbanyak. Kesimpulan terbatas pada kondisi lokal ini.

## Referensi

- https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor
- https://docs.python.org/3.11/library/multiprocessing.html#contexts-and-start-methods
- https://psutil.readthedocs.io/
- https://www.cs.toronto.edu/~kriz/cifar.html
