# Dataset CIFAR-10

Dataset dibuat oleh Alex Krizhevsky, Vinod Nair, dan Geoffrey Hinton. Sumber resmi dan deskripsi format: [halaman CIFAR-10](https://www.cs.toronto.edu/~kriz/cifar.html).

Repository menyertakan seluruh dataset dalam format binary resmi yang sudah diekstrak:

- `cifar-10-batches-bin/data_batch_1.bin` sampai `data_batch_5.bin`: 50.000 gambar training.
- `cifar-10-batches-bin/test_batch.bin`: 10.000 gambar test.
- `cifar-10-batches-bin/batches.meta.txt`: nama 10 kelas.

Setiap batch memuat 10.000 gambar RGB 32 x 32 piksel dengan ukuran 30.730.000 byte. Satu record terdiri dari satu byte label dan 3.072 byte kanal RGB. Gambar disimpan sebagai record binary, bukan 60.000 file PNG terpisah. Fungsi pembacanya tersedia di `src/dataset.py`.

Eksperimen yang dilaporkan memakai **10.000 gambar dari `data_batch_1.bin`**, bukan seluruh 60.000 gambar. Tidak dilakukan training AI atau klasifikasi; gambar hanya menjadi input transformasi untuk pengukuran performa.

Arsip sumber: [CIFAR-10 binary](https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz), MD5 resmi `c32a1d4ab5d03f1284b67883e8d87530`. Checksum arsip telah diverifikasi sebelum ekstraksi. Arsip cache tidak disertakan karena merupakan duplikat enam batch dan ukurannya melebihi batas file GitHub. `src/setup_dataset.py` dapat mengunduh dan memverifikasi kembali arsip tersebut.

`dataset_info.json` menyimpan informasi pemeriksaan dataset, sedangkan `sample_image.png` dan `sample_image_preview.png` merupakan contoh untuk inspeksi visual.

## Atribusi

Alex Krizhevsky (2009), *Learning Multiple Layers of Features from Tiny Images*. [Laporan teknis](https://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf).

Dataset merupakan materi pihak ketiga, bukan karya pembuat tugas ini. Halaman resmi meminta pengguna mengutip laporan teknis tersebut. Repository ini tidak menetapkan lisensi baru untuk dataset; hak atas materi sumber tetap milik pemegang haknya.
