# Seeding katalog NANEM

Jalankan dari root project dengan environment Django aktif. Jangan jalankan
proses fetch dan import bersamaan.

## Berkas yang digunakan

- `plant_seed_names.json`: 51 nama Indonesia, kategori, target nama ilmiah,
  query pencarian, dan catatan disambiguasi.
- `plant_selections.json`: keputusan final untuk setiap nama. Status
  `approved` memakai ID Perenual yang sudah diperiksa; status `local_only`
  memakai ID `null` dan alasan. Urutan kedua berkas harus sama.
- `plant_details_curated.json`: ringkasan field detail yang diperoleh dari
  Perenual dan aman disimpan di Git. Nilai kosong tidak diisi secara spekulatif.
- `plant_candidates.json`, `plant_details.json`, dan `seed_report.txt`:
  cache/laporan lokal yang di-ignore Git. File kandidat dan detail mentah dapat
  berisi URL gambar sementara; jangan commit atau bagikan API key.

## Ambil kandidat dan detail

Atur `PERENUAL_API_KEY` di `.env` atau environment. Fetch kandidat dari
endpoint `/api/v2/species-list`:

```bash
python manage.py seed_plants --fetch
```

Satu query baru memakai satu request; entri selesai dengan query yang sama
memakai cache, termasuk hasil kosong. `--limit N` membatasi ke N entri
pertama, bukan N request baru. `--refresh` memaksa request ulang untuk
entri yang diproses.

Setelah ID pada `plant_selections.json` ditinjau, ambil detail untuk ID
1–3000 sesuai cakupan paket gratis Perenual:

```bash
python manage.py seed_plants --fetch-details
```

Mode detail melewati entri `local_only` dan ID di atas 3000. Hasil lengkap
disimpan setelah setiap respons dan dipakai ulang saat command dijalankan
lagi. HTTP 401/403/429 menghentikan proses; 404 disimpan sebagai tidak
tersedia. Kedua mode fetch hanya menulis cache, bukan tabel `Plant`.
Mengambil detail baru **tidak otomatis** mengubah berkas kurasi yang dilacak
Git: tinjau respons dan tambahkan hanya field yang benar ke
`plant_details_curated.json`.

Dokumentasi resmi: https://perenual.com/docs/api
dan https://perenual.com/subscription-api-pricing

## Import offline

Jalankan migration, lalu cek import:

```bash
python manage.py migrate
python manage.py seed_plants --import-selected --dry-run
```

Dry-run melewati jalur tulis dalam transaksi yang dibatalkan. Setelah hasilnya
benar:

```bash
python manage.py seed_plants --import-selected
```

Import membaca manifest dan detail terkurasi. Bila ada cache detail lokal,
field yang tersedia di sana juga dipakai. Tidak ada API request saat import.
Semua 51 entri diproses, termasuk `local_only`. Tanaman dicocokkan menurut
nama NANEM atau ID Perenual, lalu diperbarui agar rerun tidak menduplikasi
data. ID utama `Plant.id` selalu milik NANEM. Satu batch dibatalkan bila
ada konflik.

Nilai `sunlight` disimpan sebagai list. Nilai `False` yang dikirim API
dibedakan dari `null` yang berarti tidak diketahui. URL gambar dengan
query bertanda waktu dan gambar `upgrade_access` ditolak; UI perlu memakai
placeholder bila `image_url` kosong.

Rentang suhu, kelembapan, curah hujan, dan kebutuhan ruang belum tersedia
dari data yang telah diverifikasi. Field itu tetap kosong sampai ditinjau
manual dengan sumber yang jelas. Nilai dukungan media tanam memakai default
model saat record baru dibuat; record lama tidak ditimpa untuk field ini.
Pada respons detail akun gratis yang diperiksa, field
`xTemperatureTolence` justru berisi pesan untuk upgrade ke Supreme, bukan
angka suhu. Jangan menyalin pesan tersebut menjadi nilai tanaman.

## Status kurasi

Saat ini 26 tanaman memakai ID Perenual dan 25 menjadi data NANEM lokal.
Pencarian ulang terhadap 11 query spesifik menyisakan tujuh query tanpa
hasil: Cabai rawit, Labu siam, Kacang panjang, Oyong, Kemangi, Daun salam,
dan Sukulen. Beberapa query lain menghasilkan tanaman yang salah nama
umum, misalnya `cherry tomato` menghasilkan Hosta hias. Keputusan per
tanaman dan alasannya ada di `plant_selections.json`.

Test:

```bash
python manage.py test apps.plants.test_seeding apps.plants.test_seed_workflow
```
