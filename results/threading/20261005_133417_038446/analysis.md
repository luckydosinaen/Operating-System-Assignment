# Analisis Sequential dan Multithreading

Saya membandingkan sequential, 2 thread, dan 4 thread pada batch pertama CIFAR-10. Setiap kondisi dijalankan tiga kali secara default, dengan proses pengukuran baru, warm-up transformasi, serta parameter LIGHT/HEAVY yang sama. Sequential diukur ulang pada rangkaian ini dan menjadi pembagi speedup, sehingga angka notebook sebelumnya tidak dicampur ke perbandingan ini.

## Hasil

| Workload | Metode | Worker | Run | Waktu rata-rata (s) | SD (s) | Gambar/s | Speedup | CPU proses (%) | RSS peak tersampel rata-rata (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HEAVY | sequential | 1 | 3 | 3.676 | 0.225 | 2727.4 | 1.00 | 98.2 | 65.98 |
| HEAVY | threading | 2 | 3 | 2.704 | 0.020 | 3698.2 | 1.36 | 173.5 | 68.82 |
| HEAVY | threading | 4 | 3 | 2.626 | 0.097 | 3811.8 | 1.40 | 224.8 | 71.73 |
| LIGHT | sequential | 1 | 3 | 0.460 | 0.005 | 21763.6 | 1.00 | 98.6 | 65.88 |
| LIGHT | threading | 2 | 3 | 0.709 | 0.014 | 14117.9 | 0.65 | 124.3 | 67.56 |
| LIGHT | threading | 4 | 3 | 0.927 | 0.350 | 11699.3 | 0.50 | 147.5 | 70.12 |

## Pembacaan hasil

Pada LIGHT, rata-rata sequential 0.460 detik, 2 thread 0.709 detik, dan 4 thread 0.927 detik. Speedup 2 thread adalah 0.65 dan 4 thread 0.50. Rata-rata tercepat pada kondisi ini adalah sequential. Speedup di atas 1 berarti lebih cepat, sedangkan di bawah 1 berarti lebih lambat dibanding sequential.

Variasi waktu (SD/rata-rata) untuk sequential, 2 thread, dan 4 thread masing-masing 0.99%, 1.98%, dan 37.75%. Tiga pengulangan merupakan gambaran awal; saya belum melakukan uji signifikansi atau pengukuran terpisah untuk membuktikan penyebab selisih waktu.

Penambahan dari 2 ke 4 thread tidak menurunkan rata-rata waktu pada workload ini. Hasil ini memperlihatkan bahwa menambah worker tidak otomatis mempercepat pipeline.

Pada HEAVY, rata-rata sequential 3.676 detik, 2 thread 2.704 detik, dan 4 thread 2.626 detik. Speedup 2 thread adalah 1.36 dan 4 thread 1.40. Rata-rata tercepat pada kondisi ini adalah threading 4 worker. Speedup di atas 1 berarti lebih cepat, sedangkan di bawah 1 berarti lebih lambat dibanding sequential.

Variasi waktu (SD/rata-rata) untuk sequential, 2 thread, dan 4 thread masing-masing 6.13%, 0.74%, dan 3.69%. Tiga pengulangan merupakan gambaran awal; saya belum melakukan uji signifikansi atau pengukuran terpisah untuk membuktikan penyebab selisih waktu.

Penambahan dari 2 ke 4 thread menurunkan rata-rata waktu pada workload ini, tetapi saya tidak menganggap peningkatannya selalu linear dengan jumlah worker.

## Hubungan dengan Operating System

Thread pengolah berada dalam satu proses dan membaca dataset yang sama. Dengan begitu tidak ada proses pengolah baru atau penyalinan dataset antar-proses. Namun thread tetap membutuhkan stack, penjadwalan, antrean task, dan koordinasi output. Pipeline ini juga menyimpan sejumlah output sementara dalam chunk. Karena itu, perubahan RSS tidak dapat dianggap berasal dari stack thread saja.

CPython 3.11 biasa menggunakan Global Interpreter Lock (GIL) untuk eksekusi kode Python. Operasi library native dapat melepas GIL, sehingga saya tidak menyimpulkan semua pemrosesan gambar pasti serial hanya karena menggunakan Python. Sebaliknya, lebih banyak thread juga tidak menjamin paralelisme efektif. Overhead task, koordinasi hash pada thread utama, penantian hasil sesuai urutan, dan bagian yang memegang GIL merupakan penjelasan yang mungkin; eksperimen ini tidak mengisolasi kontribusi masing-masing.

Komputer pengujian memiliki 22 logical CPU. CPU proses 100% setara satu logical CPU dan bisa melebihi 100% jika CPU time beberapa thread bertambah secara bersamaan. CPU time yang lebih besar tidak selalu berarti pekerjaan selesai lebih cepat: pemakaian CPU harus dibaca bersama wall time. RSS adalah memori proses, bukan seluruh pemakaian RAM komputer.

## Validasi dan batasan

SHA-256 byte output sama antara sequential, 2 thread, dan 4 thread untuk workload yang sama pada seluruh pengulangan. Ini memeriksa kesamaan output, bukan kualitas gambar. Hash hanya diperbarui pada thread utama, dan future dikonsumsi sesuai urutan pengiriman agar urutan gambar tetap sama. Input dibuat read-only.

Satu task berisi 100 gambar; maksimum 2 x worker task belum dikonsumsi pada satu saat. Ini mencegah pembuatan 10.000 future sekaligus, tetapi buffering output dan chunk size tetap memengaruhi hasil. Kesimpulan berlaku untuk implementasi serta chunk size ini. Saya belum membandingkan ukuran chunk lain, pool persistent, atau output yang disimpan ke disk.

Timer threading mencakup startup/shutdown pool, submit/wait task, transformasi, konversi ke byte, hash, dan sampling RSS. Startup interpreter, load dataset, warm-up transformasi, dan penulisan laporan berada di luar timer. Warm-up tidak membuat pool thread yang dipakai pada run berikutnya; setiap run menggunakan pool baru. Sequential menggunakan batas timer yang sama untuk pekerjaan pengolahan dan hash.

RSS diambil setiap 100 output yang dikonsumsi dan setelah shutdown pool, bukan secara kontinu; puncak singkat bisa terlewat. Setiap run memakai proses baru untuk mengurangi carry-over memori. Kondisi tetap diputar urutannya, tetapi background task dan perubahan kondisi CPU masih mungkin memengaruhi waktu. Pengukuran di bawah satu detik terutama sensitif terhadap gangguan kecil dan resolusi CPU time. Sebelum generalisasi, diperlukan lebih banyak pengulangan atau input lebih besar.

## Kesimpulan sementara

Saya sudah memperoleh perbandingan sequential dan threading 2/4 worker pada dua workload. Saya memilih interpretasi berdasarkan waktu, resource, dan kesamaan output secara bersama. Hasil ini belum menjawab performa multiprocessing; langkah berikutnya adalah menguji 2 dan 4 process dengan pekerjaan serta validasi yang setara.

## Referensi

- https://docs.python.org/3.11/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
- https://docs.python.org/3.11/library/threading.html
- https://www.cs.toronto.edu/~kriz/cifar.html
