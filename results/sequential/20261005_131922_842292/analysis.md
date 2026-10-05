# Analisis Sequential Baseline

Pada tahap ini saya menguji pemrosesan gambar satu per satu sebagai baseline. Saya menggunakan batch pertama CIFAR-10 yang sama untuk LIGHT dan HEAVY, dengan parameter transformasi tetap. Hasil di bawah berasal dari run lokal yang tersimpan di folder ini.

## Hasil pengukuran

| Workload | Gambar/run | Run | Waktu rata-rata (s) | SD (s) | Throughput rata-rata (gambar/s) | CPU proses (%) | RSS maksimum tersampel (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| LIGHT | 10000 | 3 | 0.469 | 0.008 | 21305.8 | 95.4 | 67.09 |
| HEAVY | 10000 | 3 | 3.789 | 0.075 | 2639.8 | 96.9 | 67.10 |

## Pembacaan hasil

Rata-rata waktu HEAVY adalah 8.07 kali waktu LIGHT. Rasio ini membandingkan dua workload, bukan speedup metode paralel. HEAVY melakukan lebih banyak tahap transformasi, sehingga hasil tersebut saya baca dalam konteks jumlah operasi yang berbeda. Saya tidak menganggap HEAVY menghasilkan gambar yang lebih baik; pipeline ini sengaja dipakai sebagai pekerjaan eksperimen.

Variasi waktu LIGHT (SD/rata-rata) adalah 1.60%, sedangkan HEAVY 1.99%. Tiga pengulangan memberi gambaran variasi awal, tetapi belum cukup untuk memastikan penyebab perbedaan antar-run. Aktivitas aplikasi lain, scheduling, dan kondisi CPU merupakan kemungkinan, bukan penyebab yang sudah dibuktikan oleh pengukuran ini.

LIGHT selesai dalam waktu kurang dari satu detik pada eksperimen ini. Pada interval singkat, resolusi pencatatan CPU time dan gangguan kecil lebih terlihat dalam persentase CPU; angka sedikit di atas 100% tidak cukup untuk membuktikan adanya paralelisme pengolahan. Sebelum mengambil kesimpulan kuat tentang perbandingan metode, saya perlu menguji batch lebih besar atau menambah pengulangan secara konsisten pada semua metode.

CPU proses rata-rata tercatat 95.4% untuk LIGHT dan 96.9% untuk HEAVY. Skala yang saya gunakan menganggap 100% setara dengan satu logical CPU selama interval pengukuran. Komputer ini memiliki 22 logical CPU. Kolom kapasitas mesin pada CSV membagi CPU proses dengan jumlah logical CPU; nilai itu bukan pengukuran pemakaian CPU seluruh sistem. Saya juga tidak menyimpulkan proses selalu berjalan pada core fisik yang sama.

RSS maksimum tersampel adalah 67.09 MiB untuk LIGHT dan 67.10 MiB untuk HEAVY. RSS mencakup interpreter, library, dataset yang sudah dimuat, dan memori kerja. Nilai tersebut bukan hanya ukuran output gambar. Saya tidak menumpuk semua gambar hasil di RAM; setiap gambar hasil digunakan untuk hash kemudian diganti oleh hasil gambar berikutnya. Alokasi yang dipertahankan oleh library dan urutan run dapat memengaruhi RSS. Pengambilan sampel setiap 100 gambar juga dapat melewatkan puncak singkat, jadi angka ini bukan peak RAM mutlak.

Selisih maksimum RSS tersampel HEAVY dan LIGHT adalah 0.012 MiB. Saya tidak memakai selisih ini saja untuk menyimpulkan kebutuhan RAM kedua workload berbeda secara signifikan. Eksperimen ini memakai proses yang sama antar-run dan tidak mengukur alokasi setiap operasi secara terpisah. Grafik RAM memakai sumbu mulai dari nol agar perubahan kecil tidak terlihat berlebihan.

## Validasi dan batas pengukuran

Hash SHA-256 output konsisten antar-pengulangan untuk workload yang sama. Ini memeriksa reproduksibilitas byte output, bukan penilaian kualitas visual. Waktu mencakup konversi array ke gambar, transformasi, perhitungan hash output, loop, dan pemeriksaan RSS. Download, pemuatan dataset, warm-up, penulisan CSV, dan pembuatan grafik berada di luar timer. Overhead monitoring tetap ada; belum diukur terpisah.

LIGHT dan HEAVY dijalankan bergantian antar-pengulangan untuk mengurangi ketergantungan pada urutan, tetapi ini tidak menghilangkan pengaruh background task atau temperatur. Resize mengubah ukuran kerja menjadi 64 x 64; gambar input tetap berasal dari CIFAR-10 32 x 32. Efek memperbesar gambar ini harus dijaga sama ketika metode lain dibandingkan.

## Kesimpulan sementara

Saya sudah memperoleh baseline untuk dua tingkat pekerjaan. Speedup sequential ditetapkan 1,00 sebagai acuan. Saya belum bisa menyimpulkan threading atau multiprocessing lebih cepat karena keduanya belum diuji. Langkah berikutnya adalah menjalankan transformasi, jumlah gambar, dan kebijakan output yang sama dengan 2 dan 4 worker, lalu membandingkan waktu serta resource-nya.

## Sumber

- CIFAR-10: https://www.cs.toronto.edu/~kriz/cifar.html
- Pillow ImageFilter: https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html
- psutil: https://psutil.readthedocs.io/
- Python perf_counter: https://docs.python.org/3/library/time.html#time.perf_counter
